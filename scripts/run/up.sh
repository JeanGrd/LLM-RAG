#!/usr/bin/env bash
# Start chat llama, embed llama, and backend (managed with PID files).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_DIR="${PROJECT_DIR}/.run"
BACKEND_VENV="${BACKEND_VENV:-${PROJECT_DIR}/.venv-backend}"
OPENWEBUI_VENV="${OPENWEBUI_VENV:-${PROJECT_DIR}/.venv-openwebui}"
OPENWEBUI_PORT="${OPENWEBUI_PORT:-3000}"
OPENWEBUI_HOST="${OPENWEBUI_HOST:-0.0.0.0}"
OPENWEBUI_HOME="${OPENWEBUI_HOME:-${PROJECT_DIR}/.openwebui}"
CONFIG_PATH="${PROJECT_DIR}/config/settings.yaml"

if [ ! -x "${BACKEND_VENV}/bin/python" ]; then
  echo "[-] Missing backend venv at ${BACKEND_VENV}. Run: make install"
  exit 1
fi

# Read all runtime settings from YAML (single source of truth)
mapfile -t CFG < <(
  PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH:-}" "${BACKEND_VENV}/bin/python" - <<'PY'
from urllib.parse import urlparse
from rag.settings import load_settings

cfg = load_settings()

def host_port(url: str):
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return host, port

llm_url = cfg.llama_cpp.base_url.rstrip("/")
embed_url = (cfg.llama_cpp.embed_base_url or llm_url).rstrip("/")
llm_host, llm_port = host_port(llm_url)
embed_host, embed_port = host_port(embed_url)
llm_model = (cfg.llama_cpp.llm_model or "").strip()
embed_model = (cfg.llama_cpp.embed_model or llm_model).strip()
threads = cfg.llama_cpp.threads
batch_size = "" if cfg.llama_cpp.batch_size is None else cfg.llama_cpp.batch_size
ubatch_size = "" if cfg.llama_cpp.ubatch_size is None else cfg.llama_cpp.ubatch_size
print(llm_url)
print(embed_url)
print(llm_host)
print(llm_port)
print(embed_host)
print(embed_port)
print(llm_model)
print(embed_model)
print(threads)
print(batch_size)
print(ubatch_size)
print(cfg.server.host)
print(cfg.server.port)
print("1" if cfg.server.reload else "0")
PY
)
LLM_URL="${CFG[0]}"
EMBED_URL="${CFG[1]}"
LLM_HOST="${CFG[2]}"
LLM_PORT="${CFG[3]}"
EMBED_HOST="${CFG[4]}"
EMBED_PORT="${CFG[5]}"
LLM_MODEL="${CFG[6]}"
EMBED_MODEL="${CFG[7]}"
THREADS="${CFG[8]}"
BATCH_SIZE="${CFG[9]}"
UBATCH_SIZE="${CFG[10]}"
BACKEND_HOST="${CFG[11]}"
BACKEND_PORT="${CFG[12]}"
BACKEND_RELOAD="${CFG[13]}"

BACKEND_WAIT_HOST="${BACKEND_HOST}"
if [ "${BACKEND_WAIT_HOST}" = "0.0.0.0" ] || [ "${BACKEND_WAIT_HOST}" = "::" ]; then
  BACKEND_WAIT_HOST="127.0.0.1"
fi

mkdir -p "${RUN_DIR}"

is_alive() { kill -0 "$1" >/dev/null 2>&1; }

start_bg() {
  local name="$1"; shift
  local pid_file="${RUN_DIR}/${name}.pid"
  local log_file="${RUN_DIR}/${name}.log"
  if [ -f "${pid_file}" ]; then
    local pid; pid="$(cat "${pid_file}" 2>/dev/null || true)"
    if [ -n "${pid}" ] && is_alive "${pid}"; then
      echo "[up] ${name} already running (pid=${pid})"
      return 0
    fi
  fi
  echo "[up] starting ${name}..."
  nohup "$@" >"${log_file}" 2>&1 &
  local pid=$!
  echo "${pid}" > "${pid_file}"
  sleep 1
  if ! is_alive "${pid}"; then
    echo "[up] ERROR: ${name} failed to start (see ${log_file})"
    exit 1
  fi
  echo "[up] ${name} started (pid=${pid}, log=${log_file})"
}

wait_http() {
  local name="$1" url="$2" timeout="${3:-90}"
  local start="$(date +%s)"
  while true; do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      echo "[up] ${name} ready at ${url}"
      return 0
    fi
    if [ $(( $(date +%s) - start )) -ge "${timeout}" ]; then
      echo "[up] ERROR: timeout waiting for ${name} (${url})"
      exit 1
    fi
    sleep 1
  done
}

find_one() {
  local dir="$1" pattern="$2"
  find "${dir}" -maxdepth 1 -type f -name "*.gguf" 2>/dev/null | sort | grep -Ei "${pattern}" || true
}

