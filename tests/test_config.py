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
                    "port": 9000,
                },
                "logging": {"level": "DEBUG", "format": "%(message)s"},
                "storage": {"raw_data_dir": "raw", "processed_data_dir": "processed"},
                "ingestion": {"error_data_dir": "error_data", "default_csv_file": "errors.csv"},
                "database": {"url": "sqlite:///./test.db"},
                "vector_store": {
                    "provider": "chroma",
                    "persist_directory": "chroma",
                    "collection_name": "incident_kb",
                    "telemetry_enabled": False,
                },
                "knowledge_base": {
                    "seed_file": "config/knowledge_base.json",
                    "max_results": 3,
                    "direct_match_threshold": 0.75,
                },
                "models": {
                    "primary_llm": "primary",
                    "verification_llm": "verify",
                    "verification_provider": "openai",
                    "verification_api_key_env_var": "OPENAI_API_KEY",
                    "embedding_provider": "local_hash",
                    "embedding_model": "embed",
                    "embedding_dimensions": 256,
                    "openai_api_key_env_var": "OPENAI_API_KEY",
                    "temperature": 0.0,
                },
                "search": {
                    "enabled": True,
                    "provider": "tavily",
                    "api_key_env_var": "TAVILY_API_KEY",
                    "max_results": 3,
                    "search_depth": "basic",
                },
                "classification": {
                    "taxonomy_file": "config/classification_taxonomy.json"
                },
                "workflow": {
                    "allow_direct_kb_resolution": True,
                    "verification_confidence_threshold": 0.6,
                    "refinement_confidence_threshold": 0.7,
                    "use_web_search_on_low_confidence": True,
                    "update_kb_on_verified": True,
                    "max_classification_retries": 1,
                    "max_refinement_retries": 1,
                    "route_failed_verification_to_human_review": True,
                    "route_failed_refinement_to_human_review": True,
                },
                "langsmith": {
                    "enabled": False,
                    "project": "incident-tests",
                    "endpoint": "https://api.smith.langchain.com",
                    "api_key_env_var": "LANGSMITH_API_KEY",
                    "run_name": "incident-test-run",
                },
            }
        ),
        encoding="utf-8",
    )

    settings = load_config(config_path)

    assert settings.app.name == "test-service"
    assert settings.logging.level == "DEBUG"
    assert settings.workflow.verification_confidence_threshold == 0.6
    assert settings.workflow.max_classification_retries == 1
    assert settings.langsmith.enabled is False


def test_load_config_requires_langsmith_key_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "app": {
                    "name": "test-service",
                    "environment": "test",
                    "host": "127.0.0.1",
                    "port": 9000,
                },
                "logging": {"level": "DEBUG", "format": "%(message)s"},
                "storage": {"raw_data_dir": "raw", "processed_data_dir": "processed"},
                "ingestion": {"error_data_dir": "error_data", "default_csv_file": "errors.csv"},
                "database": {"url": "sqlite:///./test.db"},
                "vector_store": {
                    "provider": "chroma",
                    "persist_directory": "chroma",
                    "collection_name": "incident_kb",
                    "telemetry_enabled": False,
                },
                "knowledge_base": {
                    "seed_file": "config/knowledge_base.json",
                    "max_results": 3,
                    "direct_match_threshold": 0.75,
                },
                "models": {
                    "primary_llm": "primary",
                    "verification_llm": "verify",
                    "verification_provider": "openai",
                    "verification_api_key_env_var": "OPENAI_API_KEY",
                    "embedding_provider": "local_hash",
                    "embedding_model": "embed",
                    "embedding_dimensions": 256,
                    "openai_api_key_env_var": "OPENAI_API_KEY",
                    "temperature": 0.0,
                },
                "search": {
                    "enabled": True,
                    "provider": "tavily",
                    "api_key_env_var": "TAVILY_API_KEY",
                    "max_results": 3,
                    "search_depth": "basic",
                },
                "classification": {
                    "taxonomy_file": "config/classification_taxonomy.json"
                },
                "workflow": {
                    "allow_direct_kb_resolution": True,
                    "verification_confidence_threshold": 0.6,
                    "refinement_confidence_threshold": 0.7,
                    "use_web_search_on_low_confidence": True,
                    "update_kb_on_verified": True,
                    "max_classification_retries": 1,
                    "max_refinement_retries": 1,
                    "route_failed_verification_to_human_review": True,
                    "route_failed_refinement_to_human_review": True,
                },
                "langsmith": {
                    "enabled": True,
                    "project": "incident-tests",
                    "endpoint": "https://api.smith.langchain.com",
                    "api_key_env_var": "LANGSMITH_API_KEY",
                    "run_name": "incident-test-run",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)

    with pytest.raises(ValueError, match="LangSmith tracing is enabled"):
        load_config(config_path)


def test_load_config_rejects_invalid_schema(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"app": {"name": "bad"}}), encoding="utf-8")

    with pytest.raises(Exception):
        load_config(config_path)
