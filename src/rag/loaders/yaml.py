from __future__ import annotations

from pathlib import Path
from typing import List

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None

from ..models import Document
from .structured import flatten_structured_data


def load_yaml(path: Path) -> List[Document]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    data = _safe_load_yaml(raw)

    if data is None:
        text = raw
    else:
        flattened = "\n".join(flatten_structured_data(data))
        dumped = yaml.safe_dump(data, sort_keys=False, allow_unicode=False) if yaml else str(data)
        text = f"Structured fields:\n{flattened}\n\nRaw YAML:\n{dumped}"

    return [
        Document(
            doc_id=path.name,
            text=text,
            metadata={"source": str(path), "format": "yaml"},
        )
    ]


def _safe_load_yaml(raw: str):
    if yaml is None:
        return _naive_yaml_parse(raw)
    try:
        return yaml.safe_load(raw)
    except yaml.YAMLError:
        return _naive_yaml_parse(raw)


def _naive_yaml_parse(raw: str):
    """
    Minimal YAML parser to keep tests working when PyYAML is unavailable.
    Handles simple nested dicts via indentation only.
    """
    result: dict = {}
    stack = [(0, result)]
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, _, value = line.strip().partition(":")
        value = value.strip() or None
        while stack and indent < stack[-1][0]:
            stack.pop()
        parent = stack[-1][1] if stack else result
        if value is None:
            container: dict = {}
            parent[key] = container
            stack.append((indent + 2, container))
        else:
            parent[key] = value
    return result
