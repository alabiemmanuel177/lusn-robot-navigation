#!/usr/bin/env python3
"""Build a deterministic, media-backed human-review queue and campaign manifest."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE_ID = "gazebo-headless-rendering-dev-v3"
QUEUE_SIZE_PER_STRATUM = 5


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantile_sample(rows: list[dict], count: int) -> list[dict]:
    ordered = sorted(rows, key=lambda row: (float(row["probability"]), row["observation_id"]))
    if len(ordered) <= count:
        return ordered
    indices = {round(index * (len(ordered) - 1) / (count - 1)) for index in range(count)}
    return [ordered[index] for index in sorted(indices)]


def main() -> None:
    queue_path = ROOT / "data" / "landmark_bridge" / "human_review_queue_v1.jsonl"
    manifest_path = ROOT / "reports" / "landmark_capture" / "campaign_manifest_v1.json"
    if queue_path.exists() or manifest_path.exists():
        raise SystemExit("review queue and campaign manifest are create-once")

    summaries = []
    media_rows = []
    all_categories: Counter[str] = Counter()
    all_entities: set[str] = set()
    successful_routes: set[str] = set()
    successful_maps: set[str] = set()
    failed_captures = []
    for summary_path in sorted((ROOT / "reports" / "landmark_capture").glob("*/summary.json")):
        summary = json.loads(summary_path.read_text())
        capture_id = summary_path.parent.name
        summaries.append(summary)
        if summary["protected_test_data"]:
            raise ValueError(f"protected data declared by {capture_id}")
        if summary["status"] != "pending_human_review":
            failed_captures.append(capture_id)
            continue
        successful_routes.add(summary["route_id"])
        successful_maps.add(summary["map_id"])
        all_categories.update(summary["categories"])
        all_entities.update(summary["entities"])
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
            row["capture_id"] = capture_id
            row["route_id"] = summary["route_id"]
            row["map_id"] = summary["map_id"]
            row["review_media"] = str(media_path.relative_to(ROOT))
            row["review_frame"] = (
                f"reports/landmark_capture/review_frames/{capture_id}/"
                f"{row['observed_at_ns']}.png"
            )
            media_rows.append(row)

    strata: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in media_rows:
        strata[(row["partition"], row["category"])].append(row)
    selected = []
    selected_ids = set()
    for key in sorted(strata):
        for row in quantile_sample(strata[key], QUEUE_SIZE_PER_STRATUM):
            if row["observation_id"] not in selected_ids:
                selected.append(row)
                selected_ids.add(row["observation_id"])
    selected.sort(key=lambda row: (
        row["partition"], row["category"], float(row["probability"]), row["observation_id"]
    ))
    if len(selected) < 20:
        raise ValueError("media-backed review queue has fewer than 20 observations")
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("x", encoding="utf-8") as handle:
        for row in selected:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    manifest = {
        "schema_version": "landmark-capture-campaign/v1",
        "provider_revision": summaries[0]["provider_revision"] if summaries else None,
        "capture_profile": PROFILE_ID,
        "protected_test_data": False,
        "online_ground_truth_used": False,
        "segmentation_labels_used": False,
        "successful_route_ids": sorted(successful_routes),
        "successful_route_count": len(successful_routes),
        "successful_map_ids": sorted(successful_maps),
        "successful_map_count": len(successful_maps),
        "failed_capture_attempts": sorted(failed_captures),
        "raw_observation_rows": sum(all_categories.values()),
        "raw_categories": dict(sorted(all_categories.items())),
        "raw_unique_entities": len(all_entities),
        "media_backed_observation_rows": len(media_rows),
        "media_backed_capture_count": len({row["capture_id"] for row in media_rows}),
        "review_queue_rows": len(selected),
        "review_queue_strata": {
            f"{partition}/{category}": count
            for (partition, category), count in sorted(Counter(
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
