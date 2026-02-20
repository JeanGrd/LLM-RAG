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
- `LLAMA_CPP_EMBED_BASE_URL` (optional dedicated embedding endpoint; defaults to `LLAMA_CPP_BASE_URL`)
- `LLAMA_CPP_LLM_MODEL` (model id from `/v1/models`; required for `/query`, optional for `/v1/chat/completions`)
- `LLAMA_CPP_EMBED_MODEL` (optional model id; if empty, backend auto-picks an embedding model when available)
- `LLAMA_CPP_RPC_TARGETS` for extra endpoints
- `LLAMA_SERVER_RPC_TARGETS` for repeated `--rpc` on llama-server

### 3) Build index
`make ingest` auto-starts a dedicated embedding `llama-server` (on `127.0.0.1:8081`) when needed.
The temporary embedding server started by `make ingest` is stopped at the end.
You can still run a chat server separately with `make llama`.

Then run:
```bash
cd /Users/jean/IdeaProjects/LLM-RAG
make ingest
```
`make ingest` is incremental (re-indexes only changed files).  
`make reingest` force un rebuild complet (reset de l'index, puis ingest de tous les fichiers).

### 4) Run backend
```bash
cd /Users/jean/IdeaProjects/LLM-RAG
make backend
```
`make backend` no longer triggers ingest automatically.
Run `make ingest` / `make reingest` explicitly when you want to rebuild the index.

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
# increase embedding token budget if you see "input is too large to process"
LLAMA_BATCH_SIZE=1024 LLAMA_UBATCH_SIZE=1024 make llama
# optional repeated --rpc
LLAMA_SERVER_RPC_TARGETS=192.168.1.40:50052,192.168.1.41:50052 make llama
```

### 5) Full stack lifecycle
```bash
# starts chat llama + embedding llama + backend + openwebui in background
make up

# stops what make up started
make down

# local diagnostics (venv, models, endpoints, config sanity)
make doctor
```

### 6) Run Open WebUI (optional)
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
  - run a dedicated embedding endpoint and set `LLAMA_CPP_EMBED_BASE_URL`
  - optionally set `LLAMA_CPP_EMBED_MODEL` to an embedding-capable model id
  - fallback mode is still available (direct LLM response without retrieval context)
- If ingestion fails with `500` on `/v1/embeddings`:
  - `make ingest` now auto-starts an embedding server if needed
  - you can choose the embedding GGUF with `LLAMA_EMBED_MODEL=/path/to/model.gguf`
  - if you already have a dedicated endpoint, set `LLAMA_CPP_EMBED_BASE_URL=http://host:port`
  - rerun `make reingest`
  - or increase llama-server `LLAMA_UBATCH_SIZE` (for example `1024`)
- To stop everything started by `make up` (including managed embedding server): `make down`

## Scripts layout
- `scripts/app/`: API and CLI entrypoints
- `scripts/data/`: ingestion
- `scripts/run/`: runtime launchers (`backend.sh`, `ingest.sh`, `openwebui.sh`, `llama_server.sh`, `up.sh`, `down.sh`, `doctor.sh`)
