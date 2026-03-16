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
    classification = result.get("classification") or {}
    verification = result.get("verification") or {}
    web_results = result.get("web_search_results") or []
    stages = result.get("stage_details", {})
    stages["chroma_db"].update(
        {
            "direct_match": result.get("kb_direct_match", False),
            "evidence_count": result.get("evidence_count", 0),
        }
    )
    stages["primary_llm"].update(
        {
            "classification": classification.get("category"),
            "resolution": classification.get("proposed_resolution"),
        }
    )
    stages["verification_llm"].update(
        {
            "passed": verification.get("passed"),
            "needs_web_search": verification.get("needs_web_search"),
            "reasoning": verification.get("reasoning"),
        }
    )
    stages["web_search"].update(
        {
            "results": len(web_results),
            "items": [
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "score": item.get("score"),
                    "content": item.get("content"),
                }
                for item in web_results
            ],
        }
    )
    stages["refinement_llm"].update(
        {
            "classification": classification.get("category"),
            "resolution": classification.get("proposed_resolution"),
        }
    )

    return {
        "final_status": result.get("status"),
        "classification": classification.get("category"),
        "resolution": classification.get("proposed_resolution"),
        "stages": stages,
        "error": result.get("error"),
    }


if __name__ == "__main__":
    main()
