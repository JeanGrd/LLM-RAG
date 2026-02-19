#!/usr/bin/env bash
# Runner for Open WebUI connected to local RAG backend (/v1).
set -euo pipefail

# Resolve Open WebUI venv:
# 1) explicit OPENWEBUI_VENV if provided
# 2) project-local .openwebui-venv
# 3) fallback to $HOME/openwebui-venv
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [ -z "${OPENWEBUI_VENV:-}" ]; then
  if [ -d "${PROJECT_DIR}/.openwebui-venv" ]; then
    OPENWEBUI_VENV="${PROJECT_DIR}/.openwebui-venv"
  else
    OPENWEBUI_VENV="${HOME}/openwebui-venv"
  fi
fi

OPENWEBUI_HOST="${OPENWEBUI_HOST:-0.0.0.0}"
OPENWEBUI_PORT="${OPENWEBUI_PORT:-3000}"
OPENAI_API_BASE_URL="${OPENAI_API_BASE_URL:-http://127.0.0.1:8000/v1}"
OPENAI_API_KEY="${OPENAI_API_KEY:-local-rag}"
ENABLE_OLLAMA_API="${ENABLE_OLLAMA_API:-false}"

if [ ! -f "${OPENWEBUI_VENV}/bin/activate" ]; then
  if command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="python3.11"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "[-] python3.11/python3 not found."
    exit 1
  fi
  echo "[openwebui] Creating venv at ${OPENWEBUI_VENV} using ${PYTHON_BIN}"
  "${PYTHON_BIN}" -m venv "${OPENWEBUI_VENV}"
fi

echo "[openwebui] Activating venv: ${OPENWEBUI_VENV}"
source "${OPENWEBUI_VENV}/bin/activate"

if ! command -v open-webui >/dev/null 2>&1; then
  echo "[openwebui] Installing Open WebUI..."
  pip install -U pip
  pip install open-webui
fi

export OPENAI_API_BASE_URL
export OPENAI_API_KEY
export ENABLE_OLLAMA_API

if command -v curl >/dev/null 2>&1; then
  models_json="$(curl -fsS "${OPENAI_API_BASE_URL}/models" 2>/dev/null || true)"
  if [ -z "${models_json}" ]; then
    echo "[openwebui] WARNING: backend is not reachable at ${OPENAI_API_BASE_URL}."
    echo "[openwebui] Start backend first: make backend"
  elif command -v python >/dev/null 2>&1; then
    model_count="$(printf '%s' "${models_json}" | python -c 'import json, sys; p=json.load(sys.stdin); print(len(p.get("data", [])))' 2>/dev/null || echo 0)"
    if [ "${model_count}" = "0" ]; then
      echo "[openwebui] WARNING: backend returned 0 models at ${OPENAI_API_BASE_URL}/models."
      echo "[openwebui] Set LLAMA_CPP_LLM_MODEL and ensure llama-server is serving a chat model."
    else
      echo "[openwebui] Models available from backend:"
      printf '%s' "${models_json}" | python -c '
import json
import sys
payload = json.load(sys.stdin)
for item in payload.get("data", []):
    model_id = item.get("id") or item.get("model")
    if model_id:
        print(f"  - {model_id}")
'
    fi
  fi
fi

echo "[openwebui] Starting Open WebUI on ${OPENWEBUI_HOST}:${OPENWEBUI_PORT}"
echo "[openwebui] Upstream backend: ${OPENAI_API_BASE_URL}"
open-webui serve --host "${OPENWEBUI_HOST}" --port "${OPENWEBUI_PORT}"
