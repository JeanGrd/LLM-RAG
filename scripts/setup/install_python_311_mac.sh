#!/usr/bin/env bash
# Install Python 3.11 via Homebrew on macOS and create project venv in repo/.venv.
# Usage: ./scripts/setup/install_python_311_mac.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_DIR="${PROJECT_DIR}/.venv"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required. Install from https://brew.sh/ then rerun."
  exit 1
fi

echo "[+] Installing python@3.11 via Homebrew"
brew install python@3.11

PYBIN="$(brew --prefix)/bin/python3.11"
echo "[+] Using $($PYBIN --version)"

echo "[+] Creating virtualenv at ${VENV_DIR}"
$PYBIN -m venv "${VENV_DIR}"

echo "[+] Done. Next:"
echo "  source ${VENV_DIR}/bin/activate"
echo "  pip install -U pip"
echo "  pip install -e ${PROJECT_DIR}"
