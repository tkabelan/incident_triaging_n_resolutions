import json

from app.schemas.error_records import RawErrorRecord
from app.storage.raw_error_storage import RawErrorStorageService


def test_raw_error_storage_persists_record_unchanged(tmp_path) -> None:
    service = RawErrorStorageService(tmp_path)
    record = RawErrorRecord(
        row_id="3",
        error_prefix="ExecutionError",
        error_message="failure",
        source_file="errors.csv",
    )

    storage_reference = service.save(record)

    assert storage_reference.endswith("errors.csv-3.json")
    stored_payload = json.loads(tmp_path.joinpath("errors.csv-3.json").read_text(encoding="utf-8"))
    assert stored_payload == record.model_dump()
