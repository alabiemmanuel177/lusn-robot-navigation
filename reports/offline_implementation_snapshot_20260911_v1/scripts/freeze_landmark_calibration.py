#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from language_nav.calibration import build_calibration_artifact


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze landmark confidence calibration")
    parser.add_argument("--input", type=Path, required=True, help="normalized JSONL samples")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--partition", choices=("development", "validation"), default="validation")
    parser.add_argument("--minimum-samples", type=int, default=20)
    args = parser.parse_args()
    source = args.input.read_bytes()
    rows = [json.loads(line) for line in source.decode().splitlines() if line.strip()]
    artifact = build_calibration_artifact(
        rows,
        input_sha256=hashlib.sha256(source).hexdigest(),
        partition=args.partition,
        minimum_samples=args.minimum_samples,
    )
    serialized = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    if args.output.exists():
        if args.output.read_text() != serialized:
            raise ValueError(f"existing calibration differs from current input: {args.output}")
    else:
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(serialized)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
