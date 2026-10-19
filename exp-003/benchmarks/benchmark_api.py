#!/usr/bin/env python3
"""EXP-003 — sequential HTTP benchmark against an OpenAI-compatible vLLM endpoint.

Method (same as Session 001):
  * N sequential requests (default 10), no client concurrency.
  * Wall-clock latency per request, measured around the full HTTP round-trip.
  * Output tokens taken from ``usage.completion_tokens``.
  * Aggregate throughput = sum(output_tokens) / sum(latency_seconds).
  * Mean latency = arithmetic mean of per-request latencies.

This is an end-to-end, single-stream observation. It is NOT a maximum-throughput
benchmark, a model-quality evaluation, or a provider comparison.

Usage:
  python3 benchmark_api.py --output qwen3-0.6b.json
  BASE_URL=http://127.0.0.1:8000 MODEL=Qwen/Qwen3-0.6B python3 benchmark_api.py
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000") + "/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("MODEL", "Qwen/Qwen3-0.6B")


def run_request(url: str, model: str, index: int, max_tokens: int, temperature: float) -> dict:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Explica brevemente el concepto {index}: "
                    "inferencia de modelos de IA en GPUs."
                ),
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "chat_template_kwargs": {"enable_thinking": False},
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.load(response)
    elapsed = time.perf_counter() - start

    tokens = data["usage"]["completion_tokens"]
    return {
        "request": index + 1,
        "latency_seconds": round(elapsed, 4),
        "output_tokens": tokens,
        "tokens_per_second_e2e": round(tokens / elapsed, 2),
        "finish_reason": data["choices"][0]["finish_reason"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="Chat-completions endpoint")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--requests", type=int, default=10)
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--output", default="benchmark.json")
    args = parser.parse_args()

    if args.requests < 1:
        parser.error("--requests must be >= 1")

    results = []
    for i in range(args.requests):
        result = run_request(
            args.url, args.model, i, args.max_tokens, args.temperature
        )
        results.append(result)
        print(
            f"Request {i + 1}: {result['latency_seconds']:.3f}s | "
            f"{result['output_tokens']} tokens | {result['finish_reason']}"
        )

    total_latency = sum(r["latency_seconds"] for r in results)
    total_tokens = sum(r["output_tokens"] for r in results)
    finish_reasons: dict[str, int] = {}
    for r in results:
        finish_reasons[r["finish_reason"]] = finish_reasons.get(r["finish_reason"], 0) + 1

    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "gpu": "NVIDIA H200",
        "requests": results,
        "total_output_tokens": total_tokens,
        "mean_latency_seconds": statistics.mean(
            r["latency_seconds"] for r in results
        ),
        "aggregate_output_tokens_per_second": total_tokens / total_latency,
        "finish_reason_counts": finish_reasons,
        "method": {
            "mode": "sequential",
            "concurrency": 1,
            "warmup_requests": 0,
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
            "enable_thinking": False,
        },
    }

    output = Path(args.output)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "mean_latency_seconds": summary["mean_latency_seconds"],
                "aggregate_output_tokens_per_second": round(
                    summary["aggregate_output_tokens_per_second"], 2
                ),
                "finish_reason_counts": finish_reasons,
                "output": str(output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
