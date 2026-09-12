from pathlib import Path

import pytest
import yaml

from language_nav.benchmark import load_semantic_route_catalog
from test_research1_adapter import _make_repository


def test_semantic_catalog_resolves_frozen_platform_route(tmp_path: Path) -> None:
    repository = _make_repository(tmp_path)
    catalog_path = tmp_path / "catalog.yaml"
    catalog_path.write_text(yaml.safe_dump({
        "schema_version": "semantic-route-catalog/v1",
        "map_id": "dev_00",
        "partition": "development",
        "routes": [{
            "base_instruction_id": "base-r1",
            "platform_route_id": "dev_00_r0",
            "anchor_region_id": "junction-1",
            "terminal_region_id": "lab-1",
            "observation_coverage": 0.9,
            "branch_index": 2,
            "side": "left",
        }],
    }))
    catalog = load_semantic_route_catalog(catalog_path, repository)
    assert catalog.routes[0].proposal.distance == 4.0


def test_semantic_catalog_rejects_evaluator_fields_and_protected_access(tmp_path: Path) -> None:
    repository = _make_repository(tmp_path)
    leaked = tmp_path / "leaked.yaml"
    leaked.write_text(yaml.safe_dump({
        "schema_version": "semantic-route-catalog/v1", "map_id": "dev_00",
        "partition": "development", "routes": [{}], "oracle_goal_pose": [1, 2],
    }))
    with pytest.raises(ValueError, match="evaluator-only"):
        load_semantic_route_catalog(leaked, repository)
    protected = tmp_path / "protected.yaml"
    protected.write_text(yaml.safe_dump({
        "schema_version": "semantic-route-catalog/v1", "map_id": "test_00",
        "partition": "test", "routes": [{}],
    }))
    with pytest.raises(PermissionError, match="explicit opt-in"):
        load_semantic_route_catalog(protected, repository)


def test_semantic_catalog_rejects_unfilled_region_placeholders(tmp_path: Path) -> None:
    repository = _make_repository(tmp_path)
    placeholder = tmp_path / "placeholder.yaml"
    placeholder.write_text(yaml.safe_dump({
        "schema_version": "semantic-route-catalog/v1", "map_id": "dev_00",
        "partition": "development", "routes": [{
            "base_instruction_id": "base-r1", "platform_route_id": "dev_00_r0",
            "anchor_region_id": "REPLACE_WITH_ID", "terminal_region_id": "lab-1",
            "observation_coverage": 0.9, "branch_index": 2, "side": "left",
        }],
    }))
    with pytest.raises(ValueError, match="placeholder"):
        load_semantic_route_catalog(placeholder, repository)
