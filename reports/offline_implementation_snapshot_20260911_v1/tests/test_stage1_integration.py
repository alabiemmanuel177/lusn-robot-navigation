"""Non-protected stage-1 contract checks; no simulator or ROS process is started.

Scene annotations below are test fixtures, never runtime detections or calibration
labels. Callback checks execute the production method with in-memory ROS doubles.
"""
import ast
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
import yaml

from language_nav.benchmark.physical_catalog import (
    load_physical_runtime_catalog, validate_physical_launch_inputs,
)
from language_nav.contracts import Pose2D, RouteEligibility, SemanticObservationContract
from language_nav.grounding import build_semantic_route_candidates
from language_nav.live import base_instruction_id
from language_nav.models import ActionKind
from language_nav.systems import SystemInput, build_central_variants


ROOT = Path(__file__).resolve().parents[1]
WORLDS = ROOT / "data/physical_worlds_v1"


def _fixture(index):
    folder = WORLDS / f"base-r{index:03d}"
    runtime = load_physical_runtime_catalog(folder / "execution_catalog.json")
    scene = yaml.safe_load((folder / "landmark_scene.yaml").read_text())
    return folder, runtime, scene


@pytest.mark.parametrize("index", range(1, 15))
def test_deployment_scene_matches_all_four_route_regions(index):
    folder, runtime, scene = _fixture(index)
    assert validate_physical_launch_inputs(
        folder / "execution_catalog.json", folder / "landmark_scene.yaml") == runtime
    assert scene["map_id"] == runtime.semantic.map_id
    assert scene["partition"] == runtime.semantic.partition
    assert scene["map_hash"] == hashlib.sha256((folder / "map.pgm").read_bytes()).hexdigest()
    entities = scene["entities"]
    assert len({entity["entity_id"] for entity in entities}) == len(entities)
    route_ids = {route.route_id for route in runtime.execution}
    assert route_ids == {route.proposal.route_id for route in runtime.semantic.routes}
    assert {(route.proposal.side, route.proposal.branch_index)
            for route in runtime.semantic.routes} == {
                ("left", 1), ("left", 2), ("right", 1), ("right", 2)}
    for route in runtime.semantic.routes:
        proposal = route.proposal
        anchors = [e for e in entities if e["region_id"] == proposal.anchor_region_id]
        terminals = [e for e in entities if e["region_id"] == proposal.terminal_region_id]
        assert len(anchors) == len(terminals) == 1
        assert anchors[0]["category"] == "chair"
        assert set(anchors[0]["route_ids"]) == route_ids
        assert terminals[0]["entity_id"] == proposal.route_id + "_entrance"
        assert terminals[0]["route_ids"] == [proposal.route_id]
        assert terminals[0]["category"] in {"office_entrance", "laboratory_entrance"}


def _synthetic_observations(scene):
    return tuple(SemanticObservationContract(
        "semantic-observation/v1", "unit-test-" + entity["entity_id"],
        entity["entity_id"], entity["category"], entity.get("attributes", {}),
        Pose2D(entity["pose"]["x"], entity["pose"]["y"]),
        tuple(entity["covariance"]), .9, 10, "map", "unit-test-only", 1,
        entity["region_id"],
    ) for entity in scene["entities"])


@pytest.mark.parametrize("guard", ["missing", "ineligible", "unobserved"])
def test_visible_scene_cannot_bypass_nav2_guard(guard):
    _, runtime, scene = _fixture(10)
    proposals = tuple(route.proposal for route in runtime.semantic.routes)
    eligibility = () if guard == "missing" else tuple(RouteEligibility(
        proposal.route_id, guard != "ineligible", guard != "unobserved",
        proposal.distance, .1, "synthetic guard fixture",
    ) for proposal in proposals)
    candidates = build_semantic_route_candidates(
        _synthetic_observations(scene), proposals, eligibility)
    assert len(candidates) == 4
    assert len({candidate.anchor_entity_id for candidate in candidates}) == 1
    inputs = SystemInput("base-r010", "Continue past the blue chair, then take the "
                         "second doorway on the left, then stop near the laboratory entrance.",
                         candidates)
    for variant in build_central_variants():
        decision = variant.decide(inputs)
        assert decision.action is ActionKind.ABSTAIN
        assert not decision.guard_passed


