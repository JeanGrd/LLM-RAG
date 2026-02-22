# Deployment (RHEL 7.9/9.7) with llama.cpp

## Scope
Single-host deployment with:
- llama.cpp server (OpenAI-compatible HTTP API)
- this FastAPI RAG backend
- optional Open WebUI pointing only to `http://<host>:8000/v1`

## 1) Install Python 3.11 and llama.cpp
Ensure `python3.11` and `llama-server` are available on PATH. Build llama.cpp if needed:
```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp && cmake -B build && cmake --build build -j
sudo cp build/bin/llama-server /usr/local/bin/
```

## 2) Project setup
```bash
cd /opt/LLM-RAG
make install    # creates .venv-backend and .venv-openwebui
```

Configuration: `config/settings.yaml` is the single source of truth (no .env).

## 3) Start llama.cpp server
```bash
llama-server \
  --model /opt/models/your-chat-model.gguf \
  --host 0.0.0.0 --port 8080 \
  --api-key "" \
  --timeout 120
```

If you have additional remote endpoints, set `llama_cpp.rpc_targets` in `config/settings.yaml`.
For split chat/embedding servers, set `llama_cpp.embed_base_url`.

## 4) Build or rebuild the vector index
```bash
cd /opt/LLM-RAG
make ingest      # incremental
# or full rebuild:
make reingest
```

## 5) Run API
Configure `config/settings.yaml` (llama_cpp.base_url, llama_cpp.embed_base_url, llm_model, embed_model, server.host/port), puis :
```bash
cd /opt/LLM-RAG
make backend
```

## 6) Verify
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
