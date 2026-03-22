from __future__ import annotations

from typing import Any

from app.core.config import Settings


def invoke_with_optional_langsmith_trace(
    workflow_call: Any,
    *,
    settings: Settings,
    initial_state: dict[str, Any],
) -> dict[str, Any]:
    langsmith_settings = getattr(settings, "langsmith", None)
    if langsmith_settings is None or not langsmith_settings.enabled:
        return workflow_call(initial_state)

    from langsmith import traceable
    from langsmith.run_helpers import tracing_context

    @traceable(name=langsmith_settings.run_name, run_type="chain")
    def _invoke() -> dict[str, Any]:
        return workflow_call(initial_state)

    with tracing_context(enabled=True):
        return _invoke()