def _provider_callback():
    # Compile the actual method in isolation so these checks need no ROS imports.
    path = ROOT / "ros_ws/src/language_nav_runtime/language_nav_runtime/semantic_routes.py"
    tree = ast.parse(path.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "SemanticRouteNode")
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef)
                  and node.name == "on_hypotheses")
    namespace = {"LanguageHypotheses": SimpleNamespace,
                 "SemanticRouteProposal": SimpleNamespace,
                 "base_instruction_id": base_instruction_id}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["on_hypotheses"]


@pytest.mark.parametrize("instruction_id, schema, expected", [
    ("base-r010", "language-hypotheses/v1", 4),
    ("base-r011", "language-hypotheses/v1", 0),
    ("invalid", "language-hypotheses/v1", 0),
    ("base-r010", "unsupported", 0),
])
def test_semantic_callback_publishes_only_current_world_alternatives(instruction_id, schema, expected):
    _, runtime, _ = _fixture(10)
    published, errors = [], []
    node = SimpleNamespace(
        catalog=runtime.semantic,
        publisher=SimpleNamespace(publish=published.append),
        get_logger=lambda: SimpleNamespace(error=errors.append),
        get_clock=lambda: SimpleNamespace(now=lambda: SimpleNamespace(nanoseconds=100)),
    )
    _provider_callback()(node, SimpleNamespace(instruction_id=instruction_id, schema_version=schema))
    assert len(published) == expected
    if expected:
        assert {message.route_id for message in published} == {
            route.route_id for route in runtime.execution}
        assert all(message.instruction_id == instruction_id for message in published)
        assert all(message.observation_coverage == 0 for message in published)
        assert all(message.proposed_at_ns == 100 for message in published)
        assert all(not hasattr(message, "expected_route_id") for message in published)
        assert not errors
    else:
        assert errors


@pytest.mark.parametrize("mutation", [
    "map_id", "map_hash", "partition", "duplicate_entity", "duplicate_region",
    "missing_region", "unknown_route", "missing_route", "terminal_identity", "map_origin",
    "map_resolution", "map_image", "relabelled_protected",
])
def test_preflight_rejects_inconsistent_deploy_bundle(tmp_path, mutation):
    # Copy only deployable inputs: evaluator manifests/gates are deliberately absent.
    for name in ("execution_catalog.json", "map.pgm", "map.yaml", "world.sdf", "landmark_scene.yaml"):
        shutil.copyfile(WORLDS / "base-r010" / name, tmp_path / name)
    scene_path = tmp_path / "landmark_scene.yaml"
    scene = yaml.safe_load(scene_path.read_text())
    if mutation in {"map_id", "map_hash", "partition"}:
        scene[mutation] = "incorrect"
    elif mutation == "duplicate_entity":
        scene["entities"][1]["entity_id"] = scene["entities"][0]["entity_id"]
    elif mutation == "duplicate_region":
        scene["entities"][1]["region_id"] = scene["entities"][0]["region_id"]
    elif mutation == "missing_region":
        scene["entities"][0]["region_id"] = "unmatched-region"
    elif mutation == "unknown_route":
        scene["entities"][0]["route_ids"].append("unknown-route")
    elif mutation == "missing_route":
        scene["entities"][0]["route_ids"].pop()
    elif mutation == "terminal_identity":
        scene["entities"][1]["entity_id"] = "incorrect-terminal"
    elif mutation.startswith("map_"):
        path = tmp_path / "map.yaml"
        metadata = yaml.safe_load(path.read_text())
        if mutation == "map_origin":
            metadata["origin"][0] += 1
        elif mutation == "map_resolution":
            metadata["resolution"] = .1
        else:
            metadata["image"] = "alternate.pgm"
        path.write_text(yaml.safe_dump(metadata))
    else:
        path = tmp_path / "execution_catalog.json"
        payload = json.loads(path.read_text())
        payload["map_id"] = "r3geo_base_r015"
        path.write_text(json.dumps(payload))
    scene_path.write_text(yaml.safe_dump(scene))
    with pytest.raises((ValueError, PermissionError)):
        validate_physical_launch_inputs(tmp_path / "execution_catalog.json", scene_path)
