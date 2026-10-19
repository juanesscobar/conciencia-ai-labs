#!/usr/bin/env bash
# EXP-003 — read-only GPU validation.
# Run inside the GPU VM. Does not start, stop or modify cloud resources.
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
VLLM_IMAGE="${VLLM_IMAGE:-vllm/vllm-openai@sha256:befccf0e7e4089aa23926bb6f887a85c0d46c2a99e6de5c5ffdf5cb7957c5b34}"
FAIL=0

section() { printf '\n== %s ==\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1" >&2; FAIL=1; }
skip() { printf 'SKIP: %s\n' "$1"; }

section "Host"
uname -a
printf 'date_utc: '; date -u +%Y-%m-%dT%H:%M:%SZ

section "NVIDIA-SMI"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,driver_version,cuda_version \
    --format=csv,noheader || fail "nvidia-smi query failed"
else
  fail "nvidia-smi not found"
fi

section "CUDA Toolkit"
if command -v nvcc >/dev/null 2>&1; then
  nvcc --version | tail -n 4
else
  fail "nvcc not found"
fi

section "PyTorch CUDA"
if "$PYTHON_BIN" - <<'PY'
import torch
print("torch:", torch.__version__)
print("cuda_available:", torch.cuda.is_available())
print("device_count:", torch.cuda.device_count())
if not torch.cuda.is_available():
    raise SystemExit(1)
x = torch.arange(4096, dtype=torch.float32, device="cuda")
y = (x * 2).sum()
torch.cuda.synchronize()
print("cuda_op_sum:", float(y))
print("device_name:", torch.cuda.get_device_name(0))
PY
then
  :
else
  fail "PyTorch CUDA operation failed"
fi

section "NVIDIA DCGM (level 1)"
if command -v dcgmi >/dev/null 2>&1; then
  dcgmi diag -r 1 || fail "DCGM level-1 diagnostic failed"
else
  skip "dcgmi not installed"
fi

section "Docker GPU access"
if ! command -v docker >/dev/null 2>&1; then
  skip "docker not installed"
elif ! docker info >/dev/null 2>&1; then
  fail "docker daemon not reachable"
elif ! docker image inspect "$VLLM_IMAGE" >/dev/null 2>&1; then
  skip "vLLM image not present locally; run scripts/docker-run.sh first"
else
  docker run --rm --gpus all "$VLLM_IMAGE" nvidia-smi -L \
    || fail "container cannot access the GPU"
fi

section "Result"
if [ "$FAIL" -eq 0 ]; then
  echo "PASS"
else
  echo "FAIL"
fi
exit "$FAIL"
