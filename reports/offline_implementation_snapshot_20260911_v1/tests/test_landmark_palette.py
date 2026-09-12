from pathlib import Path

import pytest
import yaml

from language_nav.adapters.landmark_palette import adapt_scene_palette, semantic_signature


def test_signature_is_stable_and_palette_only_changes_rgb(tmp_path: Path) -> None:
    source = tmp_path / "scene.yaml"
    profile = tmp_path / "profile.yaml"
    output = tmp_path / "runtime.yaml"
    entity = {
        "entity_id": "dev-x-chair",
        "region_id": "dev-x-region",
        "category": "chair",
        "attributes": {"color": "red"},
        "pose": {"x": 1.0, "y": 2.0, "yaw": 0.0},
        "covariance": [0.04, 0.0, 0.0, 0.04],
        "marker_rgb": [220, 40, 40],
    }
    source.write_text(yaml.safe_dump({"entities": [entity]}))
    profile.write_text(yaml.safe_dump({
        "schema_version": "landmark-capture-profile/v1",
        "profile_id": "test",
        "provider_revision": "abc",
        "camera_palette": {"chair:color=red": [173, 78, 78]},
    }))

    assert semantic_signature(entity) == "chair:color=red"
    assert adapt_scene_palette(source, output, profile) == 1
    runtime = yaml.safe_load(output.read_text())
    changed = runtime["entities"][0]
    assert changed["marker_rgb"] == [173, 78, 78]
    for key in ("entity_id", "region_id", "pose", "covariance"):
        assert changed[key] == entity[key]


def test_refuses_in_place_or_missing_signature(tmp_path: Path) -> None:
    source = tmp_path / "scene.yaml"
    profile = tmp_path / "profile.yaml"
    source.write_text(yaml.safe_dump({"entities": [{"category": "door", "marker_rgb": [1, 2, 3]}]}))
    profile.write_text(yaml.safe_dump({
        "schema_version": "landmark-capture-profile/v1",
        "profile_id": "test",
        "provider_revision": "abc",
        "camera_palette": {},
    }))
    with pytest.raises(ValueError, match="must differ"):
        adapt_scene_palette(source, source, profile)
    with pytest.raises(ValueError, match="no camera palette"):
        adapt_scene_palette(source, tmp_path / "out.yaml", profile)
