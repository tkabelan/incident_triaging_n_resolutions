from __future__ import annotations

from app.schemas.error_records import RawErrorIngestionResponse, RawErrorRecord
from app.schemas.processed_errors import (
    ClassificationResolutionResult,
    GroundingEvidence,
    KbRetrievalResponse,
    ProcessedErrorRecord,
    VerificationResult,
)
from app.workflows.error_processing import ErrorProcessingWorkflow


class FakeMcpClient:
    def ingest_raw_error(self, record: RawErrorRecord) -> RawErrorIngestionResponse:
        return RawErrorIngestionResponse(
            accepted=True,
            record=record,
            storage_reference=f"data/raw/{record.source_file}-{record.row_id}.json",
            message="ok",
        )

    def retrieve_kb(self, _processed_error: ProcessedErrorRecord) -> KbRetrievalResponse:
        return KbRetrievalResponse(
            evidence=[
                GroundingEvidence(
                    kb_id="kb1",
                    title="title",
                    category="network_error",
                    resolution="restart listener",
                    notes="note",
                    score=0.4,
                    source_type="seed",
                    error_type="network_error",
                    exception_type="SocketError",
                    severity="high",
                    service_hint="socket",
                    retryable=True,
                    resolution_type="service_restart",
                )
            ],
            direct_match=None,
        )

    def verify_resolution(self, _processed_error, classification, _evidence) -> VerificationResult:
        return VerificationResult(
            passed=True,
            confidence=classification.confidence,
            reasoning="good enough",
            needs_web_search=False,
        )


class FakeNormalizer:
    def normalize_from_storage(self, raw_storage_reference: str):
        record = ProcessedErrorRecord(
            row_id="1",
            source_file="errors.csv",
            raw_storage_reference=raw_storage_reference,
            error_prefix="[CANNOT_OPEN_SOCKET]",
            error_summary="Connection refused",
            normalized_prefix="cannot_open_socket",
            category_hint="network_error",
            keywords=["socket", "connection", "refused"],
            error_type="network_error",
            exception_type="SocketError",
            severity="high",
            service_hint="socket",
            retryable=True,
            resolution_type="service_restart",
        )
        return record, "data/processed/errors.csv-1.json"


class RetryClassifier:
    def __init__(self) -> None:
        self.calls = 0

    def classify_and_resolve(self, _processed_error, _evidence, reflection_note=None):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary classification failure")
        assert reflection_note is not None
        return ClassificationResolutionResult(
            category="network_error",
            confidence=0.82,
            reasoning="retried successfully",
            proposed_resolution="restart the listener",
            evidence=[],
        )


class FailingClassifier:
    def __init__(self) -> None:
        self.calls = 0

    def classify_and_resolve(self, _processed_error, _evidence, reflection_note=None):
        self.calls += 1
        raise RuntimeError("persistent classification failure")


class TrackingRetriever:
    def __init__(self) -> None:
        self.last_memory_signals = None

    def build_classification_from_match(self, processed_error, match, evidence):
        raise AssertionError("direct KB path should not be used")

    def upsert_verified_resolution(self, _processed_error, _classification, memory_signals=None):
        self.last_memory_signals = memory_signals
        return "learned-kb-id"


class DummySettings:
    class Ingestion:
        error_data_dir = "error_data"
        default_csv_file = "error_prefix_counts.csv"

    class Search:
        enabled = True

    class Workflow:
        allow_direct_kb_resolution = True
        verification_confidence_threshold = 0.6
        refinement_confidence_threshold = 0.7
        use_web_search_on_low_confidence = True
        update_kb_on_verified = True
        max_classification_retries = 1
        max_refinement_retries = 1
        route_failed_verification_to_human_review = True
        route_failed_refinement_to_human_review = True

    ingestion = Ingestion()
    search = Search()
    workflow = Workflow()


def test_workflow_retries_after_reflection_and_records_memory_signals() -> None:
    retriever = TrackingRetriever()
    workflow = ErrorProcessingWorkflow(
        DummySettings(),
        mcp_client=FakeMcpClient(),
        normalizer=FakeNormalizer(),
        retriever=retriever,
        classifier=RetryClassifier(),
    )

    result = workflow.run_single_error("[CANNOT_OPEN_SOCKET] Connection refused")

    assert result["status"] == "success"
    assert "reflection_primary_classification" in result["steps"]
    assert result["classification_attempts"] == 2
    assert result["reflection_notes"]
    assert retriever.last_memory_signals["classification_attempts"] == 2
    assert retriever.last_memory_signals["reflection_count"] == 1
    assert retriever.last_memory_signals["outcome_source"] == "llm_verified"


def test_workflow_routes_to_human_review_after_retry_budget_is_exhausted() -> None:
    workflow = ErrorProcessingWorkflow(
        DummySettings(),
        mcp_client=FakeMcpClient(),
        normalizer=FakeNormalizer(),
        retriever=TrackingRetriever(),
        classifier=FailingClassifier(),
    )

    result = workflow.run_single_error("[CANNOT_OPEN_SOCKET] Connection refused")

    assert result["status"] == "human_review_required"
    assert result["human_review_reason"] is not None
    assert result["classification_attempts"] == 2
