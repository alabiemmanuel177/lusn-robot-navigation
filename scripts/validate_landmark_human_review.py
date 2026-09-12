#!/usr/bin/env python3
"""Validate review provenance without generating any human labels."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EDITABLE = {"review_status", "reviewer_id", "correct"}


def normalized(row: dict) -> dict:
    return {key: value for key, value in row.items() if key not in EDITABLE}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-pending", action="store_true")
    args = parser.parse_args()
    source_path = ROOT / "data" / "landmark_bridge" / "human_review_queue_v1.jsonl"
    reviewed_path = ROOT / "data" / "landmark_bridge" / "human_review_queue_v1.reviewed.jsonl"
    campaign = json.loads(
        (ROOT / "reports" / "landmark_capture" / "campaign_manifest_v1.json").read_text()
    )
    frame_manifest = json.loads(
        (ROOT / "reports" / "landmark_capture" / "review_frame_manifest_v1.json").read_text()
    )
    source_bytes = source_path.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != campaign["review_queue_sha256"]:
        raise ValueError("source review queue differs from campaign manifest")
    if frame_manifest["queue_sha256"] != campaign["review_queue_sha256"]:
        raise ValueError("frame manifest refers to a different review queue")
    for relative, expected in frame_manifest["files"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f"review frame checksum mismatch: {relative}")
    source = [json.loads(line) for line in source_bytes.decode().splitlines() if line.strip()]
    reviewed = [
        json.loads(line) for line in reviewed_path.read_text().splitlines() if line.strip()
    ]
    if len(source) != len(reviewed):
        raise ValueError("reviewed worksheet row count changed")
    for index, (before, after) in enumerate(zip(source, reviewed, strict=True)):
        if normalized(before) != normalized(after):
            raise ValueError(f"row[{index}] changed an immutable evidence field")
    statuses = Counter(str(row.get("review_status")) for row in reviewed)
    complete = statuses == {"human_verified": len(reviewed)}
    verified = [row for row in reviewed if row.get("review_status") == "human_verified"]
    for index, row in enumerate(verified):
        if not str(row.get("reviewer_id", "")).strip():
            raise ValueError(f"verified row[{index}] lacks reviewer_id")
        if row.get("correct") not in {0, 1, False, True}:
            raise ValueError(f"verified row[{index}] lacks a binary correct label")
    validation = [row for row in verified if row["partition"] == "validation"]
    labels = Counter(int(row["correct"]) for row in validation)
    freeze_ready = complete and len(validation) >= 20 and set(labels) == {0, 1}
    report = {
        "schema_version": "landmark-human-review-validation/v1",
        "rows": len(reviewed),
        "statuses": dict(sorted(statuses.items())),
        "human_verified": len(verified),
        "validation_verified": len(validation),
        "validation_labels": {
            "incorrect": labels.get(0, 0),
            "correct": labels.get(1, 0),
        },
        "freeze_ready": freeze_ready,
        "protected_test_data": False,
        "immutable_evidence_verified": True,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if not args.allow_pending and not freeze_ready:
        raise SystemExit("human review is not freeze-ready")


if __name__ == "__main__":
    main()
