"""EXP-002A — provider readiness probe (Crusoe Cloud · zai-org/GLM-5.3-Flash).

Sanitized copy of the probe used in exp-002. The credential is read from the
environment (CRUSOE_API_KEY); no secret value is stored in this artifact.
"""
import os
import json
import time
from datetime import datetime, timezone
from openai import OpenAI

# 1. Client configuration (OpenAI-compatible endpoint)
client = OpenAI(
    api_key=os.environ["CRUSOE_API_KEY"],
    base_url="https://api.inference.crusoecloud.com/v1",
    timeout=45.0,
    max_retries=0,
)

model = "zai-org/GLM-5.3-Flash"

# 2. Run inference
prompt = "What does GPU utilization measure? Answer in one sentence."
start = time.perf_counter()

response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    max_tokens=1024,
    temperature=0.2,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "low"}},
)

latency = time.perf_counter() - start

# 3. Inspect response
choice = response.choices[0]
message = choice.message
usage = response.usage

content = message.content
finish_reason = choice.finish_reason
reasoning_present = bool(getattr(message, "reasoning_content", None))

print("\nMODEL RESPONSE:")
print(content if content else "[No visible response]")

print("\nDIAGNOSTICS:")
print("Finish reason:", finish_reason)
print("Visible content:", repr(content))
print("Reasoning present:", reasoning_present)
print("Completion tokens:", usage.completion_tokens if usage else None)

# 4. Determine real experiment status
status = (
    "success"
    if content and content.strip() and finish_reason == "stop"
    else "incomplete"
)

# 5. Build report
report = {
    "experiment": "EXP-002A",
    "provider": "crusoe",
    "model": response.model,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "latency_seconds": round(latency, 3),
    "prompt_tokens": usage.prompt_tokens if usage else None,
    "completion_tokens": usage.completion_tokens if usage else None,
    "total_tokens": usage.total_tokens if usage else None,
    "finish_reason": finish_reason,
    "reasoning_present": reasoning_present,
    "status": status,
}

print("\nEXPERIMENT METRICS:")
print(json.dumps(report, indent=2))

# 6. Save evidence
with open("exp002a-results.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print("\nEvidence saved: exp002a-results.json")
