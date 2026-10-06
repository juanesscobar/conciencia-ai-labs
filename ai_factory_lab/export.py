"""Offline, deterministic EXP-001 comparison exports for the landing package."""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from .domain import GateObservation, digest
from .experiment import FIXTURES, finish, prepare


def run_decision(decision: str) -> dict:
    provider, plan, run = prepare()
    gate = None
    if decision != "absent":
        fixture = json.loads((FIXTURES / "gate-observation.json").read_text(encoding="utf-8"))
        gate = GateObservation(decision, fixture["plan_hash"], "FIXTURE_ONLY", fixture["run_id"])
    return finish(provider, plan, run, gate)


def timeline(result: dict) -> list[dict]:
    events = [{"stage": "observation", "timestamp": s["timestamp"],
               "temperature_c": s["temperature_c"], "environment": "SIMULATED"}
              for s in result["before"]]
    events.append({"stage": "decision", "decision": result["gate"]["decision"] if result["gate"] else "absent",
                   "result": result["result"], "environment": "SIMULATED"})
    if result["execution"]["status"] == "succeeded":
        events.append({"stage": "action", "action": result["execution"]["action"],
                       "timestamp": result["execution"]["timestamp"], "environment": "SIMULATED"})
    events.extend({"stage": "verification", "timestamp": s["timestamp"],
                   "temperature_c": s["temperature_c"], "environment": "SIMULATED"}
                  for s in result["after"])
    return events


def export_comparison(out: Path) -> dict:
    """Write data only from the seeded model; no charts or interpolated values."""
    out.mkdir(parents=True, exist_ok=True)
    results = {decision: run_decision(decision) for decision in ("approved", "rejected", "absent")}
    comparison = {
        "environment": "SIMULATED", "schema_version": "exp001-comparison/0.1.0",
        "reproduction": {"seed": 7, "clock_start": "2026-09-30T00:00:00+00:00", "interactive": False},
        "decisions": [{"decision": key, "result": value["result"],
                       "action_executed": value["execution"]["status"] == "succeeded",
                       "verification": value["verification"]["status"]}
                      for key, value in results.items()],
    }
    payloads = {"comparison.json": comparison,
                "timeline.json": {"environment": "SIMULATED", "timelines": {k: timeline(v) for k, v in results.items()}},
                "results.json": {"environment": "SIMULATED", "runs": results}}
    for name, payload in payloads.items():
        (out / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    manifest = {"environment": "SIMULATED", "files": {name: digest(payload) for name, payload in payloads.items()}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return comparison
