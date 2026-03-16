import json

from app.mcp_client.client import LangChainMcpClient
from app.mcp_server.bootstrap import create_mcp_server
from app.schemas.error_records import RawErrorRecord
from app.storage.raw_error_storage import RawErrorStorageService


def test_mcp_raw_ingestion_accepts_record(tmp_path) -> None:
    storage_service = RawErrorStorageService(tmp_path)
    client = LangChainMcpClient(create_mcp_server(storage_service=storage_service))
    record = RawErrorRecord(
        row_id="1",
        error_prefix="ValueError",
        error_message="test error",
        source_file="sample.csv",
    )

    response = client.ingest_raw_error(record)

    assert response.accepted is True
    assert response.record == record
    assert response.storage_reference.endswith("sample.csv-1.json")
    stored_payload = json.loads(tmp_path.joinpath("sample.csv-1.json").read_text(encoding="utf-8"))
    assert stored_payload == record.model_dump()
