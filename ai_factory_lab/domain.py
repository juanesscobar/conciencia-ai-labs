"""Internal ports and immutable SIMULATED domain contracts."""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Protocol


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: object) -> str:
    return sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class Sample:
    timestamp: str
    target: str
    temperature_c: float | None
    admission_paused: bool = False
    assignments: int = 0
    environment: str = "SIMULATED"
    source: str = "SimulatedGPUProvider/0.1.0"


@dataclass(frozen=True)
class ActionPlan:
    target: str
    evidence_hash: str
    revision: int
    action: str = "pause_admission"
    parameters: tuple = (("paused", True),)
    environment: str = "SIMULATED"

    @property
    def fingerprint(self) -> str:
        return digest(asdict(self))


@dataclass(frozen=True)
class GateObservation:
    """Adapter value, not an approval system. Core lacks cryptographic binding."""
    decision: str
    plan_hash: str
    source: str
    run_id: str
    step_index: int = 0


class InventoryTelemetry(Protocol):
    def capabilities(self) -> dict: ...
    def snapshot(self) -> dict: ...
    def query_metrics(self) -> tuple[Sample, ...]: ...
    def list_jobs(self) -> list[dict]: ...


class ActionExecutor(Protocol):
    def plan_action(self, evidence: tuple[Sample, ...]) -> ActionPlan: ...
    def execute(self, plan: ActionPlan, gate: GateObservation | None) -> dict: ...
    def get_operation(self, operation_id: str) -> dict | None: ...


class OutcomeVerifier(Protocol):
    def verify(self, plan: ActionPlan, samples: tuple[Sample, ...]) -> dict: ...
