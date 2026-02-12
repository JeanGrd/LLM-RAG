#!/usr/bin/env bash
# Quick runner for Open WebUI connected to local RAG backend (/v1).
set -euo pipefail

OPENWEBUI_VENV="${OPENWEBUI_VENV:-$HOME/openwebui-venv}"
OPENWEBUI_HOST="${OPENWEBUI_HOST:-0.0.0.0}"
OPENWEBUI_PORT="${OPENWEBUI_PORT:-3000}"
OPENAI_API_BASE_URL="${OPENAI_API_BASE_URL:-http://localhost:8000/v1}"
OPENAI_API_KEY="${OPENAI_API_KEY:-local-rag}"

if [ ! -f "${OPENWEBUI_VENV}/bin/activate" ]; then
  if command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="python3.11"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "[-] python3.11/python3 not found."
    exit 1
  fi
  echo "[quick-openwebui] Creating venv at ${OPENWEBUI_VENV} using ${PYTHON_BIN}"
  "${PYTHON_BIN}" -m venv "${OPENWEBUI_VENV}"
fi

echo "[quick-openwebui] Activating venv: ${OPENWEBUI_VENV}"
source "${OPENWEBUI_VENV}/bin/activate"

if ! command -v open-webui >/dev/null 2>&1; then
  echo "[quick-openwebui] Installing Open WebUI..."
  pip install -U pip
  pip install open-webui
fi

export OPENAI_API_BASE_URL
export OPENAI_API_KEY

echo "[quick-openwebui] Starting Open WebUI on ${OPENWEBUI_HOST}:${OPENWEBUI_PORT}"
echo "[quick-openwebui] Upstream backend: ${OPENAI_API_BASE_URL}"
open-webui serve --host "${OPENWEBUI_HOST}" --port "${OPENWEBUI_PORT}"
