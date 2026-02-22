#!/usr/bin/env bash
# Start only the API backend. Assumes llama servers are already running.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_VENV="${BACKEND_VENV:-${PROJECT_DIR}/.venv-backend}"

if [ ! -x "${BACKEND_VENV}/bin/python" ]; then
  echo "[-] Missing backend venv at ${BACKEND_VENV}. Run: make install"
  exit 1
fi

source "${BACKEND_VENV}/bin/activate"
export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH:-}"
python "${PROJECT_DIR}/scripts/app/run_api.py"
