#!/usr/bin/env bash
# Run ingestion with automatic embedding-server startup when needed.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_VENV="${API_VENV:-${PROJECT_DIR}/.venv}"
RUN_DIR="${PROJECT_DIR}/.run"
INDEX_DIR="${INDEX_DIR:-${PROJECT_DIR}/data/indices}"

mkdir -p "${RUN_DIR}"

LLM_BASE_URL="${LLAMA_CPP_BASE_URL:-http://127.0.0.1:8080}"
CONFIGURED_EMBED_BASE_URL="${LLAMA_CPP_EMBED_BASE_URL:-}"
EMBED_HOST="${LLAMA_EMBED_HOST:-127.0.0.1}"
EMBED_PORT="${LLAMA_EMBED_PORT:-8081}"
EMBED_PORT_MAX_TRIES="${LLAMA_EMBED_PORT_MAX_TRIES:-10}"
AUTO_EMBED_BASE_URL="http://${EMBED_HOST}:${EMBED_PORT}"
INGEST_WAIT_S="${INGEST_EMBED_WAIT_S:-120}"

STARTED_EMBED_PID=""
EMBED_LOG_FILE="${RUN_DIR}/ingest-embed.log"
EMBED_PID_FILE="${RUN_DIR}/ingest-embed.pid"

endpoint_has_embedding_model() {
  local endpoint="$1"
  local models_json
  models_json="$(curl -fsS --connect-timeout 1 --max-time 2 "${endpoint%/}/v1/models" 2>/dev/null || true)"
  if [ -z "${models_json}" ]; then
    return 1
  fi

  if ! command -v python >/dev/null 2>&1; then
    # Fallback heuristic when python is unavailable.
    if command -v rg >/dev/null 2>&1; then
      echo "${models_json}" | tr '[:upper:]' '[:lower:]' | rg -q "embed|embedding"
    else
      echo "${models_json}" | tr '[:upper:]' '[:lower:]' | grep -Eq "embed|embedding"
    fi
    return $?
  fi

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
}

wait_for_embedding_endpoint() {
  local endpoint="$1"
  local timeout_s="$2"
  local started_pid="${3:-}"
  local start_ts now_ts elapsed
  start_ts="$(date +%s)"
  while true; do
    if endpoint_has_embedding_model "${endpoint}"; then
      return 0
    fi
    if [ -n "${started_pid}" ] && ! kill -0 "${started_pid}" >/dev/null 2>&1; then
      return 1
    fi
    now_ts="$(date +%s)"
    elapsed="$((now_ts - start_ts))"
    if [ "${elapsed}" -ge "${timeout_s}" ]; then
      return 1
    fi
    sleep 1
  done
}

stop_started_embed() {
  if [ -z "${STARTED_EMBED_PID}" ]; then
    return 0
  fi
  if ! kill -0 "${STARTED_EMBED_PID}" >/dev/null 2>&1; then
    rm -f "${EMBED_PID_FILE}"
    return 0
  fi
  echo "[ingest-run] stopping auto-started embedding server (pid=${STARTED_EMBED_PID})"
  kill "${STARTED_EMBED_PID}" >/dev/null 2>&1 || true
  for _ in $(seq 1 10); do
    if ! kill -0 "${STARTED_EMBED_PID}" >/dev/null 2>&1; then
      rm -f "${EMBED_PID_FILE}"
      return 0
    fi
    sleep 1
  done
  kill -9 "${STARTED_EMBED_PID}" >/dev/null 2>&1 || true
  rm -f "${EMBED_PID_FILE}"
}

