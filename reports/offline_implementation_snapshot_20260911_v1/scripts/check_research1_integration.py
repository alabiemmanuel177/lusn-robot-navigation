#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import yaml

from language_nav.adapters.research1 import audit_research1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit completed Research 1 artifacts against Research 3 contracts."
    )
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path("/home/eao/risk-calibrated-nav"),
        help="Research 1 repository (default: documented sibling path)",
    )
    args = parser.parse_args()
    report = audit_research1(args.repository)
    payload = report.to_dict()
    dependencies = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "configs" / "research_dependencies.yaml").read_text()
    )
    configured = dependencies["research_1"]
    configured_repository = Path(configured["repository"]).expanduser().resolve()
    expected_revision = str(configured["verified_revision"])
    actual_revision = "not_checked_for_custom_repository"
    revision_matches = None
    blockers = list(payload["blockers"])
    extension_hashes = {}
    if args.repository.expanduser().resolve() == configured_repository:
        completed = subprocess.run(
            ["git", "-C", str(configured_repository), "rev-parse", "HEAD"],
            text=True, capture_output=True, check=False,
        )
        actual_revision = completed.stdout.strip() if completed.returncode == 0 else "unavailable"
        revision_matches = actual_revision == expected_revision
        if not revision_matches:
            blockers.append(
                f"revision_pin: expected {expected_revision}, observed {actual_revision}"
            )
        extension_paths = {
            "core.py": "extensions/research3_landmark_bridge/research3_landmark_bridge/core.py",
            "build_research3_landmark_catalogs.py": "scripts/build_research3_landmark_catalogs.py",
        }
        for name, expected in configured.get("verified_local_extension_sha256", {}).items():
            target = configured_repository / extension_paths[name]
            actual = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else "missing"
            extension_hashes[name] = actual
            if actual != expected:
                blockers.append(f"local_extension_pin: {name} differs from verified hash")
    payload.update({
        "expected_revision": expected_revision,
        "actual_revision": actual_revision,
        "revision_matches": revision_matches,
        "blockers": blockers,
        "local_extension_sha256": extension_hashes,
    })
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
