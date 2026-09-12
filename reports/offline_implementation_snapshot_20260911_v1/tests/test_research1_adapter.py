from pathlib import Path

import pytest
import yaml

from language_nav.adapters.research1 import Research1RouteCatalog, audit_research1


def _make_repository(root: Path) -> Path:
    repository = root / "research1"
    route_dir = repository / "configs" / "routes"
    map_dir = repository / "data" / "development" / "dev_00"
    semantic_dir = repository / "src" / "semantic_perception" / "semantic_perception"
    controller_dir = repository / "src" / "experiment_controller" / "experiment_controller"
    status_dir = repository / "docs"
    for directory in (route_dir, map_dir, semantic_dir, controller_dir, status_dir):
        directory.mkdir(parents=True, exist_ok=True)
    (map_dir / "map.yaml").write_text("image: map.pgm\n")
    (map_dir / "map.pgm").write_bytes(b"P5\n1 1\n255\n\xff")

    import hashlib

    digest = hashlib.sha256()
    for name in ("map.yaml", "map.pgm"):
        digest.update(name.encode() + b"\0")
        digest.update((map_dir / name).read_bytes())
    manifest = {
        "map_id": "dev_00",
        "map_hash": digest.hexdigest(),
        "frozen": True,
        "goal_tolerance_m": 0.25,
        "goal_tolerance_rad": 0.5,
        "episode_timeout_s": 180,
        "routes": [
            {
                "route_id": "dev_00_r0",
                "start": {"x": 0, "y": 0, "yaw": 1},
                "goal": {"x": 2, "y": 3},
                "shortest_path_m": 4.0,
                "length_class": "short",
                "s0_clean_verified": True,
            }
        ],
    }
    (route_dir / "dev_00.yaml").write_text(yaml.safe_dump(manifest))
    return repository


def test_catalog_verifies_and_loads_frozen_development_route(tmp_path: Path) -> None:
    repository = _make_repository(tmp_path)
    route = Research1RouteCatalog(repository).load_partition("development")[0]
    assert route.route_id == "dev_00_r0"
    assert (route.goal.x, route.goal.y) == (2.0, 3.0)


def test_catalog_denies_protected_routes_without_explicit_opt_in(tmp_path: Path) -> None:
    repository = _make_repository(tmp_path)
    with pytest.raises(PermissionError, match="explicit opt-in"):
        Research1RouteCatalog(repository).load_partition("test")


def test_unrelated_followup_is_not_consumed_but_selected_hash_is_checked(tmp_path):
    repository = _make_repository(tmp_path)
    (repository / "configs/routes/dev_60000.yaml").write_text("invalid follow-up")
    catalog = Research1RouteCatalog(repository)
    assert len(catalog.load_partition("development")) == 1
    (repository / "data/development/dev_00/map.pgm").write_bytes(b"changed")
    with pytest.raises(ValueError, match="map hash mismatch"):
        catalog.load_partition("development")
    with pytest.raises(FileNotFoundError, match="manifest missing"):
        catalog.load_partition("development", map_ids=("dev_missing",))


def test_audit_does_not_misrepresent_dense_hazard_classes_as_landmarks(tmp_path: Path) -> None:
    repository = _make_repository(tmp_path)
    validation_map = repository / "data" / "validation" / "val_00"
    validation_map.mkdir(parents=True)
    for name in ("map.yaml", "map.pgm"):
        (validation_map / name).write_bytes(
            (repository / "data" / "development" / "dev_00" / name).read_bytes()
        )
    dev_manifest = yaml.safe_load(
        (repository / "configs" / "routes" / "dev_00.yaml").read_text()
    )
    dev_manifest["map_id"] = "val_00"
    dev_manifest["routes"][0]["route_id"] = "val_00_r0"
    (repository / "configs" / "routes" / "val_00.yaml").write_text(
        yaml.safe_dump(dev_manifest)
    )
    (repository / "configs" / "ontology.yaml").write_text(
        yaml.safe_dump({"classes": [{"id": 0, "name": "traversable_floor"}]})
    )
    (repository / "docs" / "STATUS.md").write_text("G0-G7 have evidence")
    controller = repository / "src" / "experiment_controller" / "experiment_controller" / "run_episode.py"
    controller.write_text("NavigateToPose")
    report = audit_research1(repository)
    assert report.navigation_platform_ready
    assert report.route_catalog_ready
    assert not report.semantic_observation_ready
    assert any(item.startswith("semantic_observation:") for item in report.blockers)


def test_audit_accepts_separate_non_protected_landmark_bridge(tmp_path: Path) -> None:
    repository = _make_repository(tmp_path)
    validation_map = repository / "data" / "validation" / "val_00"
    validation_map.mkdir(parents=True)
    for name in ("map.yaml", "map.pgm"):
        (validation_map / name).write_bytes(
            (repository / "data" / "development" / "dev_00" / name).read_bytes()
        )
    manifest = yaml.safe_load((repository / "configs" / "routes" / "dev_00.yaml").read_text())
    manifest["map_id"] = "val_00"
    manifest["routes"][0]["route_id"] = "val_00_r0"
    (repository / "configs" / "routes" / "val_00.yaml").write_text(yaml.safe_dump(manifest))
    (repository / "configs" / "ontology.yaml").write_text(yaml.safe_dump({
        "classes": [{"id": 0, "name": "traversable_floor"}],
    }))
    (repository / "docs" / "STATUS.md").write_text("G0-G7 have evidence")
    controller = repository / "src" / "experiment_controller" / "experiment_controller" / "run_episode.py"
    controller.write_text("NavigateToPose")

    scenes = repository / "configs" / "landmark_bridge" / "scenes"
    semantic_routes = repository / "configs" / "landmark_bridge" / "semantic_routes"
    bridge_source = (
        repository / "extensions" / "research3_landmark_bridge" /
        "research3_landmark_bridge"
    )
    scenes.mkdir(parents=True)
    semantic_routes.mkdir(parents=True)
    bridge_source.mkdir(parents=True)
    categories = [
        "chair", "door", "doorway", "glass_doors", "laboratory_entrance",
        "office_entrance", "sign",
    ]
    (scenes / "dev_00.yaml").write_text(yaml.safe_dump({
        "schema_version": "landmark-scene/v1",
        "partition": "development",
        "entities": [
            {"category": category, "route_ids": ["dev_00_r0"]}
            for category in categories
        ],
    }))
    (semantic_routes / "dev_00.yaml").write_text(yaml.safe_dump({
        "schema_version": "semantic-route-catalog/v1",
        "partition": "development",
        "routes": [{"platform_route_id": "dev_00_r0"}],
    }))
    (bridge_source / "core.py").write_text("semantic-observation/v1")
    (bridge_source / "node.py").write_text("/semantic_observations")

    report = audit_research1(repository)
    assert report.semantic_observation_ready
    assert report.bridge_landmark_categories == tuple(sorted(categories))
    assert report.semantic_route_catalog_count == 1
    assert not any(item.startswith("semantic_observation:") for item in report.blockers)
