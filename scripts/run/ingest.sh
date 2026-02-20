#!/usr/bin/env bash
# Minimal ingest runner. Starts a temporary embedding server if none is reachable.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_VENV="${BACKEND_VENV:-${PROJECT_DIR}/.venv-backend}"
RUN_DIR="${PROJECT_DIR}/.run"
INDEX_DIR="${INDEX_DIR:-${PROJECT_DIR}/data/indices}"
EMBED_MODEL="${EMBED_MODEL:-${LLAMA_EMBED_MODEL:-}}"
EMBED_HOST="${EMBED_HOST:-127.0.0.1}"
EMBED_PORT="${EMBED_PORT:-8081}"
EMBED_URL="http://${EMBED_HOST}:${EMBED_PORT}"
WAIT_S="${INGEST_WAIT_S:-90}"

mkdir -p "${RUN_DIR}" "${INDEX_DIR}"
cd "${PROJECT_DIR}"
export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH:-}"

need_full=0
if [ "$#" -eq 1 ] && { [ "$1" = "--full-rebuild" ] || [ "$1" = "--full" ]; }; then
  need_full=1
elif [ "$#" -gt 0 ]; then
  echo "Usage: scripts/run/ingest.sh [--full-rebuild]"
  exit 1
fi

if [ ! -x "${BACKEND_VENV}/bin/python" ]; then
  echo "[-] Missing backend venv at ${BACKEND_VENV}. Run: make install"
  exit 1
fi

endpoint_ready() {
  curl -fsS "${1%/}/v1/models" 2>/dev/null | grep -iq "embed"
}

STOP_PID=""
start_embed_if_needed() {
  if endpoint_ready "${EMBED_URL}"; then
    echo "[ingest] using existing embedding endpoint: ${EMBED_URL}"
    return 0
  fi
  if [ -z "${EMBED_MODEL}" ]; then
    mapfile -t ggufs < <(find "${PROJECT_DIR}/models" -maxdepth 1 -type f -name "*.gguf" | sort)
    for f in "${ggufs[@]}"; do
      low="$(basename "${f}" | tr '[:upper:]' '[:lower:]')"
      if [[ "${low}" == *embed* ]]; then
        EMBED_MODEL="${f}"
        break
      fi
    done
  fi
  if [ -z "${EMBED_MODEL}" ]; then
    echo "[-] No embedding model specified (set EMBED_MODEL or LLAMA_EMBED_MODEL)."
    exit 1
  fi
  echo "[ingest] starting temporary embed server on ${EMBED_URL} with ${EMBED_MODEL}"
  HOST="${EMBED_HOST}" PORT="${EMBED_PORT}" LLAMA_EMBEDDINGS_ONLY=1 \
    nohup "${PROJECT_DIR}/scripts/run/llama.sh" "${EMBED_MODEL}" \
      >"${RUN_DIR}/ingest-embed.log" 2>&1 &
  STOP_PID=$!
}

wait_ready() {
  local url="$1" left="${WAIT_S}"
  while [ "${left}" -gt 0 ]; do
    if endpoint_ready "${url}"; then return 0; fi
    sleep 1; left=$((left-1))
  done
  return 1
}

cleanup() {
  if [ -n "${STOP_PID}" ] && kill -0 "${STOP_PID}" >/dev/null 2>&1; then
    echo "[ingest] stopping temporary embed server (pid=${STOP_PID})"
    kill "${STOP_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

start_embed_if_needed
if ! wait_ready "${EMBED_URL}"; then
  echo "[-] Embedding endpoint not ready at ${EMBED_URL}"
  exit 1
fi

export LLAMA_CPP_EMBED_BASE_URL="${EMBED_URL}"
export RAG_CONFIG_PATH="${RAG_CONFIG_PATH:-${PROJECT_DIR}/config/settings.yaml}"
export INDEX_DIR

RESOLVED_INDEX_DIR="$(
  INDEX_DIR="${INDEX_DIR}" RAG_CONFIG_PATH="${RAG_CONFIG_PATH}" PYTHONPATH="${PYTHONPATH}" \
    "${BACKEND_VENV}/bin/python" - <<'PY'
try:
    from rag.settings import load_settings
    print(load_settings().paths.index_dir)
except Exception:
    import os
    print(os.environ.get("INDEX_DIR", ""))
PY
)"
INDEX_DIR="${RESOLVED_INDEX_DIR}"

if [ "${need_full}" = "1" ]; then
  echo "[ingest] full rebuild: clearing ${INDEX_DIR}"
  rm -rf "${INDEX_DIR}"
  mkdir -p "${INDEX_DIR}"
fi

echo "[ingest] running ingest..."
source "${BACKEND_VENV}/bin/activate"
export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH:-}"
if ! python - <<'PY' >/dev/null 2>&1
import rag
PY
then
  pip install -q --upgrade pip setuptools wheel build
  pip install -q -e "${PROJECT_DIR}" --no-build-isolation
fi
python "${PROJECT_DIR}/scripts/data/ingest.py"