start_embedding_server() {
  if ! command -v lsof >/dev/null 2>&1; then
    echo "[-] lsof is required to auto-start the embedding server."
    exit 1
  fi

  local embed_model_arg="${LLAMA_EMBED_MODEL:-}"
  local try_idx candidate_port candidate_url
  for try_idx in $(seq 0 $((EMBED_PORT_MAX_TRIES - 1))); do
    candidate_port="$((EMBED_PORT + try_idx))"
    candidate_url="http://${EMBED_HOST}:${candidate_port}"

    if endpoint_has_embedding_model "${candidate_url}"; then
      AUTO_EMBED_BASE_URL="${candidate_url}"
      STARTED_EMBED_PID=""
      rm -f "${EMBED_PID_FILE}"
      echo "[ingest-run] using existing embedding endpoint: ${AUTO_EMBED_BASE_URL}"
      return 0
    fi

    if lsof -nP -iTCP:"${candidate_port}" -sTCP:LISTEN >/dev/null 2>&1; then
      continue
    fi

    echo "[ingest-run] starting dedicated embedding server on ${candidate_url}"
    HOST="${EMBED_HOST}" \
    PORT="${candidate_port}" \
    LLAMA_EMBEDDINGS_ONLY=1 \
    "${PROJECT_DIR}/scripts/run/llama_server.sh" "${embed_model_arg}" >"${EMBED_LOG_FILE}" 2>&1 &
    STARTED_EMBED_PID=$!
    AUTO_EMBED_BASE_URL="${candidate_url}"
    echo "[ingest-run] embedding log: ${EMBED_LOG_FILE}"
    sleep 1
    if kill -0 "${STARTED_EMBED_PID}" >/dev/null 2>&1; then
      printf '%s\n' "${STARTED_EMBED_PID}" > "${EMBED_PID_FILE}"
      return 0
    fi
  done

  echo "[-] Unable to start or detect an embedding endpoint."
  echo "    Tried ${EMBED_PORT_MAX_TRIES} port(s) from ${EMBED_PORT} on host ${EMBED_HOST}."
  echo "    Check log: ${EMBED_LOG_FILE}"
  exit 1
}

ensure_env() {
  if [ ! -f "${API_VENV}/bin/activate" ]; then
    echo "[-] Missing backend venv at ${API_VENV}."
    echo "    Create it first, for example:"
    echo "    python3.11 -m venv ${API_VENV}"
    echo "    source ${API_VENV}/bin/activate && pip install -e ${PROJECT_DIR} --no-build-isolation"
    exit 1
  fi
  source "${API_VENV}/bin/activate"
}

main() {
  local force_rebuild=0
  if [ "$#" -gt 1 ]; then
    echo "[-] Unknown argument(s): $*"
    echo "    Usage: scripts/run/ingest.sh [--full-rebuild]"
    exit 1
  fi
  if [ "$#" -eq 1 ]; then
    case "$1" in
      --full-rebuild|--full)
        force_rebuild=1
        ;;
      *)
        echo "[-] Unknown argument: $1"
        echo "    Usage: scripts/run/ingest.sh [--full-rebuild]"
        exit 1
        ;;
    esac
  fi
  ensure_env

  trap stop_started_embed EXIT INT TERM

  local effective_embed_base_url
  effective_embed_base_url="${CONFIGURED_EMBED_BASE_URL:-}"
  if [ -n "${effective_embed_base_url}" ] && [ "${effective_embed_base_url%/}" != "${LLM_BASE_URL%/}" ]; then
    if ! endpoint_has_embedding_model "${effective_embed_base_url}"; then
      echo "[-] Configured LLAMA_CPP_EMBED_BASE_URL=${effective_embed_base_url} has no reachable embedding model."
      echo "    Fix the endpoint or unset LLAMA_CPP_EMBED_BASE_URL to let ingest auto-start a local embedding server."
      exit 1
    fi
  else
    if endpoint_has_embedding_model "${AUTO_EMBED_BASE_URL}"; then
      effective_embed_base_url="${AUTO_EMBED_BASE_URL}"
      echo "[ingest-run] using existing embedding endpoint: ${effective_embed_base_url}"
    else
      start_embedding_server
      if ! wait_for_embedding_endpoint "${AUTO_EMBED_BASE_URL}" "${INGEST_WAIT_S}" "${STARTED_EMBED_PID}"; then
        echo "[-] Embedding endpoint did not become ready at ${AUTO_EMBED_BASE_URL} within ${INGEST_WAIT_S}s."
        echo "    Check log: ${EMBED_LOG_FILE}"
        exit 1
      fi
      effective_embed_base_url="${AUTO_EMBED_BASE_URL}"
      echo "[ingest-run] embedding endpoint ready: ${effective_embed_base_url}"
    fi
  fi

  export RAG_CONFIG_PATH="${RAG_CONFIG_PATH:-${PROJECT_DIR}/config/settings.yaml}"
  export RAG_ENV_FILE="${RAG_ENV_FILE:-${PROJECT_DIR}/.env}"
  export LLAMA_CPP_EMBED_BASE_URL="${effective_embed_base_url}"

  if [ "${force_rebuild}" = "1" ]; then
    echo "[ingest-run] full rebuild: resetting ${INDEX_DIR}"
    rm -rf "${INDEX_DIR}"
    mkdir -p "${INDEX_DIR}"
  fi

  echo "[ingest-run] running ingest with LLAMA_CPP_EMBED_BASE_URL=${LLAMA_CPP_EMBED_BASE_URL}"
  python "${PROJECT_DIR}/scripts/data/ingest.py"
}

main "$@"
