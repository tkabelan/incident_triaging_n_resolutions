from __future__ import annotations

import logging
import os
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.processed_errors import (
    ClassificationResolutionResult,
    GroundingEvidence,
    ProcessedErrorRecord,
    VerificationResult,
)

logger = logging.getLogger(__name__)


class VerificationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    confidence: float
    reasoning: str
    needs_web_search: bool


class VerificationService:
    def __init__(self, structured_llm: Any) -> None:
        self._structured_llm = structured_llm

    @classmethod
    def from_settings(cls, settings: Any) -> "VerificationService":
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.models.verification_llm,
            temperature=settings.models.temperature,
            api_key=os.getenv(settings.models.openai_api_key_env_var),
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You verify whether an incident classification and resolution are sufficiently grounded. "
                    "Be strict. If evidence is weak or missing, set needs_web_search to true.",
                ),
                (
                    "human",
                    "Processed error:\n{processed_error}\n\nClassification:\n{classification}\n\n"
                    "Grounding evidence:\n{evidence}\n\n"
                    "Return passed, confidence, reasoning, and needs_web_search.",
                ),
            ]
        )
        structured_llm = prompt | llm.with_structured_output(VerificationDraft)
        return cls(structured_llm=structured_llm)

    def verify(
        self,
        processed_error: ProcessedErrorRecord,
        classification: ClassificationResolutionResult,
        evidence: list[GroundingEvidence],
    ) -> VerificationResult:
        draft = self._structured_llm.invoke(
            {
                "processed_error": processed_error.model_dump_json(indent=2),
                "classification": classification.model_dump_json(indent=2),
                "evidence": _format_evidence(evidence),
            }
        )
        logger.info(
            "Verified classification for row %s with pass=%s",
            processed_error.row_id,
            draft.passed,
        )
        return VerificationResult(
            passed=draft.passed,
            confidence=draft.confidence,
            reasoning=draft.reasoning,
            needs_web_search=draft.needs_web_search,
        )


def _format_evidence(evidence: list[GroundingEvidence]) -> str:
    if not evidence:
        return "No grounding evidence found."
    return "\n\n".join(
        [
            (
                f"KB ID: {item.kb_id}\n"
                f"Title: {item.title}\n"
                f"Category: {item.category}\n"
                f"Resolution: {item.resolution}\n"
                f"Notes: {item.notes}\n"
                f"Score: {item.score}"
            )
            for item in evidence
        ]
    )
