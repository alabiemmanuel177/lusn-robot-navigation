#!/usr/bin/env python3
"""Create a validation-only visual challenge from a provider-derived world."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import tempfile

import yaml

from language_nav.adapters.landmark_challenge import (
    inject_challenge_condition,
    load_challenge_condition,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research1-root", type=Path, required=True)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--runtime-scene", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--route-id", required=True)
    parser.add_argument("--condition-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    _, scene, condition = load_challenge_condition(
        args.spec, args.scene, route_id=args.route_id, condition_id=args.condition_id
    )
    runtime_scene = yaml.safe_load(args.runtime_scene.read_text())
    if runtime_scene.get("map_id") != scene.get("map_id"):
        raise ValueError("challenge runtime scene does not match the source scene")
    source_entity = next(
        item for item in scene["entities"] if item["entity_id"] == condition["entity_id"]
    )
    runtime_entity = next(
        (
            item for item in runtime_scene.get("entities", [])
            if item.get("entity_id") == condition["entity_id"]
        ),
        None,
    )
    if runtime_entity is None or (
        runtime_entity.get("category"), runtime_entity.get("attributes") or {}
    ) != (source_entity.get("category"), source_entity.get("attributes") or {}):
        raise ValueError("challenge runtime entity differs from its source identity")
    with tempfile.NamedTemporaryFile(suffix=".sdf") as handle:
        provider_world = Path(handle.name)
        subprocess.run(
            [
                "python3",
                str(args.research1_root / "scripts" / "make_landmark_world.py"),
                "--scene", str(args.scene),
                "--output", str(provider_world),
            ],
            check=True,
        )
        inject_challenge_condition(
            provider_world,
            args.output,
            scene=scene,
            condition=condition,
            camera_marker_rgb=runtime_entity["marker_rgb"],
        )
    print(args.output)


if __name__ == "__main__":
    main()
