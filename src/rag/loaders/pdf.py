from __future__ import annotations

from pathlib import Path
from typing import List

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - optional dependency
    PdfReader = None

from ..models import Document


def load_pdf(path: Path) -> List[Document]:
    if PdfReader is None:
        raise ImportError("pypdf is required for PDF loading")
    reader = PdfReader(str(path))
    docs: List[Document] = []
    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        doc_id = f"{path.name}#page={idx+1}"
        docs.append(
            Document(
                doc_id=doc_id,
                text=text,
                metadata={"source": str(path), "page": idx + 1},
            )
        )
    return docs
