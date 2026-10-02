"""SIMULATED bounded integration with real core source, isolated DB and fixture auth.

No app.main, .env, scheduler, network, live user or production persistence is loaded.
This executable is deliberately separate from the offline library/test suite.
"""
import argparse
from dataclasses import replace
from importlib.abc import MetaPathFinder
import json
from pathlib import Path
import subprocess
import sys
import types
import uuid

sys.dont_write_bytecode = True  # never write __pycache__ into the read-only core
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_factory_lab.experiment import prepare, finish
from ai_factory_lab.domain import GateObservation, digest
from ai_factory_lab.signals import SignalsAdapter, AdapterError, signal_payload


def main():
    parser = argparse.ArgumentParser(description="SIMULATED core in-process contract verification")
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    core = args.core.resolve()
    sys.path.insert(0, str(core / "backend"))
    class BlockProductionBootstrap(MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname in {"app.config", "app.main"}:
                raise ImportError("SIMULATED test forbids core configuration/application bootstrap")
            return None
    sys.meta_path.insert(0, BlockProductionBootstrap())

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    session = sessionmaker(bind=engine)()
    # Replace ONLY infrastructure dependencies before importing core code.
    database = types.ModuleType("app.database")
    database.Base = declarative_base()
    def get_db():
        yield session
    database.get_db = get_db
    database.SessionLocal = sessionmaker(bind=engine)
    database.engine = engine
    sys.modules["app.database"] = database
    # routers/__init__.py imports unrelated routes and auth configuration.
    # Load the REAL signals module without executing that package aggregator.
    routers = types.ModuleType("app.routers")
    routers.__path__ = [str(core / "backend/app/routers")]
    sys.modules["app.routers"] = routers
    auth = types.ModuleType("app.routers.auth")
    auth.get_current_user = lambda: {"identity": "SIMULATED test principal; no auth enforcement tested"}
    sys.modules["app.routers.auth"] = auth

    from app.models import Project, Mission
    from app.models.workflow import create_workflow
    from app.services.workflow_engine import execute_workflow, approve_step
    from app.routers.signals import router, SignalCreate

    database.Base.metadata.create_all(engine)
    if "app.config" in sys.modules:
        raise RuntimeError("SIMULATED isolation violated: core config was imported")
    app = FastAPI()
    app.include_router(router)
    checks = []
    def check(condition, name):
        if not condition:
            raise AssertionError("SIMULATED core contract failed: " + name)
        checks.append(name)

    project = Project(name="Conciencia AI Factory Lab — SIMULATED local fixture")
    session.add(project)
    session.flush()
    mission = Mission(name="SIMULATED EXP-001", objective="Local isolated contract verification", project_id=project.id)
    session.add(mission)
    session.commit()

    runs = []
    with TestClient(app) as client:
        def transport(method, path, payload):
            response = client.request(method, path, json=payload)
            return response.status_code, response.json()
        adapter = SignalsAdapter(transport)
        for decision in ["absent", "rejected", "approved"]:
            provider, plan, run = prepare()
            run["integration_mode"] = "CORE_IN_PROCESS"
            payload = signal_payload(str(mission.id), run)
            SignalCreate.model_validate(payload)
            delivered = adapter.emit(payload)
            check(delivered["delivery"] == "acknowledged", decision + ": real Signals router 201")
            wf = create_workflow(session, name="SIMULATED pause admission gate", project_id=str(project.id),
                                 definition=[{"name": "review simulated action", "approval": True,
                                              "lab_plan_hash": plan.fingerprint}])
            observed = execute_workflow(session, wf.id)
            check(observed.status == "paused", decision + ": real engine paused")
            if decision != "absent":
                observed = approve_step(session, observed, 0, decision == "approved")
            rows = [r for r in observed.step_results if r["step_index"] == 0]
            gate = GateObservation(rows[0]["status"], plan.fingerprint, "CORE_IN_PROCESS", observed.id)
            # Plan binding is a local snapshot invariant, NOT a core security guarantee.
            if decision == "approved":
                try:
                    provider.execute(replace(plan, target="sim-node-002"), gate)
                except PermissionError:
                    check(True, "changed target blocked by local simulator invariant")
                else:
                    check(False, "changed target")
            result = finish(provider, plan, run, gate)
            check(result["result"] == ("PASS" if decision == "approved" else "BLOCKED"), decision + ": expected simulation result")
            if decision == "approved":
                verified = adapter.emit(signal_payload(str(mission.id), result, "finding"))
                check(verified["delivery"] == "acknowledged", "verification Signal stored by real service")
            runs.append(result)
        invalid = signal_payload(str(uuid.uuid4()), run)
        try:
            adapter.emit(invalid)
        except AdapterError:
            session.rollback()
            check(True, "unknown mission rejected by real service")
        else:
            check(False, "unknown mission")
        check(client.post("/api/v1/signals/", json={"title": "SIMULATED missing mission"}).status_code == 422,
              "actual Pydantic schema rejects missing mission_id")
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=core, check=True, capture_output=True, text=True).stdout.strip()
    files = ["backend/app/routers/signals.py", "backend/app/services/signal_service.py",
             "backend/app/services/workflow_engine.py", "backend/app/models/mission.py"]
    report = {"environment": "SIMULATED", "integration_mode": "CORE_IN_PROCESS", "status": "PASS",
              "core_commit": sha, "core_source_hashes": {f: digest((core/f).read_text(encoding="utf-8")) for f in files},
              "checks": checks, "runs": runs,
              "limitations": ["In-memory SQLite dependency; not PostgreSQL or deployed service",
                              "Fixture authentication; roles and real identity NOT tested",
                              "Test driver invokes approve_step; NOT a human approval",
                              "No core binding of plan hash, approver identity or expiry",
                              "No policy or budget enforcement claimed", "No NVIDIA compatibility"]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"environment": "SIMULATED", "status": "PASS", "checks": len(checks), "core_commit": sha}))
    session.close()
    engine.dispose()


if __name__ == "__main__":
    main()
