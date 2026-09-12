"""Development-only camera-palette adaptation for landmark scene catalogues."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def semantic_signature(entity: dict[str, Any]) -> str:
    attributes = entity.get("attributes") or {}
    suffix = ",".join(f"{key}={attributes[key]}" for key in sorted(attributes))
    return f"{entity['category']}:{suffix}" if suffix else str(entity["category"])


def adapt_scene_palette(source: Path, destination: Path, profile: Path) -> int:
    """Derive a runtime catalogue with camera-space RGB codes only."""
    source = source.resolve()
    destination = destination.resolve()
    if source == destination:
        raise ValueError("source and destination must differ")
    scene = yaml.safe_load(source.read_text())
    config = yaml.safe_load(profile.read_text())
    if config.get("schema_version") != "landmark-capture-profile/v1":
        raise ValueError("capture profile must use landmark-capture-profile/v1")
    palettes = config.get("camera_palette") or {}
    changed = 0
    for entity in scene.get("entities") or []:
        signature = semantic_signature(entity)
        if signature not in palettes:
            raise ValueError(f"capture profile has no camera palette for {signature}")
        color = palettes[signature]
        if not isinstance(color, list) or len(color) != 3 or any(
            not isinstance(value, int) or not 0 <= value <= 255 for value in color
        ):
            raise ValueError(f"invalid camera palette for {signature}")
        entity["marker_rgb"] = color
        changed += 1
    if not changed:
        raise ValueError("scene contains no landmark entities")
    scene["capture_profile"] = {
        "schema_version": config["schema_version"],
        "provider_revision": config["provider_revision"],
        "profile_id": config["profile_id"],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(yaml.safe_dump(scene, sort_keys=False))
    return changed
