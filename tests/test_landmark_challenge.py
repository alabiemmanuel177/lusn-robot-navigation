from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import yaml

from language_nav.adapters.landmark_challenge import (
    inject_challenge_condition,
    load_challenge_condition,
)


def _documents(tmp_path: Path, *, protected: bool = False) -> tuple[Path, Path]:
    scene = {
        "schema_version": "landmark-scene/v1",
        "map_id": "val_00",
        "partition": "validation",
        "entities": [{
            "entity_id": "entity-1", "category": "door", "attributes": {},
            "pose": {"x": 2.0, "y": 3.0, "yaw": 0.0},
            "marker_rgb": [120, 80, 40], "route_ids": ["val_00_r0"],
        }],
    }
    condition = {
        "condition_id": "door-impostor",
        "kind": "palette_swatch_impostor_with_occlusion",
        "route_id": "val_00_r0", "entity_id": "entity-1", "view_side": -1,
        "view_distance_m": 1.4, "impostor_offset_m": 0.5,
        "impostor_size_m": 0.4, "occluder_offset_m": 0.2,
        "occluder_width_m": 1.2, "occluder_height_m": 2.0,
    }
    spec = {
        "schema_version": "landmark-challenge-campaign/v1",
        "challenge_id": "challenge", "partition": "validation",
        "protected_test_data": protected, "online_ground_truth_used": False,
        "segmentation_labels_used": False, "conditions": [condition],
    }
    scene_path, spec_path = tmp_path / "scene.yaml", tmp_path / "spec.yaml"
    scene_path.write_text(yaml.safe_dump(scene))
    spec_path.write_text(yaml.safe_dump(spec))
    return spec_path, scene_path


def test_challenge_world_is_visual_only_and_uses_source_palette(tmp_path: Path) -> None:
    spec_path, scene_path = _documents(tmp_path)
    _, scene, condition = load_challenge_condition(
        spec_path, scene_path, route_id="val_00_r0", condition_id="door-impostor"
    )
    source, output = tmp_path / "source.sdf", tmp_path / "challenge.sdf"
    source.write_text("<sdf version='1.6'><world name='default'/></sdf>")
    inject_challenge_condition(
        source, output, scene=scene, condition=condition, camera_marker_rgb=[98, 74, 52]
    )
    root = ET.parse(output).getroot()
    models = root.findall("world/model")
    assert len(models) == 2
    assert all(model.find(".//collision") is None for model in models)
    assert "0.122139 0.068478 0.034340 1" in output.read_text()


def test_challenge_rejects_protected_configuration(tmp_path: Path) -> None:
    spec_path, scene_path = _documents(tmp_path, protected=True)
    with pytest.raises(ValueError, match="non-protected"):
        load_challenge_condition(
            spec_path, scene_path, route_id="val_00_r0", condition_id="door-impostor"
        )


def test_sphere_challenge_is_visually_distinct_and_collision_free(tmp_path: Path) -> None:
    spec_path, scene_path = _documents(tmp_path)
    spec = yaml.safe_load(spec_path.read_text())
    condition = spec["conditions"][0]
    condition["kind"] = "palette_sphere_impostor_with_context"
    condition.pop("impostor_size_m")
    condition["impostor_radius_m"] = 0.24
    condition["view_distance_m"] = 2.0
    condition["occluder_width_m"] = 0.72
    spec_path.write_text(yaml.safe_dump(spec))
    _, scene, condition = load_challenge_condition(
        spec_path, scene_path, route_id="val_00_r0", condition_id="door-impostor"
    )
    source, output = tmp_path / "source.sdf", tmp_path / "sphere.sdf"
    source.write_text("<sdf version='1.6'><world name='default'/></sdf>")
    inject_challenge_condition(
        source, output, scene=scene, condition=condition, camera_marker_rgb=[98, 74, 52]
    )
    root = ET.parse(output).getroot()
    assert root.find(".//visual[@name='palette_sphere']/geometry/sphere/radius").text == "0.240000"
    assert root.find(".//collision") is None


def test_wide_context_sphere_has_explicit_low_center(tmp_path: Path) -> None:
    spec_path, scene_path = _documents(tmp_path)
    spec = yaml.safe_load(spec_path.read_text())
    condition = spec["conditions"][0]
    condition["kind"] = "palette_sphere_impostor_with_wide_context"
    condition.pop("impostor_size_m")
    condition["impostor_radius_m"] = 0.24
    condition["impostor_center_height_m"] = 0.34
    condition["occluder_width_m"] = 0.60
    spec_path.write_text(yaml.safe_dump(spec))
    _, scene, condition = load_challenge_condition(
        spec_path, scene_path, route_id="val_00_r0", condition_id="door-impostor"
    )
    source, output = tmp_path / "source.sdf", tmp_path / "wide-sphere.sdf"
    source.write_text("<sdf version='1.6'><world name='default'/></sdf>")
    inject_challenge_condition(source, output, scene=scene, condition=condition)
    model = ET.parse(output).getroot().find(".//model[@name='r3_challenge_door-impostor_impostor']")
    assert model is not None
    assert model.find("pose").text.split()[2] == "0.340000"
    assert model.find(".//collision") is None
