# EXP-003 — NVIDIA H200 GPU Inference on Nebius AI Cloud

**Status:** Session 001 completed · **Reality:** `REAL` (cloud GPU, not simulated)
**Provider:** Nebius AI Cloud · **Region:** `eu-north1`
**GPU:** NVIDIA H200 NVLink · 1 GPU · ~141 GB VRAM
**Model:** `Qwen/Qwen3-0.6B` · **Serving:** vLLM 0.32.0 · **Date:** 2026-10-19
**VM at close:** `STOPPED` (confirmed with a read-only Nebius CLI query)

EXP-003 validates the end-to-end path from a Nebius H200 instance to an
OpenAI-compatible inference endpoint: GPU recognition, CUDA/PyTorch, DCGM,
Docker GPU access, vLLM serving and a sequential HTTP benchmark. It is a
**small, single-GPU engineering validation**, not a maximum-throughput
benchmark, a model-quality evaluation or a provider comparison.

## Observed results

| Metric | Value |
| --- | --- |
| Requests | 10 sequential HTTP chat-completions |
| Output tokens | 1,163 |
| Mean end-to-end latency | **0.20773 s** (207.73 ms) |
| Aggregate output throughput | **559.86 tokens/s** |
| Finish reasons | 6 `stop`, 4 `length` (`max_tokens=128`) |
| Session spend (reported) | ~USD 1.70 over ~55 min (~USD 1.85/h arithmetic average) |

The throughput is aggregate end-to-end output throughput for a single-stream
sequential test. It is **not** the maximum throughput of an H200. Four requests
hit the `max_tokens=128` limit, so their content is not complete even though the
HTTP request succeeded.

## What was verified

1. H200 instance provisioning and SSH access with a public key.
2. A dedicated Security Group with restricted access.
3. GPU recognition via `nvidia-smi` (143,771 MiB VRAM, driver 580.173.02, CUDA 13.0).
4. CUDA Toolkit 13.0 and PyTorch 2.13.0+cu130 in the Python environment.
5. NVIDIA DCGM 4.7.0 level-1 diagnostic: **PASS**.
6. GPU access from a Docker container.
7. vLLM 0.32.0 serving `Qwen/Qwen3-0.6B` with an OpenAI-compatible API.
8. One successful chat completion persisted as evidence.
9. A 10-request sequential benchmark, persisted as JSON.
10. Evidence copied to the operator workstation; VM stopped at the end.

## Evidence

- Sanitized public evidence: [`evidence/public/session-001/`](evidence/public/session-001/)
- Sanitization report and hashes: [`evidence/public/sanitization-report.json`](evidence/public/sanitization-report.json) · [`evidence/public/MANIFEST.sha256`](evidence/public/MANIFEST.sha256)
- Evidence index: [`evidence/public/README.md`](evidence/public/README.md)

The private originals remain outside the public repository. The public mirror
was generated with [`scripts/sanitize-evidence.py`](scripts/sanitize-evidence.py).

## Reports

- [EXP-003 — H200 inference report](reports/EXP-003-H200-INFERENCE.md)
- [EXP-003 — Cost and lifecycle](reports/EXP-003-COST-AND-LIFECYCLE.md)
- [EXP-003 — Reproducibility](reports/EXP-003-REPRODUCIBILITY.md)

## Reproduce

```bash
# Inside the GPU VM, with Docker + NVIDIA Container Toolkit installed:
./scripts/validate-gpu.sh
./scripts/docker-run.sh            # vLLM on 127.0.0.1:8000
./scripts/validate-inference.sh

# From another shell on the same VM:
python3 benchmarks/benchmark_api.py --output qwen3-0.6b.json
```

`scripts/check-vm-state.py` performs a read-only Nebius lifecycle check and
prints only project names, instance names, states and regions.

## Scope and limitations

- One GPU, one node, one model (0.6B parameters).
- Sequential requests only; no concurrency, no batching study, no TTFT metric.
- No model-quality evaluation, no accuracy dataset, no provider comparison.
- No warm-up request, no fixed seed; temperature 0.6.
- No Terraform or cloud-init was used in Session 001. Provisioning was performed
  through the Nebius console. Proposed automation is documented but not tested.
- Cost is an operator-reported observation, not a reconciled billing export.

## Next: Session 002

Larger models (8B/14B), concurrent load, vLLM's own benchmark tooling, a FastAPI
gateway in front of vLLM, harness integration, and a later comparison with
Crusoe Cloud. See the reproducibility report for the pending items.
