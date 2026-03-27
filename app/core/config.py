from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

DEFAULT_CONFIG_PATH = Path("config/config.json")
CONFIG_ENV_VAR = "INCIDENT_APP_CONFIG"
DOTENV_PATH = Path(".env")


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    environment: str
    host: str
    port: int


class DeploymentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cors_allowed_origins: list[str] = []


class LoggingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str = "INFO"
    format: str = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


class StorageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_data_dir: str
    processed_data_dir: str


class IngestionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_data_dir: str
    default_csv_file: str


class DatabaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str


class VectorStoreConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    persist_directory: str
    collection_name: str
    telemetry_enabled: bool = False


class KnowledgeBaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_file: str
    max_results: int
    direct_match_threshold: float = 0.75


class ModelsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_llm: str
    verification_llm: str
    verification_provider: str = "openai"
    verification_api_key_env_var: str = "OPENAI_API_KEY"
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int = 256
    openai_api_key_env_var: str
    temperature: float = 0.0


class SearchConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    provider: str
    api_key_env_var: str
    max_results: int = 3
    search_depth: str = "basic"


class ClassificationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    taxonomy_file: str


class WorkflowPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_direct_kb_resolution: bool = True
    verification_confidence_threshold: float = 0.6
    refinement_confidence_threshold: float = 0.7
    use_web_search_on_low_confidence: bool = True
    update_kb_on_verified: bool = True
    max_classification_retries: int = 1
    max_refinement_retries: int = 1
    route_failed_verification_to_human_review: bool = True
    route_failed_refinement_to_human_review: bool = True


class LangSmithConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    project: str
    endpoint: str = "https://api.smith.langchain.com"
    api_key_env_var: str = "LANGSMITH_API_KEY"
    run_name: str = "incident-error-workflow"


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app: AppConfig
    deployment: DeploymentConfig
    logging: LoggingConfig
    storage: StorageConfig
    ingestion: IngestionConfig
    database: DatabaseConfig
    vector_store: VectorStoreConfig
    knowledge_base: KnowledgeBaseConfig
    models: ModelsConfig
    search: SearchConfig
    classification: ClassificationConfig
    workflow: WorkflowPolicyConfig
    langsmith: LangSmithConfig


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: Path | None = None) -> Settings:
    if DOTENV_PATH.exists():
        load_dotenv(DOTENV_PATH)

    path = config_path or Path(os.getenv(CONFIG_ENV_VAR, DEFAULT_CONFIG_PATH))
    with path.open("r", encoding="utf-8") as config_file:
        data = json.load(config_file)

    env_config_raw = os.getenv("INCIDENT_APP_CONFIG_OVERRIDE")
    if env_config_raw:
        data = _deep_merge(data, json.loads(env_config_raw))

    settings = Settings.model_validate(data)

    vector_store_settings = data.get("vector_store", {})
    if vector_store_settings.get("telemetry_enabled") is False:
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        os.environ["CHROMA_TELEMETRY_IMPL"] = "chromadb.telemetry.product.null.NullTelemetry"

    _apply_langsmith_environment(settings)

    return settings


def _apply_langsmith_environment(settings: Settings) -> None:
    if not settings.langsmith.enabled:
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return

    api_key = os.getenv(settings.langsmith.api_key_env_var)
    if not api_key:
        raise ValueError(
            "LangSmith tracing is enabled but the required API key environment variable "
            f"'{settings.langsmith.api_key_env_var}' is not set."
        )

    os.environ["LANGSMITH_API_KEY"] = api_key
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith.project
    os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith.endpoint


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_config()
