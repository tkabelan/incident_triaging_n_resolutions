from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from app.retrieval.local_embeddings import LocalHashEmbeddings
from app.schemas.processed_errors import (
    ClassificationResolutionResult,
    GroundingEvidence,
    KnowledgeBaseEntry,
    ProcessedErrorRecord,
)

logger = logging.getLogger(__name__)


class KnowledgeBaseRetriever:
    def __init__(
        self,
        vector_store: Any,
        seed_file: str | Path,
        max_results: int = 3,
        direct_match_threshold: float = 0.75,
    ) -> None:
        self._vector_store = vector_store
        self._seed_file = Path(seed_file)
        self._max_results = max_results
        self._direct_match_threshold = direct_match_threshold
        self._seed_if_empty()

    @classmethod
    def from_settings(cls, settings: Any) -> "KnowledgeBaseRetriever":
        from langchain_chroma import Chroma

        embeddings = _build_embeddings(settings)
        vector_store = Chroma(
            collection_name=settings.vector_store.collection_name,
            persist_directory=settings.vector_store.persist_directory,
            embedding_function=embeddings,
        )
        return cls(
            vector_store=vector_store,
            seed_file=settings.knowledge_base.seed_file,
            max_results=settings.knowledge_base.max_results,
            direct_match_threshold=settings.knowledge_base.direct_match_threshold,
        )

    def retrieve(self, processed_error: ProcessedErrorRecord) -> list[GroundingEvidence]:
        query = " ".join(
            [processed_error.error_prefix, processed_error.error_summary, *processed_error.keywords]
        )
        search_results = self._vector_store.similarity_search_with_relevance_scores(
            query,
            k=self._max_results,
            filter={"error_type": processed_error.error_type},
        )
        if not search_results:
            search_results = self._vector_store.similarity_search_with_relevance_scores(
                query,
                k=self._max_results,
            )

        evidence = [
            GroundingEvidence(
                kb_id=document.metadata["kb_id"],
                title=document.metadata["title"],
                category=document.metadata["category"],
                resolution=document.metadata["resolution"],
                notes=document.metadata["notes"],
                score=float(score),
                source_type=document.metadata.get("source_type", "seed"),
                error_type=document.metadata.get("error_type"),
                exception_type=document.metadata.get("exception_type"),
                severity=document.metadata.get("severity"),
                service_hint=document.metadata.get("service_hint"),
                retryable=document.metadata.get("retryable"),
                resolution_type=document.metadata.get("resolution_type"),
            )
            for document, score in search_results
        ]
        logger.info(
            "Retrieved %s grounding entries for raw error %s", len(evidence), processed_error.row_id
        )
        return evidence

    def get_direct_match(self, evidence: list[GroundingEvidence]) -> GroundingEvidence | None:
        if not evidence:
            return None
        best_match = max(evidence, key=lambda item: item.score)
        if best_match.score >= self._direct_match_threshold:
            return best_match
        return None

    def build_classification_from_match(
        self,
        processed_error: ProcessedErrorRecord,
        match: GroundingEvidence,
        evidence: list[GroundingEvidence],
    ) -> ClassificationResolutionResult:
        logger.info(
            "Using direct KB match %s for row %s with score %.3f",
            match.kb_id,
            processed_error.row_id,
            match.score,
        )
        return ClassificationResolutionResult(
            category=match.category,
            confidence=min(match.score, 1.0),
            reasoning=f"Resolved directly from vector KB match '{match.kb_id}' ({match.source_type}).",
            proposed_resolution=match.resolution,
            evidence=evidence,
        )

    def upsert_verified_resolution(
        self,
        processed_error: ProcessedErrorRecord,
        classification: ClassificationResolutionResult,
        memory_signals: dict[str, Any] | None = None,
    ) -> str:
        kb_id = self._build_kb_id(processed_error)
        text = (
            f"Error prefix: {processed_error.error_prefix}\n"
            f"Error summary: {processed_error.error_summary}\n"
            f"Category: {classification.category}\n"
            f"Resolution: {classification.proposed_resolution}\n"
            f"Reasoning: {classification.reasoning}"
        )
        metadata = {
            "kb_id": kb_id,
            "title": f"Learned resolution for {processed_error.normalized_prefix}",
            "category": classification.category,
            "resolution": classification.proposed_resolution,
            "notes": classification.reasoning,
            "source_type": "learned",
            "error_type": processed_error.error_type,
            "exception_type": processed_error.exception_type,
            "severity": processed_error.severity,
            "service_hint": processed_error.service_hint,
            "retryable": processed_error.retryable,
            "resolution_type": processed_error.resolution_type,
        }
        if memory_signals:
            metadata.update(_sanitize_metadata(memory_signals))
        self._vector_store.add_texts(
            texts=[text],
            metadatas=[_sanitize_metadata(metadata)],
            ids=[kb_id],
        )
        logger.info("Upserted verified resolution %s into vector KB", kb_id)
        return kb_id

    def _seed_if_empty(self) -> None:
        existing = self._vector_store.get()
        if existing.get("ids"):
            return

        entries = self._load_entries()
        texts = [self._to_document_text(entry) for entry in entries]
        metadatas = [
            _sanitize_metadata(
                {
                    "kb_id": entry.kb_id,
                    "title": entry.title,
                    "category": entry.category,
                    "resolution": entry.resolution,
                    "notes": entry.notes,
                    "source_type": entry.source_type,
                    "error_type": entry.error_type or entry.category,
                    "exception_type": entry.exception_type,
                    "severity": entry.severity or "medium",
                    "service_hint": entry.service_hint,
                    "retryable": entry.retryable,
                    "resolution_type": entry.resolution_type,
                }
            )
            for entry in entries
        ]
        ids = [entry.kb_id for entry in entries]
        self._vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        logger.info("Seeded ChromaDB collection with %s KB entries", len(entries))

    def _load_entries(self) -> list[KnowledgeBaseEntry]:
        payload = json.loads(self._seed_file.read_text(encoding="utf-8"))
        return [KnowledgeBaseEntry.model_validate(item) for item in payload]

    def _to_document_text(self, entry: KnowledgeBaseEntry) -> str:
        symptoms = ", ".join(entry.symptoms)
        return (
            f"Title: {entry.title}\n"
            f"Category: {entry.category}\n"
            f"Symptoms: {symptoms}\n"
            f"Resolution: {entry.resolution}\n"
            f"Notes: {entry.notes}"
        )

    def _build_kb_id(self, processed_error: ProcessedErrorRecord) -> str:
        fingerprint = hashlib.sha256(
            f"{processed_error.normalized_prefix}|{processed_error.error_summary}".encode("utf-8")
        ).hexdigest()[:12]
        return f"learned-{processed_error.normalized_prefix}-{fingerprint}"


def _build_embeddings(settings: Any) -> Any:
    provider = settings.models.embedding_provider.lower()
    if provider == "local_hash":
        return LocalHashEmbeddings(dimensions=settings.models.embedding_dimensions)
    if provider == "openai":
        import os

        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=settings.models.embedding_model,
            api_key=os.getenv(settings.models.openai_api_key_env_var),
        )
    raise ValueError(f"Unsupported embedding provider: {settings.models.embedding_provider}")


def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metadata.items() if value is not None}
