from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Document:
    doc_id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    doc_id: str
    text: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RagResponse:
    answer: str
    sources: List[RetrievalResult]
    model: str
    used_fallback: bool
