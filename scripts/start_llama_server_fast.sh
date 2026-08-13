#!/usr/bin/env bash
set -euo pipefail

LLAMA_SERVER="${LLAMA_SERVER:-/home/admin/llama.cpp/build/bin/llama-server}"
MODEL_REPO="${MODEL_REPO:-Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M}"

exec "$LLAMA_SERVER" \
  --hf-repo "$MODEL_REPO" \
  --no-mmproj \
  --alias rafiki-local \
  --host 127.0.0.1 \
  --port 8080 \
  --ctx-size 2048 \
  --threads 4
