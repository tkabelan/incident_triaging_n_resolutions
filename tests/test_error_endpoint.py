from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.app import create_app


class FakeWorkflow:
    def __init__(self, _settings) -> None:
        pass

    def run_single_error(self, error_text: str, *, row_id: str, source_file: str) -> dict:
        return {
            "row_id": row_id,
            "status": "success",
            "agent_trace": {
                "final_status": "success",
                "outcome_source": "llm_verified",
                "classification": "network_error",
                "resolution": "Restart the listener",
                "branch_explanation": "The primary classification passed verification strongly enough, so no web search or refinement was needed.",
                "kb_update_triggered": True,
                "kb_update_reference": "learned-kb-id",
                "kb_update_reason": "Verification passed and policy allows writing verified answers back to KB.",
                "steps": [
                    "raw_ingestion_completed",
                    "verification_completed",
                    "kb_update_completed",
                ],
                "stages": {
                    "chroma_db": {"status": "pass", "direct_match": False, "evidence_count": 1},
                    "planner": {"status": "pass", "next_action": "kb_update"},
                    "primary_llm": {"status": "pass", "confidence": 0.82},
                    "verification_llm": {"status": "pass", "confidence": 0.9, "passed": True},
                    "web_search": {"status": "skipped", "results": 0, "items": []},
                    "refinement_llm": {"status": "skipped", "attempts": 0},
                    "reflection": {"status": "not_run", "notes": []},
                    "human_review": {"status": "not_run", "reason": None},
                },
            },
            "classification": {
                "category": "network_error",
                "confidence": 0.82,
                "reasoning": "grounded",
                "proposed_resolution": "Restart the listener",
                "evidence": [],
            },
            "verification": {
                "passed": True,
                "confidence": 0.9,
                "reasoning": "verified",
                "needs_web_search": False,
            },
            "kb_update_reference": "learned-kb-id",
            "error": None,
        }


def test_single_error_endpoint_returns_agent_trace(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.errors.ErrorProcessingWorkflow", FakeWorkflow)
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/errors/process",
        json={
            "error_text": "[CANNOT_OPEN_SOCKET] Connection refused",
            "row_id": "manual-42",
            "source_file": "manual_input",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["row_id"] == "manual-42"
    assert payload["status"] == "success"
    assert payload["agent_trace"]["final_status"] == "success"
    assert payload["agent_trace"]["kb_update_triggered"] is True


def test_single_error_endpoint_rejects_empty_error_text() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/errors/process",
        json={"error_text": ""},
    )

    assert response.status_code == 422
