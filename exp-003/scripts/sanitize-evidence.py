#!/usr/bin/env python3
"""Sanitize EXP-003 evidence for public release.

The private originals stay outside the public repository. This script reads a
private session directory, writes a sanitized mirror, and emits a JSON report
with input/output SHA-256 hashes, transformations and exclusions.

Design rules:
  * Preserve the technical structure needed to audit the experiment.
  * Remove infrastructure identifiers and host-local paths.
  * Never print file contents; only counts and hashes.
  * Fail closed: if a residual sensitive pattern remains in the output, exit 2.

Usage:
  python3 scripts/sanitize-evidence.py \
      --input  /path/to/private/session-001 \
      --output evidence/public/session-001 \
      --report evidence/public/sanitization-report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Text transformations (applied to every text file)
# ---------------------------------------------------------------------------

TEXT_RULES = [
    (
        "nebius-instance-hostname",
        re.compile(r"computeinstance-[a-z0-9]{6,}"),
        "computeinstance-<redacted>",
    ),
    (
        "gpu-serial",
        re.compile(r"(Serial Number\s*:\s*)\d+"),
        r"\1<redacted-gpu-serial>",
    ),
    (
        "gpu-uuid",
        re.compile(r"(GPU UUID\s*:\s*)GPU-[0-9a-fA-F-]{20,}"),
        r"\1GPU-<redacted>",
    ),
    (
        "gpu-pdi",
        re.compile(r"(GPU PDI\s*:\s*)0x[0-9a-fA-F]+"),
        r"\1<redacted>",
    ),
    (
        "process-id",
        re.compile(r"(Process ID\s*:\s*)\d+"),
        r"\1<redacted>",
    ),
    (
        "home-path",
        re.compile(r"/home/[A-Za-z0-9._-]+/"),
        "/home/<user>/",
    ),
    (
        "docker-bridge-ip",
        re.compile(r"\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b"),
        "<private-ip>",
    ),
]

# Files that are not useful for public audit or cannot be sanitized with
# sufficient confidence.
EXCLUDED_NAMES = {
    "exp003-evidence.tar.gz",
    "resource-advice.json",
    "gpu-quotas.json",
    "resource-advice.jsonmkdir",
}

EXCLUDED_SUFFIXES = {".tar", ".tar.gz", ".tgz", ".zip", ".7z", ".gz"}

# Residual patterns that must not appear in public output.
RESIDUAL_RULES = [
    ("tenant-id", re.compile(r"\btenant-[a-z0-9]{6,}")),
    ("instance-hostname", re.compile(r"computeinstance-(?!<redacted>)")),
    ("gpu-uuid", re.compile(r"GPU-[0-9a-fA-F]{8}-")),
    ("gpu-serial", re.compile(r"Serial Number\s*:\s*\d")),
    ("gpu-pdi", re.compile(r"GPU PDI\s*:\s*0x")),
    ("home-path", re.compile(r"/home/(?!<user>)")),
    (
        "private-ip",
        re.compile(r"\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b"),
    ),
    ("docker-container-id", re.compile(r'"(?:Id|SandboxID)"\s*:\s*"[0-9a-f]{64}"')),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sanitize_text(text: str) -> tuple[str, list[str]]:
    applied: list[str] = []
    for name, pattern, replacement in TEXT_RULES:
        if pattern.search(text):
            text = pattern.sub(replacement, text)
            applied.append(name)
    return text, applied


def sanitize_vllm_inspect(raw: str) -> tuple[str, list[str]]:
    """Keep deployment facts, drop container/network internals."""
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("vllm-inspect.json: expected a list")

    sanitized = []
    applied = {"container-ids", "overlay-paths", "network-identifiers", "process-ids"}
    for container in data:
        config = container.get("Config", {}) or {}
        host = container.get("HostConfig", {}) or {}
        network = container.get("NetworkSettings", {}) or {}
        state = container.get("State", {}) or {}

        mounts = []
        for mount in (
            container.get("Mounts")
            or host.get("Mounts")
            or config.get("Mounts")
            or []
        ):
            source = mount.get("Source", "")
            if source:
                source = re.sub(r"/home/[A-Za-z0-9._-]+/", "/home/<user>/", source)
            mounts.append(
                {
                    "Type": mount.get("Type"),
                    "Source": source,
                    "Destination": mount.get("Destination"),
                    "RW": mount.get("RW"),
                }
            )

        ports = network.get("Ports") or host.get("PortBindings") or {}
        sanitized.append(
            {
                "Name": container.get("Name"),
                "Created": container.get("Created"),
                "Image": container.get("Image"),
                "Args": container.get("Args"),
                "State": {
                    "Status": state.get("Status"),
                    "Running": state.get("Running"),
                    "ExitCode": state.get("ExitCode"),
                },
                "Config": {
                    "Image": config.get("Image"),
                    "Entrypoint": config.get("Entrypoint"),
                    "Cmd": config.get("Cmd"),
                },
                "HostConfig": {
                    "PortBindings": host.get("PortBindings"),
                    "Mounts": mounts,
                },
                "NetworkSettings": {"Ports": ports},
                "_sanitization": (
                    "Container ID, PID, overlay paths, sandbox keys and bridge "
                    "network identifiers removed."
                ),
            }
        )

    return json.dumps(sanitized, indent=2) + "\n", sorted(applied)


def is_excluded(path: Path) -> str | None:
    if path.name in EXCLUDED_NAMES:
        return "excluded by policy (account metadata or duplicate archive)"
    if path.suffix.lower() in EXCLUDED_SUFFIXES or path.name.endswith(".tar.gz"):
        return "archive excluded (duplicates unredacted originals)"
    if path.stat().st_size == 0:
        return "empty file"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove the output directory before writing (only inside the output path).",
    )
    args = parser.parse_args()

    if not args.input.is_dir():
        parser.error(f"input directory not found: {args.input}")

    output = args.output
    if args.clean and output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    report_path = args.report or (output.parent / "sanitization-report.json")

    files_report = []
    excluded_report = []
    residual_findings = []
    input_root = args.input

    for source in sorted(p for p in input_root.rglob("*") if p.is_file()):
        relative = source.relative_to(input_root)
        reason = is_excluded(source)
        if reason:
            excluded_report.append({"path": str(relative), "reason": reason})
            continue

        raw_bytes = source.read_bytes()
        input_hash = sha256_bytes(raw_bytes)
        transformations: list[str] = []

        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            excluded_report.append(
                {"path": str(relative), "reason": "binary file (not published)"}
            )
            continue

        if source.name == "vllm-inspect.json":
            text, applied = sanitize_vllm_inspect(text)
            transformations.extend(applied)
        else:
            text, applied = sanitize_text(text)
            transformations.extend(applied)

        # Second-pass safety net over the generated text.
        text, applied = sanitize_text(text)
        transformations.extend(a for a in applied if a not in transformations)

        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8", newline="\n")
        if source.suffix == ".sh" or source.name == "benchmark_api.py":
            destination.chmod(0o755)

        output_hash = sha256_file(destination)
        files_report.append(
            {
                "path": str(relative),
                "input_sha256": input_hash,
                "output_sha256": output_hash,
                "output_bytes": destination.stat().st_size,
                "transformations": sorted(set(transformations)),
            }
        )

        for rule_name, pattern in RESIDUAL_RULES:
            if pattern.search(text):
                residual_findings.append(
                    {"path": str(relative), "rule": rule_name}
                )

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_root": input_root.name,
        "output_root": output.name,
        "files": files_report,
        "excluded": excluded_report,
        "residual_scan": {
            "status": "PASS" if not residual_findings else "FAIL",
            "findings": residual_findings,
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"sanitized files: {len(files_report)}")
    print(f"excluded files:  {len(excluded_report)}")
    print(f"residual scan:   {report['residual_scan']['status']}")
    print(f"report:          {report_path}")

    if residual_findings:
        for finding in residual_findings:
            print(
                f"RESIDUAL {finding['rule']} in {finding['path']}",
                file=sys.stderr,
            )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
