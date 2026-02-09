from __future__ import annotations

import os
from typing import Any, Dict

import yaml
from dotenv import dotenv_values
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Paths(BaseModel):
    data_dir: str = "./data"
    index_dir: str = "./data/indices"


class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    embed_model: str = "nomic-embed-text"
    llm_model: str = "llama3"
    timeout_s: int = 120


class CloudConfig(BaseModel):
    provider: str = "generic"
    api_url: str = "https://example-llm-provider/v1/generate"
    api_key: str = "replace-me"
    model: str = "best-model"
    timeout_s: int = 30


class RagConfig(BaseModel):
    top_k: int = 5
    chunk_size: int = 900
    chunk_overlap: int = 180
    min_score: float = 0.0
    use_cloud_first: bool = True
    fallback_to_ollama: bool = True


def yaml_config_settings_source() -> Dict[str, Any]:
    config_path = os.getenv("RAG_CONFIG_PATH", "config/settings.yaml")
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {}
    return data


def legacy_env_settings_source() -> Dict[str, Any]:
    """
    Support flat env vars like OLLAMA_BASE_URL in addition to nested OLLAMA__BASE_URL.
    Reads from both os.environ and .env (without exporting to os.environ).
    """
    env = {**dotenv_values(".env"), **os.environ}
    data: Dict[str, Any] = {}

    def set_nested(path: str, value: Any) -> None:
        if value is None or value == "":
            return
        cur = data
        parts = path.split(".")
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = value

    set_nested("ollama.base_url", env.get("OLLAMA_BASE_URL"))
    set_nested("ollama.embed_model", env.get("OLLAMA_EMBED_MODEL"))
    set_nested("ollama.llm_model", env.get("OLLAMA_LLM_MODEL"))
    set_nested("ollama.timeout_s", env.get("OLLAMA_TIMEOUT_S"))

    set_nested("cloud.provider", env.get("CLOUD_PROVIDER"))
    set_nested("cloud.api_url", env.get("CLOUD_API_URL"))
    set_nested("cloud.api_key", env.get("CLOUD_API_KEY"))
    set_nested("cloud.model", env.get("CLOUD_MODEL"))
    set_nested("cloud.timeout_s", env.get("CLOUD_TIMEOUT_S"))

    set_nested("rag.top_k", env.get("TOP_K"))
    set_nested("rag.chunk_size", env.get("CHUNK_SIZE"))
    set_nested("rag.chunk_overlap", env.get("CHUNK_OVERLAP"))
    set_nested("rag.min_score", env.get("MIN_SCORE"))
    set_nested("rag.use_cloud_first", env.get("USE_CLOUD_FIRST"))
    set_nested("rag.fallback_to_ollama", env.get("FALLBACK_TO_OLLAMA"))

    set_nested("app_env", env.get("APP_ENV"))
    set_nested("log_level", env.get("LOG_LEVEL"))

    return data


class Settings(BaseSettings):
    app_env: str = "local"
    log_level: str = "INFO"
    paths: Paths = Field(default_factory=Paths)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    cloud: CloudConfig = Field(default_factory=CloudConfig)
    rag: RagConfig = Field(default_factory=RagConfig)

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        # Priority: init < yaml < env < dotenv < file secrets
        return (
            init_settings,
            yaml_config_settings_source,
            legacy_env_settings_source,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )


def load_settings() -> Settings:
    return Settings()
