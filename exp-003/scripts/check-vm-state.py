#!/usr/bin/env python3
"""Read-only VM lifecycle check for EXP-003 (Nebius CLI).

Prints only project names, instance names, states and regions. It never prints
tenant/project IDs, credentials, IP addresses or other resource identifiers.

The script checks the project in the active profile and, when a tenant ID is
available, every project under that tenant. This avoids the false conclusion
"0 instances" when the VM lives in a different project of the same tenant.

Exit codes:
  0 = at least one query succeeded
  1 = CLI/config unavailable or every query failed
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_cli() -> str | None:
    cli = shutil.which("nebius")
    if cli:
        return cli
    candidate = Path.home() / ".nebius" / "bin" / "nebius"
    return str(candidate) if candidate.is_file() else None


def read_config() -> dict[str, str]:
    config = Path.home() / ".nebius" / "config.yaml"
    values: dict[str, str] = {}
    if not config.is_file():
        return values
    for line in config.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        for key in ("parent-id", "tenant-id"):
            if stripped.startswith(key + ":"):
                values[key] = stripped.split(":", 1)[1].strip()
    return values


def run_json(cli: str, args: list[str]) -> dict | list | None:
    env = dict(os.environ)
    env["PATH"] = str(Path(cli).parent) + os.pathsep + env.get("PATH", "")
    result = subprocess.run(
        [cli, *args, "--all", "--format", "json"],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return None


def items_of(data: dict | list | None) -> list[dict]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", []) or []
    return []


def instance_lines(cli: str, project_id: str) -> list[str]:
    data = run_json(
        cli,
        ["compute", "instance", "list", "--parent-id", project_id],
    )
    lines = []
    for item in items_of(data):
        metadata = item.get("metadata", {}) or {}
        status = item.get("status", {}) or {}
        spec = item.get("spec", {}) or {}
        lines.append(
            "  - {name}: {state} ({region})".format(
                name=metadata.get("name", "<unnamed>"),
                state=status.get("state") or item.get("state") or "<unknown>",
                region=spec.get("region") or "<unknown>",
            )
        )
    return lines


def project_id_of(item: dict) -> str | None:
    metadata = item.get("metadata", {}) or {}
    return metadata.get("id") or item.get("id")


def main() -> int:
    cli = find_cli()
    if not cli:
        print("SKIP: nebius CLI not found", file=sys.stderr)
        return 1

    config = read_config()
    default_project = config.get("parent-id")
    tenant = config.get("tenant-id")
    if not default_project and not tenant:
        print("SKIP: no parent-id/tenant-id in ~/.nebius/config.yaml", file=sys.stderr)
        return 1

    succeeded = False
    total_instances = 0

    projects: list[tuple[str, str]] = []
    if tenant:
        project_data = run_json(
            cli,
            ["iam", "project", "list", "--parent-id", tenant],
        )
        if project_data is not None:
            succeeded = True
            for item in items_of(project_data):
                metadata = item.get("metadata", {}) or {}
                pid = project_id_of(item)
                if pid:
                    projects.append((metadata.get("name", "<unnamed>"), pid))

    if default_project and all(pid != default_project for _, pid in projects):
        projects.insert(0, ("(default profile project)", default_project))

    if not projects:
        print("FAIL: no projects could be listed", file=sys.stderr)
        return 1

    for name, project_id in projects:
        lines = instance_lines(cli, project_id)
        succeeded = True
        total_instances += len(lines)
        print(f"project: {name}")
        print(f"instances: {len(lines)}")
        for line in lines:
            print(line)

    print(f"total_instances: {total_instances}")
    return 0 if succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
