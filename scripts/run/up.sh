#!/usr/bin/env bash
# Start llama.cpp + backend + Open WebUI in background (managed with pid files).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_DIR="${PROJECT_DIR}/.run"

LLM_BASE_URL="${LLAMA_CPP_BASE_URL:-http://127.0.0.1:8080}"
EMBED_BASE_URL="${LLAMA_CPP_EMBED_BASE_URL:-http://127.0.0.1:8081}"
OPENWEBUI_PORT="${OPENWEBUI_PORT:-3000}"
OPENWEBUI_HEALTH_URL="${OPENWEBUI_HEALTH_URL:-http://127.0.0.1:${OPENWEBUI_PORT}/api/version}"
export LLAMA_CPP_EMBED_BASE_URL="${EMBED_BASE_URL}"

mkdir -p "${RUN_DIR}"

is_pid_alive() {
  local pid="$1"
  kill -0 "${pid}" >/dev/null 2>&1
}

start_managed() {
  local name="$1"
  shift
  local pid_file="${RUN_DIR}/${name}.pid"
  local log_file="${RUN_DIR}/${name}.log"

  if [ -f "${pid_file}" ]; then
    local existing_pid
    existing_pid="$(cat "${pid_file}" 2>/dev/null || true)"
    if [ -n "${existing_pid}" ] && is_pid_alive "${existing_pid}"; then
      echo "[up] ${name} already running (pid=${existing_pid})"
      return 0
    fi
    rm -f "${pid_file}"
  fi

  echo "[up] starting ${name}..."
  nohup "$@" >"${log_file}" 2>&1 &
  local pid=$!
  echo "${pid}" >"${pid_file}"
  sleep 1
  if ! is_pid_alive "${pid}"; then
    echo "[up] ERROR: ${name} failed to start (see ${log_file})"
    return 1
  fi
  echo "[up] ${name} started (pid=${pid}, log=${log_file})"
}

wait_for_url() {
  local name="$1"
  local url="$2"
  local timeout_s="${3:-60}"
  local pid_file="${RUN_DIR}/${name}.pid"
  local start_ts
  start_ts="$(date +%s)"

  while true; do
    if command -v curl >/dev/null 2>&1 && curl -fsS "${url}" >/dev/null 2>&1; then
      echo "[up] ${name} ready at ${url}"
      return 0
    fi
    if [ -f "${pid_file}" ]; then
      local pid
      pid="$(cat "${pid_file}" 2>/dev/null || true)"
      if [ -n "${pid}" ] && ! is_pid_alive "${pid}"; then
        echo "[up] ERROR: ${name} exited before readiness check (${url})"
        return 1
      fi
    fi
    local now_ts
    now_ts="$(date +%s)"
    if [ $((now_ts - start_ts)) -ge "${timeout_s}" ]; then
      echo "[up] ERROR: timeout waiting for ${name} (${url})"
      return 1
    fi
    sleep 1
  done
}

endpoint_has_embedding_model() {
  local endpoint="$1"
  local models_json
  models_json="$(curl -fsS "${endpoint%/}/v1/models" 2>/dev/null || true)"
  if [ -z "${models_json}" ]; then
    return 1
  fi
  if command -v python >/dev/null 2>&1; then
    printf '%s' "${models_json}" | python -c '
import json
import sys
try:
    payload = json.load(sys.stdin)
except Exception:
    raise SystemExit(1)
for item in payload.get("data", []):
    model_id = str(item.get("id") or item.get("model") or "").strip().lower()
    if model_id and ("embed" in model_id or "embedding" in model_id):
        raise SystemExit(0)
raise SystemExit(1)
'
    return $?
  fi
  if command -v rg >/dev/null 2>&1; then
    printf '%s' "${models_json}" | tr '[:upper:]' '[:lower:]' | rg -q "embed|embedding"
  else
    printf '%s' "${models_json}" | tr '[:upper:]' '[:lower:]' | grep -Eq "embed|embedding"
  fi
}

parse_host_port() {
  local url="$1"
  local default_host="$2"
  local default_port="$3"
  local host_and_path host_port host port

  host_and_path="${url#*://}"
  host_port="${host_and_path%%/*}"
  host="${host_port%%:*}"
  port="${host_port##*:}"

  if [ -z "${host}" ] || [ "${host}" = "${host_port}" ]; then
    host="${default_host}"
  fi
  if ! [[ "${port}" =~ ^[0-9]+$ ]]; then
    port="${default_port}"
  fi
  echo "${host} ${port}"
}

if command -v curl >/dev/null 2>&1 && curl -fsS "${LLM_BASE_URL%/}/v1/models" >/dev/null 2>&1; then
  echo "[up] llama endpoint already reachable at ${LLM_BASE_URL}; skipping managed llama start"
else
  start_managed "llama" "${PROJECT_DIR}/scripts/run/llama_server.sh" "${LLAMA_MODEL:-}"
  wait_for_url "llama" "${LLM_BASE_URL%/}/v1/models" 120
fi

if command -v curl >/dev/null 2>&1 && endpoint_has_embedding_model "${EMBED_BASE_URL}"; then
  echo "[up] embedding endpoint already reachable at ${EMBED_BASE_URL}; skipping managed embed start"
else
  read -r embed_host embed_port <<< "$(parse_host_port "${EMBED_BASE_URL}" "127.0.0.1" "8081")"
  start_managed \
    "llama-embed" \
    env HOST="${embed_host}" PORT="${embed_port}" LLAMA_EMBEDDINGS_ONLY=1 \
    "${PROJECT_DIR}/scripts/run/llama_server.sh" "${LLAMA_EMBED_MODEL:-}"
  wait_for_url "llama-embed" "${EMBED_BASE_URL%/}/v1/models" 120
  if ! endpoint_has_embedding_model "${EMBED_BASE_URL}"; then
    echo "[up] ERROR: endpoint is reachable but no embedding model is published at ${EMBED_BASE_URL}"
    exit 1
  fi
fi

start_managed "backend" "${PROJECT_DIR}/scripts/run/backend.sh"
wait_for_url "backend" "http://127.0.0.1:8000/v1/models" 90

start_managed "openwebui" "${PROJECT_DIR}/scripts/run/openwebui.sh"
wait_for_url "openwebui" "${OPENWEBUI_HEALTH_URL}" 90

echo "[up] stack is up"
echo "[up] Open WebUI: http://127.0.0.1:${OPENWEBUI_PORT}"
