# EXP-003 — Reproducibility

**Session 001 · Nebius AI Cloud · 1× NVIDIA H200 · vLLM · Qwen3-0.6B**

This document separates what was **actually executed** from what is
**proposed automation**. Nothing in the "proposed" column was validated in
Session 001.

---

## Historical procedure (actually executed)

| Step | Action | Evidence |
| --- | --- | --- |
| 1 | Provision one H200 instance in Nebius `eu-north1` through the console | Session record |
| 2 | Attach a dedicated Security Group with restricted access | Session record |
| 3 | Access the VM over SSH using a public key | Session record |
| 4 | Confirm the GPU with `nvidia-smi` | `gpu-baseline.txt`, `nvidia-smi-full.txt` |
| 5 | Confirm CUDA Toolkit with `nvcc` | Session record; `python-packages.txt` |
| 6 | Run a PyTorch CUDA operation | Session record (stdout not persisted) |
| 7 | Run NVIDIA DCGM level 1 | `dcgm-level1.txt` |
| 8 | Verify GPU access from Docker | Session record |
| 9 | Start vLLM with the model bound to `127.0.0.1:8000` | `vllm.log`, `vllm-inspect.json` |
| 10 | Run one chat completion | `qwen3-inference.json` |
| 11 | Run the 10-request benchmark | `benchmarks/qwen3-0.6b.json` |
| 12 | Copy evidence to the operator workstation | Session record |
| 13 | Stop the VM | Read-only CLI check: `STOPPED` |

### Historical gaps

- The PyTorch CUDA check and the Docker GPU check were not saved as files.
- vCPU count and Docker version come from the session record, not from a file.
- The Security Group rules were not exported as evidence.
- Cost was not reconciled with a billing export.

Session 002 should close these gaps.

---

## Prerequisites

| Requirement | Minimum / expected |
| --- | --- |
| Nebius project | GPU quota for `compute.instance.gpu.h200` in the target region |
| GPU | 1× NVIDIA H200 (or compatible) |
| CPU / RAM | 16 vCPU · 200 GiB RAM provisioned |
| Disk | 100 GiB SSD |
| OS | Ubuntu 24.04 LTS with NVIDIA driver and CUDA 13.0 |
| Docker | Docker Engine + NVIDIA Container Toolkit |
| Network | SSH access; inference port bound to loopback only |
| Model cache | ~1.5 GiB free for `Qwen/Qwen3-0.6B` |
| Python | 3.11+ for the benchmark script (standard library only) |

---

## Step-by-step

### 1. Provision the instance

Use the Nebius console (historical path) or an approved infrastructure-as-code
workflow. Do not use this document as proof that Terraform exists.

Record in the session log:

- region;
- instance type and GPU count;
- start time in UTC;
- Spot policy and maximum price;
- disk size and retention policy.

### 2. Restrict access

- Use a dedicated Security Group.
- Allow SSH only from the operator's address.
- Do **not** expose port 8000 publicly. The inference port must stay on
  `127.0.0.1` at the host level.

### 3. Validate the GPU

```bash
./scripts/validate-gpu.sh
```

Expected: `PASS`. The script checks `nvidia-smi`, `nvcc`, PyTorch CUDA, DCGM
(if installed) and GPU access from an already-present vLLM image.

Persist the full output:

```bash
./scripts/validate-gpu.sh | tee evidence/gpu-validation.txt
```

### 4. Start vLLM

```bash
./scripts/docker-run.sh
```

The script:

- binds `127.0.0.1:8000:8000`;
- mounts `$HOME/exp003/models-cache` at `/root/.cache/huggingface`;
- uses the same vLLM image digest as Session 001;
- runs `vllm serve --model Qwen/Qwen3-0.6B --max-model-len 4096`.

First start downloads ~1.40 GiB of weights and takes roughly two minutes before
the API is ready.

### 5. Validate inference

In a second shell on the same VM:

```bash
./scripts/validate-inference.sh
```

Expected: `/health` returns 200, `/v1/models` lists the model, and a short chat
completion returns `finish_reason` and token counts.

### 6. Run the benchmark

```bash
python3 benchmarks/benchmark_api.py \
  --url http://127.0.0.1:8000/v1/chat/completions \
  --model Qwen/Qwen3-0.6B \
  --requests 10 \
  --max-tokens 128 \
  --temperature 0.6 \
  --output qwen3-0.6b.json
```

Expected shape (Session 001 values, not a guarantee):

| Metric | Session 001 |
| --- | ---: |
| Total output tokens | 1,163 |
| Mean latency | 0.20773 s |
| Aggregate output throughput | 559.86 tokens/s |
| Finish reasons | 6 `stop`, 4 `length` |

### 7. Preserve evidence

Create a private session directory with the raw files, then generate the public
mirror:

```bash
python3 scripts/sanitize-evidence.py \
  --input /path/to/private/session-001 \
  --output evidence/public/session-001 \
  --report evidence/public/sanitization-report.json \
  --clean
```

Verify the residual scan says `PASS` and regenerate `MANIFEST.sha256`.

### 8. Stop the VM

Stop the instance when the evidence is copied. Confirm the state with:

```bash
python3 scripts/check-vm-state.py
```

Expected: the instance appears as `STOPPED`. Do not delete resources without
explicit approval.

---

## Validation gates

| Gate | Pass condition |
| --- | --- |
| GPU present | `nvidia-smi` lists the expected GPU and VRAM |
| CUDA toolkit | `nvcc --version` succeeds |
| PyTorch CUDA | `torch.cuda.is_available()` is true and a CUDA op completes |
| DCGM | Level-1 diagnostic returns Pass |
| Docker GPU | Container can run `nvidia-smi` |
| API health | `GET /health` returns 200 |
| Model listed | `GET /v1/models` includes the model |
| Inference | Chat completion returns a valid OpenAI-shaped response |
| Benchmark | JSON contains N requests, token counts and latencies |
| Sanitization | Residual scan `PASS`; originals remain private |
| Lifecycle | VM state is `STOPPED` at close |

---

## Proposed automation (not tested)

| Proposal | Status |
| --- | --- |
| `infra/docker-run.sh` | Reference command derived from the observed container configuration; not executed by the publication workflow |
| `scripts/validate-gpu.sh` | New read-only validation script; syntax-checked, not run on a GPU in this session |
| `scripts/validate-inference.sh` | New endpoint validation script; syntax-checked, not run against a live endpoint in this session |
| Terraform / Pulumi | **Not used and not provided** |
| cloud-init | **Not used and not provided** |

Do not describe the proposed scripts as "tested on the H200" until they are run
in Session 002 and their output is persisted.

---

## Known gotchas

- vLLM logs `0.0.0.0:8000` **inside** the container; the host binding from
  `docker inspect` is what proves loopback-only exposure.
- `--model` is accepted by `vllm serve` but newer versions may prefer a
  positional model argument.
- `enable_thinking: false` is required for Qwen3 to avoid reasoning tokens in
  this setup.
- `max_tokens=128` truncates longer answers; inspect `finish_reason`.
- The first request can be slower; no warm-up was performed.
- Spot capacity can be reclaimed; retry policy belongs to a later experiment.

---

## Pending for Session 002

1. Persist stdout for every validation command.
2. Export Security Group rules and instance metadata in a sanitized form.
3. Record vCPU, RAM and Docker version from the instance itself.
4. Add concurrency and TTFT measurements.
5. Test 8B and 14B models.
6. Reconcile cost with the provider's billing export.
7. Run the proposed scripts end-to-end and update their status.
