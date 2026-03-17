from __future__ import annotations

from app.schemas.error_records import RawErrorRecord
from app.schemas.processed_errors import GroundingEvidence, VerificationResult
from app.workflows.error_processing import ErrorProcessingWorkflow
from app.workflows.state import new_graph_state


class DummySettings:
    class Ingestion:
        error_data_dir = "error_data"
        default_csv_file = "error_prefix_counts.csv"

    class Search:
        enabled = True

    ingestion = Ingestion()
    search = Search()


def _workflow() -> ErrorProcessingWorkflow:
    return ErrorProcessingWorkflow(DummySettings(), mcp_client=object(), normalizer=object(), retriever=object())


def test_planner_prefers_direct_kb_resolution() -> None:
    workflow = _workflow()
    state = new_graph_state(
        RawErrorRecord(
            row_id="manual-1",
            error_prefix="ValueError",
            error_message="Forbidden",
            source_file="manual_input",
        )
    )
    state["planner_context"] = "after_kb_retrieval"
    state["direct_match"] = GroundingEvidence(
        kb_id="kb-1",
        title="Known issue",
        category="access_denied",
        resolution="Check IAM",
        notes="Known resolution",
        score=0.91,
        source_type="learned",
        error_type="access_denied",
        exception_type="AccessDeniedException",
        severity="high",
        service_hint="s3",
        retryable=False,
        resolution_type="permission_fix",
    )

    planned = workflow._planner_node(state)

    assert planned["next_action"] == "direct_kb_resolution"
    assert planned["stage_details"]["planner"]["status"] == "pass"


def test_planner_routes_to_web_search_when_verification_requests_it() -> None:
    workflow = _workflow()
    state = new_graph_state(
        RawErrorRecord(
            row_id="manual-1",
            error_prefix="SocketError",
            error_message="Connection refused",
            source_file="manual_input",
        )
    )
    state["planner_context"] = "after_verification"
    state["verification_result"] = VerificationResult(
        passed=False,
        confidence=0.31,
        reasoning="Need external evidence.",
        needs_web_search=True,
    )

    planned = workflow._planner_node(state)

    assert planned["next_action"] == "web_search"
    assert "external evidence" in planned["decision_reason"].lower()
