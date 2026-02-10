from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Optional


class LLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        raise NotImplementedError

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Iterable[str]:
        """
        Optional streaming interface. Default: non-streaming.
        Implementations can override to yield incremental text chunks.
        """
        yield self.generate(prompt, system_prompt=system_prompt)
