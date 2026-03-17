from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

McpHandler = Callable[[dict[str, Any]], dict[str, Any]]


class McpServer:
    def __init__(self) -> None:
        self._handlers: dict[str, McpHandler] = {}

    def register_tool(self, name: str, handler: McpHandler) -> None:
        logger.info("Registering MCP tool %s", name)
        self._handlers[name] = handler

    def call_tool(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if name not in self._handlers:
            raise KeyError(f"MCP tool '{name}' is not registered")

        logger.info("Calling MCP tool %s", name)
        return self._handlers[name](payload)
