# Deployment (RHEL 7.9) with llama.cpp

## Scope
Single-host deployment with:
- llama.cpp server (OpenAI-compatible HTTP API)
- this FastAPI RAG backend
- optional Open WebUI pointing only to `http://<host>:8000/v1`

## 1) Install Python 3.11 and virtualenv
```bash
cd /opt/LLM-RAG
sudo ./scripts/setup/install_python_311_rhel7.sh
source .venv/bin/activate
pip install -U pip
pip install -e .
cp .env .env.local  # optional personal copy
```

Config precedence:
- `config/settings.yaml` provides defaults
- `.env` overrides only what you set
- keep `.env` minimal (do not duplicate every key)

## 2) Start llama.cpp server
```bash
llama-server \
  --model /opt/models/your-chat-model.gguf \
  --host 0.0.0.0 --port 8080 \
  --api-key "" \
  --timeout 120
```

If you have additional remote endpoints, set `LLAMA_CPP_RPC_TARGETS`.
For split chat/embedding servers, also set `LLAMA_CPP_EMBED_BASE_URL`.

## 3) Build or rebuild the vector index
```bash
cd /opt/LLM-RAG
source .venv/bin/activate
make ingest      # incremental
# or full rebuild:
make reingest
```

## 4) Run API
```bash
cd /opt/LLM-RAG
source .venv/bin/activate
export LLAMA_CPP_BASE_URL=http://127.0.0.1:8080
export LLAMA_CPP_EMBED_BASE_URL=http://127.0.0.1:8081  # optional split endpoint
# Use the exact id returned by: curl http://127.0.0.1:8080/v1/models
export LLAMA_CPP_LLM_MODEL=your-chat-model.gguf
HOST=0.0.0.0 PORT=8000 python scripts/app/run_api.py
```

## 5) Verify
```bash
curl -X POST http://127.0.0.1:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"Parle moi de Moko"}'
```

## Open WebUI integration
Configure one connection only:
- Base URL: `http://<host>:8000/v1`
- API key: any non-empty value

Do not point Open WebUI directly at the llama.cpp server when using this backend.

## Quick commands
Backend (auto-check deps, index if needed):
```bash
make backend
```

Open WebUI (auto-venv + fixed backend URL defaults):
```bash
make openwebui
```
