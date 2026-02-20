from __future__ import annotations

from typing import Any, List


def flatten_structured_data(data: Any, prefix: str = "") -> List[str]:
    lines: List[str] = []
    if isinstance(data, dict):
        if not data and prefix:
            lines.append(f"{prefix}: {{}}")
        for key, value in data.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            lines.extend(flatten_structured_data(value, next_prefix))
        return lines

    if isinstance(data, list):
        if not data:
            lines.append(f"{prefix}: []" if prefix else "[]")
        for idx, value in enumerate(data):
            next_prefix = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
            lines.extend(flatten_structured_data(value, next_prefix))
        return lines

    scalar = _to_scalar_text(data)
    if prefix:
        lines.append(f"{prefix}: {scalar}")
    else:
        lines.append(scalar)
    return lines


def _to_scalar_text(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
