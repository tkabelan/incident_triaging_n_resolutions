from __future__ import annotations

from app.schemas.error_records import RawErrorIngestionResponse, RawErrorRecord
from app.schemas.processed_errors import (
    ClassificationResolutionResult,
    GroundingEvidence,
    KbRetrievalResponse,
    ProcessedErrorRecord,
    VerificationResult,
    WebSearchResult,
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
    def __init__(self) -> None:
        self.verify_calls = 0

    def ingest_raw_error(self, record: RawErrorRecord) -> RawErrorIngestionResponse:
        return RawErrorIngestionResponse(
            accepted=True,
            record=record,
            storage_reference=f"data/raw/{record.source_file}-{record.row_id}.json",
            message="ok",
        )

    def verify_resolution(self, _processed_error, _classification, _evidence) -> VerificationResult:
        self.verify_calls += 1
        if self.verify_calls == 1:
            return VerificationResult(
                passed=False,
                confidence=0.32,
                reasoning="Grounding is weak.",
                needs_web_search=True,
            )
        return VerificationResult(
            passed=True,
            confidence=0.81,
            reasoning="Refined answer is now grounded well enough.",
            needs_web_search=False,
        )

    def retrieve_kb(self, _processed_error: ProcessedErrorRecord) -> KbRetrievalResponse:
        return KbRetrievalResponse(
            evidence=[
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
            ],
            direct_match=None,
        )

    def web_search(self, _query: str) -> list[WebSearchResult]:
        return [
            WebSearchResult(
                title="Result",
                url="https://example.com",
                content="Useful remediation note",
                score=0.8,
            )
        ]


class FakeNormalizer:
    def normalize_from_storage(self, raw_storage_reference: str):
        record = ProcessedErrorRecord(
            row_id="1",
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
        return record, "data/processed/errors.csv-1.json"


class FakeRetriever:
    def upsert_verified_resolution(
        self, _processed_error, _classification, memory_signals=None
    ) -> str:
        return "learned-kb-id"


class FakeClassifier:
    def classify_and_resolve(self, _processed_error: ProcessedErrorRecord, _evidence):
        return ClassificationResolutionResult(
            category="access_denied",
            confidence=0.8,
            reasoning="grounded",
            proposed_resolution="fix it",
            evidence=[],
        )

    def refine_with_web_search(
        self, _processed_error: ProcessedErrorRecord, _evidence, _web_results
    ):
        return ClassificationResolutionResult(
            category="access_denied",
            confidence=0.87,
            reasoning="Refined with web evidence.",
            proposed_resolution="check IAM and verify service connectivity",
            evidence=[],
        )


class DummySettings:
    class Ingestion:
        error_data_dir = "error_data"
        default_csv_file = "error_prefix_counts.csv"

    class Search:
        enabled = True

    ingestion = Ingestion()
    search = Search()


def test_workflow_runs_web_search_when_verification_fails() -> None:
    workflow = ErrorProcessingWorkflow(
        DummySettings(),
        ingestion_service=FakeIngestionService(),
        mcp_client=FakeMcpClient(),
        normalizer=FakeNormalizer(),
        retriever=FakeRetriever(),
        classifier=FakeClassifier(),
    )

    results = workflow.run_csv_errors()

    assert results[0]["status"] == "success_after_refinement"
    assert "web_search_completed" in results[0]["steps"]
    assert results[0]["stage_details"]["web_search"]["status"] == "pass"
    assert len(results[0]["web_search_results"]) == 1
