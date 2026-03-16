from dataclasses import dataclass

from app.retrieval.kb_retriever import KnowledgeBaseRetriever
from app.schemas.processed_errors import ProcessedErrorRecord


@dataclass
class FakeDocument:
    metadata: dict


class FakeVectorStore:
    def __init__(self) -> None:
        self.seeded = False

    def get(self) -> dict:
        return {"ids": [] if not self.seeded else ["kb-access-denied-s3"]}

    def add_texts(self, texts, metadatas, ids) -> None:
        self.seeded = True
        self.texts = texts
        self.metadatas = metadatas
        self.ids = ids

    def similarity_search_with_relevance_scores(self, query, k, filter):
        if filter is not None:
            assert filter == {"error_type": "access_denied"}
        return [
            (
                FakeDocument(
                    metadata={
                        "kb_id": "kb-access-denied-s3",
                        "title": "S3 access denied during file load",
                        "category": "access_denied",
                        "resolution": "Check IAM and bucket policy.",
                        "notes": "Permissions issue",
                        "source_type": "seed",
                        "error_type": "access_denied",
                        "exception_type": "AccessDeniedException",
                        "severity": "high",
                        "service_hint": "s3",
                        "retryable": False,
                        "resolution_type": "permission_fix",
                    }
                ),
                0.91,
            )
        ]


def test_kb_retriever_returns_grounding_results() -> None:
    retriever = KnowledgeBaseRetriever(
        vector_store=FakeVectorStore(),
        seed_file="config/knowledge_base.json",
        max_results=3,
    )
    processed_error = ProcessedErrorRecord(
        row_id="1",
        source_file="errors.csv",
        raw_storage_reference="raw-ref",
        error_prefix="ValueError",
        error_summary="AccessDeniedException Forbidden while reading S3 object",
        normalized_prefix="valueerror",
        category_hint="access_denied",
        keywords=["accessdeniedexception", "forbidden", "s3"],
        error_type="access_denied",
        exception_type="AccessDeniedException",
        severity="high",
        service_hint="s3",
        retryable=False,
        resolution_type="permission_fix",
    )

    results = retriever.retrieve(processed_error)

    assert results
    assert results[0].category == "access_denied"
    assert results[0].error_type == "access_denied"
    assert results[0].score == 0.91
    assert retriever.get_direct_match(results) is not None
