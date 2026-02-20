from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List, Tuple

from tqdm import tqdm

import requests

from rag.embeddings import LlamaCppEmbeddings
from rag.llama_cpp import (
    filter_embedding_models,
    resolve_embedding_endpoint,
    resolve_model_alias,
)
from rag.loaders import SUPPORTED_EXTENSIONS, load_document
from rag.models import Document
from rag.settings import load_settings
from rag.text.chunking import chunk_text
from rag.text.normalization import normalize_text
from rag.vectorstore import ChromaVectorStore

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "4"))
MAX_EMBED_RETRY_DEPTH = int(os.getenv("EMBED_RETRY_MAX_DEPTH", "12"))
MANIFEST_VERSION = 1
MANIFEST_FILENAME = ".ingest_manifest.json"


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


def file_signature(path: Path) -> dict:
    stat = path.stat()
    return {
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def load_manifest(index_dir: Path) -> dict:
    manifest_path = index_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        return {"version": MANIFEST_VERSION, "files": {}}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": MANIFEST_VERSION, "files": {}}
    files = payload.get("files")
    if not isinstance(files, dict):
        files = {}
    return {
        "version": payload.get("version", MANIFEST_VERSION),
        "files": files,
    }


def save_manifest(index_dir: Path, signatures: dict) -> None:
    payload = {
        "version": MANIFEST_VERSION,
        "files": signatures,
    }
    manifest_path = index_dir / MANIFEST_FILENAME
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def split_document_for_embedding(doc: Document) -> List[Document]:
    words = doc.text.split()
    parts: List[str]
    if len(words) >= 2:
        mid = len(words) // 2
        parts = [" ".join(words[:mid]), " ".join(words[mid:])]
    else:
        text = doc.text.strip()
        if len(text) < 2:
            return []
        mid = len(text) // 2
        parts = [text[:mid], text[mid:]]

    split_docs: List[Document] = []
    for idx, part in enumerate(parts, start=1):
        normalized = part.strip()
        if not normalized:
            continue
        split_docs.append(
            Document(
                doc_id=f"{doc.doc_id}#part={idx}",
                text=normalized,
                metadata=dict(doc.metadata),
            )
        )
    return split_docs


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into the vector store")
    parser.add_argument("--data-dir", default=None, help="Override data dir")
    args = parser.parse_args()

    settings = load_settings()
    data_dir = Path(args.data_dir or settings.paths.data_dir) / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)
    index_dir = Path(settings.paths.index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)

    llm_base_url = settings.llama_cpp.base_url
    rpc_targets = settings.llama_cpp.resolved_rpc_targets()
    embed_base_url, embed_rpc_targets, remote_models = resolve_embedding_endpoint(
        llm_base_url=llm_base_url,
        configured_embed_base_url=settings.llama_cpp.embed_base_url,
        rpc_targets=rpc_targets,
        timeout_s=settings.llama_cpp.timeout_s,
    )
    if not remote_models:
        raise SystemExit(
            f"Embedding endpoint not reachable ({embed_base_url}). "
            "Start an embedding-capable llama.cpp server first."
        )
    if embed_base_url.rstrip("/") != llm_base_url.rstrip("/"):
        print(f"[ingest] Using embedding endpoint: {embed_base_url}")

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
        base_url=embed_base_url,
        model=embed_model,
        timeout_s=settings.llama_cpp.timeout_s,
        rpc_targets=embed_rpc_targets,
    )
    store = ChromaVectorStore(index_dir=settings.paths.index_dir)

    files = collect_files(data_dir)
    if not files:
        print(f"No supported files found in {data_dir}")
        return

    manifest = load_manifest(index_dir)
    previous_files = manifest.get("files", {})
    current_signatures = {str(path): file_signature(path) for path in files}

    changed_files = [
        path
        for path in files
        if previous_files.get(str(path)) != current_signatures[str(path)]
    ]
    removed_sources = [source for source in previous_files.keys() if source not in current_signatures]

    unchanged_count = len(files) - len(changed_files)
    print(f"Discovered {len(files)} files ({len(changed_files)} changed, {unchanged_count} unchanged)")
    if removed_sources:
        deleted = store.delete_by_sources(removed_sources)
        print(f"Removed {deleted} stale chunks from {len(removed_sources)} deleted/changed sources")

    if not changed_files and not removed_sources:
        print("Index is already up to date")
        return

    skipped_files: List[Tuple[Path, str]] = []
    batch: List[Document] = []
    total_chunks = 0
    ingested_files = 0

    def embed_with_retry(docs: List[Document], depth: int = 0) -> Tuple[List[Document], List[List[float]]]:
        if depth > MAX_EMBED_RETRY_DEPTH:
            raise RuntimeError(
                "Exceeded embedding retry depth while trying to split oversized chunks. "
                "Reduce CHUNK_SIZE and retry."
            )
        try:
            embeddings = embedder.embed_texts([d.text for d in docs])
            return docs, embeddings
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            message = str(exc).lower()
            if status_code == 404:
                model = embed_model
                raise RuntimeError(
                    f"Embedding model '{model}' not available on llama.cpp server ({embed_base_url}). "
                    "Load or serve the model, then retry."
                ) from exc

            # llama.cpp may return transient 5xx on bigger embedding batches.
            # Retry by splitting the batch to isolate problematic requests.
            if status_code in {500, 502, 503, 504} and len(docs) > 1:
                split_at = len(docs) // 2
                print(
                    f"[ingest] Embedding batch failed with HTTP {status_code}; "
                    f"retrying in smaller batches ({len(docs)} -> {split_at}+{len(docs)-split_at})"
                )
                left_docs, left_embeddings = embed_with_retry(docs[:split_at], depth + 1)
                right_docs, right_embeddings = embed_with_retry(docs[split_at:], depth + 1)
                return left_docs + right_docs, left_embeddings + right_embeddings

            if (
                status_code in {500, 502, 503, 504}
                and len(docs) == 1
                and "too large to process" in message
            ):
                doc = docs[0]
                split_docs = split_document_for_embedding(doc)
                if len(split_docs) >= 2:
                    source = doc.metadata.get("source") or doc.doc_id
                    print(
                        f"[ingest] Chunk too large for embeddings; splitting source '{source}' "
                        f"into {len(split_docs)} smaller parts."
                    )
                    left_docs, left_embeddings = embed_with_retry([split_docs[0]], depth + 1)
                    right_docs, right_embeddings = embed_with_retry([split_docs[1]], depth + 1)
                    return left_docs + right_docs, left_embeddings + right_embeddings

            if status_code in {500, 502, 503, 504}:
                source = docs[0].metadata.get("source") if docs else None
                source_hint = str(source) if source else (docs[0].doc_id if docs else "unknown")
                raise RuntimeError(
                    f"Embedding endpoint failed for source '{source_hint}' "
                    f"(HTTP {status_code}, model '{embed_model}', endpoint '{embed_base_url}'). "
                    "Start a dedicated embedding server and set LLAMA_CPP_EMBED_BASE_URL / LLAMA_CPP_EMBED_MODEL."
                ) from exc

            raise

    def flush_batch() -> None:
        nonlocal batch, total_chunks
        if not batch:
            return
        docs_to_store, embeddings = embed_with_retry(batch)
        store.add(docs_to_store, embeddings)
        total_chunks += len(docs_to_store)
        batch = []

    for file in tqdm(changed_files, desc="Indexing"):
        try:
            docs = load_document(file)
        except Exception as exc:  # noqa: BLE001
            skipped_files.append((file, str(exc)))
            continue

        store.delete_by_sources([str(file)])
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

    skipped_sources = {str(path) for path, _ in skipped_files}
    for source in skipped_sources:
        current_signatures.pop(source, None)
    save_manifest(index_dir, current_signatures)

    if skipped_files:
        print("\nSkipped files:")
        for file, reason in skipped_files:
            print(f"- {file}: {reason}")


if __name__ == "__main__":
    main()
