"""Generate versioned SIMULATED fixture-only scenarios, never approval decisions."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_factory_lab.experiment import prepare, FIXTURES

scenarios = [
    ("EXP-002", "ECC degradation", "rising corrected ECC deltas", "ecc_corrected_count", "quarantine recommendation", "GPU excluded; hardware repair not claimed"),
    ("EXP-003", "workload failure", "job enters FAILED", "job_state", "checkpoint-aware retry recommendation", "output checksum and attempt count"),
    ("EXP-004", "underutilization", "utilization below 20% with reserved capacity", "utilization_ratio", "consolidation recommendation", "compare throughput and SLA against baseline"),
    ("EXP-005", "node failure", "three missed heartbeats", "heartbeat_age_seconds", "isolate admission recommendation", "no assignments and one owner per job"),
]
for identifier, name, trigger, metric, action, expected in scenarios:
    value = {"environment": "SIMULATED", "scenario_id": identifier, "version": "0.1.0",
             "status": "fixture_only", "name": name, "seed": 7, "trigger": trigger,
             "telemetry": metric, "signal": "risk", "recommendation": action,
             "expected_verification": expected, "execution_implemented": False,
             "before": {"state": "healthy"}, "after": {"state": "injected_fault"},
             "approval_requirement": "external core gate; no execution in this fixture"}
    (FIXTURES / (identifier + ".json")).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
_, plan, _ = prepare()
(FIXTURES / "gate-observation.json").write_text(json.dumps({
    "environment": "SIMULATED", "mode": "FIXTURE_ONLY", "run_id": "fixture-exp001-seed7",
    "plan_hash": plan.fingerprint, "seed": 7, "clock_start": "2026-09-30T00:00:00+00:00",
    "notice": "Test observation only; not a core approval or human authorization"
}, indent=2) + "\n", encoding="utf-8")
