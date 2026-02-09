from __future__ import annotations

from pathlib import Path
from typing import List

from ..models import Document


def load_text(path: Path) -> List[Document]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [
        Document(
            doc_id=path.name,
            text=text,
            metadata={"source": str(path), "format": "text"},
        )
    ]
