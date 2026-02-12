# Deployment (RHEL 7.9)

## Scope
Single-host deployment with:
- native Ollama
- this FastAPI RAG backend
- optional Open WebUI pointing only to `http://<host>:8000/v1`

## 1) Install Python 3.11 and virtualenv
```bash
cd /opt/LLM-RAG
sudo ./scripts/setup/install_python_311_rhel7.sh
source .venv/bin/activate
pip install -U pip
pip install -e .
cp .env.example .env
```

Config precedence:
- `config/settings.yaml` provides defaults
- `.env` overrides only what you set
- keep `.env` minimal (do not duplicate every key)

## 2) Start Ollama and pull required models
```bash
ollama serve
```

In another shell:
```bash
cd /opt/LLM-RAG
source .venv/bin/activate
./scripts/setup/prepare_ollama.sh
```

You can install additional chat models at any time:
```bash
ollama pull <model-name>
```

To ensure one specific chat model is present:
```bash
CHAT_MODEL=qwen2.5:1.5b ./scripts/setup/prepare_ollama.sh
```

## 3) Build or rebuild the vector index
```bash
cd /opt/LLM-RAG
source .venv/bin/activate
make reindex
```

## 4) Run API
```bash
cd /opt/LLM-RAG
source .venv/bin/activate
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_LLM_MODEL=qwen2.5:1.5b
HOST=0.0.0.0 PORT=8000 python scripts/app/run_api.py
```

## 5) Verify
```bash
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"Parle moi de Moko"}'
```

## Open WebUI integration
Configure one connection only:
- Base URL: `http://<host>:8000/v1`
- API key: any non-empty value

Do not enable direct Ollama integration in Open WebUI for this setup.

## Quick commands
Backend (auto-check deps, prepare models, index if needed):
```bash
make quick-backend
```

Open WebUI (auto-venv + fixed backend URL defaults):
```bash
make quick-openwebui
```
