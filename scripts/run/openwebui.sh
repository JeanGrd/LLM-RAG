#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OPENWEBUI_VENV="${OPENWEBUI_VENV:-${PROJECT_DIR}/.venv-openwebui}"
OPENWEBUI_HOST="${OPENWEBUI_HOST:-0.0.0.0}"
OPENWEBUI_PORT="${OPENWEBUI_PORT:-3000}"
OPENAI_API_BASE_URL="${OPENAI_API_BASE_URL:-http://127.0.0.1:8000/v1}"
OPENAI_API_KEY="${OPENAI_API_KEY:-local-rag}"
OPENWEBUI_HOME="${OPENWEBUI_HOME:-${PROJECT_DIR}/.openwebui}"
OPENWEBUI_DB_PATH="${OPENWEBUI_DB_PATH:-${OPENWEBUI_HOME}/webui.db}"

if [ ! -x "${OPENWEBUI_VENV}/bin/python" ]; then
  echo "[-] Missing Open WebUI venv at ${OPENWEBUI_VENV}. Run: make install"
  exit 1
fi

source "${OPENWEBUI_VENV}/bin/activate"

mkdir -p "${OPENWEBUI_HOME}"

# Ensure frontend assets are available under static/
pkg_root="$(
  "${OPENWEBUI_VENV}/bin/python" - <<'PY'
import importlib.util, os
spec = importlib.util.find_spec("open_webui")
print(os.path.dirname(spec.origin))
PY
)"
if [ -n "${pkg_root}" ] && [ ! -d "${pkg_root}/static/_app" ] && [ -d "${pkg_root}/frontend/_app" ]; then
  cp -R "${pkg_root}/frontend/_app" "${pkg_root}/static/_app"
fi

echo "[openwebui] upstream: ${OPENAI_API_BASE_URL}"
echo "[openwebui] starting on ${OPENWEBUI_HOST}:${OPENWEBUI_PORT}"
OPENAI_API_BASE_URL="${OPENAI_API_BASE_URL}" \
OPENAI_API_KEY="${OPENAI_API_KEY}" \
OPENWEBUI_HOME="${OPENWEBUI_HOME}" \
OPENWEBUI_DB_PATH="${OPENWEBUI_DB_PATH}" \
open-webui serve --host "${OPENWEBUI_HOST}" --port "${OPENWEBUI_PORT}"
