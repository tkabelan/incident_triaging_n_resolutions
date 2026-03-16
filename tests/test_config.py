import json
from pathlib import Path

import pytest

from app.core.config import load_config


def test_load_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "app": {
                    "name": "test-service",
                    "environment": "test",
                    "host": "127.0.0.1",
                    "port": 9000
                },
                "logging": {"level": "DEBUG", "format": "%(message)s"},
                "storage": {
                    "raw_data_dir": "raw",
                    "processed_data_dir": "processed"
                },
                "ingestion": {
                    "error_data_dir": "error_data",
                    "default_csv_file": "errors.csv"
                },
                "database": {"url": "sqlite:///./test.db"},
                "vector_store": {
                    "provider": "chroma",
                    "persist_directory": "chroma",
                    "collection_name": "incident_kb",
                    "telemetry_enabled": False
                },
                "knowledge_base": {
                    "seed_file": "config/knowledge_base.json",
                    "max_results": 3,
                    "direct_match_threshold": 0.75
                },
                "models": {
                    "primary_llm": "primary",
                    "verification_llm": "verify",
                    "embedding_provider": "local_hash",
                    "embedding_model": "embed",
                    "embedding_dimensions": 256,
                    "openai_api_key_env_var": "OPENAI_API_KEY",
                    "temperature": 0.0
                },
                "search": {
                    "enabled": True,
                    "provider": "tavily",
                    "api_key_env_var": "TAVILY_API_KEY",
                    "max_results": 3,
                    "search_depth": "basic"
                }
            }
        ),
        encoding="utf-8",
    )

    settings = load_config(config_path)

    assert settings.app.name == "test-service"
    assert settings.logging.level == "DEBUG"


def test_load_config_rejects_invalid_schema(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"app": {"name": "bad"}}), encoding="utf-8")

    with pytest.raises(Exception):
        load_config(config_path)
