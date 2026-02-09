from __future__ import annotations

from typing import List, Optional

import requests

from .base import Embeddings


class OllamaEmbeddings(Embeddings):
    def __init__(self, base_url: str, model: str, timeout_s: int = 30):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        # Try endpoints in order (new -> legacy -> OpenAI compatible).
        last_err: Optional[Exception] = None
        for fn in (self._embed_openai, self._embed_v2, self._embed_v1):
            try:
                return fn(texts)
            except requests.HTTPError as exc:
                last_err = exc
                if exc.response is not None and exc.response.status_code in (404, 405):
                    continue
                raise
        if last_err:
            raise last_err
        raise RuntimeError("No Ollama embedding endpoint succeeded")

    def _embed_v2(self, texts: List[str]) -> List[List[float]]:
        resp = requests.post(
            f"{self.base_url}/api/embed",
            json={"model": self.model, "input": texts},
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("embeddings") or data.get("embedding")
        if embeddings is None:
            raise ValueError("Missing embeddings in Ollama response")
        # Normalize to list of lists
        if embeddings and isinstance(embeddings[0], (int, float)):
            return [embeddings]  # single vector
        return embeddings

    def _embed_v1(self, texts: List[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []
        for text in texts:
            resp = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=self.timeout_s,
            )
            resp.raise_for_status()
            data = resp.json()
            embedding = data.get("embedding") or data.get("embeddings")
            if embedding is None:
                raise ValueError("Missing embedding in Ollama response")
            if embedding and isinstance(embedding[0], (int, float)):
                embeddings.append(embedding)
            else:
                embeddings.extend(embedding)
        return embeddings

    def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        resp = requests.post(
            f"{self.base_url}/v1/embeddings",
            json={"model": self.model, "input": texts},
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        data = resp.json()
        if "data" in data:
            return [item["embedding"] for item in data["data"]]
        embedding = data.get("embedding") or data.get("embeddings")
        if embedding is None:
            raise ValueError("Missing embeddings in OpenAI-compatible response")
        if embedding and isinstance(embedding[0], (int, float)):
            return [embedding]
        return embedding
