from __future__ import annotations

from app.schemas.error_records import RawErrorIngestionResponse, RawErrorRecord
from app.schemas.processed_errors import (
    ClassificationResolutionResult,
    GroundingEvidence,
    ProcessedErrorRecord,
)
from app.workflows.error_processing import ErrorProcessingWorkflow


class FakeIngestionService:
    def read_errors(self, _csv_path):
        return [
            RawErrorRecord(
                row_id="1",
                error_prefix="ValueError",
                error_message="first error",
                source_file="errors.csv",
            ),
            RawErrorRecord(
                row_id="2",
                error_prefix="ExecutionError",
                error_message="second error",
                source_file="errors.csv",
            ),
        ]


class FakeMcpClient:
    def ingest_raw_error(self, record: RawErrorRecord) -> RawErrorIngestionResponse:
        return RawErrorIngestionResponse(
            accepted=True,
            record=record,
            storage_reference=f"data/raw/{record.source_file}-{record.row_id}.json",
            message="ok",
        )


class FakeNormalizer:
    def normalize_from_storage(self, raw_storage_reference: str):
        row_id = raw_storage_reference.split("-")[-1].split(".")[0]
        record = ProcessedErrorRecord(
            row_id=row_id,
            source_file="errors.csv",
            raw_storage_reference=raw_storage_reference,
            error_prefix="ValueError",
            error_summary="summary",
            normalized_prefix="valueerror",
            category_hint="access_denied",
            keywords=["forbidden"],
            error_type="access_denied",
            exception_type="AccessDeniedException",
            severity="high",
            service_hint="s3",
            retryable=False,
            resolution_type="permission_fix",
        )
        return record, f"data/processed/errors.csv-{row_id}.json"


class FakeRetriever:
    def retrieve(self, _processed_error: ProcessedErrorRecord):
        return [
            GroundingEvidence(
                kb_id="kb1",
                title="title",
                category="access_denied",
                resolution="fix it",
                notes="note",
                score=0.9,
                source_type="seed",
                error_type="access_denied",
                exception_type="AccessDeniedException",
                severity="high",
                service_hint="s3",
                retryable=False,
                resolution_type="permission_fix",
            )
        ]


class RateLimitError(Exception):
    pass


class FakeClassifier:
    def classify_and_resolve(self, processed_error: ProcessedErrorRecord, _evidence):
        if processed_error.row_id == "1":
            raise RateLimitError("429 Too Many Requests")
        return ClassificationResolutionResult(
            category="access_denied",
            confidence=0.8,
            reasoning="grounded",
            proposed_resolution="fix it",
            evidence=[],
        )


class DummySettings:
    class Ingestion:
        error_data_dir = "error_data"
        default_csv_file = "error_prefix_counts.csv"

    ingestion = Ingestion()


def test_workflow_records_rate_limit_and_continues() -> None:
    workflow = ErrorProcessingWorkflow(
        DummySettings(),
        ingestion_service=FakeIngestionService(),
        mcp_client=FakeMcpClient(),
        normalizer=FakeNormalizer(),
        retriever=FakeRetriever(),
        classifier=FakeClassifier(),
    )

    results = workflow.run_first_three_errors()

    assert len(results) == 2
    assert results[0]["status"] == "failed"
    assert results[0]["error"]["is_rate_limited"] is True
    assert results[1]["status"] == "success"
