#!/usr/bin/env bash
# List local GGUF files and remote llama.cpp models.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODELS_DIR="${PROJECT_DIR}/models"
LLAMA_CPP_BASE_URL="${LLAMA_CPP_BASE_URL:-http://127.0.0.1:8080}"

human_size() {
  local bytes="$1"
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$bytes" <<'PY'
import sys
size = float(sys.argv[1])
units = ["B", "KB", "MB", "GB", "TB"]
idx = 0
while size >= 1024 and idx < len(units) - 1:
    size /= 1024
    idx += 1
print(f"{size:.1f}{units[idx]}")
PY
    return
  fi
  echo "${bytes}B"
}

model_kind() {
  local name_lower
  name_lower="$(echo "$1" | tr '[:upper:]' '[:lower:]')"
  if [[ "${name_lower}" == *embed* ]] || [[ "${name_lower}" == *embedding* ]]; then
    echo "embedding"
  else
    echo "chat"
  fi
}

is_valid_gguf() {
  local path="$1"
  local header
  header="$(dd if="${path}" bs=4 count=1 2>/dev/null || true)"
  [ "${header}" = "GGUF" ]
}

echo "[models] Local folder: ${MODELS_DIR}"
if [ ! -d "${MODELS_DIR}" ]; then
  echo "  - missing directory"
else
  found_any=0
  printf "  %-52s %-10s %-10s %s\n" "name" "size" "kind" "status"
  while IFS= read -r -d '' file; do
    found_any=1
    filename="$(basename "${file}")"
    size_bytes="$(stat -f%z "${file}" 2>/dev/null || stat -c%s "${file}" 2>/dev/null || echo 0)"
    size_human="$(human_size "${size_bytes}")"
    kind="$(model_kind "${filename}")"
    if is_valid_gguf "${file}"; then
      status="ok"
    else
      status="invalid (not GGUF)"
    fi
    printf "  %-52s %-10s %-10s %s\n" "${filename}" "${size_human}" "${kind}" "${status}"
  done < <(find "${MODELS_DIR}" -maxdepth 1 -type f -name '*.gguf' -print0)
  if [ "${found_any}" = "0" ]; then
    echo "  - no .gguf file found"
  fi
fi

echo
echo "[models] Remote endpoint: ${LLAMA_CPP_BASE_URL%/}/v1/models"
if ! command -v curl >/dev/null 2>&1; then
  echo "  - curl is not available"
  exit 0
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "  - python3 is required to parse JSON output"
  exit 0
fi

remote_json="$(curl -fsS "${LLAMA_CPP_BASE_URL%/}/v1/models" 2>/dev/null || true)"
if [ -z "${remote_json}" ]; then
  echo "  - endpoint not reachable"
  exit 0
fi

remote_models="$(printf '%s' "${remote_json}" | python3 -c '
import json
import sys
try:
    payload = json.load(sys.stdin)
except Exception:
    print("")
    raise SystemExit(0)
for item in payload.get("data", []):
    model_id = item.get("id") or item.get("model")
    if isinstance(model_id, str) and model_id.strip():
        print(model_id.strip())
')"

if [ -z "${remote_models}" ]; then
  echo "  - no model published by server"
  exit 0
fi

printf "  %-52s %s\n" "id" "kind"
while IFS= read -r model_id; do
  [ -z "${model_id}" ] && continue
  printf "  %-52s %s\n" "${model_id}" "$(model_kind "${model_id}")"
done <<< "${remote_models}"
