#!/usr/bin/env python3
"""Build the v2 validation-expansion human-review queue.

The v1 review (60 tasks) completed with every validation-partition detection
marked correct, so the calibration freeze is blocked: fitting requires both
outcomes. This create-once script samples ADDITIONAL validation-partition
observations from the same verified, media-backed captures, excluding every
observation already reviewed in v1.

Sampling per category: the lowest-probability observations first (most likely
to contain a genuine detector miss) plus a quantile spread over the remainder.
Selection depends only on the detector's own probability, never on any label,
so conditional correctness E[correct | p] is unbiased.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_ID = "gazebo-headless-rendering-dev-v3"
LOWEST_PER_STRATUM = 5
SPREAD_PER_STRATUM = 3


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantile_sample(rows: list[dict], count: int) -> list[dict]:
    ordered = sorted(rows, key=lambda row: (float(row["probability"]), row["observation_id"]))
    if len(ordered) <= count:
        return ordered
    indices = {round(index * (len(ordered) - 1) / (count - 1)) for index in range(count)}
    return [ordered[index] for index in sorted(indices)]


def main() -> None:
    queue_path = ROOT / "data" / "landmark_bridge" / "human_review_queue_v2.jsonl"
    manifest_path = ROOT / "reports" / "landmark_capture" / "campaign_manifest_v2.json"
    if queue_path.exists() or manifest_path.exists():
        raise SystemExit("v2 review queue and campaign manifest are create-once")
    v1_queue = ROOT / "data" / "landmark_bridge" / "human_review_queue_v1.jsonl"
    v1_ids = {
        json.loads(line)["observation_id"]
        for line in v1_queue.read_text().splitlines()
        if line.strip()
    }

    media_rows = []
    for summary_path in sorted((ROOT / "reports" / "landmark_capture").glob("*/summary.json")):
        summary = json.loads(summary_path.read_text())
        capture_id = summary_path.parent.name
        if summary["protected_test_data"]:
            raise ValueError(f"protected data declared by {capture_id}")
        if summary["status"] != "pending_human_review":
            continue
        if not summary.get("review_media_available") or summary.get("capture_profile") != PROFILE_ID:
            continue
        review_log = ROOT / "data" / "landmark_bridge" / f"{capture_id}-review.jsonl"
        if sha256(review_log) != summary["review_log_sha256"]:
            raise ValueError(f"review log checksum mismatch for {capture_id}")
        media_path = summary_path.parent / "review_media"
        for relative, expected in summary["review_media_files"].items():
            if sha256(media_path / relative) != expected:
                raise ValueError(f"review media checksum mismatch for {capture_id}/{relative}")
        for line in review_log.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row["review_status"] != "pending_human_review" or row["correct"] is not None:
                raise ValueError(f"non-pending row in source capture {capture_id}")
            if row["partition"] != "validation":
                continue
            if row["observation_id"] in v1_ids:
                continue
            row["capture_id"] = capture_id
            row["route_id"] = summary["route_id"]
            row["map_id"] = summary["map_id"]
            row["review_media"] = str(media_path.relative_to(ROOT))
            row["review_frame"] = (
                f"reports/landmark_capture/review_frames/{capture_id}/"
                f"{row['observed_at_ns']}.png"
            )
            media_rows.append(row)

    strata: dict[str, list[dict]] = defaultdict(list)
    for row in media_rows:
        strata[row["category"]].append(row)
    selected = []
    selected_ids: set[str] = set()
    for category in sorted(strata):
        ordered = sorted(
            strata[category],
            key=lambda row: (float(row["probability"]), row["observation_id"]),
        )
        picks = ordered[:LOWEST_PER_STRATUM]
        remainder = ordered[LOWEST_PER_STRATUM:]
        picks += quantile_sample(remainder, SPREAD_PER_STRATUM)
        for row in picks:
            if row["observation_id"] not in selected_ids:
                selected.append(row)
                selected_ids.add(row["observation_id"])
    selected.sort(key=lambda row: (
        row["partition"], row["category"], float(row["probability"]), row["observation_id"]
    ))
    if not selected:
        raise ValueError("no additional validation observations available for v2")
    with queue_path.open("x", encoding="utf-8") as handle:
        for row in selected:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    manifest = {
        "schema_version": "landmark-capture-campaign/v2-expansion",
        "reason": "v1 validation review contained no incorrect labels; freeze requires both outcomes",
        "capture_profile": PROFILE_ID,
        "protected_test_data": False,
        "online_ground_truth_used": False,
        "segmentation_labels_used": False,
        "partition": "validation",
        "sampling": {
            "lowest_probability_per_category": LOWEST_PER_STRATUM,
            "quantile_spread_per_category": SPREAD_PER_STRATUM,
            "label_independent": True,
        },
        "v1_queue_sha256": sha256(v1_queue),
        "excluded_v1_observations": len(v1_ids),
        "candidate_rows": len(media_rows),
        "review_queue_rows": len(selected),
        "review_queue_strata": {
            f"{row_partition}/{category}": count
            for (row_partition, category), count in sorted(Counter(
                (row["partition"], row["category"]) for row in selected
            ).items())
        },
        "review_queue_sha256": sha256(queue_path),
        "review_status": "pending_human_review",
        "calibration_frozen": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
