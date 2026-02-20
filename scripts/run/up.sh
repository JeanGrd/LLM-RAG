#!/usr/bin/env bash
# Start chat llama, embed llama, and backend (managed with PID files).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_DIR="${PROJECT_DIR}/.run"
BACKEND_VENV="${BACKEND_VENV:-${PROJECT_DIR}/.venv-backend}"
OPENWEBUI_VENV="${OPENWEBUI_VENV:-${PROJECT_DIR}/.venv-openwebui}"
OPENWEBUI_PORT="${OPENWEBUI_PORT:-3000}"
OPENWEBUI_HOST="${OPENWEBUI_HOST:-0.0.0.0}"
OPENWEBUI_HOME="${OPENWEBUI_HOME:-${PROJECT_DIR}/.openwebui}"

LLM_MODEL="${LLM_MODEL:-${LLAMA_MODEL:-}}"
EMBED_MODEL="${EMBED_MODEL:-${LLAMA_EMBED_MODEL:-}}"
LLM_PORT="${LLM_PORT:-8080}"
EMBED_PORT="${EMBED_PORT:-8081}"
BACKEND_PORT="${PORT:-8000}"

mkdir -p "${RUN_DIR}"

is_alive() { kill -0 "$1" >/dev/null 2>&1; }

start_bg() {
  local name="$1"; shift
  local pid_file="${RUN_DIR}/${name}.pid"
  local log_file="${RUN_DIR}/${name}.log"
  if [ -f "${pid_file}" ]; then
    local pid; pid="$(cat "${pid_file}" 2>/dev/null || true)"
    if [ -n "${pid}" ] && is_alive "${pid}"; then
      echo "[up] ${name} already running (pid=${pid})"
      return 0
    fi
  fi
  echo "[up] starting ${name}..."
  nohup "$@" >"${log_file}" 2>&1 &
  local pid=$!
  echo "${pid}" > "${pid_file}"
  sleep 1
  if ! is_alive "${pid}"; then
    echo "[up] ERROR: ${name} failed to start (see ${log_file})"
    exit 1
  fi
  echo "[up] ${name} started (pid=${pid}, log=${log_file})"
}

wait_http() {
  local name="$1" url="$2" timeout="${3:-90}"
  local start="$(date +%s)"
  while true; do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      echo "[up] ${name} ready at ${url}"
      return 0
    fi
    if [ $(( $(date +%s) - start )) -ge "${timeout}" ]; then
      echo "[up] ERROR: timeout waiting for ${name} (${url})"
      exit 1
    fi
    sleep 1
  done
}

if [ -z "${LLM_MODEL}" ]; then
  mapfile -t files < <(find "${PROJECT_DIR}/models" -maxdepth 1 -type f -name "*.gguf" | sort)
  for f in "${files[@]}"; do
    base="$(basename "${f}" | tr '[:upper:]' '[:lower:]')"
    if [[ "${base}" != *embed* ]]; then
      LLM_MODEL="${f}"
      break
    fi
  done
fi
if [ -z "${LLM_MODEL}" ]; then
  echo "[-] No chat model found. Place a chat/instruct GGUF in models/ and set LLM_MODEL."
  exit 1
fi

if [ -z "${EMBED_MODEL}" ]; then
  mapfile -t files < <(find "${PROJECT_DIR}/models" -maxdepth 1 -type f -name "*.gguf" | sort)
  for f in "${files[@]}"; do
    base="$(basename "${f}" | tr '[:upper:]' '[:lower:]')"
    if [[ "${base}" == *embed* ]]; then
      EMBED_MODEL="${f}"
      break
    fi
  done
  if [ -z "${EMBED_MODEL}" ]; then
    EMBED_MODEL="${LLM_MODEL}"
    echo "[up] No dedicated embedding model; reusing chat model."
  fi
fi

start_bg "llama-chat" env HOST=0.0.0.0 PORT="${LLM_PORT}" "${PROJECT_DIR}/scripts/run/llama.sh" "${LLM_MODEL}"
wait_http "llama-chat" "http://127.0.0.1:${LLM_PORT}/v1/models" 60

start_bg "llama-embed" env HOST=0.0.0.0 PORT="${EMBED_PORT}" LLAMA_EMBEDDINGS_ONLY=1 "${PROJECT_DIR}/scripts/run/llama.sh" "${EMBED_MODEL}"
wait_http "llama-embed" "http://127.0.0.1:${EMBED_PORT}/v1/models" 60

if [ ! -x "${BACKEND_VENV}/bin/python" ]; then
  echo "[-] Missing backend venv at ${BACKEND_VENV}. Run: make install"
  exit 1
fi
start_bg "backend" env PORT="${BACKEND_PORT}" LLAMA_CPP_BASE_URL="http://127.0.0.1:${LLM_PORT}" LLAMA_CPP_EMBED_BASE_URL="http://127.0.0.1:${EMBED_PORT}" \
  bash -c "source '${BACKEND_VENV}/bin/activate' && export PYTHONPATH='${PROJECT_DIR}/src':${PYTHONPATH:-} && python '${PROJECT_DIR}/scripts/app/run_api.py'"
wait_http "backend" "http://127.0.0.1:${BACKEND_PORT}/v1/models" 60

if [ ! -x "${OPENWEBUI_VENV}/bin/python" ]; then
  echo "[-] Missing Open WebUI venv at ${OPENWEBUI_VENV}. Run: make install"
  exit 1
fi
start_bg "openwebui" env \
  OPENWEBUI_HOST="${OPENWEBUI_HOST}" \
  OPENWEBUI_PORT="${OPENWEBUI_PORT}" \
  OPENWEBUI_HOME="${OPENWEBUI_HOME}" \
  OPENWEBUI_DB_PATH="${OPENWEBUI_HOME}/webui.db" \
  OPENAI_API_BASE_URL="http://127.0.0.1:${BACKEND_PORT}/v1" \
  OPENAI_API_KEY="${OPENAI_API_KEY:-local-rag}" \
  "${PROJECT_DIR}/scripts/run/openwebui.sh"
wait_http "openwebui" "http://127.0.0.1:${OPENWEBUI_PORT}/api/version" 120

echo "[up] stack is up"
echo "[up] Open WebUI: http://127.0.0.1:${OPENWEBUI_PORT}"
