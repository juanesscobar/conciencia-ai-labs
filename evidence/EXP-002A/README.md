# Evidence — EXP-002A (Provider readiness probe: Crusoe Cloud · GLM-5.3-Flash)

Sanitized evidence for the REAL provider probe filed as EXP-002A.

| File | Description |
| --- | --- |
| `result.json` | Raw report emitted by the probe for the **successful** run (status, latency, tokens, finish_reason, reasoning_present). |
| `probe.py` | The probe script (sanitized). Reads the credential from `CRUSOE_API_KEY`; no secret stored. |

**Sanitization:** hostname/PII removed, no public IPs, no operator username, credential never persisted.
Only the fields relevant to the result are kept.

## Three observed outcomes

The probe was run three times. Only the successful run left a persistent artifact
(`result.json` is overwritten each run; the script aborts on error).

| # | Observed result | Artifact |
| --- | --- | --- |
| 1 | Response without visible content (`content` empty → `incomplete`) | none (overwritten) |
| 2 | HTTP 503 `capacity_unavailable` (provider capacity) | none (error) |
| 3 | Successful inference — `stop`, 2.071 s, 51 tokens, no `reasoning_content` | `result.json` |

Report: [`../../docs/EXP-002A-REPORT.md`](../../docs/EXP-002A-REPORT.md).

This remains a small, bounded probe: it shows connectivity, response shape and a capacity-limited
failure mode — not sustained availability, model quality, cost or rate limits. Provider resilience
is the scope of EXP-002B, not this experiment.
