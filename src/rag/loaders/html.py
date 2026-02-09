from __future__ import annotations

from pathlib import Path
from typing import List

from bs4 import BeautifulSoup

from ..models import Document


def load_html(path: Path) -> List[Document]:
    raw = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(" ", strip=True)
    return [
        Document(
            doc_id=path.name,
            text=text,
            metadata={"source": str(path), "format": "html"},
        )
    ]
