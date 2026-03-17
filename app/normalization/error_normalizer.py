from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from app.normalization.taxonomy import classify_taxonomy
from app.schemas.error_records import RawErrorRecord
from app.schemas.processed_errors import ProcessedErrorRecord
from app.storage.processed_error_storage import ProcessedErrorStorageService

logger = logging.getLogger(__name__)

STOPWORDS = {"the", "and", "from", "with", "while", "calling", "this", "that", "for"}


class ErrorNormalizationService:
    def __init__(self, processed_storage: ProcessedErrorStorageService) -> None:
        self._processed_storage = processed_storage

    def normalize(
        self, record: RawErrorRecord, raw_storage_reference: str
    ) -> tuple[ProcessedErrorRecord, str]:
        logger.info("Normalizing raw error record %s", record.row_id)
        summary = self._extract_summary(record.error_message)
        full_error_text = self._normalize_text(record.error_message)
        normalized_prefix = record.error_prefix.split(":")[0].strip().lower()
        category_hint = self._infer_category(full_error_text, normalized_prefix)
        keywords = self._extract_keywords(f"{record.error_prefix} {full_error_text}")
        taxonomy = classify_taxonomy(record.error_prefix, full_error_text)

        processed_record = ProcessedErrorRecord(
            row_id=record.row_id,
            source_file=record.source_file,
            raw_storage_reference=raw_storage_reference,
            error_prefix=record.error_prefix,
            error_summary=summary,
            normalized_prefix=normalized_prefix,
            category_hint=category_hint,
            keywords=keywords,
            error_type=taxonomy.error_type,
            exception_type=taxonomy.exception_type,
            severity=taxonomy.severity,
            service_hint=taxonomy.service_hint,
            retryable=taxonomy.retryable,
            resolution_type=taxonomy.resolution_type,
        )
        storage_reference = self._processed_storage.save(processed_record)
        return processed_record, storage_reference

    def normalize_from_storage(
        self, raw_storage_reference: str
    ) -> tuple[ProcessedErrorRecord, str]:
        payload = json.loads(Path(raw_storage_reference).read_text(encoding="utf-8"))
        record = RawErrorRecord.model_validate(payload)
        return self.normalize(record, raw_storage_reference)

    def _extract_summary(self, error_message: str) -> str:
        first_line = error_message.strip().splitlines()[0]
        return self._normalize_text(first_line)

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _extract_keywords(self, text: str) -> list[str]:
        words = re.findall(r"[A-Za-z0-9_./:-]+", text.lower())
        keywords: list[str] = []
        for word in words:
            if len(word) < 3 or word in STOPWORDS or word in keywords:
                continue
            keywords.append(word)
            if len(keywords) == 8:
                break
        return keywords

    def _infer_category(self, summary: str, normalized_prefix: str) -> str:
        text = f"{normalized_prefix} {summary}".lower()
        if "forbidden" in text or "accessdenied" in text or "access denied" in text:
            return "access_denied"
        if "filenotfound" in text or "no such file or directory" in text:
            return "file_not_found"
        if "conflicting commit" in text or "concurrency control" in text:
            return "concurrency_conflict"
        return normalized_prefix or "unknown"
