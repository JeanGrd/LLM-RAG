from __future__ import annotations

from typing import List, Optional

import requests

from rag.llama_cpp import EndpointPool

from .base import Embeddings


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
        resp.raise_for_status()
        data = resp.json()
        if "data" in data:
            return [item["embedding"] for item in data["data"]]
        embedding = data.get("embedding") or data.get("embeddings")
        if embedding is None:
            raise ValueError("Missing embeddings in llama.cpp response")
        if embedding and isinstance(embedding[0], (int, float)):
            return [embedding]
        return embedding
