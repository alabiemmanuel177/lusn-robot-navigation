#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from language_nav.evaluation import analyze_paired_graph_records


def _load(path: Path) -> tuple[list[dict], str]:
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    sidecar = path.with_name(path.name + ".sha256")
    if not sidecar.is_file() or sidecar.read_text().strip() != checksum:
        raise ValueError(f"checksum mismatch or missing sidecar for {path}")
    rows = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        envelope = json.loads(line)
        record = envelope["record"]
        canonical = json.dumps(record, separators=(",", ":"), sort_keys=True)
        expected = hashlib.sha256(canonical.encode()).hexdigest()
        if envelope.get("record_checksum") != expected:
            raise ValueError(f"record checksum mismatch at {path}:{line_number}")
        rows.append(record)
    return rows, checksum


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze immutable Research 3 graph campaigns")
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    args = parser.parse_args()
    development, development_sha = _load(args.development)
    validation, validation_sha = _load(args.validation)
    development_maps = {row["map_id"] for row in development}
    validation_maps = {row["map_id"] for row in validation}
    overlap = development_maps & validation_maps
    if overlap:
        raise ValueError("development/validation map overlap: " + ", ".join(sorted(overlap)))
    payload = {
        "schema_version": "research3-graph-analysis/v1",
        "evidence_scope": "deterministic_graph_world_engineering_only",
        "inputs": {
            "development": {"path": str(args.development), "sha256": development_sha},
            "validation": {"path": str(args.validation), "sha256": validation_sha},
        },
        "development": analyze_paired_graph_records(
            development, bootstrap_samples=args.bootstrap_samples, seed=301
        ),
        "validation": analyze_paired_graph_records(
            validation, bootstrap_samples=args.bootstrap_samples, seed=302
        ),
        "claim_limit": (
            "These results validate deterministic policy behavior only; they are not "
            "Gazebo, physical-robot, perception-calibration, or confirmatory evidence."
        ),
    }
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output.exists():
        if args.output.read_text() != serialized:
            raise ValueError(f"existing analysis does not match immutable inputs: {args.output}")
    else:
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(serialized)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
