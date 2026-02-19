# LLM-RAG (llama.cpp)

Local RAG backend using:
- FastAPI (`/query`, `/v1/models`, `/v1/chat/completions`)
- llama.cpp server (OpenAI-compatible HTTP API) for embeddings + generation
- ChromaDB local vector index
- Optional Open WebUI pointing to `http://127.0.0.1:8000/v1`

## Quickstart

### 1) Prerequisites
- Python `3.11+`
- A running llama.cpp server (e.g. `llama-server` from the upstream repo)

#### Models location
- Put your `.gguf` files in `./models/` (created in the repo root).
- Recommended starter for your Apple M4 Pro: `ggml-org_gemma-3-1b-it-GGUF_gemma-3-1b-it-Q4_K_M.gguf`.
- Helper to launch the server using the first `.gguf` in `models/`:
  ```bash
  ./scripts/run/llama_server.sh                 # auto-picks first .gguf
  # or pick a specific file
  ./scripts/run/llama_server.sh ./models/your-chat-model.gguf
  ```

Example server command:
```bash
llama-server \
  --model /path/to/your-chat-model.gguf \
  --host 0.0.0.0 --port 8080 \
  --api-key "" \
  --timeout 120
```
If you have multiple remote endpoints, set `LLAMA_CPP_RPC_TARGETS` (comma/semicolon separated).
The backend round-robins across `LLAMA_CPP_BASE_URL` and RPC targets.

### 2) Install project
```bash
cd /Users/jean/IdeaProjects/LLM-RAG
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e . --no-build-isolation
cp .env .env.local  # optional personal copy
```

Configuration model:
- `config/settings.yaml` = project defaults (shared baseline)
- `.env` = local overrides (machine/user specific)
- if the same key exists in both, `.env` wins
- keep `.env` minimal (set only what you override)

Key settings (see `.env`):
- `LLAMA_CPP_BASE_URL` (default `http://127.0.0.1:8080`)
- `LLAMA_CPP_LLM_MODEL` (model id from `/v1/models`; required for `/query`, optional for `/v1/chat/completions`)
- `LLAMA_CPP_EMBED_MODEL` (optional model id; if empty, backend auto-picks an embedding model when available)
- `LLAMA_CPP_RPC_TARGETS` for extra endpoints
- `LLAMA_SERVER_RPC_TARGETS` for repeated `--rpc` on llama-server

### 3) Build index
Start the llama.cpp server first, then:
```bash
cd /Users/jean/IdeaProjects/LLM-RAG
source .venv/bin/activate
make ingest
```

### 4) Run backend
```bash
cd /Users/jean/IdeaProjects/LLM-RAG
make backend
```

Start llama.cpp:
```bash
# inspect local + remote models quickly
make models

# Chat server (default port 8080). Embeddings endpoint is enabled by default.
make llama
# or pick one explicitly
LLAMA_MODEL=/path/to/model.gguf make llama
# optional tuning
LLAMA_THREADS=8 LLAMA_THREADS_BATCH=8 LLAMA_PARALLEL=4 make llama
# optional repeated --rpc
LLAMA_SERVER_RPC_TARGETS=192.168.1.40:50052,192.168.1.41:50052 make llama
```

### 5) Run Open WebUI (optional)
```bash
cd /Users/jean/IdeaProjects/LLM-RAG
make openwebui
```

Open WebUI must use a single connection:
- Base URL: `http://127.0.0.1:8000/v1`
- API key: any non-empty value

## Quick validation
```bash
curl http://127.0.0.1:8000/v1/models
curl -X POST http://127.0.0.1:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"Parle moi de Moko"}'
```

## Troubleshooting
- If backend returns 502 and llama-server logs `POST /v1/embeddings ... 400`:
  - backend now falls back to direct LLM response (no retrieval context)
  - to restore full RAG quality, set `LLAMA_CPP_EMBED_MODEL` to an embedding-capable model id

## Scripts layout
- `scripts/app/`: API and CLI entrypoints
- `scripts/data/`: ingestion
- `scripts/run/`: runtime launchers
