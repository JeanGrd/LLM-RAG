#!/usr/bin/env bash
# Start a llama.cpp HTTP server using a model stored under the project models/ directory.
# Usage:
#   ./scripts/run/llama_server.sh [path-to-model.gguf]
# If no argument is provided, it will take the first *.gguf found in ./models.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODELS_DIR="${PROJECT_DIR}/models"
MODEL_PATH="${1:-${LLAMA_MODEL:-}}"

if [ -z "${MODEL_PATH}" ]; then
  gguf_files=()
  while IFS= read -r -d '' file; do
    gguf_files+=("${file}")
  done < <(find "${MODELS_DIR}" -maxdepth 1 -type f -name '*.gguf' -print0)
  if [ "${#gguf_files[@]}" -eq 0 ]; then
    echo "[-] No *.gguf found in ${MODELS_DIR}."
    echo "    Download a model (e.g. llama-3.2-3b-instruct-q4_k_m.gguf) into that folder, then rerun."
    exit 1
  fi
  for candidate in "${gguf_files[@]}"; do
    name_lower="$(basename "${candidate}" | tr '[:upper:]' '[:lower:]')"
    if [[ "${name_lower}" != *embed* ]]; then
      MODEL_PATH="${candidate}"
      break
    fi
  done
  # If all files look like embedding models, do not start chat mode by mistake.
  if [ -z "${MODEL_PATH}" ]; then
    if [ "${LLAMA_EMBEDDINGS_ONLY:-0}" = "1" ]; then
      MODEL_PATH="${gguf_files[0]}"
    else
      echo "[-] Only embedding models were found in ${MODELS_DIR}."
      echo "    Add a chat/instruct GGUF, or run embeddings-only mode:"
      echo "    LLAMA_EMBEDDINGS_ONLY=1 make llama"
      exit 1
    fi
  fi
fi

if [ ! -f "${MODEL_PATH}" ]; then
  echo "[-] Model file not found: ${MODEL_PATH}"
  exit 1
fi
if [ "$(dd if="${MODEL_PATH}" bs=4 count=1 2>/dev/null || true)" != "GGUF" ]; then
  echo "[-] '${MODEL_PATH}' is not a valid GGUF file."
  echo "    Tip: if your file is a few bytes (HTML/text), the download probably failed or requires auth."
  exit 1
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
TIMEOUT="${LLAMA_TIMEOUT_S:-120}"
LLAMA_THREADS="${LLAMA_THREADS:-8}"
LLAMA_THREADS_BATCH="${LLAMA_THREADS_BATCH:-${LLAMA_THREADS}}"
LLAMA_PARALLEL="${LLAMA_PARALLEL:-}"
LLAMA_ENABLE_EMBEDDINGS="${LLAMA_ENABLE_EMBEDDINGS:-1}"
LLAMA_EMBEDDINGS_ONLY="${LLAMA_EMBEDDINGS_ONLY:-0}"
LLAMA_SERVER_EXTRA_ARGS="${LLAMA_SERVER_EXTRA_ARGS:-}"
LLAMA_SERVER_RPC_TARGETS="${LLAMA_SERVER_RPC_TARGETS:-}"

if ! command -v llama-server >/dev/null 2>&1; then
  echo "[-] llama-server is not installed or not in PATH."
  echo "    Install with brew: brew install llama.cpp"
  exit 1
fi

rpc_targets=()
add_rpc_target() {
  local raw="$1"
  local normalized
  normalized="$(echo "${raw}" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
  if [ -z "${normalized}" ]; then
    return
  fi
  for existing in "${rpc_targets[@]}"; do
    if [ "${existing}" = "${normalized}" ]; then
      return
    fi
  done
  rpc_targets+=("${normalized}")
}

if [ -n "${LLAMA_SERVER_RPC_TARGETS}" ]; then
  rpc_from_env="$(echo "${LLAMA_SERVER_RPC_TARGETS}" | tr ';' ',' | tr ',' '\n')"
  while IFS= read -r target; do
    add_rpc_target "${target}"
  done <<< "${rpc_from_env}"
fi

echo "[llama-server] Model: ${MODEL_PATH}"
echo "[llama-server] Host: ${HOST}:${PORT}"
name_lower="$(basename "${MODEL_PATH}" | tr '[:upper:]' '[:lower:]')"
if [[ "${name_lower}" == *embed* ]] && [ "${LLAMA_EMBEDDINGS_ONLY}" != "1" ]; then
  echo "[llama-server] WARNING: selected model looks like an embedding model."
  echo "[llama-server]          For chat, choose an instruct/chat GGUF instead."
  echo "[llama-server]          For embedding-only mode, set LLAMA_EMBEDDINGS_ONLY=1."
fi
if [ "${LLAMA_EMBEDDINGS_ONLY}" = "1" ]; then
  LLAMA_ENABLE_EMBEDDINGS=1
fi
if [ "${LLAMA_ENABLE_EMBEDDINGS}" = "1" ]; then
  echo "[llama-server] Embeddings endpoint: enabled"
fi
if [ "${LLAMA_EMBEDDINGS_ONLY}" = "1" ]; then
  echo "[llama-server] Mode: embeddings-only"
fi
if [ "${#rpc_targets[@]}" -gt 0 ]; then
  echo "[llama-server] RPC targets:"
  for target in "${rpc_targets[@]}"; do
    echo "  - ${target}"
  done
fi

cmd=(
  llama-server
  --model "${MODEL_PATH}"
  --host "${HOST}"
  --port "${PORT}"
  --timeout "${TIMEOUT}"
  --threads "${LLAMA_THREADS}"
  --threads-batch "${LLAMA_THREADS_BATCH}"
)

if [ -n "${LLAMA_PARALLEL}" ]; then
  cmd+=(--parallel "${LLAMA_PARALLEL}")
fi
if [ "${#rpc_targets[@]}" -gt 0 ]; then
  for target in "${rpc_targets[@]}"; do
    cmd+=(--rpc "${target}")
  done
fi
if [ "${LLAMA_ENABLE_EMBEDDINGS}" = "1" ]; then
  cmd+=(--embeddings)
fi
if [ -n "${LLAMA_API_KEY:-}" ]; then
  cmd+=(--api-key "${LLAMA_API_KEY}")
fi
if [ -n "${LLAMA_ALIAS:-}" ]; then
  cmd+=(--alias "${LLAMA_ALIAS}")
fi
if [ -n "${LLAMA_SERVER_EXTRA_ARGS}" ]; then
  # shellcheck disable=SC2206
  extra_args=( ${LLAMA_SERVER_EXTRA_ARGS} )
  cmd+=("${extra_args[@]}")
fi

exec "${cmd[@]}"
