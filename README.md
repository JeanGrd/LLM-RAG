# LLM-RAG (English)

Fast, minimal Retrieval-Augmented Generation stack with:
- Ollama for embeddings + local/fallback LLM
- Optional cloud LLM adapter
- FastAPI backend exposing both native and OpenAI-compatible endpoints (with streaming)
- Open WebUI compose file wired to the backend

## Quickstart
```bash
cd /Users/jean/IdeaProjects/LLM-RAG
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .          # offline-friendly (setuptools)
```

Configure (env preferred):
```bash
cp .env.example .env
# adjust MODEL_NAME, OLLAMA_BASE_URL, keys, etc.
```

Run API (local host using Ollama):
```bash
export OLLAMA_BASE_URL=http://localhost:11434
export MODEL_PROVIDER=ollama
export MODEL_NAME=qwen2.5:1.5b   # or any installed chat model
python scripts/run_api.py        # listens on :8000
```

## Endpoints
- `/query` — simple JSON, non-stream, returns answer + sources.
- `/v1/models` — OpenAI-compatible list.
- `/v1/chat/completions` — OpenAI-compatible chat **with streaming SSE** (`stream=true`).

### cURL examples
Non-stream:
```bash
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is policy X?"}'
```
Stream (SSE):
```bash
curl -N -X POST http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen2.5:1.5b","stream":true,"messages":[{"role":"user","content":"Explain X"}]}'
```

## Open WebUI
```bash
# Start Ollama + Open WebUI (expects API on host:8000)
./scripts/compose.sh -f docker-compose.open-webui.yml up -d
```
- Choose the model exposed by `/v1/models` (e.g., `qwen2.5:1.5b`).
- Ensure “Stream response” is enabled in UI; API already streams.

## Data ingestion
```bash
python scripts/ingest.py          # reads data/raw, builds Chroma index
make reindex                      # full rebuild
```
Supports PDF, Markdown, HTML, XML/JSON/YAML, and plain text. Documents are chunked word-wise.

## Project layout (short)
```
config/            settings, logging
scripts/           ingest, query CLI, run API, compose helper
src/rag/           core (api, llm, embeddings, loaders, vectorstore, rag pipeline)
tests/             unit tests (loaders, settings, pipeline)
```

## Notes
- Default embeddings: `nomic-embed-text` (Ollama).
- Set `MODEL_NAME` to an installed chat model in Ollama (`ollama list`).
- If running inside Docker, Open WebUI reaches host API via `host.docker.internal:8000`.
- Streaming headers disable proxy buffering (`X-Accel-Buffering: no`) to keep token flow live.
