from pathlib import Path

from app.ingestion.csv_ingestion import CsvErrorIngestionService


def test_csv_ingestion_reads_records() -> None:
    service = CsvErrorIngestionService()

    records = service.read_errors(Path("error_data") / "error_prefix_counts.csv")

    assert records
    assert len(records) == 3
    assert records[0].row_id == "1"
    assert records[0].source_file == "error_prefix_counts.csv"
    assert records[0].error_prefix
