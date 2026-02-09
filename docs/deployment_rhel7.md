# Deployment (RHEL 7.9)

## Assumptions
- Python 3.10+ available (system or via `pyenv`).
- A reachable Ollama instance for embeddings and fallback LLM.
- Network access to the cloud LLM endpoint.

## Steps

1. Create a virtual environment

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -U pip
```

2. Install dependencies

```bash
pip install -e .
```

3. Configure

- Copy `.env.example` to `.env` and set:
  - `CLOUD_API_URL`, `CLOUD_API_KEY`, `CLOUD_MODEL`
  - `OLLAMA_BASE_URL`, `OLLAMA_EMBED_MODEL`, `OLLAMA_LLM_MODEL`

4. Ingest data

```bash
python scripts/ingest.py
```

5. Run API

```bash
HOST=0.0.0.0 PORT=8000 python scripts/run_api.py
```

## Notes
- If Ollama is not supported on your RHEL 7.9 host, run it on a separate Linux host and point `OLLAMA_BASE_URL` to it.
- For production, run with a process manager (systemd) or containerize the service.
