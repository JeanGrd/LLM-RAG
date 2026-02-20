from __future__ import annotations

import logging
from itertools import cycle
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import urlparse

import requests


def build_endpoint_urls(base_url: str, rpc_targets: Optional[Iterable[str]] = None) -> List[str]:
    urls: List[str] = []

    def _add(url: str) -> None:
        normalized = (url or "").strip().rstrip("/")
        if normalized and normalized not in urls:
            urls.append(normalized)

    _add(base_url)
    for target in rpc_targets or []:
        _add(str(target))
    return urls


class EndpointPool:
    """Round-robin selector over llama.cpp endpoints."""

    def __init__(self, endpoints: List[str]):
        if not endpoints:
            raise ValueError("No llama.cpp endpoints configured")
        self._cycle = cycle(endpoints)

    @classmethod
    def from_config(
        cls,
        base_url: str,
        rpc_targets: Optional[Iterable[str]] = None,
    ) -> "EndpointPool":
        return cls(build_endpoint_urls(base_url, rpc_targets))

    def next(self) -> str:
        return next(self._cycle)


def resolve_model_alias(model_name: str, available_models: Iterable[str]) -> str:
    normalized = (model_name or "").strip()
    if not normalized:
        return normalized

    model_ids = [m.strip() for m in available_models if isinstance(m, str) and m.strip()]
    if not model_ids:
        return normalized
    if normalized in model_ids:
        return normalized

    basename = Path(normalized).name
    if basename in model_ids:
        return basename

    for model_id in model_ids:
        if Path(model_id).name == basename:
            return model_id
    return normalized


def is_embedding_model_name(model_name: str) -> bool:
    name = (model_name or "").strip().lower()
    if not name:
        return False
    return "embed" in name or "embedding" in name


def filter_chat_models(model_names: Iterable[str]) -> List[str]:
    return [
        name
        for name in model_names
        if isinstance(name, str) and name.strip() and not is_embedding_model_name(name)
    ]


def filter_embedding_models(model_names: Iterable[str]) -> List[str]:
    return [
        name
        for name in model_names
        if isinstance(name, str) and name.strip() and is_embedding_model_name(name)
    ]


def list_remote_models(
    endpoints: Iterable[str],
    timeout_s: int,
    logger: Optional[logging.Logger] = None,
) -> List[str]:
    names: List[str] = []
    timeout = min(timeout_s, 10)
    for endpoint in endpoints:
        base_url = (endpoint or "").strip().rstrip("/")
        if not base_url:
            continue
        try:
            resp = requests.get(f"{base_url}/v1/models", timeout=timeout)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:  # noqa: BLE001
            if logger:
                logger.warning("Unable to list models from %s: %s", base_url, exc)
            continue

        for item in payload.get("data", []):
            if not isinstance(item, dict):
                continue
            model_id = item.get("id") or item.get("model")
            if isinstance(model_id, str) and model_id.strip() and model_id not in names:
                names.append(model_id.strip())
    return names


def resolve_embedding_endpoint(
    llm_base_url: str,
    configured_embed_base_url: str,
    rpc_targets: Optional[Iterable[str]],
    timeout_s: int,
    logger: Optional[logging.Logger] = None,
) -> tuple[str, list[str], list[str]]:
    embed_base_url = (configured_embed_base_url or "").strip() or llm_base_url
    same_base_url = embed_base_url.rstrip("/") == llm_base_url.rstrip("/")
    embed_rpc_targets = list(rpc_targets or []) if same_base_url else []

    embed_endpoints = build_endpoint_urls(embed_base_url, embed_rpc_targets)
    embed_remote_models = list_remote_models(embed_endpoints, timeout_s, logger)

    # If embeddings are not exposed on the chat endpoint, try a sibling endpoint
    # on the next port (common local split setup: 8080 chat, 8081 embeddings).
    if same_base_url and not filter_embedding_models(embed_remote_models):
        parsed = urlparse(llm_base_url)
        if parsed.scheme in {"http", "https"} and parsed.hostname and parsed.port:
            sibling_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port + 1}"
            sibling_models = list_remote_models([sibling_url], timeout_s, logger)
            if filter_embedding_models(sibling_models):
                if logger:
                    logger.info(
                        "Auto-selected dedicated embedding endpoint: %s (from %s)",
                        sibling_url,
                        llm_base_url,
                    )
                return sibling_url, [], sibling_models

    return embed_base_url, embed_rpc_targets, embed_remote_models
