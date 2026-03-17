from __future__ import annotations

from app.schemas.error_records import RawErrorRecord
from app.workflows.state import AgentWorkflowStateModel, clone_graph_state, new_graph_state


def test_new_graph_state_has_default_stage_details() -> None:
    raw_record = RawErrorRecord(
        row_id="manual-1",
        error_prefix="ValueError",
        error_message="ValueError: Forbidden",
        source_file="manual_input",
    )

    state = new_graph_state(raw_record)

    assert state["row_id"] == "manual-1"
    assert state["status"] == "in_progress"
    assert set(state["stage_details"]) == {
        "chroma_db",
        "planner",
        "primary_llm",
        "verification_llm",
        "web_search",
        "refinement_llm",
        "reflection",
        "human_review",
    }
    assert state["stage_details"]["primary_llm"]["status"] == "not_run"


def test_clone_graph_state_returns_independent_copy() -> None:
    raw_record = RawErrorRecord(
        row_id="manual-1",
        error_prefix="ValueError",
        error_message="ValueError: Forbidden",
        source_file="manual_input",
    )
    original = new_graph_state(raw_record)

    cloned = clone_graph_state(original)
    cloned["steps"].append("raw_ingestion_started")
    cloned["stage_details"]["primary_llm"]["status"] = "pass"

    assert original["steps"] == []
    assert original["stage_details"]["primary_llm"]["status"] == "not_run"


def test_state_model_serializes_result_shape() -> None:
    raw_record = RawErrorRecord(
        row_id="manual-1",
        error_prefix="ValueError",
        error_message="ValueError: Forbidden",
        source_file="manual_input",
    )
    state = AgentWorkflowStateModel.create(raw_record)

    result = state.to_result()

    assert result["row_id"] == "manual-1"
    assert result["kb_match_found"] is False
    assert result["classification"] is None
    assert result["stage_details"]["verification_llm"]["status"] == "not_run"
