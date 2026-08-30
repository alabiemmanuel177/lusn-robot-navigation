from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from language_nav.adapters.research1 import Research1RouteCatalog
from language_nav.grounding import SemanticRouteProposal


@dataclass(frozen=True)
class SemanticCatalogRoute:
    base_instruction_id: str
    platform_route_id: str
    proposal: SemanticRouteProposal


@dataclass(frozen=True)
class SemanticRouteCatalog:
    schema_version: str
    map_id: str
    partition: str
    routes: tuple[SemanticCatalogRoute, ...]


def load_semantic_route_catalog(
    path: str | Path,
    research1_repository: str | Path,
    *,
    allow_protected: bool = False,
) -> SemanticRouteCatalog:
    catalog_path = Path(path)
    payload = yaml.safe_load(catalog_path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("semantic route catalogue must be a mapping")
    if payload.get("schema_version") != "semantic-route-catalog/v1":
        raise ValueError("unsupported semantic route catalogue schema")
    partition = str(payload.get("partition", ""))
    if partition not in {"development", "validation", "test"}:
        raise ValueError("semantic route catalogue partition is invalid")
    if partition == "test" and not allow_protected:
        raise PermissionError("protected semantic route catalogue requires explicit opt-in")
    map_id = str(payload.get("map_id", ""))
    if not map_id:
        raise ValueError("semantic route catalogue map_id is required")
    forbidden = {"oracle_goal_pose", "correct_grounding", "future_observations"}
    leaked = forbidden & set(payload)
    if leaked:
        raise ValueError("evaluator-only fields in semantic route catalogue: " + ", ".join(sorted(leaked)))

    platform = Research1RouteCatalog(research1_repository).load_partition(
        partition, allow_protected=allow_protected
    )
    platform_by_id = {route.route_id: route for route in platform}
    routes: list[SemanticCatalogRoute] = []
    instruction_ids: set[str] = set()
    platform_ids: set[str] = set()
    for index, item in enumerate(payload.get("routes") or []):
        if not isinstance(item, dict):
            raise ValueError(f"catalogue route[{index}] must be a mapping")
        base_id = str(item.get("base_instruction_id", ""))
        platform_id = str(item.get("platform_route_id", ""))
        if not base_id or not platform_id:
            raise ValueError(f"catalogue route[{index}] identifiers are required")
        if base_id in instruction_ids or platform_id in platform_ids:
            raise ValueError("catalogue instruction and platform route IDs must be unique")
        platform_route = platform_by_id.get(platform_id)
        if platform_route is None or platform_route.map_id != map_id:
            raise ValueError(f"catalogue route {platform_id} does not resolve on map {map_id}")
        anchor_region_id = str(item["anchor_region_id"])
        terminal_region_id = str(item["terminal_region_id"])
        if anchor_region_id.startswith("REPLACE_") or terminal_region_id.startswith("REPLACE_"):
            raise ValueError("catalogue placeholder region IDs must be replaced")
        instruction_ids.add(base_id)
        platform_ids.add(platform_id)
        routes.append(
            SemanticCatalogRoute(
                base_instruction_id=base_id,
                platform_route_id=platform_id,
                proposal=SemanticRouteProposal(
                    route_id=platform_id,
                    anchor_region_id=anchor_region_id,
                    terminal_region_id=terminal_region_id,
                    distance=platform_route.shortest_path_m,
                    prior_risk=float(item.get("prior_risk", 0.0)),
                    observation_coverage=float(item["observation_coverage"]),
                    traversability_observed=bool(item.get("traversability_observed", True)),
                    branch_index=int(item["branch_index"]),
                    side=str(item["side"]),
                    relation=str(item.get("relation", "past")),
                ),
            )
        )
    if not routes:
        raise ValueError("semantic route catalogue must contain routes")
    return SemanticRouteCatalog("semantic-route-catalog/v1", map_id, partition, tuple(routes))
