from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.search.tavily_search import TavilySearchService

WEB_SEARCH_TOOL = "search.web"


def create_web_search_handler(
    search_service: TavilySearchService,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def search(payload: dict[str, Any]) -> dict[str, Any]:
        query = payload["query"]
        results = search_service.search(query)
        return {"results": [item.model_dump() for item in results]}

    return search
