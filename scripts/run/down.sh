#!/usr/bin/env bash
# Stop managed stack started by scripts/run/up.sh.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_DIR="${PROJECT_DIR}/.run"

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

  if ! kill -0 "${pid}" >/dev/null 2>&1; then
    rm -f "${pid_file}"
    echo "[down] ${name}: process already stopped"
    return 0
  fi

  echo "[down] stopping ${name} (pid=${pid})"
  kill "${pid}" >/dev/null 2>&1 || true

  for _ in $(seq 1 10); do
    if ! kill -0 "${pid}" >/dev/null 2>&1; then
      rm -f "${pid_file}"
      echo "[down] ${name}: stopped"
      return 0
    fi
    sleep 1
  done

  echo "[down] ${name}: force kill"
  kill -9 "${pid}" >/dev/null 2>&1 || true
  rm -f "${pid_file}"
}

stop_managed "openwebui"
stop_managed "backend"
stop_managed "llama"

echo "[down] done"
