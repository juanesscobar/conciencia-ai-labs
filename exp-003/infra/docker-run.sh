#!/usr/bin/env bash
# EXP-003 — run vLLM on a single H200, bound to loopback only.
# Historical Session 001 used this shape (port 127.0.0.1:8000, model cache bind).
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen3-0.6B}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
VLLM_IMAGE="${VLLM_IMAGE:-vllm/vllm-openai@sha256:befccf0e7e4089aa23926bb6f887a85c0d46c2a99e6de5c5ffdf5cb7957c5b34}"
MODELS_CACHE="${MODELS_CACHE:-$HOME/exp003/models-cache}"

mkdir -p "$MODELS_CACHE"

exec docker run --rm --gpus all --name exp003-vllm \
  -p 127.0.0.1:8000:8000 \
  -v "$MODELS_CACHE:/root/.cache/huggingface" \
  "$VLLM_IMAGE" \
  --model "$MODEL" \
  --max-model-len "$MAX_MODEL_LEN"
