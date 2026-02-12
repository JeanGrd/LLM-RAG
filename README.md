# LLM-RAG

Local RAG backend using:
- FastAPI (`/query`, `/v1/models`, `/v1/chat/completions`)
- Ollama for embeddings and generation
- ChromaDB local vector index
- Optional Open WebUI connected through `http://localhost:8000/v1`

## Quickstart

### 1) Prerequisites
- Python `3.11+`
- Ollama installed

### 2) Install project
```bash
cd /Users/jean/IdeaProjects/LLM-RAG
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e . --no-build-isolation
cp .env.example .env
```

Configuration model:
- `config/settings.yaml` = project defaults (shared baseline)
- `.env` = local overrides (machine/user specific)
- if the same key exists in both, `.env` wins
- keep `.env` minimal (set only what you override)

Model behavior:
- `/v1/models` lists all chat models installed in Ollama
- `/v1/chat/completions` uses the `model` sent in each request
- `ollama.llm_model` (or `OLLAMA_LLM_MODEL`) is only the default when no model is provided (for example `/query`); you can leave it blank and rely on request-time `model`
  - if you leave it blank, `/query` will return a 400; use `/v1/chat/completions` with `model`

### 3) Start Ollama and prepare models
```bash
ollama serve
```

In another terminal:
```bash
cd /Users/jean/IdeaProjects/LLM-RAG
source .venv/bin/activate
./scripts/setup/prepare_ollama.sh
```

To add more chat models:
```bash
ollama pull <model-name>
```

### 4) Build index
```bash
cd /Users/jean/IdeaProjects/LLM-RAG
source .venv/bin/activate
make reindex
```

### 5) Run backend
```bash
cd /Users/jean/IdeaProjects/LLM-RAG
make quick-backend   # alias: make quick
```

### 6) Run Open WebUI (optional)
```bash
cd /Users/jean/IdeaProjects/LLM-RAG
make quick-openwebui
```

Open WebUI must use a single connection:
- Base URL: `http://localhost:8000/v1`
- API key: any non-empty value

## Quick validation
```bash
curl http://localhost:8000/v1/models
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"Parle moi de Moko"}'
```

## Scripts layout
- `scripts/app/`: API and CLI entrypoints
- `scripts/data/`: ingestion
- `scripts/setup/`: environment and model setup
- `scripts/run/`: runtime launchers
