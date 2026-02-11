#!/usr/bin/env bash
# Quick & dirty runner on RHEL/CentOS 7 with native Ollama + API.
# Prereqs:
#   - Run install_python_311_rhel7.sh once (installs python3.11 and .venv)
#   - Ollama installed natively and running (systemctl start ollama)
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_VENV="${PROJECT_DIR}/.venv"
MODEL_NAME="${MODEL_NAME:-qwen2.5:1.5b}"
INDEX_DIR="${PROJECT_DIR}/data/indices"
FORCE_REINDEX="${FORCE_REINDEX:-0}"

echo "[rhel7] Activating API venv"
source "${API_VENV}/bin/activate"

if ! python -c "import rag, uvicorn" >/dev/null 2>&1; then
  echo "[rhel7] Missing API dependencies in ${API_VENV}. Installing project package..."
  pip install -e "${PROJECT_DIR}" --no-build-isolation
fi

export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
export MODEL_PROVIDER=ollama
export MODEL_NAME="${MODEL_NAME}"

echo "[rhel7] Ensuring Ollama models (chat + embed)"
"${PROJECT_DIR}/scripts/prepare_ollama.sh"

if [ "${FORCE_REINDEX}" = "1" ] || [ ! -d "${INDEX_DIR}" ] || [ -z "$(ls -A "${INDEX_DIR}" 2>/dev/null)" ]; then
  echo "[rhel7] Building/refreshing index..."
  python "${PROJECT_DIR}/scripts/ingest.py"
else
  echo "[rhel7] Index present at ${INDEX_DIR} (skip reindex; set FORCE_REINDEX=1 to rebuild)"
fi

echo "[rhel7] Starting API (Ctrl+C to stop)"
python "${PROJECT_DIR}/scripts/run_api.py"
