from __future__ import annotations

import sqlite3
import sys
from typing import Iterable, List

MIN_SQLITE_VERSION = (3, 35, 0)


def _ensure_sqlite_compat() -> None:
    """
    Chroma requires sqlite >= 3.35. On older distros (e.g. RHEL 7),
    swap stdlib sqlite3 with pysqlite3 when available.
    """
    if sqlite3.sqlite_version_info >= MIN_SQLITE_VERSION:
        return
    try:
        import pysqlite3  # type: ignore[import-not-found]
    except ImportError as exc:
        version = sqlite3.sqlite_version
        raise RuntimeError(
            f"Detected sqlite {version}, but Chroma requires >= 3.35. "
            "Install fallback in the active venv: `pip install pysqlite3-binary`."
        ) from exc
    sys.modules["sqlite3"] = pysqlite3


_ensure_sqlite_compat()

try:
    import chromadb
except ImportError:  # pragma: no cover - optional dependency
    chromadb = None

from ..models import Document, RetrievalResult
from .base import VectorStore


class ChromaVectorStore(VectorStore):
    def __init__(self, index_dir: str, collection_name: str = "rag"):
        if chromadb is None:
            raise ImportError("chromadb is required for ChromaVectorStore")
        # Disable outbound telemetry by default (no PostHog calls).
        client_settings = chromadb.config.Settings(anonymized_telemetry=False)
        self.client = chromadb.PersistentClient(path=index_dir, settings=client_settings)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add(self, documents: Iterable[Document], embeddings: List[List[float]]) -> None:
        docs = list(documents)
        if not docs:
            return
        ids = [d.doc_id for d in docs]
        metadatas = [d.metadata for d in docs]
        texts = [d.text for d in docs]
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

    def query(self, query_embedding: List[float], top_k: int) -> List[RetrievalResult]:
        res = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        results: List[RetrievalResult] = []
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        ids = res.get("ids", [[]])[0]
        for doc_id, text, meta, dist in zip(ids, docs, metas, dists):
            score = 1.0 - float(dist) if dist is not None else 0.0
            results.append(
                RetrievalResult(
                    doc_id=doc_id,
                    text=text,
                    score=score,
                    metadata=meta or {},
                )
            )
        return results
