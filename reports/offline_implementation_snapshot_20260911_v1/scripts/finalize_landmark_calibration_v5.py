#!/usr/bin/env python3
"""Finalize reviewed v1+v2+v5 rows and freeze calibration create-once."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

from language_nav.calibration import build_calibration_artifact
from research3_landmark_bridge.core import finalize_human_calibration_rows


ROOT = Path(__file__).resolve().parents[1]


def write_verified(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"existing create-once artifact differs: {path}")
        return
    with path.open("xb") as handle:
        handle.write(payload)


def main() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_landmark_human_review_v5.py")],
        cwd=ROOT,
        check=True,
    )
    rows = []
    reviewed_payload = b""
    for tag in ("v1", "v2", "v5"):
        path = ROOT / "data" / "landmark_bridge" / f"human_review_queue_{tag}.reviewed.jsonl"
        payload = path.read_bytes()
        reviewed_payload += payload
        rows.extend(json.loads(line) for line in payload.decode().splitlines() if line.strip())
    write_verified(
        ROOT / "data" / "landmark_bridge" / "human_review_queue_combined.reviewed.jsonl",
        reviewed_payload,
    )
    samples = finalize_human_calibration_rows(rows)
    sample_payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in samples).encode()
    sample_path = ROOT / "data" / "landmark_bridge" / "validation_calibration_samples_v1.jsonl"
    write_verified(sample_path, sample_payload)
    artifact = build_calibration_artifact(
        samples,
        input_sha256=hashlib.sha256(sample_payload).hexdigest(),
        partition="validation",
        minimum_samples=20,
    )
    artifact["sampling_scope"] = "natural_validation_plus_prespecified_wide_context_sphere_challenge"
    artifact["deployment_error_prevalence_estimated"] = False
    artifact["excluded_review_queues"] = ["v3", "v4"]
    artifact_path = ROOT / "configs" / "landmark_calibration_v1.json"
    write_verified(artifact_path, (json.dumps(artifact, indent=2, sort_keys=True) + "\n").encode())
    print(artifact_path)


if __name__ == "__main__":
    main()
