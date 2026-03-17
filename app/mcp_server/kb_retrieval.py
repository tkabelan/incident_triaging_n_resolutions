from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.retrieval.kb_retriever import KnowledgeBaseRetriever
from app.schemas.processed_errors import KbRetrievalResponse, ProcessedErrorRecord


KB_RETRIEVAL_TOOL = "kb.retrieve"


def create_kb_retrieval_handler(
    retriever: KnowledgeBaseRetriever,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def retrieve(payload: dict[str, Any]) -> dict[str, Any]:
        processed_error = ProcessedErrorRecord.model_validate(payload["processed_error"])
        evidence = retriever.retrieve(processed_error)
        direct_match = retriever.get_direct_match(evidence)
        return KbRetrievalResponse(
            evidence=evidence,
            direct_match=direct_match,
        ).model_dump()

    return retrieve
