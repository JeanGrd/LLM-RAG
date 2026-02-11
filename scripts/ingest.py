from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List, Tuple

import requests
from tqdm import tqdm

from rag.embeddings import OllamaEmbeddings
from rag.loaders import SUPPORTED_EXTENSIONS, load_document
from rag.models import Document
from rag.settings import load_settings
from rag.text.chunking import chunk_text
from rag.text.normalization import normalize_text
from rag.vectorstore import ChromaVectorStore

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "8"))


def collect_files(root: Path) -> List[Path]:
    return sorted(
        [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    )


def build_chunks(documents: List[Document], chunk_size: int, overlap: int) -> List[Document]:
    chunks: List[Document] = []
    for doc in documents:
        normalized = normalize_text(doc.text)
        for idx, chunk in enumerate(chunk_text(normalized, chunk_size, overlap)):
            chunk_id = f"{doc.doc_id}#chunk={idx+1}"
            chunks.append(
                Document(
                    doc_id=chunk_id,
                    text=chunk,
                    metadata=doc.metadata,
                )
            )
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into the vector store")
    parser.add_argument("--data-dir", default=None, help="Override data dir")
    args = parser.parse_args()

    settings = load_settings()
    data_dir = Path(args.data_dir or settings.paths.data_dir) / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Quick readiness probe so we fail fast if Ollama isn't running.
    try:
        resp = requests.get(f"{settings.ollama.base_url}/api/tags", timeout=5)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"Ollama not reachable at {settings.ollama.base_url}. "
            "Start it first: `ollama serve` (or ensure the service is up)."
        ) from exc

    embedder = OllamaEmbeddings(
        base_url=settings.ollama.base_url,
        model=settings.ollama.embed_model,
        timeout_s=settings.ollama.timeout_s,
    )
    store = ChromaVectorStore(index_dir=settings.paths.index_dir)

    files = collect_files(data_dir)
    if not files:
        print(f"No supported files found in {data_dir}")
        return

    skipped_files: List[Tuple[Path, str]] = []
    batch: List[Document] = []
    total_chunks = 0
    ingested_files = 0

    def flush_batch() -> None:
        nonlocal batch, total_chunks
        if not batch:
            return
        try:
            embeddings = embedder.embed_texts([d.text for d in batch])
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                model = settings.ollama.embed_model
                raise RuntimeError(
                    f"Embedding model '{model}' not found on Ollama ({settings.ollama.base_url}). "
                    f"Install it first, e.g.: make ollama-pull MODEL={model}"
                ) from exc
            raise
        store.add(batch, embeddings)
        total_chunks += len(batch)
        batch = []

    for file in tqdm(files, desc="Indexing"):
        try:
            docs = load_document(file)
        except Exception as exc:  # noqa: BLE001
            skipped_files.append((file, str(exc)))
            continue

        file_chunks = build_chunks(docs, settings.rag.chunk_size, settings.rag.chunk_overlap)
        if not file_chunks:
            continue
        ingested_files += 1
        for doc in file_chunks:
            batch.append(doc)
            if len(batch) >= BATCH_SIZE:
                flush_batch()

    flush_batch()

    if total_chunks == 0:
        print("No chunks were indexed")
    else:
        print(f"Indexed {total_chunks} chunks from {ingested_files} files")

    if skipped_files:
        print("\nSkipped files:")
        for file, reason in skipped_files:
            print(f"- {file}: {reason}")


if __name__ == "__main__":
    main()
