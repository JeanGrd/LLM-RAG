#!/usr/bin/env bash
# Minimal ingest runner. Starts a temporary embedding server if none is reachable.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_VENV="${BACKEND_VENV:-${PROJECT_DIR}/.venv-backend}"
RUN_DIR="${PROJECT_DIR}/.run"
CONFIG_PATH="${PROJECT_DIR}/config/settings.yaml"

# Ensure backend venv exists for config parsing
if [ ! -x "${BACKEND_VENV}/bin/python" ]; then
  echo "[-] Missing backend venv at ${BACKEND_VENV}. Run: make install"
  exit 1
fi

# Derive runtime values from YAML (single source of truth)
mapfile -t INFO < <(
  PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH:-}" "${BACKEND_VENV}/bin/python" - <<'PY'
from urllib.parse import urlparse
from rag.settings import load_settings

cfg = load_settings()
embed_url = (cfg.llama_cpp.embed_base_url or cfg.llama_cpp.base_url).rstrip("/")

def host_port(url: str):
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return host, port

embed_host, embed_port = host_port(embed_url)
embed_model = (cfg.llama_cpp.embed_model or cfg.llama_cpp.llm_model).strip()

print(embed_url)
print(embed_host)
print(embed_port)
print(embed_model)
print(cfg.ingest.wait_ready_s)
print(cfg.paths.index_dir)
PY
)
EMBED_URL="${INFO[0]}"
EMBED_HOST="${INFO[1]}"
EMBED_PORT="${INFO[2]}"
EMBED_MODEL="${INFO[3]}"
WAIT_S="${INFO[4]}"
INDEX_DIR="${INFO[5]}"

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
    mapfile -t embed_candidates < <(find "${PROJECT_DIR}/models/embed" -maxdepth 1 -type f -name "*.gguf" 2>/dev/null | sort)
    if [ "${#embed_candidates[@]}" -eq 0 ]; then
      mapfile -t embed_candidates < <(find "${PROJECT_DIR}/models" -maxdepth 1 -type f -name "*.gguf" 2>/dev/null | sort | grep -i embed || true)
    fi
    if [ "${#embed_candidates[@]}" -gt 1 ]; then
      echo "[-] Multiple embedding models found; set llama_cpp.embed_model in config/settings.yaml to choose:" >&2
      printf '  %s\n' "${embed_candidates[@]}" >&2
      exit 1
    fi
    if [ "${#embed_candidates[@]}" -eq 1 ]; then
      EMBED_MODEL="${embed_candidates[0]}"
    fi
fi
if [ -z "${EMBED_MODEL}" ]; then
  echo "[-] No embedding model specified in config/settings.yaml (llama_cpp.embed_model) or models/embed/."
  exit 1
fi
if [ ! -f "${EMBED_MODEL}" ]; then
  echo "[-] Embedding model file not found: ${EMBED_MODEL}"
  exit 1
fi
  echo "[ingest] starting temporary embed server on ${EMBED_URL} with ${EMBED_MODEL}"
  HOST="${EMBED_HOST}" PORT="${EMBED_PORT}" LLAMA_EMBEDDINGS_ONLY=1 \
    nohup "${PROJECT_DIR}/scripts/run/llama.sh" "${EMBED_MODEL}" \
      >"${RUN_DIR}/ingest-embed.log" 2>&1 &
  STOP_PID=$!
  sleep 1
  if ! kill -0 "${STOP_PID}" >/dev/null 2>&1; then
    echo "[-] Failed to start embed server; see ${RUN_DIR}/ingest-embed.log"
    exit 1
  fi
}

wait_ready() {
  local url="$1" left="${WAIT_S}"
  while [ "${left}" -gt 0 ]; do
    if endpoint_ready "${url}"; then return 0; fi
    if [ -n "${STOP_PID}" ] && ! kill -0 "${STOP_PID}" >/dev/null 2>&1; then
      echo "[-] Embed server exited; see ${RUN_DIR}/ingest-embed.log"
      return 1
    fi
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
  echo "[-] Backend dependencies missing. Run: make install"
  exit 1
fi
python "${PROJECT_DIR}/scripts/data/ingest.py" --config "${CONFIG_PATH}"
echo "[ingest] completed successfully."
