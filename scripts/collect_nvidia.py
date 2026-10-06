"""Read-only NVIDIA telemetry capture/import utility; no cloud SDK or credentials."""
import argparse
import json
from pathlib import Path

from ai_factory_lab.nvidia import collect_nvidia_smi, parse_nvidia_smi_csv


def main():
    parser = argparse.ArgumentParser(description="Import or explicitly capture read-only NVIDIA telemetry")
    parser.add_argument("--input", type=Path, help="saved nvidia-smi CSV; works without a GPU")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="explicitly run one local nvidia-smi command")
    args = parser.parse_args()
    if bool(args.input) == args.execute:
        parser.error("choose exactly one of --input or --execute")
    capture = collect_nvidia_smi() if args.execute else parse_nvidia_smi_csv(args.input.read_text(encoding="utf-8"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(capture, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
