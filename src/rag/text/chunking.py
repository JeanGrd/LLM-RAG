from __future__ import annotations

from typing import Iterable, List


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be < chunk_size")

    words = text.split()
    if not words:
        return []

    chunks: List[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start = end - overlap
    return chunks


def chunk_many(texts: Iterable[str], chunk_size: int, overlap: int) -> List[str]:
    all_chunks: List[str] = []
    for text in texts:
        all_chunks.extend(chunk_text(text, chunk_size, overlap))
    return all_chunks
