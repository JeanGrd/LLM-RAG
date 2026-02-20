from __future__ import annotations

import re
from pathlib import Path
from typing import List

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - optional dependency
    BeautifulSoup = None

from ..models import Document


def load_html(path: Path) -> List[Document]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if BeautifulSoup:
        text = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    else:
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()
    return [
        Document(
            doc_id=path.name,
            text=text,
            metadata={"source": str(path), "format": "html"},
        )
    ]
