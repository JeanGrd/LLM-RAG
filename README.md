# LLM-RAG (llama.cpp)

Local RAG stack: FastAPI backend + llama.cpp HTTP server (chat + embeddings) + Chroma vector index.

## Quickstart (simplifié)

1) Prérequis
- Python 3.11 (`python3.11` dans le PATH)
- Binaire `llama-server` récent (support Qwen3). macOS : `brew install llama.cpp`. RHEL 9.7 : compiler depuis https://github.com/ggerganov/llama.cpp (`cmake .. && make -j`).
- Modèles `.gguf` dans `./models/` : un modèle chat (`LLM_MODEL`) et un modèle embedding (`EMBED_MODEL`).

2) Installation (venvs : backend + Open WebUI)
```bash
make install              # crée .venv-backend et .venv-openwebui, installe les deps
```

3) Stack complète
```bash
make up                   # chat 8080, embed 8081, backend 8000, Open WebUI 3000
```
Logs/PIDs dans `.run/`, données WebUI persistées dans `.openwebui/`.

4) Ingestion
```bash
make ingest               # incrémental, démarre un embed temporaire si besoin
make reingest             # reset index puis ingest complet
```

5) Arrêt
```bash
make down                 # stoppe chat + embed + backend + WebUI
```

Configuration (pas de `.env`, uniquement `config/settings.yaml`)
- `config/settings.yaml` : `llama_cpp.base_url`, `embed_base_url`, `llm_model`, `embed_model`, `paths.index_dir`, etc.
- Overrides possibles via variables d’environnement (ex: `LLM_MODEL=... make up`) mais aucun fichier `.env` n’est lu.

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
