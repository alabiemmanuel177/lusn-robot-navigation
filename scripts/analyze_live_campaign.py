#!/usr/bin/env python3
"""Validate and summarize a completed non-protected combined live campaign."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(args.output.suffix + ".sha256").exists():
        raise SystemExit("refusing to overwrite create-once analysis")
    config = yaml.safe_load(args.config.read_text())
    campaign = json.loads(args.campaign.read_text())
    expected = [item["route_id"] for item in config["routes"]]
    observed = [item["route_id"] for item in campaign["episodes"]]
    if expected != observed or len(observed) != len(set(observed)):
        raise SystemExit("campaign route order/identity differs from preregistration")
    if config.get("protected_test_routes_used") is not False:
        raise SystemExit("protected campaign is not accepted by this analyzer")

    r2_decisions = r2_alarms = 0
    frozen_hashes = set()
    action_counts: dict[str, int] = {}
    partitions: dict[str, dict[str, int]] = {}
    verified = []
    for episode in campaign["episodes"]:
        run_id = episode["run_id"]
        if episode.get("protected_test_routes_used") is not False:
            raise SystemExit(f"{run_id}: protected-data assertion failed")
        if not episode.get("valid_terminal_outcome") or episode.get("collision"):
            raise SystemExit(f"{run_id}: invalid terminal outcome or collision")
        base = ROOT / "reports/live_episodes" / run_id
        r2_path = base / "research2" / f"{run_id}.json"
        r3_path = base / "research3" / f"{run_id}.json"
        if not r2_path.is_file() or not r3_path.is_file():
            raise SystemExit(f"{run_id}: missing provider or consumer sidecar")
        r2 = json.loads(r2_path.read_text())
        r3 = json.loads(r3_path.read_text())
        assets = r2["assets"]
        if (
            not assets.get("frozen")
            or assets.get("engineering_smoke")
            or r2.get("engineering_smoke")
            or r2.get("decision_count", 0) < 1
        ):
            raise SystemExit(f"{run_id}: Research 2 evidence is unfrozen, smoke, or empty")
        if r3.get("schema_version") != "research3-live-episode/v1":
            raise SystemExit(f"{run_id}: invalid Research 3 sidecar schema")
        r2_decisions += int(r2["decision_count"])
        r2_alarms += int(r2["alarm_count"])
        frozen_hashes.add(assets["checkpoint_sha256"])
        action_counts[r3["action"]] = action_counts.get(r3["action"], 0) + 1
        partition = episode["partition"]
        bucket = partitions.setdefault(partition, {"episodes": 0, "navigation_success": 0})
        bucket["episodes"] += 1
        bucket["navigation_success"] += int(bool(episode["navigation_success"]))
        verified.append({
            "run_id": run_id,
            "route_id": episode["route_id"],
            "partition": partition,
            "navigation_success": bool(episode["navigation_success"]),
            "reason": episode["reason"],
            "research2_decisions": r2["decision_count"],
            "research2_alarms": r2["alarm_count"],
            "research2_sha256": sha256(r2_path),
            "research3_sha256": sha256(r3_path),
        })

    report = {
        "schema_version": "research3-live-analysis/v1",
        "campaign_id": campaign["campaign_id"],
        "campaign_complete": bool(campaign["campaign_complete"]),
        "protected_test_routes_used": False,
        "episode_count": len(verified),
        "valid_terminal_outcomes": len(verified),
        "navigation_successes": sum(item["navigation_success"] for item in verified),
        "monitor_driven_abstentions": sum(
            item["reason"].startswith("monitor-driven abstention") for item in verified
        ),
        "collisions": 0,
        "research2_decisions": r2_decisions,
        "research2_alarms": r2_alarms,
        "frozen_checkpoint_sha256": sorted(frozen_hashes),
        "initial_action_counts": action_counts,
        "partitions": partitions,
        "config_sha256": sha256(args.config),
        "campaign_sha256": sha256(args.campaign),
        "calibration_sha256": sha256(ROOT / "configs/landmark_calibration_v1.json"),
        "episodes": verified,
        "claim_scope": config["claim_scope"],
    }
    if len(frozen_hashes) != 1 or len(verified) != 14:
        raise SystemExit("campaign does not use one frozen model across all 14 routes")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    digest_path = args.output.with_suffix(args.output.suffix + ".sha256")
    digest_path.write_text(sha256(args.output) + "  " + args.output.name + "\n")
    print(json.dumps({key: report[key] for key in (
        "episode_count", "navigation_successes", "monitor_driven_abstentions",
        "collisions", "research2_decisions", "research2_alarms", "partitions",
    )}, sort_keys=True))


if __name__ == "__main__":
    main()
