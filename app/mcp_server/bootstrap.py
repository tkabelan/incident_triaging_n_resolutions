from __future__ import annotations

import os

from app.core.config import get_settings
from app.mcp_server.kb_retrieval import KB_RETRIEVAL_TOOL, create_kb_retrieval_handler
from app.mcp_server.raw_ingestion import RAW_INGESTION_TOOL, create_raw_ingestion_handler
from app.mcp_server.server import McpServer
from app.mcp_server.verification import VERIFICATION_TOOL, create_verification_handler
from app.mcp_server.web_search import WEB_SEARCH_TOOL, create_web_search_handler
from app.retrieval.kb_retriever import KnowledgeBaseRetriever
from app.search.tavily_search import TavilySearchService
from app.storage.raw_error_storage import RawErrorStorageService
from app.verification.service import VerificationService


def create_mcp_server(
    storage_service: RawErrorStorageService | None = None,
    retriever: KnowledgeBaseRetriever | None = None,
) -> McpServer:
    server = McpServer()
    settings = get_settings()
    raw_storage = storage_service or RawErrorStorageService(settings.storage.raw_data_dir)
    kb_retriever = retriever or KnowledgeBaseRetriever.from_settings(settings)
    server.register_tool(RAW_INGESTION_TOOL, create_raw_ingestion_handler(raw_storage))
    server.register_tool(KB_RETRIEVAL_TOOL, create_kb_retrieval_handler(kb_retriever))
    if os.getenv(settings.models.openai_api_key_env_var):
        server.register_tool(
            VERIFICATION_TOOL,
            create_verification_handler(VerificationService.from_settings(settings)),
        )
    if settings.search.enabled and os.getenv(settings.search.api_key_env_var):
        server.register_tool(
            WEB_SEARCH_TOOL,
            create_web_search_handler(TavilySearchService.from_settings(settings)),
        )
    return server
