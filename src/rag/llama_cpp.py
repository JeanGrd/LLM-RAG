from __future__ import annotations

import logging
from itertools import cycle
from pathlib import Path
from typing import Iterable, List, Optional

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
