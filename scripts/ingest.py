from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List

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
    files: List[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
    return files


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

    files = collect_files(data_dir)
    if not files:
        print(f"No supported files found in {data_dir}")
        return

    embedder = OllamaEmbeddings(
        base_url=settings.ollama.base_url,
        model=settings.ollama.embed_model,
        timeout_s=settings.ollama.timeout_s,
    )
    store = ChromaVectorStore(index_dir=settings.paths.index_dir)

    all_chunks: List[Document] = []
    for file in tqdm(files, desc="Loading"):
        docs = load_document(file)
        all_chunks.extend(build_chunks(docs, settings.rag.chunk_size, settings.rag.chunk_overlap))

    if not all_chunks:
        print("No chunks to index")
        return

    texts = [c.text for c in all_chunks]
    for i in tqdm(range(0, len(texts), BATCH_SIZE), desc="Embedding"):
        batch_docs = all_chunks[i : i + BATCH_SIZE]
        batch_embeddings = embedder.embed_texts([d.text for d in batch_docs])
        store.add(batch_docs, batch_embeddings)

    print(f"Indexed {len(all_chunks)} chunks")


if __name__ == "__main__":
    main()
