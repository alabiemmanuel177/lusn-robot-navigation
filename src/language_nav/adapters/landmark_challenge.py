"""Validation-only visual challenge worlds for landmark calibration evidence."""
from __future__ import annotations

import math
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml


SCHEMA_VERSION = "landmark-challenge-campaign/v1"
SWATCH_CONDITION_KIND = "palette_swatch_impostor_with_occlusion"
SPHERE_CONDITION_KIND = "palette_sphere_impostor_with_context"
WIDE_SPHERE_CONDITION_KIND = "palette_sphere_impostor_with_wide_context"
CONDITION_KINDS = {
    SWATCH_CONDITION_KIND,
    SPHERE_CONDITION_KIND,
    WIDE_SPHERE_CONDITION_KIND,
}


def load_challenge_condition(
    spec_path: str | Path,
    scene_path: str | Path,
    *,
    route_id: str,
    condition_id: str,
) -> tuple[dict, dict, dict]:
    """Load and validate one non-protected validation challenge condition."""
    spec = yaml.safe_load(Path(spec_path).read_text())
    scene = yaml.safe_load(Path(scene_path).read_text())
    if spec.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported landmark challenge schema")
    if spec.get("partition") != "validation" or spec.get("protected_test_data") is not False:
        raise ValueError("challenge campaign must be validation-only and non-protected")
    if spec.get("online_ground_truth_used") is not False:
        raise ValueError("challenge campaign must not use online ground truth")
    if spec.get("segmentation_labels_used") is not False:
        raise ValueError("challenge campaign must not use segmentation labels")
    if scene.get("partition") != "validation":
        raise ValueError("challenge scene must use the validation partition")

    conditions = spec.get("conditions") or []
    identifiers = [str(item.get("condition_id", "")) for item in conditions]
    if any(not value for value in identifiers) or len(identifiers) != len(set(identifiers)):
        raise ValueError("challenge condition IDs must be non-empty and unique")
    condition = next(
        (item for item in conditions if item.get("condition_id") == condition_id), None
    )
    if condition is None:
        raise ValueError(f"unknown challenge condition: {condition_id}")
    if condition.get("route_id") != route_id:
        raise ValueError("challenge condition does not belong to the requested route")
    kind = condition.get("kind")
    if kind not in CONDITION_KINDS:
        raise ValueError("unsupported challenge condition kind")

    entity = next(
        (
            item for item in scene.get("entities", [])
            if item.get("entity_id") == condition.get("entity_id")
        ),
        None,
    )
    if entity is None or route_id not in entity.get("route_ids", []):
        raise ValueError("challenge entity must belong to the selected validation route")

    side = condition.get("view_side")
    values = {
        "view_distance_m": (1.0, 2.2),
        "impostor_offset_m": (0.30, 0.75),
        "occluder_offset_m": (0.08, 0.30),
        "occluder_width_m": (0.60, 1.6),
        "occluder_height_m": (1.7, 2.2),
    }
    if kind == SWATCH_CONDITION_KIND:
        values["impostor_size_m"] = (0.25, 0.60)
    else:
        values["impostor_radius_m"] = (0.18, 0.30)
    if kind == WIDE_SPHERE_CONDITION_KIND:
        values["impostor_center_height_m"] = (0.28, 0.45)
    if side not in {-1, 1}:
        raise ValueError("challenge view_side must be -1 or 1")
    for name, (minimum, maximum) in values.items():
        value = float(condition.get(name, math.nan))
        if not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError(f"challenge {name} must be in [{minimum}, {maximum}]")
    if float(condition["occluder_offset_m"]) >= float(condition["impostor_offset_m"]):
        raise ValueError("the palette impostor must be closer to the camera than the occluder")
    return spec, scene, condition


