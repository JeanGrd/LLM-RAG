# LLM-RAG (English)

Fast, minimal Retrieval-Augmented Generation stack with:
- Ollama for embeddings + local/fallback LLM
- Optional cloud LLM adapter
- FastAPI backend exposing native and OpenAI-compatible endpoints (with streaming)
- Open WebUI supported (run separately; no Docker required)

## Quickstart
```bash
cd /Users/jean/IdeaProjects/LLM-RAG
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .                 # offline-friendly (setuptools)
./scripts/prepare_ollama.sh      # pull chat + embedding models if missing
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
One-liner “quick & dirty” runners:
```bash
./scripts/run_quick_mac.sh        # macOS
# or
./scripts/run_quick_rhel7.sh      # RHEL 7.9
# add FORCE_REINDEX=1 to rebuild the index
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

## Open WebUI (no Docker)
- Needs Python >=3.11 in a separate venv.
- Example:
```bash
python3.11 -m venv ~/openwebui-venv
source ~/openwebui-venv/bin/activate
pip install --upgrade pip
pip install open-webui
export OPENAI_API_BASE_URL=http://localhost:8000/v1
export OPENAI_API_KEY=local-rag
open-webui serve --host 0.0.0.0 --port 3000
```
- In the UI, pick any model from `/v1/models` (e.g., `qwen2.5:1.5b`) and enable “Stream response”.

## Data ingestion
```bash
python scripts/ingest.py          # reads data/raw, builds Chroma index
make reindex                      # full rebuild
```
The ingester pings Ollama first; ensure `ollama serve` is running and `nomic-embed-text` is pulled.
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
- Streaming headers disable proxy buffering (`X-Accel-Buffering: no`) to keep token flow live.
