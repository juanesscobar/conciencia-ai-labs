"""Bounded, read-only NVIDIA telemetry capture and offline parsing.

This module deliberately does not schedule, create, or control cloud resources.
It can parse a saved ``nvidia-smi`` CSV capture without a GPU being present.
"""
from __future__ import annotations

from datetime import datetime, timezone
import csv
import io
import subprocess


QUERY_FIELDS = (
    "timestamp,index,uuid,name,driver_version,pstate,temperature.gpu,"
    "utilization.gpu,power.draw,memory.used,memory.total"
)
FIELD_NAMES = (
    "timestamp", "gpu_index", "gpu_uuid", "gpu_name", "driver_version", "pstate",
    "temperature_c", "utilization_pct", "power_w", "memory_used_mib", "memory_total_mib",
)
NUMERIC_FIELDS = {"gpu_index": int, "temperature_c": float, "utilization_pct": float,
                  "power_w": float, "memory_used_mib": float, "memory_total_mib": float}
MISSING = {"", "[N/A]", "N/A", "Not Supported", "Unknown Error"}


def _value(name: str, raw: str):
    raw = raw.strip()
    if raw in MISSING:
        return None
    try:
        return NUMERIC_FIELDS[name](raw) if name in NUMERIC_FIELDS else raw
    except ValueError as error:
        raise ValueError(f"invalid {name}: {raw!r}") from error


def parse_nvidia_smi_csv(raw: str, captured_at: str | None = None) -> dict:
    """Convert no-header/no-units CSV to an importable, lossless absence-aware capture."""
    rows = list(csv.reader(io.StringIO(raw)))
    if not rows:
        raise ValueError("nvidia-smi capture is empty")
    devices = []
    for row in rows:
        if len(row) != len(FIELD_NAMES):
            raise ValueError(f"expected {len(FIELD_NAMES)} columns, got {len(row)}")
        devices.append(dict(zip(FIELD_NAMES, (_value(k, v) for k, v in zip(FIELD_NAMES, row)))))
    return {
        "schema_version": "nvidia-telemetry/0.1.0",
        "environment": "REAL_CAPTURE", "capture_mode": "READ_ONLY",
        "captured_at": captured_at or datetime.now(timezone.utc).isoformat(),
        "collector": {"command": "nvidia-smi", "query_fields": QUERY_FIELDS,
                      "format": "csv,noheader,nounits",
                      "units": {"temperature_c": "C", "utilization_pct": "%", "power_w": "W",
                                "memory_used_mib": "MiB", "memory_total_mib": "MiB"}},
        "devices": devices,
        "raw_csv": raw,
    }


def collect_nvidia_smi(timeout_seconds: int = 10) -> dict:
    """Run one bounded read-only command. Caller must opt in explicitly."""
    completed = subprocess.run(
        ["nvidia-smi", f"--query-gpu={QUERY_FIELDS}", "--format=csv,noheader,nounits"],
        check=True, capture_output=True, text=True, timeout=timeout_seconds,
    )
    return parse_nvidia_smi_csv(completed.stdout)
