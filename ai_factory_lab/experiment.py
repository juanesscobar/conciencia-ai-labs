"""Finite EXP-001 orchestration. Governance remains external to the Lab."""
from dataclasses import asdict
from pathlib import Path
import json

from .domain import digest
from .simulator import SimulatedGPUProvider, ThermalVerifier, diagnose

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def prepare(seed=7, start="2026-09-30T00:00:00+00:00", missing=False):
    fixture = json.loads((FIXTURES / "EXP-001.json").read_text(encoding="utf-8"))
    provider = SimulatedGPUProvider(seed, start)
    for i, temperature in enumerate(fixture["temperatures_c"]):
        provider.sample(None if missing and i == 3 else temperature)
    before = provider.query_metrics()
    plan = provider.plan_action(before)
    run = {"environment": "SIMULATED", "scenario_id": fixture["scenario_id"],
           "scenario_version": fixture["version"], "generator_version": "0.1.0",
           "seed": seed, "clock_start": start, "clock_step_seconds": 10,
           "provenance": "SimulatedGPUProvider/0.1.0", "fixture_hash": digest(fixture),
           "run_id": digest({"fixture": fixture, "seed": seed, "start": start, "missing": missing})[:24],
           "diagnosis": diagnose(before), "before": [asdict(s) for s in before],
           "plan": asdict(plan), "plan_hash": plan.fingerprint,
           "rationale": "Three consecutive synthetic samples >85C; pause admission in simulator only.",
           "limitations": ["No physical thermal model", "Core gate has no plan/identity/expiry binding",
                           "Cooling after pause is a fixture assumption, not an observed hardware effect"],
           "integration_mode": "FIXTURE_ONLY"}
    return provider, plan, run


def finish(provider, plan, run, gate=None, recovery=True):
    run = dict(run)
    run["gate"] = asdict(gate) if gate else None
    run["integration_mode"] = gate.source if gate else run["integration_mode"]
    run["execution"] = {"environment": "SIMULATED", "status": "not_executed"}
    run["verification"] = {"environment": "SIMULATED", "status": "NOT_RUN"}
    run["after"] = []
    if run["diagnosis"] != "THERMAL_ANOMALY":
        run["result"] = "BLOCKED_INSUFFICIENT_EVIDENCE"
    else:
        try:
            run["execution"] = provider.execute(plan, gate)
        except (PermissionError, ValueError) as error:
            run["result"] = "BLOCKED"
            run["reason"] = str(error)
        else:
            # Explicit model: current job completes, no new admission, synthetic cooling.
            fixture = json.loads((FIXTURES / "EXP-001.json").read_text(encoding="utf-8"))
            after = tuple(provider.sample(t if recovery else 90) for t in fixture["recovery_c"])
            run["after"] = [asdict(s) for s in after]
            run["verification"] = ThermalVerifier().verify(plan, after)
            run["result"] = run["verification"]["status"]
    run["final_state"] = provider.snapshot()
    run["result_hash"] = digest(run)
    return run
