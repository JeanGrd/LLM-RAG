from __future__ import annotations

from pathlib import Path
from typing import List

from .html import load_html
from .markdown import load_markdown
from .pdf import load_pdf
from .text import load_text
from ..models import Document


SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".html", ".htm", ".txt"}


def load_document(path: Path) -> List[Document]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path)
    if suffix in {".md", ".markdown"}:
        return load_markdown(path)
    if suffix in {".html", ".htm"}:
        return load_html(path)
    if suffix == ".txt":
        return load_text(path)
    raise ValueError(f"Unsupported file type: {path}")
