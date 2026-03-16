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
            )
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
        record = ProcessedErrorRecord(
            row_id="1",
            source_file="errors.csv",
            raw_storage_reference=raw_storage_reference,
            error_prefix="ValueError",
            error_summary="Forbidden while reading S3",
            normalized_prefix="valueerror",
            category_hint="access_denied",
            keywords=["forbidden", "s3"],
            error_type="access_denied",
            exception_type="AccessDeniedException",
            severity="high",
            service_hint="s3",
            retryable=False,
            resolution_type="permission_fix",
        )
        return record, "data/processed/errors.csv-1.json"


class FakeRetriever:
    def __init__(self) -> None:
        self.upserted = []

    def retrieve(self, _processed_error: ProcessedErrorRecord):
        return [
            GroundingEvidence(
                kb_id="kb1",
                title="title",
                category="access_denied",
                resolution="check IAM",
                notes="seed note",
                score=0.92,
                source_type="learned",
                error_type="access_denied",
                exception_type="AccessDeniedException",
                severity="high",
                service_hint="s3",
                retryable=False,
                resolution_type="permission_fix",
            )
        ]

    def get_direct_match(self, evidence):
        return evidence[0]

    def build_classification_from_match(self, processed_error, match, evidence):
        return ClassificationResolutionResult(
            category=match.category,
            confidence=match.score,
            reasoning="Resolved directly from vector KB match.",
            proposed_resolution=match.resolution,
            evidence=evidence,
        )

    def upsert_verified_resolution(self, processed_error, classification):
        self.upserted.append((processed_error, classification))
        return "learned-kb-id"


class FailingClassifier:
    def classify_and_resolve(self, *_args, **_kwargs):
        raise AssertionError("Classifier should not run when direct KB match exists")


class DummySettings:
    class Ingestion:
        error_data_dir = "error_data"
        default_csv_file = "error_prefix_counts.csv"

    class Search:
        enabled = True

    ingestion = Ingestion()
    search = Search()


def test_workflow_short_circuits_on_strong_kb_match() -> None:
    retriever = FakeRetriever()
    workflow = ErrorProcessingWorkflow(
        DummySettings(),
        ingestion_service=FakeIngestionService(),
        mcp_client=FakeMcpClient(),
        normalizer=FakeNormalizer(),
        retriever=retriever,
        classifier=FailingClassifier(),
    )

    results = workflow.run_first_three_errors()

    assert results[0]["status"] == "resolved_from_kb"
    assert results[0]["classification"]["proposed_resolution"] == "check IAM"
    assert results[0]["verification"] is None
    assert results[0]["kb_update_reference"] is None
