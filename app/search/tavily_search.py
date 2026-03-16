from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.schemas.processed_errors import WebSearchResult


logger = logging.getLogger(__name__)


class TavilySearchService:
    def __init__(self, api_key: str, max_results: int = 3, search_depth: str = "basic") -> None:
        self._api_key = api_key
        self._max_results = max_results
        self._search_depth = search_depth

    @classmethod
    def from_settings(cls, settings: Any) -> "TavilySearchService":
        api_key = os.getenv(settings.search.api_key_env_var)
        if not api_key:
            raise ValueError(f"Missing Tavily API key in env var {settings.search.api_key_env_var}")
        return cls(
            api_key=api_key,
            max_results=settings.search.max_results,
            search_depth=settings.search.search_depth,
        )

    def search(self, query: str) -> list[WebSearchResult]:
        logger.info("Running Tavily search for query: %s", query)
        response = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key": self._api_key,
                "query": query,
                "max_results": self._max_results,
                "search_depth": self._search_depth,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        return [
            WebSearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
                score=item.get("score"),
            )
            for item in payload.get("results", [])
        ]
