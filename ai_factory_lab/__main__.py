import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from .domain import GateObservation, digest
from .experiment import prepare, finish, FIXTURES
from .export import export_comparison


def main():
    parser = argparse.ArgumentParser(description="SIMULATED EXP-001 offline demo; no real approvals")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--start", default="2026-09-30T00:00:00+00:00")
    parser.add_argument("--fixture-decision", choices=["absent", "rejected", "approved"], default="absent")
    parser.add_argument("--missing-telemetry", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--export-comparison", type=Path,
                        help="write approved/rejected/absent SIMULATED data package and exit")
    args = parser.parse_args()
    if args.export_comparison:
        print(json.dumps(export_comparison(args.export_comparison), indent=2))
        return 0
    provider, plan, run = prepare(args.seed, args.start, args.missing_telemetry)
    gate = None
    if args.fixture_decision != "absent":
        fixture = json.loads((FIXTURES / "gate-observation.json").read_text(encoding="utf-8"))
        gate = GateObservation(args.fixture_decision, fixture["plan_hash"], "FIXTURE_ONLY", fixture["run_id"])
    result = finish(provider, plan, run, gate)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        root = Path(__file__).resolve().parents[1]
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
        state = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True)
        hashes = {str(p.relative_to(root)): digest(p.read_text(encoding="utf-8"))
                  for folder in ["ai_factory_lab"] for p in sorted((root / folder).rglob("*"))
                  if p.suffix in {".py", ".json"}}
        manifest = {"environment": "SIMULATED", "schema_version": "0.1.0",
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "integration_mode": result["integration_mode"], "run_id": result["run_id"],
                    "git_commit": sha.stdout.strip() if sha.returncode == 0 else None,
                    "working_tree_dirty": bool(state.stdout.strip()), "source_hashes": hashes,
                    "result_hash": digest(result), "seed": args.seed, "clock_start": args.start,
                    "scenario_id": result["scenario_id"], "scenario_version": result["scenario_version"]}
        for name, content in [("result.json", result), ("manifest.json", manifest)]:
            (args.out / name).write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
