#!/usr/bin/env bash
# Stop managed processes started by up.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_DIR="${PROJECT_DIR}/.run"

stop_one() {
  local name="$1"
  local pid_file="${RUN_DIR}/${name}.pid"
  if [ ! -f "${pid_file}" ]; then
    echo "[down] ${name}: not managed (no pid file)"
    return
  fi
  local pid; pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [ -z "${pid}" ]; then
    echo "[down] ${name}: empty pid file"
    rm -f "${pid_file}"
    return
  fi
  if kill -0 "${pid}" >/dev/null 2>&1; then
    echo "[down] stopping ${name} (pid=${pid})"
    kill "${pid}" >/dev/null 2>&1 || true
    sleep 1
    if kill -0 "${pid}" >/dev/null 2>&1; then
      kill -9 "${pid}" >/dev/null 2>&1 || true
    fi
  else
    echo "[down] ${name}: process not running"
  fi
  rm -f "${pid_file}"
}

stop_one "backend"
stop_one "llama-embed"
stop_one "llama-chat"

echo "[down] done"
