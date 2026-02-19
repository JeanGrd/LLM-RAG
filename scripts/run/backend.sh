#!/usr/bin/env bash
# Runner for backend API with llama.cpp server.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_VENV="${API_VENV:-${PROJECT_DIR}/.venv}"
INDEX_DIR="${INDEX_DIR:-${PROJECT_DIR}/data/indices}"
FORCE_REINGEST="${FORCE_REINGEST:-0}"
CHECK_ONLY="${CHECK_ONLY:-0}"

cd "${PROJECT_DIR}"

if [ "${CHECK_ONLY}" = "1" ]; then
  # Check-only mode disables heavyweight operations (model pulls, ingestion, server start).
  FORCE_REINGEST=0
fi

if [ ! -f "${API_VENV}/bin/activate" ]; then
  echo "[-] Missing backend venv at ${API_VENV}."
  echo "    Create it first, for example:"
  echo "    python3.11 -m venv ${API_VENV}"
  echo "    source ${API_VENV}/bin/activate && pip install -e ${PROJECT_DIR} --no-build-isolation"
  exit 1
fi

echo "[backend] Activating backend venv: ${API_VENV}"
source "${API_VENV}/bin/activate"

if ! python -c "import rag, uvicorn" >/dev/null 2>&1; then
  echo "[backend] Missing backend dependencies. Installing package..."
  pip install -e "${PROJECT_DIR}" --no-build-isolation
fi

if [ "${CHECK_ONLY}" = "1" ]; then
  echo "[backend] Check-only mode: venv and python deps OK. Skipping model prep, ingest, and server start."
  exit 0
fi

export RAG_CONFIG_PATH="${RAG_CONFIG_PATH:-${PROJECT_DIR}/config/settings.yaml}"
export RAG_ENV_FILE="${RAG_ENV_FILE:-${PROJECT_DIR}/.env}"
export LLAMA_CPP_BASE_URL="${LLAMA_CPP_BASE_URL:-http://127.0.0.1:8080}"
if [ -n "${MODEL_NAME:-}" ] && [ -z "${LLAMA_CPP_LLM_MODEL:-}" ]; then
  export LLAMA_CPP_LLM_MODEL="${MODEL_NAME}"
fi

configured_model="$(
  python -c 'from rag.settings import load_settings; print((load_settings().llama_cpp.llm_model or "").strip())'
)"
if [ -n "${configured_model}" ] && [ -z "${LLAMA_CPP_LLM_MODEL:-}" ]; then
  export LLAMA_CPP_LLM_MODEL="${configured_model}"
fi

if [ -z "${LLAMA_CPP_LLM_MODEL:-}" ] && command -v curl >/dev/null 2>&1; then
  discovered_model="$(
    curl -fsS "${LLAMA_CPP_BASE_URL%/}/v1/models" 2>/dev/null | python -c '
import json
import sys
try:
    payload = json.load(sys.stdin)
except Exception:
    print("")
    raise SystemExit(0)
for item in payload.get("data", []):
    model_id = str(item.get("id", "")).strip()
    low = model_id.lower()
    if model_id and "embed" not in low and "embedding" not in low:
        print(model_id)
        raise SystemExit(0)
print("")
'
  )"
  if [ -n "${discovered_model}" ]; then
    export LLAMA_CPP_LLM_MODEL="${discovered_model}"
    echo "[backend] Auto-selected chat model: ${LLAMA_CPP_LLM_MODEL}"
  fi
fi

if [ -n "${LLAMA_CPP_LLM_MODEL:-}" ]; then
  model_lower="$(echo "${LLAMA_CPP_LLM_MODEL}" | tr '[:upper:]' '[:lower:]')"
  if [[ "${model_lower}" == *embed* ]] || [[ "${model_lower}" == *embedding* ]]; then
    echo "[-] LLAMA_CPP_LLM_MODEL='${LLAMA_CPP_LLM_MODEL}' looks like an embedding model."
    echo "    Set a chat/instruct model, e.g.:"
    echo "    LLAMA_CPP_LLM_MODEL=ggml-org_gemma-3-1b-it-GGUF_gemma-3-1b-it-Q4_K_M.gguf"
    exit 1
  fi
  echo "[backend] Chat model: ${LLAMA_CPP_LLM_MODEL}"
else
  echo "[backend] WARNING: no default LLAMA_CPP_LLM_MODEL resolved."
  echo "[backend] /query will fail until you set a chat model."
fi

echo "[backend] Llama endpoint: ${LLAMA_CPP_BASE_URL}"

if [ "${FORCE_REINGEST}" = "1" ] || [ ! -d "${INDEX_DIR}" ] || [ -z "$(ls -A "${INDEX_DIR}" 2>/dev/null)" ]; then
  echo "[backend] Building/refreshing vector index..."
  python "${PROJECT_DIR}/scripts/data/ingest.py"
else
  echo "[backend] Existing index found at ${INDEX_DIR}. Skipping reingest."
fi

echo "[backend] Starting API on ${HOST:-0.0.0.0}:${PORT:-8000}"
python "${PROJECT_DIR}/scripts/app/run_api.py"
