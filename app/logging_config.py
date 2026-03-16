from __future__ import annotations

import logging

from app.core.config import LoggingConfig


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "-"
        return True


def init_logging(config: LoggingConfig) -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    handler = logging.StreamHandler()
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(logging.Formatter(config.format))

    root_logger.setLevel(config.level.upper())
    root_logger.addHandler(handler)
