from __future__ import annotations

from app.mcp_client.client import LangChainMcpClient
from app.mcp_server.bootstrap import create_mcp_server
from app.schemas.processed_errors import GroundingEvidence, ProcessedErrorRecord


class FakeRetriever:
    def retrieve(self, _processed_error: ProcessedErrorRecord) -> list[GroundingEvidence]:
        return [
            GroundingEvidence(
                kb_id="kb-1",
                title="Socket connection refused",
                category="network_error",
                resolution="Check whether the target service is listening on the port.",
                notes="Loopback connection refused",
                score=0.88,
                source_type="seed",
                error_type="network_error",
                exception_type="SocketError",
                severity="high",
                service_hint="socket",
                retryable=True,
                resolution_type="service_restart",
            )
        ]

    def get_direct_match(self, evidence: list[GroundingEvidence]) -> GroundingEvidence | None:
        return evidence[0]


def test_mcp_kb_retrieval_returns_typed_evidence() -> None:
    client = LangChainMcpClient(create_mcp_server(retriever=FakeRetriever()))
    processed_error = ProcessedErrorRecord(
        row_id="manual-1",
        source_file="manual_input",
        raw_storage_reference="data/raw/manual_input-manual-1.json",
        error_prefix="[CANNOT_OPEN_SOCKET]",
        error_summary="Connection refused while opening local socket",
        normalized_prefix="cannot_open_socket",
        category_hint="network_error",
        keywords=["socket", "connection", "refused"],
        error_type="network_error",
        exception_type="SocketError",
        severity="high",
        service_hint="socket",
        retryable=True,
        resolution_type="service_restart",
    )

    response = client.retrieve_kb(processed_error)

    assert len(response.evidence) == 1
    assert response.evidence[0].kb_id == "kb-1"
    assert response.direct_match is not None
    assert response.direct_match.category == "network_error"
