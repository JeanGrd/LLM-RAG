#!/usr/bin/env bash
# Project diagnostics: env, models, endpoints, and runtime sanity checks.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_VENV="${API_VENV:-${PROJECT_DIR}/.venv}"
if [ -z "${OPENWEBUI_VENV:-}" ]; then
  if [ -d "${PROJECT_DIR}/.openwebui-venv" ]; then
    OPENWEBUI_VENV="${PROJECT_DIR}/.openwebui-venv"
  else
    OPENWEBUI_VENV="${HOME}/openwebui-venv"
  fi
fi
MODELS_DIR="${MODELS_DIR:-${PROJECT_DIR}/models}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8000/v1}"
LLM_BASE_URL="${LLAMA_CPP_BASE_URL:-http://127.0.0.1:8080}"
EMBED_BASE_URL="${LLAMA_CPP_EMBED_BASE_URL:-${LLM_BASE_URL}}"

ok_count=0
warn_count=0
fail_count=0

ok() {
  echo "[OK] $1"
  ok_count=$((ok_count + 1))
}

warn() {
  echo "[WARN] $1"
  warn_count=$((warn_count + 1))
}

fail() {
  echo "[FAIL] $1"
  fail_count=$((fail_count + 1))
}

check_http_json() {
  local url="$1"
  if ! command -v curl >/dev/null 2>&1; then
    warn "curl not installed; cannot probe ${url}"
    return 0
  fi
  if curl -fsS "${url}" >/dev/null 2>&1; then
    ok "Reachable: ${url}"
  else
    fail "Unreachable: ${url}"
  fi
}

echo "[doctor] Project: ${PROJECT_DIR}"

if [ -f "${API_VENV}/bin/activate" ]; then
  ok "Backend venv found: ${API_VENV}"
  if "${API_VENV}/bin/python" -c "import rag, uvicorn" >/dev/null 2>&1; then
    ok "Backend Python deps look installed"
  else
    fail "Backend deps missing in ${API_VENV} (run: source .venv/bin/activate && pip install -e . --no-build-isolation)"
  fi
else
  fail "Backend venv missing: ${API_VENV}"
fi

if [ -f "${OPENWEBUI_VENV}/bin/activate" ]; then
  ok "OpenWebUI venv found: ${OPENWEBUI_VENV}"
else
  warn "OpenWebUI venv not found at ${OPENWEBUI_VENV} (created on first make openwebui run)"
fi

if [ ! -d "${MODELS_DIR}" ]; then
  fail "Models directory missing: ${MODELS_DIR}"
else
  gguf_found=0
  invalid_count=0
  while IFS= read -r -d '' model_path; do
    gguf_found=1
    header="$(dd if="${model_path}" bs=4 count=1 2>/dev/null || true)"
    if [ "${header}" = "GGUF" ]; then
      ok "GGUF model OK: $(basename "${model_path}")"
    else
      fail "Invalid GGUF file: ${model_path}"
      invalid_count=$((invalid_count + 1))
    fi
  done < <(find "${MODELS_DIR}" -maxdepth 1 -type f -name '*.gguf' -print0)
  if [ "${gguf_found}" = "0" ]; then
    fail "No .gguf models found in ${MODELS_DIR}"
  fi
  if [ "${invalid_count}" -gt 0 ]; then
    warn "Fix invalid GGUF files before launch"
  fi
fi

if [ -f "${PROJECT_DIR}/.env" ]; then
  ok ".env found (${PROJECT_DIR}/.env)"
else
  warn ".env not found (defaults will be used)"
fi

if [ -f "${API_VENV}/bin/python" ]; then
  if "${API_VENV}/bin/python" - <<'PY' >/dev/null 2>&1
from rag.settings import load_settings
cfg = load_settings()
llm_model = (cfg.llama_cpp.llm_model or "").strip().lower()
if llm_model and ("embed" in llm_model or "embedding" in llm_model):
    raise SystemExit(1)
PY
  then
    ok "Default chat model setting looks valid"
  else
    fail "LLAMA_CPP_LLM_MODEL looks like an embedding model"
  fi
fi

check_http_json "${LLM_BASE_URL%/}/v1/models"
if [ "${EMBED_BASE_URL%/}" != "${LLM_BASE_URL%/}" ]; then
  check_http_json "${EMBED_BASE_URL%/}/v1/models"
fi
check_http_json "${BACKEND_BASE_URL%/}/models"

echo
echo "[doctor] Result: ${ok_count} OK, ${warn_count} WARN, ${fail_count} FAIL"
if [ "${fail_count}" -gt 0 ]; then
  exit 1
fi
