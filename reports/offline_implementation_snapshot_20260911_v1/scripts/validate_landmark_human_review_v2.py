#!/usr/bin/env python3
"""Validate v1+v2 review provenance jointly without generating any human labels.

Runs the same integrity checks as validate_landmark_human_review.py over both
the v1 queue and the v2 validation-expansion queue, then computes combined
freeze-readiness: every row human-verified, at least 20 verified validation
rows, and both correct/incorrect outcomes present in the validation partition.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EDITABLE = {"review_status", "reviewer_id", "correct"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized(row: dict) -> dict:
    return {key: value for key, value in row.items() if key not in EDITABLE}


def check_version(tag: str, campaign_key: str) -> list[dict]:
    """Verify one queue version's checksums and immutability; return reviewed rows."""
    source_path = ROOT / "data" / "landmark_bridge" / f"human_review_queue_{tag}.jsonl"
    reviewed_path = ROOT / "data" / "landmark_bridge" / f"human_review_queue_{tag}.reviewed.jsonl"
    campaign = json.loads(
        (ROOT / "reports" / "landmark_capture" / f"campaign_manifest_{tag}.json").read_text()
    )
    frame_manifest = json.loads(
        (ROOT / "reports" / "landmark_capture" / f"review_frame_manifest_{tag}.json").read_text()
    )
    source_bytes = source_path.read_bytes()
    if sha256_bytes(source_bytes) != campaign[campaign_key]:
        raise ValueError(f"{tag}: source review queue differs from campaign manifest")
    if frame_manifest["queue_sha256"] != campaign[campaign_key]:
        raise ValueError(f"{tag}: frame manifest refers to a different review queue")
    for relative, expected in frame_manifest["files"].items():
        if sha256_bytes((ROOT / relative).read_bytes()) != expected:
            raise ValueError(f"{tag}: review frame checksum mismatch: {relative}")
    source = [json.loads(line) for line in source_bytes.decode().splitlines() if line.strip()]
    reviewed = [
        json.loads(line) for line in reviewed_path.read_text().splitlines() if line.strip()
    ]
    if len(source) != len(reviewed):
        raise ValueError(f"{tag}: reviewed worksheet row count changed")
    for index, (before, after) in enumerate(zip(source, reviewed, strict=True)):
        if normalized(before) != normalized(after):
            raise ValueError(f"{tag}: row[{index}] changed an immutable evidence field")
    return reviewed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-pending", action="store_true")
    args = parser.parse_args()
    reviewed = check_version("v1", "review_queue_sha256")
    reviewed += check_version("v2", "review_queue_sha256")
    # v2 expansion must not re-review a v1 observation
    ids = [row["observation_id"] for row in reviewed]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate observation_id across v1 and v2 queues")

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
        "schema_version": "landmark-human-review-validation/v2",
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
