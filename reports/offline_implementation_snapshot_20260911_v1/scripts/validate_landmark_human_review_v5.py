#!/usr/bin/env python3
"""Validate v1+v2 natural review and the final v5 wide-context sphere challenge."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from validate_landmark_human_review_v2 import check_version


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CATEGORIES = {
    "chair", "door", "doorway", "glass_doors", "laboratory_entrance",
    "office_entrance", "sign",
}
SPHERE_KIND = "palette_sphere_impostor_with_wide_context"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-pending", action="store_true")
    args = parser.parse_args()
    by_tag = {tag: check_version(tag, "review_queue_sha256") for tag in ("v1", "v2", "v5")}
    reviewed = [row for tag in ("v1", "v2", "v5") for row in by_tag[tag]]
    ids = [row["observation_id"] for row in reviewed]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate observation_id across v1, v2, and v5 queues")

    v5 = by_tag["v5"]
    if len(v5) != 21 or {row["category"] for row in v5} != REQUIRED_CATEGORIES:
        raise ValueError("v5 challenge coverage differs from the frozen seven-category queue")
    if any(row.get("partition") != "validation" for row in v5):
        raise ValueError("v5 challenge rows must all be validation samples")
    if any(row.get("challenge_condition_kind") != SPHERE_KIND for row in v5):
        raise ValueError("v5 challenge contains a non-wide-context-sphere condition")

    manifest = json.loads(
        (ROOT / "reports" / "landmark_capture" / "campaign_manifest_v5.json").read_text()
    )
    rejected = manifest.get("rejected_review_queues", {})
    if set(rejected) != {"v3", "v4"} or any(
        item.get("included_in_calibration") is not False for item in rejected.values()
    ):
        raise ValueError("v5 manifest does not explicitly exclude v3 and v4")

    statuses = Counter(str(row.get("review_status")) for row in reviewed)
    verified = [row for row in reviewed if row.get("review_status") == "human_verified"]
    for index, row in enumerate(verified):
        if not str(row.get("reviewer_id", "")).strip():
            raise ValueError(f"verified row[{index}] lacks reviewer_id")
        if row.get("correct") not in {0, 1, False, True}:
            raise ValueError(f"verified row[{index}] lacks a binary correct label")
    validation = [row for row in verified if row["partition"] == "validation"]
    labels = Counter(int(row["correct"]) for row in validation)
    complete = statuses == {"human_verified": len(reviewed)}
    freeze_ready = complete and len(validation) >= 20 and set(labels) == {0, 1}
    report = {
        "schema_version": "landmark-human-review-validation/v5",
        "rows": len(reviewed),
        "statuses": dict(sorted(statuses.items())),
        "human_verified": len(verified),
        "validation_verified": len(validation),
        "validation_labels": {"incorrect": labels.get(0, 0), "correct": labels.get(1, 0)},
        "v5_challenge_rows": len(v5),
        "v5_categories": sorted(REQUIRED_CATEGORIES),
        "v5_condition_kind": SPHERE_KIND,
        "rejected_review_queues": ["v3", "v4"],
        "freeze_ready": freeze_ready,
        "protected_test_data": False,
        "immutable_evidence_verified": True,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if not args.allow_pending and not freeze_ready:
        raise SystemExit("human review is not freeze-ready")


if __name__ == "__main__":
    main()
