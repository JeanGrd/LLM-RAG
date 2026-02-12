# Architecture

## Overview

The system follows a classic local RAG pipeline:
- Ollama for generation.
- Ollama embeddings for retrieval.
- ChromaDB local persistent vector index.

## Data Flow

1. Ingestion
   - Sources: PDF + Markdown + HTML (Wiki exports).
   - Loaders extract text.
   - Text normalization + chunking.
   - Embeddings computed with Ollama.
   - Vectors stored in ChromaDB (local persistent store).

2. Retrieval
   - Query embedded with Ollama.
   - Top-K vectors fetched from Chroma.

3. Generation
   - Prompt built with retrieved context.
   - Ollama chat model generates the response from retrieved context.

## Modules

- `rag/loaders/` loaders for file types.
- `rag/text/` normalization + chunking.
- `rag/embeddings/` Ollama client.
- `rag/vectorstore/` Chroma adapter (swapable).
- `rag/llm/` Ollama adapter.
- `rag/rag/` orchestration and prompts.
- `rag/api/` FastAPI service.
  - Native endpoint: `/query`
  - OpenAI-compatible endpoints: `/v1/models`, `/v1/chat/completions`

## Scaling Notes

- Replace Chroma with a service-backed vector store (Qdrant, Milvus) when needed.
- For hybrid search, add a BM25 layer and merge scores.
- Add a reranker for improved precision.
