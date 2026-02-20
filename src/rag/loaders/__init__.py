from __future__ import annotations

from pathlib import Path
from typing import List

from .html import load_html
from .json import load_json
from .markdown import load_markdown
from .pdf import load_pdf
from .text import load_text
from .xml import load_xml
from .yaml import load_yaml
from ..models import Document


TEXT_EXTENSIONS = {
    ".txt",
    ".log",
    ".cfg",
    ".conf",
    ".ini",
    ".toml",
    ".csv",
    ".tsv",
    ".rst",
}
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".md",
    ".markdown",
    ".html",
    ".htm",
    ".xml",
    ".json",
    ".jsonl",
    ".ndjson",
    ".yaml",
    ".yml",
    *TEXT_EXTENSIONS,
}


def load_document(path: Path) -> List[Document]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path)
    if suffix in {".md", ".markdown"}:
        return load_markdown(path)
    if suffix in {".html", ".htm"}:
        return load_html(path)
    if suffix == ".xml":
        return load_xml(path)
    if suffix in {".json", ".jsonl", ".ndjson"}:
        return load_json(path)
    if suffix in {".yaml", ".yml"}:
        return load_yaml(path)
    if suffix in TEXT_EXTENSIONS:
        return load_text(path)
    raise ValueError(f"Unsupported file type: {path}")
