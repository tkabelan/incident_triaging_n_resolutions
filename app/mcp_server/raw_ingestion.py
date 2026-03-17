from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from app.schemas.error_records import RawErrorIngestionRequest, RawErrorIngestionResponse
from app.storage.raw_error_storage import RawErrorStorageService

logger = logging.getLogger(__name__)

RAW_INGESTION_TOOL = "error.ingest_raw"


def create_raw_ingestion_handler(
    storage_service: RawErrorStorageService,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def ingest_raw_error(payload: dict[str, Any]) -> dict[str, Any]:
        request = RawErrorIngestionRequest.model_validate(payload)
        logger.info(
            "Accepted raw error record %s from %s",
            request.record.row_id,
            request.record.source_file,
        )

        storage_reference = storage_service.save(request.record)
        response = RawErrorIngestionResponse(
            accepted=True,
            record=request.record,
            storage_reference=storage_reference,
            message="Raw error record accepted and stored for downstream processing",
        )
        return response.model_dump()

    return ingest_raw_error
