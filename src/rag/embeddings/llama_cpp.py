from __future__ import annotations

from typing import List, Optional

import requests

from rag.llama_cpp import EndpointPool

from .base import Embeddings


def _extract_error_message(resp: requests.Response) -> str:
    try:
        payload = resp.json()
    except ValueError:
        payload = {}

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message") or error.get("type")
            if isinstance(message, str) and message.strip():
                return message.strip()
        for key in ("message", "detail"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    fallback = (resp.text or "").strip()
    return fallback or f"HTTP {resp.status_code}"


class LlamaCppEmbeddings(Embeddings):
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_s: int = 30,
        rpc_targets: Optional[List[str]] = None,
    ):
        self.model = model
        self.timeout_s = timeout_s
        self._pool = EndpointPool.from_config(base_url, rpc_targets)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        url = f"{self._pool.next()}/v1/embeddings"
        resp = requests.post(
            url,
            json={"model": self.model, "input": texts},
            timeout=self.timeout_s,
        )
        if resp.status_code == 501:
            raise ValueError(
                "llama.cpp /v1/embeddings is disabled (HTTP 501). "
                "Start llama-server with --embeddings."
            )
        if resp.status_code == 400:
            detail = _extract_error_message(resp)
            low = detail.lower()
            hint = ""
            if "pooling type" in low and "none" in low:
                hint = " Restart llama-server with LLAMA_POOLING=mean (example: LLAMA_POOLING=mean make llama)."
            raise ValueError(
                f"llama.cpp rejected /v1/embeddings for model '{self.model}' at {url}: {detail}.{hint}"
            )
        if resp.status_code >= 400:
            detail = _extract_error_message(resp)
            hint = ""
            if resp.status_code >= 500:
                hint = (
                    " If chat and embeddings use different models, run a dedicated embedding endpoint "
                    "and set LLAMA_CPP_EMBED_BASE_URL / LLAMA_CPP_EMBED_MODEL."
                )
            raise requests.HTTPError(
                f"llama.cpp /v1/embeddings failed (HTTP {resp.status_code}) for model '{self.model}' at {url}: {detail}.{hint}",
                response=resp,
            )
        data = resp.json()
        if "data" in data:
            return [item["embedding"] for item in data["data"]]
        embedding = data.get("embedding") or data.get("embeddings")
        if embedding is None:
            raise ValueError("Missing embeddings in llama.cpp response")
        if embedding and isinstance(embedding[0], (int, float)):
            return [embedding]
        return embedding
