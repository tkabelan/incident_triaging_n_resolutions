from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict

from app.schemas.error_records import RawErrorRecord
from app.schemas.processed_errors import (
    ClassificationResolutionResult,
    GroundingEvidence,
    ProcessedErrorRecord,
    VerificationResult,
    WebSearchResult,
)


class StageDetail(TypedDict, total=False):
    status: str
    confidence: float | None
    error: dict[str, Any] | None
    direct_match: bool
    evidence_count: int
    classification: str | None
    resolution: str | None
    passed: bool | None
    needs_web_search: bool | None
    reasoning: str | None
    results: int
    items: list[dict[str, Any]]


class AgentWorkflowState(TypedDict, total=False):
    row_id: str
    source_file: str
    raw_record: RawErrorRecord
    raw_storage_reference: str | None
    processed_storage_reference: str | None
    processed_error: ProcessedErrorRecord | None
    evidence: list[GroundingEvidence]
    direct_match: GroundingEvidence | None
    classification_result: ClassificationResolutionResult | None
    verification_result: VerificationResult | None
    web_search_results: list[WebSearchResult]
    kb_update_reference: str | None
    search_query: str | None
    planner_context: str | None
    next_action: str | None
    decision_reason: str | None
    reflection_context: str | None
    reflection_notes: list[str]
    classification_attempts: int
    refinement_attempts: int
    human_review_reason: str | None
    outcome_source: str | None
    memory_signals: dict[str, Any]
    status: str
    steps: list[str]
    stage_details: dict[str, StageDetail]
    error: dict[str, Any] | None


class StageDetailModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "not_run"
    confidence: float | None = None
    error: dict[str, Any] | None = None
    direct_match: bool | None = None
    evidence_count: int | None = None
    classification: str | None = None
    resolution: str | None = None
    passed: bool | None = None
    needs_web_search: bool | None = None
    reasoning: str | None = None
    results: int | None = None
    items: list[dict[str, Any]] = Field(default_factory=list)


class AgentWorkflowStateModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    row_id: str
    source_file: str
    raw_record: RawErrorRecord
    raw_storage_reference: str | None = None
    processed_storage_reference: str | None = None
    processed_error: ProcessedErrorRecord | None = None
    evidence: list[GroundingEvidence] = Field(default_factory=list)
    direct_match: GroundingEvidence | None = None
    classification_result: ClassificationResolutionResult | None = None
    verification_result: VerificationResult | None = None
    web_search_results: list[WebSearchResult] = Field(default_factory=list)
    kb_update_reference: str | None = None
    search_query: str | None = None
    planner_context: str | None = None
    next_action: str | None = None
    decision_reason: str | None = None
    reflection_context: str | None = None
    reflection_notes: list[str] = Field(default_factory=list)
    classification_attempts: int = 0
    refinement_attempts: int = 0
    human_review_reason: str | None = None
    outcome_source: str | None = None
    memory_signals: dict[str, Any] = Field(default_factory=dict)
    status: str = "in_progress"
    steps: list[str] = Field(default_factory=list)
    stage_details: dict[str, StageDetailModel] = Field(default_factory=dict)
    error: dict[str, Any] | None = None

    @classmethod
    def create(cls, raw_record: RawErrorRecord) -> "AgentWorkflowStateModel":
        return cls(
            row_id=raw_record.row_id,
            source_file=raw_record.source_file,
            raw_record=raw_record,
            stage_details=default_stage_detail_models(),
        )

    @classmethod
    def from_graph_state(cls, state: AgentWorkflowState) -> "AgentWorkflowStateModel":
        payload = dict(state)
        payload["stage_details"] = {
            name: StageDetailModel.model_validate(detail)
            for name, detail in payload.get("stage_details", {}).items()
        }
        return cls.model_validate(payload)

    def to_graph_state(self) -> AgentWorkflowState:
        return {
            "row_id": self.row_id,
            "source_file": self.source_file,
            "raw_record": self.raw_record,
            "raw_storage_reference": self.raw_storage_reference,
            "processed_storage_reference": self.processed_storage_reference,
            "processed_error": self.processed_error,
            "evidence": list(self.evidence),
            "direct_match": self.direct_match,
            "classification_result": self.classification_result,
            "verification_result": self.verification_result,
            "web_search_results": list(self.web_search_results),
            "kb_update_reference": self.kb_update_reference,
            "search_query": self.search_query,
            "planner_context": self.planner_context,
            "next_action": self.next_action,
            "decision_reason": self.decision_reason,
            "reflection_context": self.reflection_context,
            "reflection_notes": list(self.reflection_notes),
            "classification_attempts": self.classification_attempts,
            "refinement_attempts": self.refinement_attempts,
            "human_review_reason": self.human_review_reason,
            "outcome_source": self.outcome_source,
            "memory_signals": dict(self.memory_signals),
            "status": self.status,
            "steps": list(self.steps),
            "stage_details": {
                name: detail.model_dump(exclude_none=True)
                for name, detail in self.stage_details.items()
            },
            "error": self.error,
        }

    def to_result(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "status": self.status,
            "steps": list(self.steps),
            "stage_details": {
                name: detail.model_dump(exclude_none=True) for name, detail in self.stage_details.items()
            },
            "kb_match_found": bool(self.evidence),
            "kb_direct_match": self.direct_match is not None,
            "evidence_count": len(self.evidence),
            "raw_storage_reference": self.raw_storage_reference,
            "processed_storage_reference": self.processed_storage_reference,
            "processed_error": self.processed_error.model_dump() if self.processed_error else None,
            "classification": self.classification_result.model_dump() if self.classification_result else None,
            "verification": self.verification_result.model_dump() if self.verification_result else None,
            "web_search_results": [item.model_dump() for item in self.web_search_results],
            "kb_update_reference": self.kb_update_reference,
            "next_action": self.next_action,
            "decision_reason": self.decision_reason,
            "human_review_reason": self.human_review_reason,
            "reflection_notes": list(self.reflection_notes),
            "classification_attempts": self.classification_attempts,
            "refinement_attempts": self.refinement_attempts,
            "outcome_source": self.outcome_source,
            "memory_signals": dict(self.memory_signals),
            "error": self.error,
        }


def default_stage_detail_models() -> dict[str, StageDetailModel]:
    return {
        "chroma_db": StageDetailModel(),
        "planner": StageDetailModel(),
        "primary_llm": StageDetailModel(),
        "verification_llm": StageDetailModel(),
        "web_search": StageDetailModel(),
        "refinement_llm": StageDetailModel(),
        "reflection": StageDetailModel(),
        "human_review": StageDetailModel(),
    }


def new_graph_state(raw_record: RawErrorRecord) -> AgentWorkflowState:
    return AgentWorkflowStateModel.create(raw_record).to_graph_state()


def clone_graph_state(state: AgentWorkflowState) -> AgentWorkflowState:
    return AgentWorkflowStateModel.from_graph_state(state).to_graph_state()


def graph_state_to_result(state: AgentWorkflowState) -> dict[str, Any]:
    return AgentWorkflowStateModel.from_graph_state(state).to_result()
