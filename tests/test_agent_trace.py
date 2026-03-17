from __future__ import annotations

from app.schemas.error_records import RawErrorRecord
from app.schemas.processed_errors import (
    ClassificationResolutionResult,
    GroundingEvidence,
    VerificationResult,
)
from app.workflows.state import AgentWorkflowStateModel


def test_agent_trace_contains_frontend_ready_stage_details() -> None:
    raw_record = RawErrorRecord(
        row_id="manual-1",
        error_prefix="[CANNOT_OPEN_SOCKET]",
        error_message="Connection refused",
        source_file="manual_input",
    )
    state = AgentWorkflowStateModel.create(raw_record)
    state.status = "success_after_refinement"
    state.outcome_source = "refined_after_web_search"
    state.steps = [
        "raw_ingestion_completed",
        "kb_retrieval_completed",
        "primary_classification_completed",
        "verification_completed",
        "web_search_completed",
        "refinement_completed",
    ]
    state.evidence = [
        GroundingEvidence(
            kb_id="kb1",
            title="Known socket issue",
            category="network_error",
            resolution="restart listener",
            notes="note",
            score=0.78,
            source_type="seed",
            error_type="network_error",
            exception_type="SocketError",
            severity="high",
            service_hint="socket",
            retryable=True,
            resolution_type="service_restart",
        )
    ]
    state.classification_result = ClassificationResolutionResult(
        category="network_error",
        confidence=0.84,
        reasoning="grounded",
        proposed_resolution="restart listener",
        evidence=state.evidence,
    )
    state.verification_result = VerificationResult(
        passed=True,
        confidence=0.81,
        reasoning="verified",
        needs_web_search=False,
    )
    state.stage_details["web_search"].status = "pass"
    state.stage_details["planner"].status = "pass"
    state.next_action = "kb_update"
    state.decision_reason = "Verified answer can be written back."

    trace = state.to_result()["agent_trace"]

    assert trace["final_status"] == "success_after_refinement"
    assert trace["outcome_source"] == "refined_after_web_search"
    assert trace["kb_update_triggered"] is False
    assert trace["stages"]["chroma_db"]["evidence_count"] == 1
    assert trace["stages"]["planner"]["next_action"] == "kb_update"
    assert trace["stages"]["web_search"]["results"] == 0
    assert trace["stages"]["primary_llm"]["classification"] == "network_error"


def test_agent_trace_explains_direct_kb_resolution() -> None:
    raw_record = RawErrorRecord(
        row_id="manual-1",
        error_prefix="ValueError",
        error_message="Forbidden",
        source_file="manual_input",
    )
    state = AgentWorkflowStateModel.create(raw_record)
    state.status = "resolved_from_kb"

    trace = state.to_result()["agent_trace"]

    assert "resolved directly from the KB" in trace["branch_explanation"]


def test_agent_trace_explains_verified_primary_path() -> None:
    raw_record = RawErrorRecord(
        row_id="manual-1",
        error_prefix="ValueError",
        error_message="Forbidden",
        source_file="manual_input",
    )
    state = AgentWorkflowStateModel.create(raw_record)
    state.status = "success"
    state.verification_result = VerificationResult(
        passed=True,
        confidence=0.9,
        reasoning="Strongly verified.",
        needs_web_search=False,
    )

    trace = state.to_result()["agent_trace"]

    assert "passed verification strongly enough" in trace["branch_explanation"]
