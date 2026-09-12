"""Deployable physical-world adapter. Never reads evaluator manifests or labels."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import yaml

from language_nav.adapters.research1 import Research1Route
from language_nav.benchmark.semantic_catalog import SemanticCatalogRoute, SemanticRouteCatalog
from language_nav.contracts import Pose2D
from language_nav.grounding import SemanticRouteProposal


@dataclass(frozen=True)
class PhysicalRuntimeCatalog:
    semantic: SemanticRouteCatalog
    execution: tuple[Research1Route, ...]


def validated_absent_anchor(directory, runtime):
    """Validate deployable absence provenance, without reading evaluator answers.

    This authorizes an engineering input shape, not a frozen campaign or a
    positive/negative observation. Proposal coverage remains zero.
    """
    directory = Path(directory)
    path = directory / 'absence_intervention.json'
    if not path.exists():
        return None
    report = json.loads(path.read_text())
    base = runtime.semantic.routes[0].base_instruction_id
    if (report.get('schema_version') != 'research3-physical-absence-intervention/v1'
            or report.get('base_instruction_id') != base
            or report.get('partition') != runtime.semantic.partition
            or report.get('protected_content_used') is not False
            or report.get('geometry_audit_passed') is not True
            or report.get('map_policy') != 'remove_chair_occupancy_for_all_systems'):
        raise ValueError('invalid absent-anchor intervention identity/policy')
    for name in ('world.sdf', 'map.pgm', 'map.yaml', 'execution_catalog.json', 'landmark_scene.yaml'):
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != report.get('asset_sha256', {}).get(name):
            raise ValueError('absent-anchor runtime asset hash mismatch: ' + name)
    expected = {'chair_seat', 'chair_back'} | {
        f'chair_leg_{dx}_{dy}' for dx in (-.16, .16) for dy in (-.16, .16)}
    if set(report.get('removed_models', [])) != expected:
        raise ValueError('absent-anchor removed model identity mismatch')
    if any(m.attrib.get('name', '').startswith('chair_')
           for m in ET.parse(directory / 'world.sdf').findall('./world/model')):
        raise ValueError('chair geometry remains in absent-anchor world')
    scene = yaml.safe_load((directory / 'landmark_scene.yaml').read_text())
    if any(e.get('category') == 'chair' or e.get('entity_id') == report.get('removed_entity_id')
           for e in scene.get('entities', [])):
        raise ValueError('chair perception truth remains in absent-anchor world')
    return runtime.semantic.map_id + '_chair_region'


def load_physical_runtime_catalog(path: str | Path) -> PhysicalRuntimeCatalog:
    path = Path(path)
    payload = json.loads(path.read_text())
    required = {"schema_version", "map_id", "map_sha256", "world_sha256", "partition", "start", "routes"}
    if set(payload) != required or payload["schema_version"] != "research3-physical-route-catalog/v1":
        raise ValueError("invalid deployable physical catalogue fields/schema")
    if payload["partition"] not in {"development", "validation"}:
        raise PermissionError("protected physical catalogues require a separately authorized runtime")
    match = re.fullmatch(r"r3geo_base_r([0-9]{3})", payload["map_id"])
    if not match:
        raise ValueError("invalid physical map identity")
    index = int(match[1])
    expected_partition = "development" if 1 <= index <= 10 else "validation" if 11 <= index <= 14 else None
    if payload["partition"] != expected_partition:
        raise PermissionError("physical map identity is outside the declared non-protected split")
    for name, key in (("map.pgm", "map_sha256"), ("world.sdf", "world_sha256")):
        if hashlib.sha256((path.parent / name).read_bytes()).hexdigest() != payload[key]:
            raise ValueError(f"physical asset hash mismatch: {name}")

    def pose(value):
        if set(value) != {"x", "y", "yaw"} or not all(
                type(v) in (int, float) and math.isfinite(v) for v in value.values()):
            raise ValueError("physical poses must be finite x/y/yaw")
        return Pose2D(float(value["x"]), float(value["y"]), float(value["yaw"]))

    start = pose(payload["start"])
    semantic, execution, seen = [], [], set()
    for item in payload["routes"]:
        if set(item) != {"route_id", "goal", "side", "ordinal", "terminal_entity_id"}:
            raise ValueError("invalid deployable route fields")
        key = (item["side"], item["ordinal"])
        if item["side"] not in {"left", "right"} or type(item["ordinal"]) is not int or item["ordinal"] not in (1, 2) or key in seen:
            raise ValueError("physical routes must contain four distinct side/ordinal alternatives")
        seen.add(key)
        route_id = f"{payload['map_id']}_{item['side']}_{item['ordinal']}"
        if item["route_id"] != route_id or item["terminal_entity_id"] != route_id + "_entrance":
            raise ValueError("route/terminal identity mismatch")
        goal = pose(item["goal"])
        distance = math.hypot(goal.x - start.x, goal.y - start.y)
        # Distance is only a proposal heuristic. Nav2 supplies path cost/eligibility.
        execution.append(Research1Route(route_id, payload["map_id"], start, goal,
                                        distance, "physical_proposal", .35, .5, 180.0))
        proposal = SemanticRouteProposal(route_id, payload["map_id"] + "_chair_region",
                                         item["terminal_entity_id"] + "_region", distance,
                                         0.0, 0.0, True, item["ordinal"], item["side"])
        semantic.append(SemanticCatalogRoute("base-r" + match[1], route_id, proposal))
    if len(seen) != 4:
        raise ValueError("physical catalogue requires all four alternatives")
    return PhysicalRuntimeCatalog(SemanticRouteCatalog(
        payload["schema_version"], payload["map_id"], payload["partition"], tuple(semantic)), tuple(execution))


def validate_physical_launch_inputs(catalog_path, scene_path, map_path=None):
    """Cross-check deployable launch assets without opening evaluator answers.

    Format v1 has fixed occupancy metadata; enforce it because its catalogue only
    pins pixels, not map.yaml. A future format must explicitly pin variable metadata.
    Scene labels are verified for association only, never turned into observations.
    """
    catalog_path, scene_path = Path(catalog_path), Path(scene_path)
    runtime = load_physical_runtime_catalog(catalog_path)
    map_path = Path(map_path) if map_path is not None else catalog_path.parent / "map.yaml"
    metadata = yaml.safe_load(map_path.read_text())
    expected = {"image": "map.pgm", "resolution": .05, "origin": [-1., -5., 0.],
                "negate": 0, "occupied_thresh": .65, "free_thresh": .196}
    if metadata != expected or (map_path.parent / "map.pgm").resolve() != (catalog_path.parent / "map.pgm").resolve():
        raise ValueError("physical map metadata/image does not match v1 geometry")
    scene = yaml.safe_load(scene_path.read_text())
    catalogue = json.loads(catalog_path.read_text())
    if (scene.get("schema_version") != "landmark-scene/v1"
            or scene.get("partition") != runtime.semantic.partition
            or scene.get("map_id") != runtime.semantic.map_id
            or scene.get("map_hash") != catalogue["map_sha256"]):
        raise ValueError("physical scene/map identity mismatch")
    entities = scene.get("entities", [])
    if (not entities or len({e["entity_id"] for e in entities}) != len(entities)
            or len({e["region_id"] for e in entities}) != len(entities)):
        raise ValueError("physical scene requires unique entity and region identities")
    by_region = {e["region_id"]: e for e in entities}
    absent_anchor = validated_absent_anchor(catalog_path.parent, runtime)
    if absent_anchor and any(e.get('category') == 'chair' or e.get('region_id') == absent_anchor for e in entities):
        raise ValueError('runtime scene reintroduces absent anchor')
    route_ids = {r.route_id for r in runtime.execution}
    if any(not set(e.get("route_ids", [])) <= route_ids for e in entities):
        raise ValueError("scene references an unknown physical route")
    for route in runtime.semantic.routes:
        for region in (route.proposal.anchor_region_id, route.proposal.terminal_region_id):
            if region == absent_anchor and region == route.proposal.anchor_region_id:
                continue
            entity = by_region.get(region)
            if entity is None or route.platform_route_id not in entity.get("route_ids", []):
                raise ValueError("physical route/scene region association missing")
        terminal = by_region[route.proposal.terminal_region_id]
        if terminal["entity_id"] != route.platform_route_id + "_entrance":
            raise ValueError("physical terminal identity mismatch")
    return runtime
