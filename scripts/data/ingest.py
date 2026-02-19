from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List, Tuple

from tqdm import tqdm

import requests

from rag.embeddings import LlamaCppEmbeddings
from rag.llama_cpp import (
    build_endpoint_urls,
    filter_embedding_models,
    list_remote_models,
    resolve_model_alias,
)
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

    endpoints = build_endpoint_urls(settings.llama_cpp.base_url, settings.llama_cpp.resolved_rpc_targets())
    remote_models = list_remote_models(endpoints, settings.llama_cpp.timeout_s)
    if not remote_models:
        raise SystemExit(
            f"llama.cpp server not reachable at any configured endpoint ({', '.join(endpoints)}). "
            "Start it first (e.g. `llama-server --model path/to/model.gguf`)."
        )

    embed_model = (settings.llama_cpp.embed_model or "").strip()
    if not embed_model:
        embedding_models = filter_embedding_models(remote_models)
        if embedding_models:
            embed_model = embedding_models[0]
        elif (settings.llama_cpp.llm_model or "").strip():
            embed_model = settings.llama_cpp.llm_model
        else:
            embed_model = remote_models[0]
    embed_model = resolve_model_alias(embed_model, remote_models)
    embedder = LlamaCppEmbeddings(
        base_url=settings.llama_cpp.base_url,
        model=embed_model,
        timeout_s=settings.llama_cpp.timeout_s,
        rpc_targets=settings.llama_cpp.resolved_rpc_targets(),
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
                model = embed_model
                raise RuntimeError(
                    f"Embedding model '{model}' not available on llama.cpp server ({settings.llama_cpp.base_url}). "
                    "Load or serve the model, then retry."
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
