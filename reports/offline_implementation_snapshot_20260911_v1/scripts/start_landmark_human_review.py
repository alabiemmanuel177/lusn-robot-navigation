#!/usr/bin/env python3
"""Create the editable human-review worksheet from the immutable queue."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worksheet", choices=("v1", "v2", "v3", "v4", "v5"), default="v1")
    args = parser.parse_args()
    source = ROOT / "data" / "landmark_bridge" / f"human_review_queue_{args.worksheet}.jsonl"
    destination = (
        ROOT / "data" / "landmark_bridge"
        / f"human_review_queue_{args.worksheet}.reviewed.jsonl"
    )
    manifest = json.loads(
        (
            ROOT / "reports" / "landmark_capture"
            / f"campaign_manifest_{args.worksheet}.json"
        ).read_text()
    )
    payload = source.read_bytes()
    observed = hashlib.sha256(payload).hexdigest()
    if observed != manifest["review_queue_sha256"]:
        raise ValueError("immutable review queue checksum mismatch")
    if destination.exists():
        raise SystemExit("review worksheet is create-once")
    with destination.open("xb") as handle:
        handle.write(payload)
    print(destination)


if __name__ == "__main__":
    main()
