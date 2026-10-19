#!/usr/bin/env bash
# EXP-003 — validate the local vLLM inference endpoint.
# Assumes the container is bound to 127.0.0.1:8000 (see scripts/docker-run.sh).
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
MODEL="${MODEL:-Qwen/Qwen3-0.6B}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
TMP_JSON="$(mktemp)"
trap 'rm -f "$TMP_JSON"' EXIT

section() { printf '\n== %s ==\n' "$1"; }

section "Health"
curl -fsS "$BASE_URL/health" && printf '\n'

section "Models"
curl -fsS "$BASE_URL/v1/models" | "$PYTHON_BIN" -c '
import json, sys
data = json.load(sys.stdin)
names = [m.get("id") for m in data.get("data", [])]
print("models:", ", ".join(names) if names else "(none)")
'

section "Chat completion"
"$PYTHON_BIN" - "$BASE_URL" "$MODEL" "$TMP_JSON" <<'PY'
import json
import sys
import urllib.request

base_url, model, output = sys.argv[1], sys.argv[2], sys.argv[3]
payload = {
    "model": model,
    "messages": [
        {"role": "user", "content": "Responde solo: OK"}
    ],
    "max_tokens": 8,
    "temperature": 0.0,
    "chat_template_kwargs": {"enable_thinking": False},
}
request = urllib.request.Request(
    base_url + "/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=60) as response:
    data = json.load(response)
with open(output, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
choice = data["choices"][0]
print("finish_reason:", choice.get("finish_reason"))
print("completion_tokens:", data["usage"]["completion_tokens"])
print("content:", repr(choice["message"].get("content")))
PY

section "Result"
echo "PASS"
