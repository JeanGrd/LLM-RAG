#!/usr/bin/env bash
# Ensure required Ollama models are present (chat + embedding).
# Works on macOS/Linux with native Ollama installed and reachable on localhost.
# Usage:
#   ./scripts/setup/prepare_ollama.sh
# Optional env:
#   CHAT_MODEL (optional; if empty, chat pull is skipped)
#   EMBED_MODEL (default: nomic-embed-text)
set -euo pipefail

CHAT_MODEL="${CHAT_MODEL:-}"
EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "[-] ollama CLI not found. Install and start ollama serve first."
  exit 1
fi

need_pull() {
  local name="$1"
  ollama list | awk '{print $1}' | grep -Fx "$name" >/dev/null 2>&1 || return 0
  return 1
}

echo "[+] Checking embedding model: $EMBED_MODEL"
if need_pull "$EMBED_MODEL"; then
  echo "    Pulling $EMBED_MODEL ..."
  ollama pull "$EMBED_MODEL"
else
  echo "    Already present."
fi

if [ -z "${CHAT_MODEL}" ]; then
  echo "[+] CHAT_MODEL not set. Skipping chat model pull."
else
  echo "[+] Checking chat model: $CHAT_MODEL"
  if need_pull "$CHAT_MODEL"; then
    echo "    Pulling $CHAT_MODEL ..."
    ollama pull "$CHAT_MODEL"
  else
    echo "    Already present."
  fi
fi

echo "[+] Ollama models ready."
