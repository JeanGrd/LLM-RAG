#!/usr/bin/env bash
# Start llama-server (native binary) with a given model.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODEL_PATH="${LLM_MODEL:-${1:-}}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
EMBEDDINGS_ONLY="${LLAMA_EMBEDDINGS_ONLY:-0}"
THREADS="${LLAMA_THREADS:-4}"

if [ -z "${MODEL_PATH}" ]; then
  echo "[-] LLM_MODEL not set and no model path passed."
  exit 1
fi
if [ ! -f "${MODEL_PATH}" ]; then
  echo "[-] Model file not found: ${MODEL_PATH}"
  exit 1
fi
if ! command -v llama-server >/dev/null 2>&1; then
  echo "[-] llama-server binary not found in PATH. Install llama.cpp (e.g. brew install llama.cpp)."
  exit 1
fi

cmd=(
  llama-server
  --model "${MODEL_PATH}"
  --host "${HOST}"
  --port "${PORT}"
  --threads "${THREADS}"
)

cmd+=(--embeddings)
if [ "${EMBEDDINGS_ONLY}" = "1" ]; then
  cmd+=(--pooling mean)
fi

exec "${cmd[@]}"
