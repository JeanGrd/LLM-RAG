#!/usr/bin/env bash
# Start only the API backend. Assumes llama servers are already running.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_VENV="${BACKEND_VENV:-${PROJECT_DIR}/.venv-backend}"
PORT="${PORT:-8000}"
LLM_URL="${LLAMA_CPP_BASE_URL:-http://127.0.0.1:8080}"
EMBED_URL="${LLAMA_CPP_EMBED_BASE_URL:-http://127.0.0.1:8081}"

if [ ! -x "${BACKEND_VENV}/bin/python" ]; then
  echo "[-] Missing backend venv at ${BACKEND_VENV}. Run: make install"
  exit 1
fi

export RAG_CONFIG_PATH="${RAG_CONFIG_PATH:-${PROJECT_DIR}/config/settings.yaml}"
export LLAMA_CPP_BASE_URL="${LLM_URL}"
export LLAMA_CPP_EMBED_BASE_URL="${EMBED_URL}"

echo "[backend] using LLM: ${LLM_URL}"
echo "[backend] using EMBED: ${EMBED_URL}"

source "${BACKEND_VENV}/bin/activate"
export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH:-}"
python "${PROJECT_DIR}/scripts/app/run_api.py"
