from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from ..models import Document
from .structured import flatten_structured_data


def load_json(path: Path) -> List[Document]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    data = _parse_json_by_extension(raw, path.suffix.lower())
    if data is None:
        text = raw
    else:
        flattened = "\n".join(flatten_structured_data(data))
        pretty = json.dumps(data, ensure_ascii=False, indent=2)
        text = f"Structured fields:\n{flattened}\n\nRaw JSON:\n{pretty}"
    return [
        Document(
            doc_id=path.name,
            text=text,
            metadata={"source": str(path), "format": "json"},
        )
    ]


def _parse_json_by_extension(raw: str, suffix: str) -> Any:
    if suffix in {".jsonl", ".ndjson"}:
        return _parse_json_lines(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _parse_json_lines(raw: str) -> List[Any]:
    rows: List[Any] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"raw": line})
    return rows
