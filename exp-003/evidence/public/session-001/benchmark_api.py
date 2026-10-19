import json
import statistics
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

url = "http://127.0.0.1:8000/v1/chat/completions"
results = []

for i in range(10):
    payload = {
        "model": "Qwen/Qwen3-0.6B",
        "messages": [
            {"role": "user",
             "content": f"Explica brevemente el concepto {i}: "
                        "inferencia de modelos de IA en GPUs."}
        ],
        "max_tokens": 128,
        "temperature": 0.6,
        "chat_template_kwargs": {"enable_thinking": False}
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.load(response)
    elapsed = time.perf_counter() - start

    tokens = data["usage"]["completion_tokens"]
    results.append({
        "request": i + 1,
        "latency_seconds": round(elapsed, 4),
        "output_tokens": tokens,
        "tokens_per_second_e2e": round(tokens / elapsed, 2),
        "finish_reason": data["choices"][0]["finish_reason"]
    })
    print(f"Request {i+1}: {elapsed:.3f}s | {tokens} tokens")

total_latency = sum(r["latency_seconds"] for r in results)
summary = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "model": "Qwen/Qwen3-0.6B",
    "gpu": "NVIDIA H200",
    "requests": results,
    "total_output_tokens": sum(r["output_tokens"] for r in results),
    "mean_latency_seconds": statistics.mean(
        r["latency_seconds"] for r in results
    ),
    "aggregate_output_tokens_per_second":
        sum(r["output_tokens"] for r in results) / total_latency
}

output = Path.home() / "exp003/evidence/benchmarks/qwen3-0.6b.json"
output.write_text(json.dumps(summary, indent=2))
print(json.dumps({
    "mean_latency_seconds": summary["mean_latency_seconds"],
    "aggregate_output_tokens_per_second":
        round(summary["aggregate_output_tokens_per_second"], 2),
    "output": str(output)
}, indent=2))
