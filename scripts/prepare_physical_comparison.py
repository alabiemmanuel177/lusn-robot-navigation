#!/usr/bin/env python3
"""Create an offline, non-executable physical-world comparison draft.

Only development/validation execution catalogues are opened. Held-out IDs are
reservations, never inputs to catalogue validation or execution commands.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random

import yaml

from language_nav.benchmark import CorruptionCondition

ROOT = Path(__file__).resolve().parents[1]
SYSTEMS = ("B1", "B2", "B4", "B5", "B6")
GATES = (
    "stage1_physical_inspection", "calibration_coverage_new_worlds",
    "genuine_human_review_and_calibration_freeze", "condition_interventions_validated",
    "source_asset_model_pins", "resource_isolation_research2",
    "independent_measurement_and_collision_validation", "protocol_and_sample_size_freeze",
    "heldout_evaluator_authorization_and_access_control",
)


def prepare_plan(config: dict, worlds: Path) -> dict:
    """Return a draft; setting gate values cannot authorize this offline tool."""
    if config.get("status") != "draft_not_frozen_not_authorized_for_execution":
        raise ValueError("only a draft configuration is accepted")
    if tuple(config.get("systems", ())) != SYSTEMS:
        raise ValueError("expected five predeclared systems")
    if config.get("instruction_seed") != 0:
        raise ValueError("only existing s0 instruction variants are reserved")
    order_seed = config.get("execution_order_seed")
    if type(order_seed) is not int:
        raise ValueError("execution_order_seed must be an integer")
    if set(config.get("execution_gates", {})) != set(GATES):
        raise ValueError("all draft readiness gates must be explicit")
    expected = {
        "development": [f"base-r{i:03}" for i in range(1, 11)],
        "validation": [f"base-r{i:03}" for i in range(11, 15)],
        "held_out_reserved": [f"base-r{i:03}" for i in range(15, 21)],
    }
    if config.get("world_ids") != expected:
        raise ValueError("world reservations must match the predeclared split")
    conditions = tuple(condition.value for condition in CorruptionCondition)
    blocks = []
    hashes = {}
    for partition in ("development", "validation"):
        for base in expected[partition]:
            path = worlds / base / "execution_catalog.json"
            raw = path.read_bytes()
            catalog = json.loads(raw)
            routes = catalog.get("routes", [])
            if (catalog.get("partition") != partition or len(routes) != 4
                    or len({route["route_id"] for route in routes}) != 4
                    or {(r["side"], r["ordinal"]) for r in routes}
                    != {("left", 1), ("left", 2), ("right", 1), ("right", 2)}):
                raise ValueError(f"invalid four-alternative catalogue: {base}")
            hashes[base] = hashlib.sha256(raw).hexdigest()
            for condition in conditions:
                blocks.append({"base_instruction_id": base, "partition": partition,
                               "condition": condition,
                               "variant_id": f"{base}-{condition}-s0"})
    rng = random.Random(order_seed)
    rng.shuffle(blocks)
    system_order = list(SYSTEMS)
    rng.shuffle(system_order)
    episodes = []
    for block_index, block in enumerate(blocks):
        offset = block_index % len(SYSTEMS)
        rotated = system_order[offset:] + system_order[:offset]
        for position, system in enumerate(rotated):
            episodes.append({**block, "system_id": system,
                             "episode_id": f"{block['variant_id']}-{system}",
                             "paired_block_index": block_index,
                             "within_block_position": position,
                             "execution_index": len(episodes),
                             "environment_intervention": (
                                 "remove_chair_asset_and_perception_truth_before_launch"
                                 if block["condition"] == "missing_landmark" else "none"),
                             "execution_authorized": False})
    return {
        "schema_version": "research3-physical-comparison-plan/v1",
        "status": config["status"], "execution_authorized": False,
        "protected_content_read": False, "protected_test_routes_used": False,
        "episode_count": len(episodes), "paired_block_count": len(blocks),
        "instruction_seed": 0, "execution_order_seed": order_seed,
        "simulation_seed_status": "unresolved",
        "sample_size_status": "engineering_draft_confirmatory_power_unresolved",
        "catalogue_sha256": hashes, "execution_gates": config["execution_gates"],
        "failure_policy": config["failure_policy"],
        "order_design": "seeded_block_shuffle_rotating_system_order_position_balanced_within_one",
        "heldout_reservation": {
            "world_ids": expected["held_out_reserved"], "episode_count_if_frozen": 240,
            "status": "separate_gated_plan_required_no_content_loaded_no_execution",
        },
        "episodes": episodes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path,
                        default=ROOT / "configs/physical_campaign_draft_v1.yaml")
    parser.add_argument("--worlds", type=Path, default=ROOT / "data/physical_worlds_v1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.config.read_bytes()
    plan = prepare_plan(yaml.safe_load(raw), args.worlds)
    plan["draft_config_sha256"] = hashlib.sha256(raw).hexdigest()
    with args.output.open("x") as stream:
        json.dump(plan, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(f"Prepared {plan['episode_count']} non-executable draft episodes: {args.output}")


if __name__ == "__main__":
    main()
