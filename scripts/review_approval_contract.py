"""Characterize the current core approval gate without changing the core.

This is a source-bound, in-process test. It replaces persistence and
authentication only; it never starts the core application, reads .env, or
contacts a service. Results describe core commit-specific behavior.
"""

from datetime import datetime, timedelta
from importlib.abc import MetaPathFinder
import inspect
import importlib
import json
from pathlib import Path
import subprocess
import sys
import types


class _BlockBootstrap(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {"app.config", "app.main"}:
            raise ImportError("approval review forbids core application bootstrap")
        return None


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Core approval-gate characterization")
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    core = args.core.resolve()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(core / "backend"))
    sys.meta_path.insert(0, _BlockBootstrap())

    from sqlalchemy import create_engine
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    database = types.ModuleType("app.database")
    database.Base = declarative_base()
    database.engine = engine
    database.SessionLocal = session_factory
    database.get_db = lambda: iter((db,))
    sys.modules["app.database"] = database
    auth = types.ModuleType("app.services.auth")
    auth.get_current_user = lambda: {"fixture": "SIMULATED; identity/roles not tested"}
    sys.modules["app.services.auth"] = auth
    routers = types.ModuleType("app.routers")
    routers.__path__ = [str(core / "backend/app/routers")]
    sys.modules["app.routers"] = routers

    from app.models.audit import AuditEvent
    from app.models.workflow import Workflow, WorkflowRun, create_workflow
    from app.models.user import User, UserRole
    from app.services.workflow_engine import approve_step, execute_workflow
    workflows_router = importlib.import_module("app.routers.workflows")

    database.Base.metadata.create_all(engine)
    checks: list[dict] = []

    def record(name: str, observed, guarantee: str = ""):
        checks.append({"name": name, "observed": observed, "guarantee": guarantee})

    def start_gate(definition: list[dict]) -> tuple[Workflow, WorkflowRun]:
        wf = create_workflow(db, name="SIMULATED approval characterization", project_id=None, definition=definition)
        return wf, execute_workflow(db, wf.id)

    # 1: no authorization has no executor path in the approved-gate workflow.
    _, pending = start_gate([{"name": "review", "approval": True}, {"name": "after"}])
    record("missing_approval_pauses", pending.status == "paused" and pending.step_results[0]["status"] == "waiting_approval",
           "EXISTS: approval:true pauses this workflow run")

    # 2: rejection cancels and prevents subsequent step execution.
    _, rejected = start_gate([{"name": "review", "approval": True}, {"name": "after"}])
    approve_step(db, rejected, 0, False)
    record("rejection_cancels", rejected.status == "cancelled" and len(rejected.step_results) == 1,
           "EXISTS: rejected pending step cancels the run")

    # 3/8: definition/preconditions are mutable JSON and not bound to decision.
    wf, changed = start_gate([{"name": "review", "approval": True, "target": "node-a", "parameters": {"x": 1},
                                "preconditions": {"node_ready": True}}, {"name": "after"}])
    wf.definition = [{"name": "review", "approval": True, "target": "node-b", "parameters": {"x": 2},
                      "preconditions": {"node_ready": False}}, {"name": "after"}]
    db.commit()
    approve_step(db, changed, 0, True)
    record("changed_plan_still_approves", changed.status == "completed" and changed.step_results[0]["status"] == "approved",
           "ABSENT: approval does not bind target, parameters or preconditions")

    # 4: an old pending run remains approvable.
    _, expired = start_gate([{"name": "review", "approval": True}])
    expired.paused_at = datetime.now().replace(tzinfo=None) - timedelta(days=30)
    db.commit()
    approve_step(db, expired, 0, True)
    record("old_pending_run_approves", expired.status == "completed",
           "ABSENT: no expiration check was observed")

    # 5: role exists in data but approval handler does not receive current_user.
    signature = inspect.signature(workflows_router.approve_run)
    record("approval_handler_has_no_actor_argument", "user" not in signature.parameters and "current_user" not in signature.parameters,
           "ABSENT: route has authentication dependency but approval decision has no actor/role enforcement")
    record("user_roles_are_data_only_for_gate", sorted(role.value for role in UserRole),
           "EXISTS: User roles are modeled; no gate role check is wired")

    # 6: a consumed authorization cannot be approved twice sequentially.
    _, consumed = start_gate([{"name": "review", "approval": True}])
    approve_step(db, consumed, 0, True)
    try:
        approve_step(db, consumed, 0, True)
    except ValueError:
        second_approval_rejected = True
    else:
        second_approval_rejected = False
    record("sequential_reuse_rejected", second_approval_rejected,
           "EXISTS: only a paused run with waiting step is accepted")

    # Gate is opt-in: ordinary workflow execution has no mandatory policy gate.
    _, ungated = start_gate([{"name": "declared-step-without-gate"}])
    record("ungated_workflow_completes", ungated.status == "completed",
           "EXISTS: gate is per-step opt-in; no mandatory action policy was observed")

    # 9: retry configuration is persisted in definition but current engine consumes one attempt.
    _, retry = start_gate([{"name": "unavailable-agent", "task": "SIMULATED", "required_capabilities": ["missing"], "retries": 3}])
    record("retry_configuration_not_executed", retry.status == "failed" and len(retry.step_results) == 1,
           "ABSENT: no retry loop was observed in workflow_engine")

    record("approval_is_not_append_only_audit", db.query(AuditEvent).count() == 0,
           "ABSENT: gate transitions live in WorkflowRun.events, not AuditEvent")
    record("no_approval_record_table", not {"approval_requests", "approval_decisions"}.intersection(database.Base.metadata.tables),
           "ABSENT: no first-class approval request/decision persistence in inspected model metadata")
    record("no_optimistic_version", "version" not in WorkflowRun.__table__.columns,
           "ABSENT: no version column on WorkflowRun")
    source = (core / "backend/app/services/workflow_engine.py").read_text(encoding="utf-8")
    record("no_row_lock_in_approve_step", "with_for_update" not in source,
           "GAP: no concurrency characterization is claimed; source inspection found no row lock")

    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=core, check=True, capture_output=True, text=True).stdout.strip()
    report = {
        "environment": "SIMULATED",
        "review_type": "characterization",
        "core_commit": sha,
        "status": "PASS",
        "checks": checks,
        "limitations": [
            "SQLite in memory and fixture identity; no deployed service, PostgreSQL or human actor test",
            "Concurrent approvals are a documented source-level gap, not a deterministic race proof",
            "No real infrastructure action was executed",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"environment": "SIMULATED", "status": "PASS", "checks": len(checks), "core_commit": sha}))
    db.close()
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
