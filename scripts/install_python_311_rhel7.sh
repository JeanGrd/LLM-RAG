#!/usr/bin/env bash
# Install Python 3.11 on RHEL/CentOS 7.x, create project venv in repo/.venv.
# Usage: sudo ./scripts/install_python_311_rhel7.sh
set -euo pipefail

PY_VERSION=3.11.8
PY_PREFIX=/usr/local
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${PROJECT_DIR}/.venv"

echo "[+] Installing build dependencies (yum)"
yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel readline-devel sqlite-devel make wget >/dev/null

if ! command -v python3.11 >/dev/null 2>&1; then
  echo "[+] Downloading Python ${PY_VERSION}"
  cd /tmp
  wget -q https://www.python.org/ftp/python/${PY_VERSION}/Python-${PY_VERSION}.tgz
  tar xzf Python-${PY_VERSION}.tgz
  cd Python-${PY_VERSION}
  echo "[+] Building Python ${PY_VERSION}"
  ./configure --prefix=${PY_PREFIX} --enable-optimizations >/dev/null
  make -s -j"$(nproc)"
  make altinstall >/dev/null
fi
echo "[+] Using $(/usr/local/bin/python3.11 --version)"

echo "[+] Creating virtualenv at ${VENV_DIR}"
/usr/local/bin/python3.11 -m venv "${VENV_DIR}"

echo "[+] Done. Next:"
echo "  source ${VENV_DIR}/bin/activate"
echo "  pip install -U pip"
echo "  pip install -e ${PROJECT_DIR}"
