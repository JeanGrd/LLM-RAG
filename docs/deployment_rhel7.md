# Deployment (RHEL 7.9)

## Scope
Single-host deployment with:
- native Ollama
- this FastAPI RAG backend
- optional Open WebUI pointing only to `http://<host>:8000/v1`

## 1) Install Python 3.11 and virtualenv
```bash
cd /opt/LLM-RAG
sudo ./scripts/install_python_311_rhel7.sh
source .venv/bin/activate
pip install -U pip
pip install -e .
cp .env.example .env
```

## 2) Start Ollama and pull required models
```bash
ollama serve
```

In another shell:
```bash
cd /opt/LLM-RAG
source .venv/bin/activate
./scripts/prepare_ollama.sh
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
export MODEL_PROVIDER=ollama
export MODEL_NAME=qwen2.5:1.5b
HOST=0.0.0.0 PORT=8000 python scripts/run_api.py
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

