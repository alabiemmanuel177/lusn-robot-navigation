#!/usr/bin/env python3
"""Create a checksum-verified analysis after authorized held-out execution."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from language_nav.evaluation import analyze_paired_graph_records


def load(path: Path) -> tuple[list[dict], str]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    checksum_path = path.with_name(path.name + ".sha256")
    if not checksum_path.is_file() or checksum_path.read_text().strip() != digest:
        raise ValueError("held-out campaign checksum mismatch")
    rows = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        envelope = json.loads(line)
        record = envelope["record"]
        canonical = json.dumps(record, separators=(",", ":"), sort_keys=True)
        if envelope.get("record_checksum") != hashlib.sha256(canonical.encode()).hexdigest():
            raise ValueError(f"held-out record checksum mismatch at line {line_number}")
        if not str(record.get("map_id", "")).startswith("test_"):
            raise ValueError(f"non-held-out record at line {line_number}")
        rows.append(record)
    return rows, digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-episodes", type=int, default=240)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")
    rows, digest = load(args.input)
    if len(rows) != args.expected_episodes:
        raise ValueError(f"expected {args.expected_episodes} held-out episodes, got {len(rows)}")
    payload = {
        "schema_version": "research3-graph-heldout-analysis/v1",
        "protocol_version": "1.1",
        "evidence_scope": "protected_deterministic_graph_world",
        "input": {"path": str(args.input), "sha256": digest, "episodes": len(rows)},
        "analysis": analyze_paired_graph_records(rows, bootstrap_samples=5000, seed=303),
        "claim_limit": (
            "Held-out graph-world results test the language policy under deterministic "
            "authored observations; they are not Gazebo or physical-robot performance."
        ),
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(args.output)


if __name__ == "__main__":
    main()
