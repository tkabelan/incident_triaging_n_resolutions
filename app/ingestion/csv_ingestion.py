from __future__ import annotations

import csv
import logging
from pathlib import Path

from app.schemas.error_records import RawErrorRecord


logger = logging.getLogger(__name__)

MAX_ERROR_RECORDS = 3


class CsvErrorIngestionService:
    def read_errors(self, csv_path: str | Path) -> list[RawErrorRecord]:
        path = Path(csv_path)
        logger.info("Reading error CSV from %s", path)

        records: list[RawErrorRecord] = []
        with path.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            required_columns = {"error_prefix", "error_message"}
            missing_columns = required_columns - set(reader.fieldnames or [])
            if missing_columns:
                raise ValueError(
                    f"CSV file {path} is missing required columns: {sorted(missing_columns)}"
                )

            for index, row in enumerate(reader, start=1):
                if len(records) >= MAX_ERROR_RECORDS:
                    break

                try:
                    records.append(
                        RawErrorRecord(
                            row_id=str(index),
                            error_prefix=(row.get("error_prefix") or "").strip(),
                            error_message=(row.get("error_message") or "").strip(),
                            source_file=path.name,
                        )
                    )
                except Exception as exc:
                    logger.warning(
                        "Skipping malformed CSV row %s in %s: %s", index, path.name, exc
                    )
        logger.info(
            "Loaded %s raw error records from %s using the first %s rows",
            len(records),
            path.name,
            MAX_ERROR_RECORDS,
        )
        return records
