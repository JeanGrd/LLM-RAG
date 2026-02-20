from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Paths(BaseModel):
    data_dir: str = "./data"
    index_dir: str = "./data/indices"


class LlamaCppConfig(BaseModel):
    base_url: str = "http://127.0.0.1:8080"
    embed_base_url: str = ""  # optional dedicated endpoint for /v1/embeddings
    llm_model: str = ""  # optional default; if empty, client must pass model per request
    embed_model: str = ""  # falls back to llm_model when empty
    timeout_s: int = 120
    rpc_targets: list[str] = Field(default_factory=list)

    def resolved_rpc_targets(self) -> list[str]:
        targets: list[str] = []
        for item in self.rpc_targets:
            normalized = item.strip()
            if normalized and normalized not in targets:
                targets.append(normalized)
        return targets


class RagConfig(BaseModel):
    top_k: int = 5
    chunk_size: int = 900
    chunk_overlap: int = 180
    min_score: float = 0.0


def _coerce_env_number(value: Any, allow_float: bool = False) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return int(value)
    except ValueError:
        if allow_float:
            try:
                return float(value)
            except ValueError:
                return value
        return value


def yaml_config_settings_source() -> Dict[str, Any]:
    config_path = os.getenv("RAG_CONFIG_PATH", "config/settings.yaml")
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _ensure_writable_dir(path: str, fallback_leaf: str) -> str:
    """
    Ensure a directory exists and is writable; otherwise fall back to ~/.local/share/llm-rag/<leaf>.
    """
    target = Path(path).expanduser()
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return str(target)
    except Exception as exc:  # pragma: no cover
        fallback_root = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share"))
        fallback = fallback_root / "llm-rag" / fallback_leaf
        fallback.mkdir(parents=True, exist_ok=True)
        probe = fallback / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return str(fallback)


class Settings(BaseSettings):
    app_env: str = "local"
    log_level: str = "INFO"
    paths: Paths = Field(default_factory=Paths)
    llama_cpp: LlamaCppConfig = Field(default_factory=LlamaCppConfig)
    rag: RagConfig = Field(default_factory=RagConfig)

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        extra="ignore",
        env_file=None,
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
        # Priority (highest -> lowest):
        # init args, process env, YAML defaults, file secrets.
        return (
            init_settings,
            env_settings,
            yaml_config_settings_source,
            file_secret_settings,
        )

    def primary_provider(self) -> Literal["llama_cpp"]:
        return "llama_cpp"


def load_settings() -> Settings:
    settings = Settings()
    settings.paths.data_dir = str(Path(settings.paths.data_dir).expanduser())
    settings.paths.index_dir = _ensure_writable_dir(settings.paths.index_dir, "indices")
    return settings
