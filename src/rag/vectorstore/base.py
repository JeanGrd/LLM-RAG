from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List

from ..models import Document, RetrievalResult


class VectorStore(ABC):
    @abstractmethod
    def add(self, documents: Iterable[Document], embeddings: List[List[float]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def query(self, query_embedding: List[float], top_k: int) -> List[RetrievalResult]:
        raise NotImplementedError
