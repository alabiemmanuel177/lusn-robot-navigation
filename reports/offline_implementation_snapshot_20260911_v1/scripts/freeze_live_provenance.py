#!/usr/bin/env python3
"""Freeze hashes for the exact dirty-tree sources used by a live campaign."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
R1 = Path("/home/eao/risk-calibrated-nav")
R2 = Path("/home/eao/failure-prediction")
OUTPUT = ROOT / "reports/live_campaign_v2.provenance.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def revision(path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def dirty(path: Path) -> bool:
    return bool(subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain=v1", "--untracked-files=all"],
        check=True, capture_output=True, text=True,
    ).stdout.strip())


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit(f"refusing to overwrite {OUTPUT}")
    files = [
        ROOT / "src/language_nav/live.py",
        ROOT / "ros_ws/src/language_nav_planner/language_nav_planner/node.py",
        ROOT / "ros_ws/src/language_nav_runtime/language_nav_runtime/monitor_bridge.py",
        ROOT / "ros_ws/src/language_nav_runtime/language_nav_runtime/semantic_routes.py",
        ROOT / "ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py",
        ROOT / "scripts/run_live_episode.py",
        ROOT / "scripts/run_live_campaign.py",
        ROOT / "configs/live_campaign_v2.yaml",
        ROOT / "configs/landmark_calibration_v1.json",
        ROOT / "reports/live_campaign_v2.summary.json",
        ROOT / "reports/live_campaign_v2.analysis.json",
        R2 / "ros_ws/src/failure_monitor/failure_monitor/node.py",
        R2 / "ros_ws/src/failure_monitor/failure_monitor/monitor_core.py",
        R2 / "configs/model_freeze.yaml",
        R2 / "configs/alarm_policy.yaml",
    ]
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise SystemExit("missing provenance inputs: " + ", ".join(missing))
    document = {
        "schema_version": "research3-live-provenance/v1",
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "protected_test_routes_used": False,
        "repositories": {
            "research1": {"path": str(R1), "revision": revision(R1), "dirty": dirty(R1)},
            "research2": {"path": str(R2), "revision": revision(R2), "dirty": dirty(R2)},
            "research3": {"path": str(ROOT), "revision": revision(ROOT), "dirty": dirty(ROOT)},
        },
        "files": {str(path): sha256(path) for path in files},
        "limitation": (
            "Exact source files are hash-pinned, but Research 2 and Research 3 require "
            "clean commits before this can be called a revision-pinned release."
        ),
    }
    OUTPUT.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(sha256(OUTPUT), OUTPUT)


if __name__ == "__main__":
    main()
