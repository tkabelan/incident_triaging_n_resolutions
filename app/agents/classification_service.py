from __future__ import annotations

import logging
import os
from typing import Any

from app.classification.taxonomy import ClassificationTaxonomy, load_classification_taxonomy
from app.schemas.processed_errors import (
    ClassificationResolutionDraft,
    ClassificationResolutionResult,
    GroundingEvidence,
    ProcessedErrorRecord,
    WebSearchResult,
)

logger = logging.getLogger(__name__)


class PrimaryClassificationService:
    def __init__(
        self,
        structured_llm: Any,
        taxonomy: ClassificationTaxonomy | None = None,
    ) -> None:
        self._structured_llm = structured_llm
        self._taxonomy = taxonomy

    @classmethod
    def from_settings(cls, settings: Any) -> "PrimaryClassificationService":
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        taxonomy = load_classification_taxonomy(settings.classification.taxonomy_file)
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
                    "Use only the provided evidence. Keep confidence low when evidence is weak.\n\n"
                    "{taxonomy_rules}",
                ),
                (
                    "human",
                    "Processed error:\n{processed_error}\n\nGrounding evidence:\n{evidence}\n\n"
                    "Return category, main_category, subcategory, confidence, reasoning, and proposed_resolution.",
                ),
            ]
        )
        structured_llm = prompt | llm.with_structured_output(ClassificationResolutionDraft)
        return cls(structured_llm=structured_llm, taxonomy=taxonomy)

    def classify_and_resolve(
        self,
        processed_error: ProcessedErrorRecord,
        evidence: list[GroundingEvidence],
        reflection_note: str | None = None,
    ) -> ClassificationResolutionResult:
        draft = self._invoke(
            processed_error=processed_error,
            evidence_text=_format_evidence(evidence),
            reflection_note=reflection_note,
        )
        logger.info(
            "Produced classification for row %s with category %s",
            processed_error.row_id,
            draft.category,
        )
        return ClassificationResolutionResult(
            category=draft.category,
            main_category=self._resolve_main_category(draft),
            subcategory=self._resolve_subcategory(draft),
            confidence=draft.confidence,
            reasoning=draft.reasoning,
            proposed_resolution=draft.proposed_resolution,
            evidence=evidence,
        )

    def refine_with_web_search(
        self,
        processed_error: ProcessedErrorRecord,
        evidence: list[GroundingEvidence],
        web_results: list[WebSearchResult],
        reflection_note: str | None = None,
    ) -> ClassificationResolutionResult:
        draft = self._invoke(
            processed_error=processed_error,
            evidence_text=_format_evidence(evidence)
            + "\n\nExternal web evidence:\n"
            + _format_web_results(web_results),
            reflection_note=reflection_note,
        )
        logger.info(
            "Produced refined classification for row %s with category %s",
            processed_error.row_id,
            draft.category,
        )
        return ClassificationResolutionResult(
            category=draft.category,
            main_category=self._resolve_main_category(draft),
            subcategory=self._resolve_subcategory(draft),
            confidence=draft.confidence,
            reasoning=draft.reasoning,
            proposed_resolution=draft.proposed_resolution,
            evidence=evidence,
        )

    def _invoke(
        self,
        *,
        processed_error: ProcessedErrorRecord,
        evidence_text: str,
        reflection_note: str | None = None,
    ) -> ClassificationResolutionDraft:
        if reflection_note:
            evidence_text = evidence_text + "\n\nReflection guidance:\n" + reflection_note
        return self._structured_llm.invoke(
            {
                "processed_error": processed_error.model_dump_json(indent=2),
                "evidence": evidence_text,
                "taxonomy_rules": self._taxonomy.prompt_text() if self._taxonomy else "",
            }
        )

    def _resolve_main_category(self, draft: ClassificationResolutionDraft) -> str | None:
        if not self._taxonomy:
            return draft.main_category
        resolved_main, _ = self._taxonomy.resolve(
            category=draft.category,
            main_category=draft.main_category,
            subcategory=draft.subcategory,
        )
        return resolved_main

    def _resolve_subcategory(self, draft: ClassificationResolutionDraft) -> str | None:
        if not self._taxonomy:
            return draft.subcategory
        _, resolved_subcategory = self._taxonomy.resolve(
            category=draft.category,
            main_category=draft.main_category,
            subcategory=draft.subcategory,
        )
        return resolved_subcategory


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


def _format_web_results(results: list[WebSearchResult]) -> str:
    if not results:
        return "No web search results found."
    return "\n\n".join(
        [
            (
                f"Title: {item.title}\n"
                f"URL: {item.url}\n"
                f"Content: {item.content}\n"
                f"Score: {item.score}"
            )
            for item in results
        ]
    )
