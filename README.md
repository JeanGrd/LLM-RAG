# LLM-RAG (FR/EN)

Bilingual Retrieval-Augmented Generation skeleton that uses:
- Cloud LLM for answer generation (primary)
- Local Ollama for embeddings and fallback LLM

## Quickstart (macOS)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

Configure:

```bash
cp .env.example .env
# edit .env with your cloud provider + Ollama settings
```

Ingest data:

```bash
python scripts/ingest.py
```

Query via CLI:

```bash
python scripts/query_cli.py "Quelle est la politique X ?"
```

Run API:

```bash
python scripts/run_api.py
```

## Project Layout

```
config/            # settings + logging
scripts/           # ingest, query, run API
src/rag/           # core modules
  api/             # FastAPI entrypoint
  embeddings/      # Ollama embeddings client
  llm/             # cloud + ollama LLM adapters
  loaders/         # PDF/Markdown/HTML loaders
  rag/             # pipeline + prompts
  text/            # normalization + chunking
  vectorstore/     # Chroma adapter
```

## Configuration

- `.env` (recommended) or `config/settings.yaml`
- Environment variables use nested names with `__`.

Examples:
- `OLLAMA__BASE_URL`
- `CLOUD__API_KEY`
- `RAG__TOP_K`
- `MIN_SCORE` (filter low-similarity results)

If you installed `qwen3` in Ollama, set the exact tag from `ollama list`, e.g.:
- `OLLAMA_LLM_MODEL=qwen3:4b`

## Notes

- Chunking is word-based (`chunk_size` and `chunk_overlap` are in words).
- Use a multilingual embedding model in Ollama for mixed FR/EN corpora.
- Cloud LLM adapter is generic; adjust payload/response for your provider.

## Docs
- `docs/architecture.md`
- `docs/data_format.md`
- `docs/deployment_rhel7.md`
