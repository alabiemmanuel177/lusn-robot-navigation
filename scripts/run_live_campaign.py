#!/usr/bin/env python3
"""Run every preregistered non-protected live integration episode once."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/live_campaign_v1.yaml")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "reports/live_campaign_v1.summary.json"
    )
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite create-once campaign summary: {args.output}")
    config = yaml.safe_load(args.config.read_text())
    if (
        config.get("schema_version") != "research3-live-campaign/v1"
        or config.get("protected_test_routes_used") is not False
        or set(config.get("partition_scope") or []) - {"development", "validation"}
    ):
        raise SystemExit("campaign is not an authorized non-protected live campaign")

    results = []
    for index, item in enumerate(config["routes"], 1):
        route_id = str(item["route_id"])
        if route_id.startswith("test_"):
            raise SystemExit("protected route encountered")
        print(f"[{index}/{len(config['routes'])}] {route_id}", flush=True)
        attempts = []
        summary = None
        for attempt in (1, 2):
            run_id = f"{config['campaign_id']}-{route_id.replace('_', '-')}-a{attempt}"
            completed = subprocess.run([
                sys.executable,
                str(ROOT / "scripts/run_live_episode.py"),
                "--route-id", route_id,
                "--variant-id", str(item["variant_id"]),
                "--run-id", run_id,
            ])
            summary_path = ROOT / "reports/live_episodes" / run_id / "summary.json"
            attempt_record = {
                "run_id": run_id,
                "runner_exit_code": completed.returncode,
                "terminal_summary_written": summary_path.is_file(),
            }
            attempts.append(attempt_record)
            if summary_path.is_file():
                summary = json.loads(summary_path.read_text())
                summary["runner_exit_code"] = completed.returncode
                break
            print(f"  infrastructure retry {attempt}/2 did not reach a terminal outcome", flush=True)
        if summary is None:
            summary = {
                "run_id": attempts[-1]["run_id"],
                "route_id": route_id,
                "navigation_success": False,
                "valid_terminal_outcome": False,
                "runner_exit_code": attempts[-1]["runner_exit_code"],
                "reason": "both infrastructure attempts ended without a terminal summary",
            }
        summary["attempts"] = attempts
        results.append(summary)

    report = {
        "schema_version": "research3-live-campaign-summary/v1",
        "campaign_id": config["campaign_id"],
        "config": str(args.config.resolve()),
        "protected_test_routes_used": False,
        "episode_count": len(results),
        "navigation_success_count": sum(bool(item["navigation_success"]) for item in results),
        "monitor_prediction_observed_count": sum(
            bool(item.get("monitor_prediction_observed")) for item in results
        ),
        "valid_terminal_outcome_count": sum(
            bool(item.get("valid_terminal_outcome")) for item in results
        ),
        "all_successful": all(
            item["navigation_success"] for item in results
        ),
        "campaign_complete": all(
            item.get("valid_terminal_outcome") and item["runner_exit_code"] == 0
            for item in results
        ),
        "episodes": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({key: report[key] for key in (
        "campaign_id", "episode_count", "navigation_success_count",
        "monitor_prediction_observed_count", "valid_terminal_outcome_count",
        "all_successful", "campaign_complete",
    )}, sort_keys=True))
    if not report["campaign_complete"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
