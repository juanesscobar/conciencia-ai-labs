# Evidence — EXP-002A (Provider readiness probe: Crusoe Cloud · GLM-5.3-Flash)

Sanitized evidence for the REAL provider probe filed as EXP-002A.

| File | Description |
| --- | --- |
| `result.json` | Raw report emitted by the probe (status, latency, tokens, finish_reason, reasoning_present). |
| `probe.py` | The probe script (sanitized). Reads the credential from `CRUSOE_API_KEY`; no secret stored. |

**Sanitization:** hostname/PII removed, no public IPs, no operator username, credential never persisted.
Only the fields relevant to the result are kept.

**Result:** `status=success`, `finish_reason=stop`, latency `2.071 s`, tokens `23/28/51`, `reasoning_present=false`.

Report: [`../../docs/EXP-002A-REPORT.md`](../../docs/EXP-002A-REPORT.md).

Combined with EXP-001 v0.2 this remains a small, bounded probe: it shows connectivity and
response shape, not sustained availability, model quality, cost or rate limits.
