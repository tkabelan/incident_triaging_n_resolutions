from __future__ import annotations

import json
from typing import Any

from app.core.config import get_settings
from app.logging_config import init_logging
from app.workflows.error_processing import ErrorProcessingWorkflow

DEFAULT_ERROR_TEXT = """[CANNOT_OPEN_SOCKET] Can not open socket]"""


def main() -> None:
    settings = get_settings()
    init_logging(settings.logging)
    workflow = ErrorProcessingWorkflow(settings)
    result = workflow.run_single_error(DEFAULT_ERROR_TEXT)
    print(json.dumps(_format_output(result), indent=2))


def _format_output(result: dict[str, Any]) -> dict[str, Any]:
    trace = dict(result.get("agent_trace") or {})
    trace["error"] = result.get("error")
    return trace


if __name__ == "__main__":
    main()
