from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class Embeddings(ABC):
    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError
