from __future__ import annotations

from pathlib import Path
from typing import List
from xml.etree import ElementTree

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - optional dependency
    BeautifulSoup = None

from ..models import Document


def load_xml(path: Path) -> List[Document]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    text = _extract_text(raw)
    return [
        Document(
            doc_id=path.name,
            text=text,
            metadata={"source": str(path), "format": "xml"},
        )
    ]


def _extract_text(raw: str) -> str:
    if BeautifulSoup is not None:
        try:
            soup = BeautifulSoup(raw, "xml")
            text = soup.get_text(" ", strip=True)
            if text:
                return text
            soup = BeautifulSoup(raw, "html.parser")
            text = soup.get_text(" ", strip=True)
            if text:
                return text
        except Exception:
            # fall back to stdlib parser below
            pass
    try:
        root = ElementTree.fromstring(raw)
        return " ".join(root.itertext())
    except ElementTree.ParseError:
        return raw