pick_single() {
  local label="$1"; shift
  local files=("$@")
  local count="${#files[@]}"
  if [ "${count}" -eq 0 ]; then
    echo ""
  elif [ "${count}" -eq 1 ]; then
    echo "${files[0]}"
  else
    echo "[-] Multiple ${label} models found; set config/settings.yaml (llama_cpp.${label}_model) to choose:" >&2
    printf '  %s\n' "${files[@]}" >&2
    exit 1
  fi
}

if [ -z "${LLM_MODEL}" ]; then
  mapfile -t chat_candidates < <(find_one "${PROJECT_DIR}/models/chat" ".*" | grep -vi embed || true)
  if [ "${#chat_candidates[@]}" -eq 0 ]; then
    mapfile -t chat_candidates < <(find_one "${PROJECT_DIR}/models" ".*" | grep -vi embed || true)
  fi
  LLM_MODEL="$(pick_single "llm" "${chat_candidates[@]}")"
fi
if [ -z "${LLM_MODEL}" ]; then
  echo "[-] No chat model configured in config/settings.yaml (llama_cpp.llm_model) or found in models/ or models/chat."
  exit 1
fi

if [ -z "${EMBED_MODEL}" ]; then
  mapfile -t embed_candidates < <(find_one "${PROJECT_DIR}/models/embed" "embed" || true)
  if [ "${#embed_candidates[@]}" -eq 0 ]; then
    mapfile -t embed_candidates < <(find_one "${PROJECT_DIR}/models" "embed" || true)
  fi
  EMBED_MODEL="$(pick_single "embed" "${embed_candidates[@]}")"
  if [ -z "${EMBED_MODEL}" ]; then
    EMBED_MODEL="${LLM_MODEL}"
    echo "[up] No embedding model configured; reusing chat model."
  fi
fi

USE_SINGLE_LLAMA="${USE_SINGLE_LLAMA:-0}"
if [ "${EMBED_URL}" = "${LLM_URL}" ]; then
  USE_SINGLE_LLAMA=1
  EMBED_MODEL="${LLM_MODEL}"
  EMBED_PORT="${LLM_PORT}"
  echo "[up] embed_base_url == base_url -> using single llama server."
fi

start_bg "llama-chat" env HOST="${LLM_HOST}" PORT="${LLM_PORT}" LLAMA_THREADS="${THREADS}" LLAMA_BATCH_SIZE="${BATCH_SIZE}" LLAMA_UBATCH_SIZE="${UBATCH_SIZE}" "${PROJECT_DIR}/scripts/run/llama.sh" "${LLM_MODEL}"
wait_http "llama-chat" "${LLM_URL}/v1/models" 60

if [ "${USE_SINGLE_LLAMA}" != "1" ]; then
  start_bg "llama-embed" env HOST="${EMBED_HOST}" PORT="${EMBED_PORT}" LLAMA_THREADS="${THREADS}" LLAMA_BATCH_SIZE="${BATCH_SIZE}" LLAMA_UBATCH_SIZE="${UBATCH_SIZE}" LLAMA_EMBEDDINGS_ONLY=1 "${PROJECT_DIR}/scripts/run/llama.sh" "${EMBED_MODEL}"
  wait_http "llama-embed" "${EMBED_URL}/v1/models" 60
fi

if [ ! -x "${BACKEND_VENV}/bin/python" ]; then
  echo "[-] Missing backend venv at ${BACKEND_VENV}. Run: make install"
  exit 1
fi
start_bg "backend" bash -c "source '${BACKEND_VENV}/bin/activate' && export PYTHONPATH='${PROJECT_DIR}/src':${PYTHONPATH:-} && python '${PROJECT_DIR}/scripts/app/run_api.py'" || { echo '[-] backend failed'; exit 1; }
wait_http "backend" "http://${BACKEND_WAIT_HOST}:${BACKEND_PORT}/v1/models" 60

if [ ! -x "${OPENWEBUI_VENV}/bin/python" ]; then
  echo "[-] Missing Open WebUI venv at ${OPENWEBUI_VENV}. Run: make install"
  exit 1
fi
start_bg "openwebui" env \
  OPENWEBUI_HOST="${OPENWEBUI_HOST}" \
  OPENWEBUI_PORT="${OPENWEBUI_PORT}" \
  OPENWEBUI_HOME="${OPENWEBUI_HOME}" \
  OPENWEBUI_DB_PATH="${OPENWEBUI_HOME}/webui.db" \
  OPENAI_API_BASE_URL="http://${BACKEND_WAIT_HOST}:${BACKEND_PORT}/v1" \
  OPENAI_API_KEY="${OPENAI_API_KEY:-local-rag}" \
  "${PROJECT_DIR}/scripts/run/openwebui.sh" || { echo '[-] openwebui failed'; exit 1; }
wait_http "openwebui" "http://127.0.0.1:${OPENWEBUI_PORT}/api/version" 120

echo "[up] stack is up"
echo "[up] Open WebUI: http://127.0.0.1:${OPENWEBUI_PORT}"
