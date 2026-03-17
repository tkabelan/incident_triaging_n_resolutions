from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from app.agents.classification_service import PrimaryClassificationService
from app.core.config import Settings
from app.ingestion.csv_ingestion import CsvErrorIngestionService
from app.mcp_client.client import LangChainMcpClient
from app.mcp_server.bootstrap import create_mcp_server
from app.normalization.error_normalizer import ErrorNormalizationService
from app.retrieval.kb_retriever import KnowledgeBaseRetriever
from app.schemas.error_records import RawErrorRecord
from app.storage.processed_error_storage import ProcessedErrorStorageService
from app.workflows.policy import WorkflowPolicy
from app.workflows.state import (
    AgentWorkflowState,
    clone_graph_state,
    graph_state_to_result,
    new_graph_state,
)

logger = logging.getLogger(__name__)
MAX_WEB_SEARCH_QUERY_LENGTH = 380


class ErrorProcessingWorkflow:
    def __init__(
        self,
        settings: Settings,
        *,
        ingestion_service: CsvErrorIngestionService | None = None,
        mcp_client: LangChainMcpClient | None = None,
        normalizer: ErrorNormalizationService | None = None,
        retriever: KnowledgeBaseRetriever | None = None,
        classifier: PrimaryClassificationService | None = None,
    ) -> None:
        self._settings = settings
        self._ingestion_service = ingestion_service or CsvErrorIngestionService()
        self._mcp_client = mcp_client or LangChainMcpClient(create_mcp_server())
        self._normalizer = normalizer or ErrorNormalizationService(
            ProcessedErrorStorageService(settings.storage.processed_data_dir)
        )
        self._retriever = retriever or KnowledgeBaseRetriever.from_settings(settings)
        self._classifier = classifier
        self._policy = WorkflowPolicy.from_settings(settings)
        self._progress_callback: Callable[[dict[str, Any]], None] | None = None
        self._graph = self._build_graph()

    def run_first_three_errors(self) -> list[dict]:
        csv_path = (
            Path(self._settings.ingestion.error_data_dir)
            / self._settings.ingestion.default_csv_file
        )
        logger.info("Starting end-to-end processing for first three errors from %s", csv_path)
        results: list[dict] = []
        for raw_record in self._ingestion_service.read_errors(csv_path):
            results.append(self._process_one_error(raw_record))
        logger.info("Completed end-to-end processing for %s errors", len(results))
        return results

    def run_single_error(
        self,
        error_text: str,
        *,
        row_id: str = "manual-1",
        source_file: str = "manual_input",
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        logger.info("Starting end-to-end processing for a single manual error")
        raw_record = RawErrorRecord(
            row_id=row_id,
            error_prefix=self._infer_error_prefix(error_text),
            error_message=error_text,
            source_file=source_file,
        )
        return self._process_one_error(raw_record, progress_callback=progress_callback)

    def _process_one_error(
        self,
        raw_record: Any,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        self._progress_callback = progress_callback
        try:
            self._emit_progress(
                title="📂 Parsing error",
                description="The agent accepted the input and is preparing the workflow.",
                stage="input",
            )
            final_state = self._graph.invoke(new_graph_state(raw_record))
        except Exception as exc:
            logger.exception("Failed processing error row %s", raw_record.row_id)
            final_state = new_graph_state(raw_record)
            final_state["error"] = self._format_error(exc)
            final_state["status"] = "failed"
            final_state["steps"].append("failed")
            self._emit_progress(
                title="⚠️ Workflow failed",
                description="The run stopped before a reliable answer was produced.",
                stage="workflow",
                status="failed",
            )
        finally:
            self._progress_callback = None

        return graph_state_to_result(final_state)

    def _build_web_search_query(
        self,
        processed_error: Any,
        classification: Any,
    ) -> str:
        parts = [
            processed_error.error_type,
            processed_error.exception_type or "",
            processed_error.service_hint or "",
            classification.category,
            processed_error.error_summary,
            " ".join(processed_error.keywords[:4]),
        ]
        query = " ".join(part.strip() for part in parts if part and part.strip())
        if len(query) <= MAX_WEB_SEARCH_QUERY_LENGTH:
            return query
        return query[:MAX_WEB_SEARCH_QUERY_LENGTH].rstrip()

    def _format_error(self, exc: Exception) -> dict[str, Any]:
        error_type = exc.__class__.__name__
        message = str(exc)
        is_rate_limited = error_type == "RateLimitError" or "429" in message
        return {
            "type": error_type,
            "message": message,
            "is_rate_limited": is_rate_limited,
            "retryable": is_rate_limited,
        }

    def _infer_error_prefix(self, error_text: str) -> str:
        first_line = error_text.strip().splitlines()[0] if error_text.strip() else "ManualError"
        if ":" in first_line:
            return first_line
        first_token = first_line.split()[0] if first_line.split() else "ManualError"
        return first_token

    def _build_graph(self):
        graph = StateGraph(AgentWorkflowState)
        graph.add_node("raw_ingestion", self._raw_ingestion_node)
        graph.add_node("normalization", self._normalization_node)
        graph.add_node("kb_retrieval", self._kb_retrieval_node)
        graph.add_node("planner", self._planner_node)
        graph.add_node("direct_kb_resolution", self._direct_kb_resolution_node)
        graph.add_node("primary_classification", self._primary_classification_node)
        graph.add_node("verification", self._verification_node)
        graph.add_node("kb_update", self._kb_update_node)
        graph.add_node("reflection", self._reflection_node)
        graph.add_node("human_review", self._human_review_node)
        graph.add_node("verification_failed", self._verification_failed_node)
        graph.add_node("web_search", self._web_search_node)
        graph.add_node("refinement", self._refinement_node)
        graph.add_node("refinement_verification", self._refinement_verification_node)
        graph.add_node("refinement_failed", self._refinement_failed_node)

        graph.add_edge(START, "raw_ingestion")
        graph.add_edge("raw_ingestion", "normalization")
        graph.add_edge("normalization", "kb_retrieval")
        graph.add_edge("kb_retrieval", "planner")
        graph.add_conditional_edges(
            "planner",
            self._route_after_planner,
            {
                "direct_kb_resolution": "direct_kb_resolution",
                "primary_classification": "primary_classification",
                "verification": "verification",
                "kb_update": "kb_update",
                "web_search": "web_search",
                "refinement": "refinement",
                "refinement_verification": "refinement_verification",
                "reflection": "reflection",
                "human_review": "human_review",
                "verification_failed": "verification_failed",
                "refinement_failed": "refinement_failed",
                "end": END,
            },
        )
        graph.add_edge("direct_kb_resolution", END)
        graph.add_edge("primary_classification", "planner")
        graph.add_edge("verification", "planner")
        graph.add_edge("reflection", "planner")
        graph.add_edge("human_review", END)
        graph.add_edge("verification_failed", END)
        graph.add_edge("web_search", "planner")
        graph.add_edge("refinement", "planner")
        graph.add_edge("refinement_verification", "planner")
        graph.add_edge("refinement_failed", END)
        graph.add_edge("kb_update", END)
        return graph.compile()

    def _raw_ingestion_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        updates = self._clone_state(state)
        self._emit_progress(
            title="📂 Capturing input",
            description="The raw error is being stored for audit and replay.",
            stage="raw_ingestion",
        )
        updates["steps"].extend(["raw_ingestion_started", "raw_ingestion_completed"])
        raw_response = self._mcp_client.ingest_raw_error(state["raw_record"])
        updates["raw_storage_reference"] = raw_response.storage_reference
        return updates

    def _normalization_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        updates = self._clone_state(state)
        self._emit_progress(
            title="🧹 Normalizing error",
            description="The agent is cleaning the message and extracting key fields.",
            stage="normalization",
        )
        updates["steps"].append("normalization_started")
        processed_record, processed_storage_reference = self._normalizer.normalize_from_storage(
            state["raw_storage_reference"]
        )
        updates["processed_error"] = processed_record
        updates["processed_storage_reference"] = processed_storage_reference
        updates["steps"].append("normalization_completed")
        return updates

    def _kb_retrieval_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        updates = self._clone_state(state)
        self._emit_progress(
            title="🗂️ Checking the knowledge base",
            description="The agent is looking for similar incidents and prior resolutions.",
            stage="kb_retrieval",
        )
        updates["steps"].append("kb_retrieval_started")
        retrieval = self._mcp_client.retrieve_kb(state["processed_error"])
        updates["evidence"] = retrieval.evidence
        updates["direct_match"] = retrieval.direct_match
        updates["planner_context"] = "after_kb_retrieval"
        updates["steps"].append("kb_retrieval_completed")
        updates["stage_details"]["chroma_db"]["status"] = "pass" if retrieval.evidence else "fail"
        updates["stage_details"]["chroma_db"]["confidence"] = (
            updates["direct_match"].score if updates["direct_match"] is not None else None
        )
        return updates

    def _planner_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        updates = self._clone_state(state)
        context = updates.get("planner_context")
        next_action, reason = self._decide_next_action(updates)
        updates["next_action"] = next_action
        updates["decision_reason"] = reason
        updates["steps"].append(f"planner_{context or 'unknown'}")
        updates["stage_details"]["planner"]["status"] = "pass"
        updates["stage_details"]["planner"]["reasoning"] = reason
        return updates

    def _direct_kb_resolution_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        updates = self._clone_state(state)
        self._emit_progress(
            title="📚 Reusing known answer",
            description="A strong KB match was found, so the agent can answer without new model calls.",
            stage="direct_kb_resolution",
        )
        classification = self._retriever.build_classification_from_match(
            state["processed_error"],
            state["direct_match"],
            state["evidence"],
        )
        updates["classification_result"] = classification
        updates["status"] = "resolved_from_kb"
        updates["outcome_source"] = "kb_direct"
        updates["steps"].append("resolved_from_kb")
        updates["stage_details"]["primary_llm"]["status"] = "skipped"
        updates["stage_details"]["verification_llm"]["status"] = "skipped"
        updates["stage_details"]["web_search"]["status"] = "skipped"
        updates["stage_details"]["refinement_llm"]["status"] = "skipped"
        return updates

    def _primary_classification_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        updates = self._clone_state(state)
        self._emit_progress(
            title="🧠 Calling classifier",
            description="The primary model is classifying the error and drafting a resolution.",
            stage="primary_classification",
        )
        updates["steps"].append("primary_classification_started")
        updates["classification_attempts"] = state.get("classification_attempts", 0) + 1
        try:
            classifier = self._get_classifier()
            classification = self._classify_with_optional_reflection(
                classifier,
                state["processed_error"],
                state["evidence"],
                self._latest_reflection_note(state),
            )
        except Exception as exc:
            self._emit_progress(
                title="🧠 Classifier failed",
                description="The primary model could not complete this attempt.",
                stage="primary_classification",
                status="failed",
            )
            updates["stage_details"]["primary_llm"]["status"] = "fail"
            updates["stage_details"]["primary_llm"]["error"] = self._format_error(exc)
            updates["error"] = self._format_error(exc)
            updates["planner_context"] = "after_primary_classification_failure"
            updates["reflection_context"] = "primary_classification"
            updates["steps"].append("primary_classification_failed")
            return updates
        updates["classification_result"] = classification
        updates["stage_details"]["primary_llm"]["status"] = "pass"
        updates["stage_details"]["primary_llm"]["confidence"] = classification.confidence
        updates["stage_details"]["primary_llm"]["error"] = None
        updates["error"] = None
        updates["planner_context"] = "after_primary_classification"
        updates["steps"].append("primary_classification_completed")
        return updates

    def _verification_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        updates = self._clone_state(state)
        self._emit_progress(
            title="✅ Verifying answer",
            description="A second model is checking whether the first answer is reliable.",
            stage="verification",
        )
        updates["steps"].append("verification_started")
        try:
            verification = self._mcp_client.verify_resolution(
                state["processed_error"],
                state["classification_result"],
                state["evidence"],
            )
        except Exception as exc:
            updates["stage_details"]["verification_llm"]["status"] = "fail"
            updates["stage_details"]["verification_llm"]["error"] = self._format_error(exc)
            updates["error"] = self._format_error(exc)
            updates["status"] = "failed"
            updates["steps"].append("failed")
            return updates
        updates["verification_result"] = verification
        updates["stage_details"]["verification_llm"]["status"] = (
            "pass" if verification.passed else "fail"
        )
        updates["stage_details"]["verification_llm"]["confidence"] = verification.confidence
        if verification.passed:
            updates["stage_details"]["verification_llm"]["error"] = None
            updates["error"] = None
        updates["planner_context"] = "after_verification"
        updates["steps"].append("verification_completed")
        return updates

    def _kb_update_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        updates = self._clone_state(state)
        self._emit_progress(
            title="📚 Updating knowledge base",
            description="The verified result is being saved for future reuse.",
            stage="kb_update",
        )
        updates["steps"].append("kb_update_started")
        updates["outcome_source"] = (
            "refined_after_web_search"
            if "refinement_completed" in updates["steps"]
            else "llm_verified"
        )
        updates["memory_signals"] = self._build_memory_signals(updates)
        updates["kb_update_reference"] = self._retriever.upsert_verified_resolution(
            state["processed_error"],
            state["classification_result"],
            updates["memory_signals"],
        )
        updates["steps"].append("kb_update_completed")
        if "web_search_completed" not in updates["steps"]:
            updates["stage_details"]["web_search"]["status"] = "skipped"
        if "refinement_completed" not in updates["steps"]:
            updates["stage_details"]["refinement_llm"]["status"] = "skipped"
        updates["status"] = (
            "success_after_refinement" if "refinement_completed" in updates["steps"] else "success"
        )
        return updates

    def _verification_failed_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        updates = self._clone_state(state)
        updates["stage_details"]["web_search"]["status"] = "skipped"
        updates["stage_details"]["refinement_llm"]["status"] = "skipped"
        updates["status"] = "verification_failed"
        return updates

    def _web_search_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        updates = self._clone_state(state)
        self._emit_progress(
            title="🔎 Searching the web",
            description="The agent is gathering external evidence because internal confidence was not enough.",
            stage="web_search",
        )
        updates["steps"].append("web_search_started")
        query = self._build_web_search_query(
            state["processed_error"], state["classification_result"]
        )
        updates["search_query"] = query
        try:
            web_results = self._mcp_client.web_search(query)
        except Exception as exc:
            updates["stage_details"]["web_search"]["status"] = "fail"
            updates["stage_details"]["web_search"]["error"] = self._format_error(exc)
            updates["error"] = self._format_error(exc)
            updates["status"] = "failed"
            updates["steps"].append("failed")
            return updates
        updates["web_search_results"] = web_results
        updates["stage_details"]["web_search"]["status"] = "pass" if web_results else "fail"
        if web_results:
            updates["stage_details"]["web_search"]["error"] = None
            updates["error"] = None
        updates["planner_context"] = "after_web_search"
        updates["steps"].append("web_search_completed")
        return updates

    def _refinement_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        updates = self._clone_state(state)
        self._emit_progress(
            title="🛠️ Refining the answer",
            description="The model is combining KB and web evidence into a stronger answer.",
            stage="refinement",
        )
        updates["steps"].append("refinement_started")
        updates["refinement_attempts"] = state.get("refinement_attempts", 0) + 1
        try:
            classifier = self._get_classifier()
            refined_classification = self._refine_with_optional_reflection(
                classifier,
                state["processed_error"],
                state["evidence"],
                state["web_search_results"],
                self._latest_reflection_note(state),
            )
        except Exception as exc:
            updates["stage_details"]["refinement_llm"]["status"] = "fail"
            updates["stage_details"]["refinement_llm"]["error"] = self._format_error(exc)
            updates["error"] = self._format_error(exc)
            updates["planner_context"] = "after_refinement_failure"
            updates["reflection_context"] = "refinement"
            updates["steps"].append("refinement_failed")
            return updates
        updates["classification_result"] = refined_classification
        updates["stage_details"]["refinement_llm"]["status"] = "pass"
        updates["stage_details"]["refinement_llm"]["confidence"] = refined_classification.confidence
        updates["stage_details"]["refinement_llm"]["error"] = None
        updates["error"] = None
        updates["planner_context"] = "after_refinement"
        updates["steps"].append("refinement_completed")
        return updates

    def _refinement_verification_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        updates = self._clone_state(state)
        updates["steps"].append("refinement_verification_started")
        try:
            refined_verification = self._mcp_client.verify_resolution(
                state["processed_error"],
                state["classification_result"],
                state["evidence"],
            )
        except Exception as exc:
            updates["stage_details"]["verification_llm"]["error"] = self._format_error(exc)
            updates["error"] = self._format_error(exc)
            updates["status"] = "failed"
            updates["steps"].append("failed")
            return updates
        updates["verification_result"] = refined_verification
        updates["stage_details"]["verification_llm"]["status"] = (
            "pass" if refined_verification.passed else "fail"
        )
        updates["stage_details"]["verification_llm"]["confidence"] = refined_verification.confidence
        if refined_verification.passed:
            updates["stage_details"]["verification_llm"]["error"] = None
            updates["error"] = None
        updates["planner_context"] = "after_refinement_verification"
        updates["steps"].append("refinement_verification_completed")
        return updates

    def _reflection_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        updates = self._clone_state(state)
        self._emit_progress(
            title="🔁 Retrying carefully",
            description="The agent is narrowing the next attempt after the previous step did not succeed.",
            stage="reflection",
        )
        context = state.get("reflection_context") or "unknown"
        note = self._build_reflection_note(state)
        updates["reflection_notes"].append(note)
        updates["steps"].append(f"reflection_{context}")
        updates["stage_details"]["reflection"]["status"] = "pass"
        updates["stage_details"]["reflection"]["reasoning"] = note
        updates["planner_context"] = (
            "after_primary_classification_reflection"
            if context == "primary_classification"
            else "after_refinement_reflection"
        )
        return updates

    def _human_review_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        updates = self._clone_state(state)
        self._emit_progress(
            title="🧑‍💻 Routing to human review",
            description="The workflow stopped safely because it could not reach a reliable autonomous answer.",
            stage="human_review",
            status="complete",
        )
        updates["status"] = "human_review_required"
        updates["human_review_reason"] = (
            state.get("decision_reason") or "Workflow escalated to human review."
        )
        updates["steps"].append("human_review_required")
        updates["stage_details"]["human_review"]["status"] = "pass"
        updates["stage_details"]["human_review"]["reasoning"] = updates["human_review_reason"]
        return updates

    def _refinement_failed_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        updates = self._clone_state(state)
        updates["status"] = "refinement_failed"
        return updates

    def _route_after_planner(self, state: AgentWorkflowState) -> str:
        if state.get("status") == "failed":
            return "end"
        return state.get("next_action", "end")

    def _decide_next_action(self, state: AgentWorkflowState) -> tuple[str, str]:
        if state.get("status") == "failed":
            return "end", "A prior node failed, so the graph will stop."

        context = state.get("planner_context")
        if context == "after_kb_retrieval":
            decision = self._policy.decide_after_kb_retrieval(state.get("direct_match"))
            return decision.action, decision.reason

        if context == "after_primary_classification":
            decision = self._policy.decide_after_primary_classification()
            return decision.action, decision.reason

        if context == "after_primary_classification_failure":
            decision = self._policy.decide_after_primary_classification_failure(
                state.get("classification_attempts", 0)
            )
            return decision.action, decision.reason

        if context == "after_primary_classification_reflection":
            return (
                "primary_classification",
                "Reflection completed, so the primary classifier will retry.",
            )

        if context == "after_verification":
            decision = self._policy.decide_after_verification(
                state.get("verification_result"),
                search_enabled=self._is_search_enabled(),
            )
            if decision.action == "verification_failed":
                terminal = self._policy.decide_after_verification_terminal_failure()
                return terminal.action, terminal.reason
            return decision.action, decision.reason

        if context == "after_web_search":
            decision = self._policy.decide_after_web_search()
            return decision.action, decision.reason

        if context == "after_refinement":
            decision = self._policy.decide_after_refinement()
            return decision.action, decision.reason

        if context == "after_refinement_failure":
            decision = self._policy.decide_after_refinement_failure(
                state.get("refinement_attempts", 0)
            )
            return decision.action, decision.reason

        if context == "after_refinement_reflection":
            return "refinement", "Reflection completed, so refinement will retry."

        if context == "after_refinement_verification":
            decision = self._policy.decide_after_refinement_verification(
                state.get("verification_result")
            )
            if decision.action == "refinement_failed":
                terminal = self._policy.decide_after_refinement_terminal_failure()
                return terminal.action, terminal.reason
            return decision.action, decision.reason

        return "end", "No planner context was set, so the graph will stop."

    def _clone_state(self, state: AgentWorkflowState) -> AgentWorkflowState:
        return clone_graph_state(state)

    def _get_classifier(self) -> PrimaryClassificationService:
        if self._classifier is None:
            self._classifier = PrimaryClassificationService.from_settings(self._settings)
        return self._classifier

    def _classify_with_optional_reflection(
        self,
        classifier: Any,
        processed_error: Any,
        evidence: list[Any],
        reflection_note: str | None,
    ) -> Any:
        if reflection_note:
            return classifier.classify_and_resolve(
                processed_error,
                evidence,
                reflection_note=reflection_note,
            )
        return classifier.classify_and_resolve(processed_error, evidence)

    def _refine_with_optional_reflection(
        self,
        classifier: Any,
        processed_error: Any,
        evidence: list[Any],
        web_search_results: list[Any],
        reflection_note: str | None,
    ) -> Any:
        if reflection_note:
            return classifier.refine_with_web_search(
                processed_error,
                evidence,
                web_search_results,
                reflection_note=reflection_note,
            )
        return classifier.refine_with_web_search(processed_error, evidence, web_search_results)

    def _is_search_enabled(self) -> bool:
        search_settings = getattr(self._settings, "search", None)
        return getattr(search_settings, "enabled", True)

    def _latest_reflection_note(self, state: AgentWorkflowState) -> str | None:
        notes = state.get("reflection_notes", [])
        return notes[-1] if notes else None

    def _build_reflection_note(self, state: AgentWorkflowState) -> str:
        context = state.get("reflection_context") or "unknown"
        error = state.get("error") or {}
        if context == "primary_classification":
            return (
                "Retry primary classification with a narrower grounded answer and explicit use of evidence only. "
                f"Previous issue: {error.get('message', 'classification failure')}."
            )
        if context == "refinement":
            return (
                "Retry refinement using concise synthesis of KB and web evidence with explicit grounding. "
                f"Previous issue: {error.get('message', 'refinement failure')}."
            )
        return "Retry with a narrower grounded answer."

    def _build_memory_signals(self, state: AgentWorkflowState) -> dict[str, Any]:
        verification = state.get("verification_result")
        web_results = state.get("web_search_results", [])
        evidence = state.get("evidence", [])
        return {
            "outcome_source": state.get("outcome_source"),
            "final_status": state.get("status"),
            "verification_confidence": verification.confidence if verification else None,
            "verification_passed": verification.passed if verification else None,
            "needs_web_search": verification.needs_web_search if verification else None,
            "web_result_count": len(web_results),
            "used_web_search": bool(web_results),
            "classification_attempts": state.get("classification_attempts", 0),
            "refinement_attempts": state.get("refinement_attempts", 0),
            "reflection_count": len(state.get("reflection_notes", [])),
            "evidence_kb_ids": ",".join(item.kb_id for item in evidence) or None,
            "has_direct_match": state.get("direct_match") is not None,
        }

    def _emit_progress(
        self,
        *,
        title: str,
        description: str,
        stage: str,
        status: str = "running",
    ) -> None:
        if self._progress_callback is None:
            return
        self._progress_callback(
            {
                "type": "progress",
                "stage": stage,
                "status": status,
                "title": title,
                "description": description,
            }
        )
