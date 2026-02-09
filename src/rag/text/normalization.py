from __future__ import annotations

import re


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()
