from __future__ import annotations

import logging

from app.mcp_server.kb_retrieval import KB_RETRIEVAL_TOOL
from app.mcp_server.raw_ingestion import RAW_INGESTION_TOOL
from app.mcp_server.server import McpServer
from app.mcp_server.verification import VERIFICATION_TOOL
from app.mcp_server.web_search import WEB_SEARCH_TOOL
from app.schemas.error_records import RawErrorIngestionResponse, RawErrorRecord
from app.schemas.processed_errors import (
    ClassificationResolutionResult,
    GroundingEvidence,
    KbRetrievalResponse,
    ProcessedErrorRecord,
    VerificationResult,
    WebSearchResult,
)


logger = logging.getLogger(__name__)


class LangChainMcpClient:
    def __init__(self, server: McpServer) -> None:
        self._server = server

    def ingest_raw_error(self, record: RawErrorRecord) -> RawErrorIngestionResponse:
        logger.info("Submitting raw error record %s through MCP", record.row_id)
        response = self._server.call_tool(RAW_INGESTION_TOOL, {"record": record.model_dump()})
        return RawErrorIngestionResponse.model_validate(response)

    def retrieve_kb(
        self,
        processed_error: ProcessedErrorRecord,
    ) -> KbRetrievalResponse:
        logger.info("Submitting KB retrieval for row %s through MCP", processed_error.row_id)
        response = self._server.call_tool(
            KB_RETRIEVAL_TOOL,
            {
                "processed_error": processed_error.model_dump(),
            },
        )
        return KbRetrievalResponse.model_validate(response)

    def verify_resolution(
        self,
        processed_error: ProcessedErrorRecord,
        classification: ClassificationResolutionResult,
        evidence: list[GroundingEvidence],
    ) -> VerificationResult:
        logger.info("Submitting verification for row %s through MCP", processed_error.row_id)
        response = self._server.call_tool(
            VERIFICATION_TOOL,
            {
                "processed_error": processed_error.model_dump(),
                "classification": classification.model_dump(),
                "evidence": [item.model_dump() for item in evidence],
            },
        )
        return VerificationResult.model_validate(response)

    def web_search(self, query: str) -> list[WebSearchResult]:
        logger.info("Submitting web search through MCP")
        response = self._server.call_tool(WEB_SEARCH_TOOL, {"query": query})
        return [WebSearchResult.model_validate(item) for item in response.get("results", [])]
