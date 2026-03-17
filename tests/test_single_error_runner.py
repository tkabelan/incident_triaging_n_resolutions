from __future__ import annotations

from app.schemas.error_records import RawErrorIngestionResponse, RawErrorRecord
from app.schemas.processed_errors import (
    ClassificationResolutionResult,
    GroundingEvidence,
    KbRetrievalResponse,
    ProcessedErrorRecord,
)
from app.workflows.error_processing import ErrorProcessingWorkflow


class FakeMcpClient:
    def ingest_raw_error(self, record: RawErrorRecord) -> RawErrorIngestionResponse:
        return RawErrorIngestionResponse(
            accepted=True,
            record=record,
            storage_reference="data/raw/manual_input-manual-1.json",
            message="ok",
        )

    def retrieve_kb(self, _processed_error: ProcessedErrorRecord) -> KbRetrievalResponse:
        evidence = [
            GroundingEvidence(
                kb_id="kb1",
                title="title",
                category="access_denied",
                resolution="check IAM",
                notes="note",
                score=0.95,
                source_type="learned",
                error_type="access_denied",
                exception_type="AccessDeniedException",
                severity="high",
                service_hint="s3",
                retryable=False,
                resolution_type="permission_fix",
            )
        ]
        return KbRetrievalResponse(evidence=evidence, direct_match=evidence[0])


class FakeNormalizer:
    def normalize_from_storage(self, raw_storage_reference: str):
        record = ProcessedErrorRecord(
            row_id="manual-1",
            source_file="manual_input",
            raw_storage_reference=raw_storage_reference,
            error_prefix="ValueError: AccessDeniedException",
            error_summary="AccessDeniedException: Forbidden",
            normalized_prefix="valueerror",
            category_hint="access_denied",
            keywords=["accessdeniedexception", "forbidden", "s3"],
            error_type="access_denied",
            exception_type="AccessDeniedException",
            severity="high",
            service_hint="s3",
            retryable=False,
            resolution_type="permission_fix",
        )
        return record, "data/processed/manual_input-manual-1.json"


class FakeRetriever:
    def build_classification_from_match(self, processed_error, match, evidence):
        return ClassificationResolutionResult(
            category=match.category,
            confidence=match.score,
            reasoning="Resolved directly from vector KB match.",
            proposed_resolution=match.resolution,
            evidence=evidence,
        )


class DummySettings:
    class Ingestion:
        error_data_dir = "error_data"
        default_csv_file = "error_prefix_counts.csv"

    class Search:
        enabled = True

    ingestion = Ingestion()
    search = Search()


def test_run_single_error_returns_step_trace() -> None:
    workflow = ErrorProcessingWorkflow(
        DummySettings(),
        mcp_client=FakeMcpClient(),
        normalizer=FakeNormalizer(),
        retriever=FakeRetriever(),
        classifier=None,
    )

    result = workflow.run_single_error("ValueError: AccessDeniedException Forbidden")

    assert result["status"] == "resolved_from_kb"
    assert "raw_ingestion_started" in result["steps"]
    assert "kb_retrieval_completed" in result["steps"]
    assert "resolved_from_kb" in result["steps"]
