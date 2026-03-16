import json

from app.normalization.error_normalizer import ErrorNormalizationService
from app.schemas.error_records import RawErrorRecord
from app.storage.processed_error_storage import ProcessedErrorStorageService


def test_error_normalizer_creates_processed_record(tmp_path) -> None:
    raw_path = tmp_path / "raw.json"
    raw_payload = {
        "row_id": "1",
        "error_prefix": "ValueError: Error loading CSV files from S3",
        "error_message": "ValueError: Error loading CSV files from S3\nAccessDeniedException: Forbidden",
        "source_file": "error_prefix_counts.csv",
    }
    raw_path.write_text(json.dumps(raw_payload), encoding="utf-8")

    service = ErrorNormalizationService(ProcessedErrorStorageService(tmp_path / "processed"))
    processed, storage_reference = service.normalize_from_storage(str(raw_path))

    assert processed.category_hint == "access_denied"
    assert processed.error_type == "access_denied"
    assert processed.exception_type == "AccessDeniedException"
    assert processed.service_hint == "s3"
    assert processed.raw_storage_reference == str(raw_path)
    assert "forbidden" in processed.error_summary.lower() or "valueerror" in processed.error_summary.lower()
    assert storage_reference.endswith("error_prefix_counts.csv-1.json")


def test_error_normalizer_extracts_keywords(tmp_path) -> None:
    service = ErrorNormalizationService(ProcessedErrorStorageService(tmp_path))
    record = RawErrorRecord(
        row_id="2",
        error_prefix="ExecutionError",
        error_message="No such file or directory: s3://bucket/path",
        source_file="errors.csv",
    )

    processed, _ = service.normalize(record, "raw-ref")

    assert processed.category_hint == "file_not_found"
    assert processed.error_type == "file_not_found"
    assert processed.retryable is True
    assert "s3://bucket/path" in processed.keywords
