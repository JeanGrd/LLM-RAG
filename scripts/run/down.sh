#!/usr/bin/env bash
# Stop managed stack started by scripts/run/up.sh.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_DIR="${PROJECT_DIR}/.run"

LLM_BASE_URL="${LLAMA_CPP_BASE_URL:-http://127.0.0.1:8080}"
EMBED_BASE_URL="${LLAMA_CPP_EMBED_BASE_URL:-http://127.0.0.1:8081}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8000/v1}"
OPENWEBUI_PORT="${OPENWEBUI_PORT:-3000}"

url_port_or_default() {
  local url="$1"
  local default_port="$2"
  local host_and_path host_port port

  host_and_path="${url#*://}"
  host_port="${host_and_path%%/*}"
  if [[ "${host_port}" == *:* ]]; then
    port="${host_port##*:}"
    if [[ "${port}" =~ ^[0-9]+$ ]]; then
      echo "${port}"
      return 0
    fi
  fi
  echo "${default_port}"
}

LLM_PORT="$(url_port_or_default "${LLM_BASE_URL}" "8080")"
EMBED_PORT="$(url_port_or_default "${EMBED_BASE_URL}" "${LLM_PORT}")"
BACKEND_PORT="$(url_port_or_default "${BACKEND_BASE_URL}" "8000")"

stop_pid() {
  local name="$1"
  local pid="$2"
  local source="${3:-pid file}"

  if ! kill -0 "${pid}" >/dev/null 2>&1; then
    echo "[down] ${name}: process already stopped (pid=${pid}, ${source})"
    return 0
  fi

  echo "[down] stopping ${name} (pid=${pid}, ${source})"
  kill "${pid}" >/dev/null 2>&1 || true

  for _ in $(seq 1 10); do
    if ! kill -0 "${pid}" >/dev/null 2>&1; then
      echo "[down] ${name}: stopped"
      return 0
    fi
    sleep 1
  done

  echo "[down] ${name}: force kill (pid=${pid})"
  kill -9 "${pid}" >/dev/null 2>&1 || true
}

stop_managed() {
  local name="$1"
  local pid_file="${RUN_DIR}/${name}.pid"
  if [ ! -f "${pid_file}" ]; then
    echo "[down] ${name}: not managed (no pid file)"
    return 0
  fi

  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [ -z "${pid}" ]; then
    rm -f "${pid_file}"
    echo "[down] ${name}: stale pid file removed"
    return 0
  fi

  stop_pid "${name}" "${pid}" "managed"
  rm -f "${pid_file}"
}

stop_named_pid_file() {
  local name="$1"
  local pid_file="$2"
  if [ ! -f "${pid_file}" ]; then
    echo "[down] ${name}: not managed (no pid file)"
    return 0
  fi
  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [ -z "${pid}" ]; then
    rm -f "${pid_file}"
    echo "[down] ${name}: stale pid file removed"
    return 0
  fi
  stop_pid "${name}" "${pid}" "managed"
  rm -f "${pid_file}"
}

pid_cwd() {
  local pid="$1"
  lsof -a -p "${pid}" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n1
}

matches_service_pid() {
  local name="$1"
  local cmd="$2"
  local pid="$3"
  local port="$4"
  local cwd
  cwd="$(pid_cwd "${pid}")"

  case "${name}" in
    llama)
      [[ "${cmd}" == llama* ]] || [[ "${cmd}" == *"llama-server"* ]]
      ;;
    backend)
      [ "${port}" = "${BACKEND_PORT}" ] && [ "${cwd}" = "${PROJECT_DIR}" ]
      ;;
    openwebui)
      [ "${port}" = "${OPENWEBUI_PORT}" ] && [ "${cwd}" = "${PROJECT_DIR}" ]
      ;;
    *)
      return 1
      ;;
  esac
}

stop_by_port_if_matches() {
  local name="$1"
  local port="$2"

  if ! command -v lsof >/dev/null 2>&1; then
    echo "[down] ${name}: lsof not available, cannot probe port ${port}"
    return 0
  fi

  local listeners
  listeners="$(lsof -nP -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null | awk 'NR>1 {print $1":"$2}' | sort -u || true)"
  if [ -z "${listeners}" ]; then
    echo "[down] ${name}: no listener on port ${port}"
    return 0
  fi

  local stopped_any=0
  while IFS= read -r listener; do
    [ -z "${listener}" ] && continue
    local cmd pid
    cmd="${listener%%:*}"
    pid="${listener##*:}"
    if matches_service_pid "${name}" "${cmd}" "${pid}" "${port}"; then
      stop_pid "${name}" "${pid}" "port ${port}"
      stopped_any=1
    else
      local cwd
      cwd="$(pid_cwd "${pid}")"
      echo "[down] ${name}: listener on port ${port} does not match service signature (pid=${pid}, cmd=${cmd}, cwd=${cwd:-unknown})"
    fi
  done <<< "${listeners}"

  if [ "${stopped_any}" = "0" ]; then
    echo "[down] ${name}: no matching process stopped on port ${port}"
  fi
}

stop_managed "openwebui"
stop_by_port_if_matches "openwebui" "${OPENWEBUI_PORT}"

stop_managed "backend"
stop_by_port_if_matches "backend" "${BACKEND_PORT}"

stop_managed "llama"
stop_by_port_if_matches "llama" "${LLM_PORT}"
stop_managed "llama-embed"
if [ "${EMBED_PORT}" != "${LLM_PORT}" ]; then
  stop_by_port_if_matches "llama" "${EMBED_PORT}"
fi
stop_named_pid_file "ingest-embed" "${RUN_DIR}/ingest-embed.pid"

echo "[down] done"
