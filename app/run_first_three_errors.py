from __future__ import annotations

import json

from app.core.config import get_settings
from app.logging_config import init_logging
from app.workflows.error_processing import ErrorProcessingWorkflow


def main() -> None:
    settings = get_settings()
    init_logging(settings.logging)
    workflow = ErrorProcessingWorkflow(settings)
    results = workflow.run_first_three_errors()
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