def inject_challenge_condition(
    source_world: str | Path,
    destination: str | Path,
    *,
    scene: dict,
    condition: dict,
    camera_marker_rgb: list[int] | tuple[int, int, int] | None = None,
) -> Path:
    """Add visual-only occlusion and an unregistered palette impostor."""
    source = Path(source_world)
    target = Path(destination)
    if source.resolve() == target.resolve():
        raise ValueError("challenge destination must differ from its source world")
    tree = ET.parse(source)
    world = tree.getroot().find("world")
    if world is None:
        raise ValueError("challenge source is missing its SDF world")
    if any((item.get("name") or "").startswith("r3_challenge_") for item in world.findall("model")):
        raise ValueError("challenge source already contains challenge models")

    entity = next(
        item for item in scene["entities"]
        if item["entity_id"] == condition["entity_id"]
    )
    pose = entity["pose"]
    yaw = float(pose["yaw"])
    side = int(condition["view_side"])
    normal_x, normal_y = math.cos(yaw), math.sin(yaw)

    def toward_viewer(distance: float) -> tuple[float, float]:
        return (
            float(pose["x"]) + side * distance * normal_x,
            float(pose["y"]) + side * distance * normal_y,
        )

    condition_id = str(condition["condition_id"])
    marker_rgb = camera_marker_rgb or entity["marker_rgb"]
    if len(marker_rgb) != 3 or any(not 0 <= int(value) <= 255 for value in marker_rgb):
        raise ValueError("challenge camera marker RGB must contain three bytes")
    def srgb_to_linear(value: int) -> float:
        channel = int(value) / 255.0
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    color = " ".join(f"{srgb_to_linear(int(value)):.6f}" for value in marker_rgb)
    marker_material = (
        "<material><ambient>0 0 0 1</ambient><diffuse>0 0 0 1</diffuse>"
        f"<emissive>{color} 1</emissive>"
        "<specular>0 0 0 1</specular></material>"
    )
    neutral_material = (
        "<material><ambient>0.16 0.17 0.19 1</ambient>"
        "<diffuse>0.16 0.17 0.19 1</diffuse><specular>0 0 0 1</specular></material>"
    )

    impostor_x, impostor_y = toward_viewer(float(condition["impostor_offset_m"]))
    if condition["kind"] in {SPHERE_CONDITION_KIND, WIDE_SPHERE_CONDITION_KIND}:
        radius = float(condition["impostor_radius_m"])
        geometry = f"<sphere><radius>{radius:.6f}</radius></sphere>"
        visual_name = "palette_sphere"
        height = (
            float(condition["impostor_center_height_m"])
            if condition["kind"] == WIDE_SPHERE_CONDITION_KIND
            else 0.66
        )
    else:
        impostor_size = float(condition["impostor_size_m"])
        geometry = f"<box><size>0.04 {impostor_size:.6f} {impostor_size:.6f}</size></box>"
        visual_name = "palette_swatch"
        height = 0.62
    impostor = ET.fromstring(
        f"<model name='r3_challenge_{condition_id}_impostor'><static>true</static>"
        f"<pose>{impostor_x:.6f} {impostor_y:.6f} {height:.6f} 0 0 {yaw:.6f}</pose>"
        f"<link name='link'><visual name='{visual_name}'><geometry>{geometry}</geometry>"
        f"{marker_material}</visual></link></model>"
    )
    occluder_x, occluder_y = toward_viewer(float(condition["occluder_offset_m"]))
    occluder_width = float(condition["occluder_width_m"])
    occluder_height = float(condition["occluder_height_m"])
    occluder = ET.fromstring(
        f"<model name='r3_challenge_{condition_id}_occluder'><static>true</static>"
        f"<pose>{occluder_x:.6f} {occluder_y:.6f} {occluder_height / 2:.6f} "
        f"0 0 {yaw:.6f}</pose><link name='link'><visual name='neutral_screen'>"
        "<geometry><box>"
        f"<size>0.06 {occluder_width:.6f} {occluder_height:.6f}</size>"
        f"</box></geometry>{neutral_material}</visual></link></model>"
    )
    world.extend((impostor, occluder))
    target.parent.mkdir(parents=True, exist_ok=True)
    tree.write(target, encoding="unicode", xml_declaration=True)
    return target
