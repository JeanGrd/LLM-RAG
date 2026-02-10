from __future__ import annotations

import re
from pathlib import Path
from typing import List

try:
    import markdown  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    markdown = None

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - optional dependency
    BeautifulSoup = None

from ..models import Document


def load_markdown(path: Path) -> List[Document]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    html = markdown.markdown(raw) if markdown else raw
    if BeautifulSoup:
        rendered_text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    else:
        rendered_text = _render_markdown_plain(raw)
    if rendered_text:
        text = f"{raw}\n\nRendered text:\n{rendered_text}"
    else:
        text = raw
    return [
        Document(
            doc_id=path.name,
            text=text,
            metadata={"source": str(path), "format": "markdown"},
        )
    ]


def _render_markdown_plain(raw: str) -> str:
    # Very small fallback renderer: strip common Markdown tokens.
    text = re.sub(r"[#>*`~_\-]+", " ", raw)
    text = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", text)  # links
    text = re.sub(r"\s+", " ", text)
    return text.strip()
