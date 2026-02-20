from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Literal

import yaml
from dotenv import dotenv_values
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file_path() -> str:
    return os.getenv("RAG_ENV_FILE", ".env")


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


def legacy_env_settings_source() -> Dict[str, Any]:
    """
    Support flat env vars like LLAMA_CPP_BASE_URL in addition to nested LLAMA_CPP__BASE_URL.
    Reads from both os.environ and .env (without exporting to os.environ).
    """
    env_file_vals = dotenv_values(_env_file_path())
    env = {**env_file_vals, **os.environ}
    data: Dict[str, Any] = {}

    def set_nested(path: str, value: Any) -> None:
        if value is None or value == "":
            return
        cur = data
        parts = path.split(".")
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = value

    def _split_list(raw: Any) -> list[str]:
        if raw is None:
            return []
        if isinstance(raw, str):
            parts: list[str] = []
            for chunk in raw.replace(";", ",").split(","):
                parts.extend(chunk.split())
            return [p.strip() for p in parts if p.strip()]
        if isinstance(raw, (list, tuple, set)):
            return [str(item).strip() for item in raw if str(item).strip()]
        return []

    set_nested("llama_cpp.base_url", env.get("LLAMA_CPP_BASE_URL"))
    set_nested("llama_cpp.embed_base_url", env.get("LLAMA_CPP_EMBED_BASE_URL"))
    set_nested("llama_cpp.embed_model", env.get("LLAMA_CPP_EMBED_MODEL"))
    set_nested("llama_cpp.llm_model", env.get("LLAMA_CPP_LLM_MODEL") or env.get("MODEL_NAME"))
    set_nested("llama_cpp.timeout_s", env.get("LLAMA_CPP_TIMEOUT_S"))
    rpc_targets = _split_list(env.get("LLAMA_CPP_RPC_TARGETS"))
    if rpc_targets:
        set_nested("llama_cpp.rpc_targets", rpc_targets)

    set_nested("paths.data_dir", env.get("DATA_DIR"))
    set_nested("paths.index_dir", env.get("INDEX_DIR"))

    set_nested("rag.top_k", _coerce_env_number(env.get("TOP_K")))
    set_nested("rag.chunk_size", _coerce_env_number(env.get("CHUNK_SIZE")))
    set_nested("rag.chunk_overlap", _coerce_env_number(env.get("CHUNK_OVERLAP")))
    set_nested("rag.min_score", _coerce_env_number(env.get("MIN_SCORE"), allow_float=True))

    set_nested("app_env", env.get("APP_ENV"))
    set_nested("log_level", env.get("LOG_LEVEL"))

    return data


def _ensure_writable_dir(path: str, fallback_leaf: str) -> str:
    """
    Make sure a directory exists and is writable. If not, fall back to a
    user-writable location under $XDG_DATA_HOME or ~/.local/share/llm-rag/<leaf>.
    """
    target = Path(path).expanduser()
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return str(target)
    except Exception as exc:  # pragma: no cover - platform/perm specific
        fallback_root = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share"))
        fallback = fallback_root / "llm-rag" / fallback_leaf
        fallback.mkdir(parents=True, exist_ok=True)
        probe = fallback / ".write_test"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except Exception as exc2:
            raise RuntimeError(
                f"Neither '{target}' nor fallback '{fallback}' is writable: {exc2}"
            ) from exc
        print(f"[settings] '{target}' not writable; using '{fallback}' instead ({exc}).")
        return str(fallback)


class Settings(BaseSettings):
    app_env: str = "local"
    log_level: str = "INFO"
    paths: Paths = Field(default_factory=Paths)
    llama_cpp: LlamaCppConfig = Field(default_factory=LlamaCppConfig)
    rag: RagConfig = Field(default_factory=RagConfig)

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=_env_file_path(),
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
        # Priority (highest -> lowest):
        # init args, process env, .env, legacy flat env mapping, YAML defaults, file secrets.
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            legacy_env_settings_source,
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
