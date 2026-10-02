"""Finite seeded model. Temperatures are invented, not a physical GPU model."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from copy import deepcopy
import math
import random

from .domain import ActionPlan, GateObservation, Sample, digest


def diagnose(samples: tuple[Sample, ...]) -> str:
    if len(samples) < 3:
        return "UNKNOWN"
    window = samples[-3:]
    if any(s.temperature_c is None or not math.isfinite(s.temperature_c)
           or s.environment != "SIMULATED" for s in window):
        return "UNKNOWN"
    if len({s.target for s in window}) != 1:
        return "UNKNOWN"
    try:
        times = [datetime.fromisoformat(s.timestamp) for s in window]
        if any(t.tzinfo is None for t in times):
            return "UNKNOWN"
    except (TypeError, ValueError):
        return "UNKNOWN"
    if any((b - a).total_seconds() != 10 for a, b in zip(times, times[1:])):
        return "UNKNOWN"
    return "THERMAL_ANOMALY" if all(s.temperature_c > 85 for s in window) else "NORMAL"


class SimulatedGPUProvider:
    def __init__(self, seed: int = 7, start: str = "2026-09-30T00:00:00+00:00"):
        self.seed = seed
        self.clock = datetime.fromisoformat(start)
        if self.clock.tzinfo is None:
            raise ValueError("SIMULATED clock requires timezone")
        self.clock = self.clock.astimezone(timezone.utc)
        self.rng = random.Random(seed)
        self.target = "sim-node-001"
        self.revision = 0
        self.paused = False
        self.samples: list[Sample] = []
        self.operations: dict[str, dict] = {}

    def capabilities(self) -> dict:
        return {"environment": "SIMULATED", "actions": ["pause_admission"],
                "unsupported": ["quarantine_gpu", "restart_workload", "real_infrastructure"]}

    def snapshot(self) -> dict:
        return {"environment": "SIMULATED", "node": self.target, "gpu": "sim-gpu-001",
                "revision": self.revision, "admission_paused": self.paused,
                "ecc_corrected": 0, "utilization_ratio": 0.9 if not self.paused else 0.1,
                "power_w_model": 250 if not self.paused else 80,
                "timestamp": self.clock.isoformat()}

    def list_jobs(self) -> list[dict]:
        return [{"id": "sim-job-001", "environment": "SIMULATED", "node": self.target,
                 "state": "completed" if self.paused else "running"}]

    def sample(self, temperature: float | None) -> Sample:
        value = None if temperature is None else round(temperature + self.rng.uniform(-0.1, 0.1), 3)
        sample = Sample(self.clock.isoformat(), self.target, value, self.paused)
        self.samples.append(sample)
        self.clock += timedelta(seconds=10)
        return sample

    def query_metrics(self) -> tuple[Sample, ...]:
        return tuple(self.samples)

    def plan_action(self, evidence: tuple[Sample, ...]) -> ActionPlan:
        return ActionPlan(self.target, digest([asdict(s) for s in evidence]), self.revision)

    def execute(self, plan: ActionPlan, gate: GateObservation | None) -> dict:
        # A local invariant protects ONLY this in-memory simulator, not the core.
        if gate is None or gate.decision != "approved" or gate.plan_hash != plan.fingerprint:
            raise PermissionError("SIMULATED approval absent, rejected or plan changed")
        if gate.source not in {"FIXTURE_ONLY", "CORE_IN_PROCESS"} or not gate.run_id or gate.step_index != 0:
            raise PermissionError("SIMULATED unsupported gate provenance")
        if plan.environment != "SIMULATED" or plan.target != self.target:
            raise PermissionError("SIMULATED target/environment mismatch")
        if plan.action != "pause_admission" or plan.parameters != (("paused", True),):
            raise ValueError("SIMULATED unsupported action/parameters")
        operation_id = plan.fingerprint
        if operation_id in self.operations:
            return deepcopy(self.operations[operation_id])
        if plan.revision != self.revision:
            raise PermissionError("SIMULATED stale revision")
        current = self.query_metrics()
        if diagnose(current) != "THERMAL_ANOMALY" or digest([asdict(s) for s in current]) != plan.evidence_hash:
            raise PermissionError("SIMULATED insufficient or changed evidence")
        if (self.clock - datetime.fromisoformat(current[-1].timestamp)).total_seconds() != 10:
            raise PermissionError("SIMULATED stale observation window")
        self.paused = True
        self.revision += 1
        result = {"environment": "SIMULATED", "operation_id": operation_id,
                  "status": "succeeded", "target": plan.target, "parameters": dict(plan.parameters),
                  "action": plan.action, "timestamp": self.clock.isoformat()}
        self.operations[operation_id] = result
        return deepcopy(result)

    def get_operation(self, operation_id: str) -> dict | None:
        return deepcopy(self.operations.get(operation_id))


class ThermalVerifier:
    """Observes samples; never accepts executor success as proof of recovery."""
    def verify(self, plan: ActionPlan, samples: tuple[Sample, ...]) -> dict:
        status = "UNKNOWN"
        if len(samples) == 5 and all(s.temperature_c is not None and math.isfinite(s.temperature_c)
                                     for s in samples):
            try:
                times = [datetime.fromisoformat(s.timestamp) for s in samples]
                if any(t.tzinfo is None for t in times):
                    raise ValueError("missing timezone")
            except (TypeError, ValueError):
                return {"environment": "SIMULATED", "status": "UNKNOWN", "target": plan.target,
                        "samples_checked": len(samples), "reason": "invalid sample timestamps"}
            healthy = all(s.environment == "SIMULATED" and s.target == plan.target
                          and s.temperature_c < 75 and s.admission_paused and s.assignments == 0
                          for s in samples)
            healthy = healthy and all((b-a).total_seconds() == 10 for a,b in zip(times,times[1:]))
            status = "PASS" if healthy else "FAIL"
        return {"environment": "SIMULATED", "status": status, "samples_checked": len(samples),
                "target": plan.target, "method": "five post-action samples <75C; admission paused; no assignments"}
