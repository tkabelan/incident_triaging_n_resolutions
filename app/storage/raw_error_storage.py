from __future__ import annotations

import json
import logging
from pathlib import Path

from app.schemas.error_records import RawErrorRecord


logger = logging.getLogger(__name__)


class RawErrorStorageService:
    def __init__(self, raw_data_dir: str | Path) -> None:
        self._raw_data_dir = Path(raw_data_dir)

    def save(self, record: RawErrorRecord) -> str:
        self._raw_data_dir.mkdir(parents=True, exist_ok=True)
        storage_path = self._raw_data_dir / f"{record.source_file}-{record.row_id}.json"
        storage_path.write_text(
            json.dumps(record.model_dump(), indent=2),
            encoding="utf-8",
        )
        logger.info("Stored raw error record %s at %s", record.row_id, storage_path)
        return str(storage_path)
