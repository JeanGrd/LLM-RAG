# LLM-RAG

Lean Retrieval-Augmented Generation backend with:
- FastAPI API (`/query` and OpenAI-compatible `/v1/*`)
- Chroma vector index
- Ollama for embeddings and generation
- Open WebUI support through a single backend endpoint

## Installation

### Prerequisites
- Python `3.11+`
- Ollama installed and running (`ollama serve`)

### Setup
```bash
cd /Users/jean/IdeaProjects/LLM-RAG
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
cp .env.example .env
```

## Prepare Models
```bash
./scripts/prepare_ollama.sh
```
Default models:
- chat: `qwen2.5:1.5b`
- embeddings: `nomic-embed-text`

Override with:
```bash
CHAT_MODEL=phi3:mini EMBED_MODEL=nomic-embed-text ./scripts/prepare_ollama.sh
```

## Build Index
```bash
python scripts/ingest.py
```

Full rebuild:
```bash
make reindex
```

## Run API
```bash
export OLLAMA_BASE_URL=http://localhost:11434
export MODEL_PROVIDER=ollama
export MODEL_NAME=qwen2.5:1.5b
python scripts/run_api.py
```

API is available at `http://localhost:8000`.

If you get `ModuleNotFoundError: No module named 'uvicorn'`, install project dependencies in the venv:
```bash
pip install -e . --no-build-isolation
```

## Open WebUI (Single Source)

Run Open WebUI separately (its own virtual environment is recommended), then configure only:
- Base URL: `http://localhost:8000/v1`
- API key: any non-empty value (for example `local-rag`)

Important:
- Do not use direct Ollama integration in Open WebUI for this project.
- Use only the OpenAI-compatible connection above, otherwise requests can bypass RAG.

## Endpoints
- `POST /query`: simple non-streaming RAG response with sources
- `GET /v1/models`: returns the single configured runtime model
- `POST /v1/chat/completions`: OpenAI-compatible chat (supports `stream=true`)
- `GET /health`: health and runtime information

## cURL Examples
Non-stream:
```bash
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"Parle moi de Moko"}'
```

Stream:
```bash
curl -N -X POST http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen2.5:1.5b","stream":true,"messages":[{"role":"user","content":"Parle moi de Moko"}]}'
```

## Optional Helper Scripts
- `scripts/install_python_311_rhel7.sh`
- `scripts/install_python_311_mac.sh`
- `scripts/run_quick_rhel7.sh`
- `scripts/run_quick_mac.sh`

These are convenience scripts only. The manual setup above is the canonical path.
