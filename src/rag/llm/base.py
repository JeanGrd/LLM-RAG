from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class LLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        raise NotImplementedError
