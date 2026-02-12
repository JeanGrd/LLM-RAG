#!/usr/bin/env bash
# Quick runner for backend API with native Ollama.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_VENV="${API_VENV:-${PROJECT_DIR}/.venv}"
INDEX_DIR="${INDEX_DIR:-${PROJECT_DIR}/data/indices}"
FORCE_REINDEX="${FORCE_REINDEX:-0}"
PREPARE_MODELS="${PREPARE_MODELS:-1}"

if [ ! -f "${API_VENV}/bin/activate" ]; then
  echo "[-] Missing backend venv at ${API_VENV}."
  echo "    Create it first, for example:"
  echo "    python3.11 -m venv ${API_VENV}"
  echo "    source ${API_VENV}/bin/activate && pip install -e ${PROJECT_DIR} --no-build-isolation"
  exit 1
fi

echo "[quick-backend] Activating backend venv: ${API_VENV}"
source "${API_VENV}/bin/activate"

if ! python -c "import rag, uvicorn" >/dev/null 2>&1; then
  echo "[quick-backend] Missing backend dependencies. Installing package..."
  pip install -e "${PROJECT_DIR}" --no-build-isolation
fi

export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
if [ -n "${MODEL_NAME:-}" ] && [ -z "${OLLAMA_LLM_MODEL:-}" ]; then
  export OLLAMA_LLM_MODEL="${MODEL_NAME}"
fi

if [ "${PREPARE_MODELS}" = "1" ]; then
  echo "[quick-backend] Ensuring Ollama models (chat + embeddings)"
  if [ -n "${OLLAMA_LLM_MODEL:-}" ]; then
    CHAT_MODEL="${OLLAMA_LLM_MODEL}" EMBED_MODEL="${OLLAMA_EMBED_MODEL:-nomic-embed-text}" \
      "${PROJECT_DIR}/scripts/setup/prepare_ollama.sh"
  else
    EMBED_MODEL="${OLLAMA_EMBED_MODEL:-nomic-embed-text}" "${PROJECT_DIR}/scripts/setup/prepare_ollama.sh"
  fi
fi

if [ "${FORCE_REINDEX}" = "1" ] || [ ! -d "${INDEX_DIR}" ] || [ -z "$(ls -A "${INDEX_DIR}" 2>/dev/null)" ]; then
  echo "[quick-backend] Building/refreshing vector index..."
  python "${PROJECT_DIR}/scripts/data/ingest.py"
else
  echo "[quick-backend] Existing index found at ${INDEX_DIR}. Skipping reindex."
fi

echo "[quick-backend] Starting API on ${HOST:-0.0.0.0}:${PORT:-8000}"
python "${PROJECT_DIR}/scripts/app/run_api.py"
