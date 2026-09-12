#!/usr/bin/env python3
"""Prepare a non-protected diagnostic matrix without executing experiments."""
import argparse
import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    benchmark = ROOT / "data/manifests/instruction_benchmark_v0.1.json"
    routes_path = ROOT / "configs/live_campaign_v2.yaml"
    routes = yaml.safe_load(routes_path.read_text())["routes"]
    variants = json.loads(benchmark.read_text())["deployed_variants"]
    episodes = []
    for route in routes:
        base = route["variant_id"].split("-truthful_original-")[0]
        if not route["route_id"].startswith(("dev_", "val_")):
            raise ValueError("protected route in development/validation matrix")
        matches = [v for v in variants if v["base_instruction_id"] == base]
        if len(matches) != 8:
            raise ValueError(f"expected eight variants for {base}")
        for variant in matches:
            for system in ("B1", "B2", "B4", "B5", "B6"):
                episodes.append({"route_id": route["route_id"], "variant_id": variant["variant_id"],
                                 "system_id": system})
    assert len(episodes) == 560
    payload = {
        "schema_version": "research3-live-comparison-plan/v1",
        "status": "prepared_diagnostic_matrix_not_confirmatory_protocol",
        "protected_test_routes_used": False,
        "episode_count": len(episodes),
        "benchmark_sha256": hashlib.sha256(benchmark.read_bytes()).hexdigest(),
        "route_manifest_sha256": hashlib.sha256(routes_path.read_bytes()).hexdigest(),
        "shared_controls": {"goal_tolerance_m": 0.35, "wall_timeout_s": 180,
                            "inspection_budget": 1, "inspection_dwell_s": 2},
        "execution_gates": [
            "independent semantic evaluation annotations and scorer validated",
            "all five live policy variants smoke-tested",
            "retain all collisions, timeouts and post-dispatch infrastructure failures",
            "freeze source snapshot and execution order before campaign",
            "document common monitor guard and single-route catalogue limitations",
        ],
        "episodes": episodes,
    }
    with args.output.open("x") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"Prepared {len(episodes)} episodes: {args.output}")


if __name__ == "__main__":
    main()
