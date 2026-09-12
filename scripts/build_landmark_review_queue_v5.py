#!/usr/bin/env python3
"""Build the create-once final wide-context sphere challenge review queue."""
from __future__ import annotations

from collections import Counter
import json

from build_landmark_review_queue_v4 import ROOT, PROFILE, sha256, stratified_three


SPEC = ROOT / "configs" / "landmark_challenge_campaign_v5.yaml"
EXPECTED = {
    "v5-val00-sign-sphere": "sign",
    "v5-val00-door-sphere": "door",
    "v5-val00-glass-sphere": "glass_doors",
    "v5-val00-chair-sphere": "chair",
    "v5-val00-doorway-sphere-side1": "doorway",
    "v5-val00-office-sphere": "office_entrance",
    "v5-val01-laboratory-sphere": "laboratory_entrance",
}
CHALLENGE_ID = "validation-identity-spheres-v5"
CONDITION_KIND = "palette_sphere_impostor_with_wide_context"


def main() -> None:
    queue_path = ROOT / "data" / "landmark_bridge" / "human_review_queue_v5.jsonl"
    manifest_path = ROOT / "reports" / "landmark_capture" / "campaign_manifest_v5.json"
    if queue_path.exists() or manifest_path.exists():
        raise SystemExit("v5 review queue and campaign manifest are create-once")

    seen: set[str] = set()
    prior_hashes = {}
    for tag in ("v1", "v2"):
        path = ROOT / "data" / "landmark_bridge" / f"human_review_queue_{tag}.jsonl"
        prior_hashes[f"{tag}_queue_sha256"] = sha256(path)
        for line in path.read_text().splitlines():
            if line.strip():
                seen.add(json.loads(line)["observation_id"])

    by_condition: dict[str, list[dict]] = {}
    audited_captures = []
    for summary_path in sorted((ROOT / "reports" / "landmark_capture").glob("*/summary.json")):
        summary = json.loads(summary_path.read_text())
        condition_id = summary.get("challenge_condition_id")
        if condition_id not in EXPECTED or summary.get("status") != "pending_human_review":
            continue
        capture_id = summary_path.parent.name
        if summary.get("challenge_id") != CHALLENGE_ID:
            raise ValueError(f"unexpected challenge id for {capture_id}")
        if sha256(SPEC) != summary.get("challenge_spec_sha256"):
            raise ValueError(f"challenge specification mismatch for {capture_id}")
        if summary.get("challenge_condition_kind") != CONDITION_KIND:
            raise ValueError(f"challenge condition is not a wide-context sphere for {capture_id}")
        if summary.get("protected_test_data") or summary.get("partition") != "validation":
            raise ValueError(f"protected or non-validation challenge capture: {capture_id}")
        if summary.get("online_ground_truth_used") or summary.get("segmentation_labels_used"):
            raise ValueError(f"forbidden online labels declared by {capture_id}")
        if summary.get("detector_configuration_changed") is not False:
            raise ValueError(f"detector configuration changed in {capture_id}")
        if summary.get("capture_profile_sha256") != sha256(PROFILE):
            raise ValueError(f"capture profile mismatch for {capture_id}")
        if condition_id in by_condition:
            raise ValueError(f"multiple successful captures for challenge condition {condition_id}")

        review_log = ROOT / "data" / "landmark_bridge" / f"{capture_id}-review.jsonl"
        if sha256(review_log) != summary.get("review_log_sha256"):
            raise ValueError(f"review log checksum mismatch for {capture_id}")
        media_path = summary_path.parent / "review_media"
        for relative, expected_hash in summary.get("review_media_files", {}).items():
            if sha256(media_path / relative) != expected_hash:
                raise ValueError(f"review media checksum mismatch for {capture_id}/{relative}")

        target_entity = summary.get("view_entity_id")
        candidates = []
        for line in review_log.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("entity_id") != target_entity:
                continue
            if row.get("category") != EXPECTED[condition_id]:
                raise ValueError(f"unexpected target category in {capture_id}")
            if row.get("review_status") != "pending_human_review" or row.get("correct") is not None:
                raise ValueError(f"source challenge row already contains a verdict: {capture_id}")
            if row["observation_id"] in seen:
                continue
            row.update({
                "capture_id": capture_id,
                "route_id": summary["route_id"],
                "map_id": summary["map_id"],
                "review_media": str(media_path.relative_to(ROOT)),
                "review_frame": (
                    f"reports/landmark_capture/review_frames/{capture_id}/"
                    f"{row['observed_at_ns']}.png"
                ),
                "challenge_id": summary["challenge_id"],
                "challenge_condition_id": condition_id,
                "challenge_condition_kind": summary["challenge_condition_kind"],
            })
            candidates.append(row)
        selected = stratified_three(candidates)
        by_condition[condition_id] = selected
        seen.update(row["observation_id"] for row in selected)
        audited_captures.append(capture_id)

    missing = sorted(set(EXPECTED) - set(by_condition))
    if missing:
        raise ValueError("missing successful challenge conditions: " + ", ".join(missing))
    rows = sorted(
        (row for selected in by_condition.values() for row in selected),
        key=lambda row: (row["category"], float(row["probability"]), row["observation_id"]),
    )
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode()
    with queue_path.open("xb") as handle:
        handle.write(payload)

    rejected = {}
    for tag, reason in {
        "v3": "rectangular distractors made semantic object identity ambiguous",
        "v4": "pre-review visual audit found a clipped sphere and insufficient context",
    }.items():
        source = ROOT / "data" / "landmark_bridge" / f"human_review_queue_{tag}.jsonl"
        reviewed = ROOT / "data" / "landmark_bridge" / f"human_review_queue_{tag}.reviewed.jsonl"
        rejected[tag] = {
            "reason": reason,
            "source_sha256": sha256(source),
            "reviewed_sha256": sha256(reviewed),
            "included_in_calibration": False,
        }
    manifest = {
        "schema_version": "landmark-capture-campaign/v5-wide-sphere-challenge",
        "reason": "full sphere silhouette and wider scene context replace rejected v3 and v4 queues",
        "partition": "validation",
        "protected_test_data": False,
        "online_ground_truth_used": False,
        "segmentation_labels_used": False,
        "detector_configuration_changed": False,
        "selection_uses_human_labels": False,
        "sampling": "minimum, median, and maximum detector probability per prespecified sphere condition",
        "conditions": len(by_condition),
        "review_queue_rows": len(rows),
        "review_queue_strata": dict(sorted(Counter(row["category"] for row in rows).items())),
        "review_queue_sha256": sha256(queue_path),
        "capture_ids": sorted(audited_captures),
        "challenge_spec_sha256": sha256(SPEC),
        "rejected_review_queues": rejected,
        **prior_hashes,
        "review_status": "pending_human_review",
        "calibration_frozen": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
