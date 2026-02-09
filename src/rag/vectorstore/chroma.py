from __future__ import annotations

from typing import Iterable, List

import chromadb

from ..models import Document, RetrievalResult
from .base import VectorStore


class ChromaVectorStore(VectorStore):
    def __init__(self, index_dir: str, collection_name: str = "rag"):
        self.client = chromadb.PersistentClient(path=index_dir)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add(self, documents: Iterable[Document], embeddings: List[List[float]]) -> None:
        docs = list(documents)
        if not docs:
            return
        ids = [d.doc_id for d in docs]
        metadatas = [d.metadata for d in docs]
        texts = [d.text for d in docs]
        self.collection.add(
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
