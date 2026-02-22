# LLM-RAG (llama.cpp)

Local RAG stack: FastAPI backend + native `llama-server` (chat + embeddings) + Chroma vector index + optional Open WebUI.

## Quickstart

Prerequisites
- Python 3.11 available as `python3.11`.
- `llama-server` binary installed (Qwen3-capable). Build from [ggerganov/llama.cpp](https://github.com/ggerganov/llama.cpp) (`cmake -B build && cmake --build build -j && sudo cp build/bin/llama-server /usr/local/bin`), or use a packaged binary if available.
- Models under `./models/`. Recommended layout:
  - `models/chat/` for chat/inference GGUFs
  - `models/embed/` for embedding GGUFs
  - If multiple GGUFs are present and `config/settings.yaml` does not name one, startup will list the choices and exit.
- Optional local caches/tmp (keep downloads inside the repo):
  ```bash
  mkdir -p .cache/pip tmp
  export PIP_CACHE_DIR="$PWD/.cache/pip"
  export TMPDIR="$PWD/tmp"
  ```

Install (creates `.venv-backend` and `.venv-openwebui`)
```bash
make install
```

Bring up full stack (waits for readiness)
```bash
make up   # chat 8080, embed 8081, backend 8000, Open WebUI 3000
```
Logs/PIDs in `.run/`; WebUI data in `.openwebui/`.

Ingest
```bash
make ingest     # incremental, auto-starts a temporary embed server if needed
make reingest   # reset index then ingest from scratch
```

Stop
```bash
make down
```

Configuration (YAML-only)
- `config/settings.yaml` is the single source of truth (no `.env`).
- Set `llama_cpp.base_url`, `embed_base_url`, `llm_model`, `embed_model`; API host/port under `server.*`; storage under `paths.*`; RAG params under `rag.*`; ingest params under `ingest.*`.
- From scratch: put your model paths in `config/settings.yaml`, then `make install && make up && make reingest`.
- Linux note: requires Python 3.11 and a recent GCC/CMake to build llama.cpp; ensure `llama-server` is installed on PATH.

Quick validation
```bash
curl http://127.0.0.1:8000/v1/models
curl -X POST http://127.0.0.1:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"Tell me about Moko"}'
```

Troubleshooting
- Keep pip downloads and temp files inside the repo:
  ```bash
  mkdir -p .cache/pip tmp
  export PIP_CACHE_DIR="$PWD/.cache/pip"
  export TMPDIR="$PWD/tmp"
  ```
- To reuse the chat server for embeddings, set `llama_cpp.embed_base_url` equal to `llama_cpp.base_url` or export `USE_SINGLE_LLAMA=1` before `make up`.
- `/v1/embeddings` 400/502: ensure the embedding server is running with `--embeddings` and that `llama_cpp.embed_model` points to a valid GGUF.
- Ingest failures: verify the embedding endpoint in `llama_cpp.embed_base_url` is reachable; run `make reingest` to rebuild the index from scratch.
- Stop everything started by `make up`: `make down`.

Scripts layout
- `scripts/app/`: API and CLI entrypoints
- `scripts/data/`: ingestion
- `scripts/run/`: launchers (`backend.sh`, `ingest.sh`, `openwebui.sh`, `llama.sh`, `up.sh`, `down.sh`)
