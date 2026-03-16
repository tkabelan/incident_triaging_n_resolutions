from __future__ import annotations

import logging
import os
from typing import Any

from app.schemas.processed_errors import (
    ClassificationResolutionDraft,
    ClassificationResolutionResult,
    GroundingEvidence,
    ProcessedErrorRecord,
)


logger = logging.getLogger(__name__)


class PrimaryClassificationService:
    def __init__(self, structured_llm: Any) -> None:
        self._structured_llm = structured_llm

    @classmethod
    def from_settings(cls, settings: Any) -> "PrimaryClassificationService":
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.models.primary_llm,
            temperature=settings.models.temperature,
            api_key=os.getenv(settings.models.openai_api_key_env_var),
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You classify operational errors and propose grounded resolutions. "
                    "Use only the provided evidence. Keep confidence low when evidence is weak.",
                ),
                (
                    "human",
                    "Processed error:\n{processed_error}\n\nGrounding evidence:\n{evidence}\n\n"
                    "Return category, confidence, reasoning, and proposed_resolution.",
                ),
            ]
        )
        structured_llm = prompt | llm.with_structured_output(ClassificationResolutionDraft)
        return cls(structured_llm=structured_llm)

    def classify_and_resolve(
        self,
        processed_error: ProcessedErrorRecord,
        evidence: list[GroundingEvidence],
    ) -> ClassificationResolutionResult:
        draft = self._structured_llm.invoke(
            {
                "processed_error": processed_error.model_dump_json(indent=2),
                "evidence": _format_evidence(evidence),
            }
        )
        logger.info(
            "Produced classification for row %s with category %s",
            processed_error.row_id,
            draft.category,
        )
        return ClassificationResolutionResult(
            category=draft.category,
            confidence=draft.confidence,
            reasoning=draft.reasoning,
            proposed_resolution=draft.proposed_resolution,
            evidence=evidence,
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
