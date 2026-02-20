#!/usr/bin/env bash
# Create virtualenvs for backend and Open WebUI (llama uses native binary).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_VENV="${BACKEND_VENV:-${PROJECT_DIR}/.venv-backend}"
OPENWEBUI_VENV="${OPENWEBUI_VENV:-${PROJECT_DIR}/.venv-openwebui}"
PY_BIN="${PYTHON_BIN:-python3.11}"
OPENWEBUI_PY_BIN="${OPENWEBUI_PY_BIN:-python3.11}"

create_venv() {
  local venv_path="$1"
  local py_bin="$2"
  if [ -d "${venv_path}" ]; then
    echo "[install] venv already exists: ${venv_path}"
    return 0
  fi
  if ! command -v "${py_bin}" >/dev/null 2>&1; then
    echo "[-] ${py_bin} not found. Install Python 3.11 and retry."
    exit 1
  fi
  echo "[install] Creating venv at ${venv_path}"
  "${py_bin}" -m venv "${venv_path}"
}

pip_install() {
  local venv_path="$1"; shift
  source "${venv_path}/bin/activate"
  pip install -U pip
  if [ "$#" -gt 0 ]; then
    pip install "$@"
  fi
  deactivate
}

create_venv "${BACKEND_VENV}" "${PY_BIN}"
pip_install "${BACKEND_VENV}" pip setuptools wheel build
pip_install "${BACKEND_VENV}" -e "${PROJECT_DIR}" --no-build-isolation

create_venv "${OPENWEBUI_VENV}" "${OPENWEBUI_PY_BIN}"
pip_install "${OPENWEBUI_VENV}" -U pip setuptools wheel
pip_install "${OPENWEBUI_VENV}" open-webui

echo "[install] Done."
echo "[install] Backend venv : ${BACKEND_VENV}"
echo "[install] WebUI venv   : ${OPENWEBUI_VENV}"
