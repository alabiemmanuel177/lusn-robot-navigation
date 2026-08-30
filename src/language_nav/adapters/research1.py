from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from language_nav.contracts import Pose2D


_PARTITION_PREFIX = {"development": "dev", "validation": "val", "test": "test"}
_DATASET_LANDMARKS = frozenset(
    {
        "chair",
        "door",
        "doorway",
        "glass_doors",
        "laboratory_entrance",
        "office_entrance",
        "sign",
    }
)


@dataclass(frozen=True)
class Research1Route:
    route_id: str
    map_id: str
    start: Pose2D
    goal: Pose2D
    shortest_path_m: float
    length_class: str
    goal_tolerance_m: float
    goal_tolerance_rad: float
    episode_timeout_s: float


@dataclass(frozen=True)
class Research1CompatibilityReport:
    repository: str
    navigation_platform_ready: bool
    route_catalog_ready: bool
    benchmark_routes_ready: bool
    semantic_observation_ready: bool
    compatible_landmark_categories: tuple[str, ...]
    bridge_landmark_categories: tuple[str, ...]
    research1_semantic_categories: tuple[str, ...]
    required_landmark_categories: tuple[str, ...]
    semantic_route_catalog_count: int
    development_route_count: int
    validation_route_count: int
    unmatched_benchmark_routes: tuple[str, ...]
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


class Research1RouteCatalog:
    """Read and verify frozen Research 1 routes without importing its code.

    Protected test manifests are denied by default. Loading them requires an explicit
    opt-in so development tooling cannot accidentally inspect held-out material.
    """

    def __init__(self, repository: str | Path) -> None:
        self.repository = Path(repository).expanduser().resolve()

    def load_partition(
        self,
        partition: str,
        *,
        allow_protected: bool = False,
    ) -> tuple[Research1Route, ...]:
        if partition not in _PARTITION_PREFIX:
            raise ValueError(f"unsupported Research 1 partition: {partition}")
        if partition == "test" and not allow_protected:
            raise PermissionError("protected Research 1 test routes require explicit opt-in")
        prefix = _PARTITION_PREFIX[partition]
        paths = sorted((self.repository / "configs" / "routes").glob(f"{prefix}_*.yaml"))
        if not paths:
            raise FileNotFoundError(f"no Research 1 {partition} route manifests found")
        routes: list[Research1Route] = []
        for path in paths:
            routes.extend(self._load_manifest(path, partition))
        return tuple(routes)

    def _load_manifest(self, path: Path, partition: str) -> tuple[Research1Route, ...]:
        payload = yaml.safe_load(path.read_text())
        if not isinstance(payload, dict):
            raise ValueError(f"{path}: route manifest must be a mapping")
        map_id = str(payload.get("map_id", ""))
        if path.stem != map_id:
            raise ValueError(f"{path}: map_id does not match filename")
        if not payload.get("frozen"):
            raise ValueError(f"{path}: Research 1 map is not frozen")
        self._verify_map_hash(map_id, partition, str(payload.get("map_hash", "")))

        originals = list(payload.get("routes") or [])
        replacements = list(payload.get("replacement_routes") or [])
        replaced = {str(item["replaces_route_id"]) for item in replacements}
        active = [item for item in originals if str(item.get("route_id")) not in replaced]
        active.extend(replacements)
        if any(not item.get("s0_clean_verified") for item in active):
            raise ValueError(f"{path}: active route lacks clean S0 verification")

        timeout = float(payload["episode_timeout_s"])
        tolerance_m = float(payload["goal_tolerance_m"])
        tolerance_rad = float(payload["goal_tolerance_rad"])
        return tuple(
            Research1Route(
                route_id=str(item["route_id"]),
                map_id=map_id,
                start=_pose(item["start"]),
                goal=_pose(item["goal"]),
                shortest_path_m=float(item["shortest_path_m"]),
                length_class=str(item["length_class"]),
                goal_tolerance_m=tolerance_m,
                goal_tolerance_rad=tolerance_rad,
                episode_timeout_s=timeout,
            )
            for item in active
        )

    def _verify_map_hash(self, map_id: str, partition: str, recorded: str) -> None:
        map_dir = self.repository / "data" / partition / map_id
        digest = hashlib.sha256()
        for name in ("map.yaml", "map.pgm"):
            path = map_dir / name
            if not path.is_file():
                raise FileNotFoundError(f"Research 1 map artifact missing: {path}")
            digest.update(name.encode("utf-8") + b"\0")
            digest.update(path.read_bytes())
        if not recorded or digest.hexdigest() != recorded:
            raise ValueError(f"Research 1 map hash mismatch: {map_id}")


def audit_research1(repository: str | Path) -> Research1CompatibilityReport:
    """Report which completed Research 1 outputs can be consumed by this project."""

    root = Path(repository).expanduser().resolve()
    catalog = Research1RouteCatalog(root)
    blockers: list[str] = []
    development: tuple[Research1Route, ...] = ()
    validation: tuple[Research1Route, ...] = ()
    try:
        development = catalog.load_partition("development")
        validation = catalog.load_partition("validation")
    except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        blockers.append(f"route_catalog: {exc}")

    from language_nav.benchmark.corpus import build_corpus

    available_route_ids = {route.route_id for route in (*development, *validation)}
    benchmark_route_ids = {
        route.platform_route_id
        for route in build_corpus()
        if route.partition in {"development", "validation"}
    }
    unmatched_routes = tuple(sorted(benchmark_route_ids - available_route_ids))
    benchmark_routes_ready = bool(benchmark_route_ids) and not unmatched_routes
    if unmatched_routes:
        blockers.append(
            "benchmark_routes: Research 3 references unavailable Research 1 routes: "
            + ", ".join(unmatched_routes)
        )

    ontology_path = root / "configs" / "ontology.yaml"
    categories: set[str] = set()
    if ontology_path.is_file():
        ontology = yaml.safe_load(ontology_path.read_text()) or {}
        categories = {
            str(item.get("name"))
            for item in ontology.get("classes", [])
            if isinstance(item, dict) and item.get("name")
        }
    else:
        blockers.append("semantic_ontology: configs/ontology.yaml is missing")

    bridge_root = root / "configs" / "landmark_bridge"
    bridge_categories: set[str] = set()
    bridge_route_ids: set[str] = set()
    bridge_problems: list[str] = []
    scene_paths = sorted((bridge_root / "scenes").glob("*.yaml"))
    for path in scene_paths:
        payload = yaml.safe_load(path.read_text()) or {}
        if payload.get("schema_version") != "landmark-scene/v1":
            bridge_problems.append(f"{path.name}: invalid landmark scene schema")
            continue
        if payload.get("partition") not in {"development", "validation"}:
            bridge_problems.append(f"{path.name}: protected or invalid landmark partition")
        for entity in payload.get("entities") or []:
            bridge_categories.add(str(entity.get("category", "")))
            bridge_route_ids.update(str(route_id) for route_id in entity.get("route_ids") or [])
    semantic_route_paths = sorted((bridge_root / "semantic_routes").glob("*.yaml"))
    semantic_route_ids: set[str] = set()
    for path in semantic_route_paths:
        payload = yaml.safe_load(path.read_text()) or {}
        if payload.get("schema_version") != "semantic-route-catalog/v1":
            bridge_problems.append(f"{path.name}: invalid semantic route catalogue schema")
            continue
        if payload.get("partition") not in {"development", "validation"}:
            bridge_problems.append(f"{path.name}: protected or invalid semantic route partition")
        semantic_route_ids.update(
            str(item.get("platform_route_id", "")) for item in payload.get("routes") or []
        )
    unresolved_bridge_routes = (bridge_route_ids | semantic_route_ids) - available_route_ids
    if unresolved_bridge_routes:
        bridge_problems.append(
            "bridge references unavailable Research 1 routes: "
            + ", ".join(sorted(unresolved_bridge_routes))
        )
    if bridge_route_ids != semantic_route_ids:
        bridge_problems.append("landmark scenes and semantic catalogues cover different routes")

    bridge_source = (
        root / "extensions" / "research3_landmark_bridge" /
        "research3_landmark_bridge" / "core.py"
    )
    bridge_node = bridge_source.with_name("node.py")
    contract_implemented = (
        bridge_source.is_file()
        and "semantic-observation/v1" in bridge_source.read_text()
        and bridge_node.is_file()
        and "/semantic_observations" in bridge_node.read_text()
    )
    compatible = bridge_categories & _DATASET_LANDMARKS
    semantic_ready = (
        contract_implemented
        and bool(scene_paths)
        and bool(semantic_route_paths)
        and _DATASET_LANDMARKS <= bridge_categories
        and not bridge_problems
    )
    if not semantic_ready:
        blockers.append(
            "semantic_observation: the separate Research 1 landmark bridge is missing, "
            "incomplete, protected, or inconsistent with frozen routes"
        )
        blockers.extend(f"semantic_bridge: {problem}" for problem in bridge_problems)

    status_path = root / "docs" / "STATUS.md"
    status = status_path.read_text() if status_path.is_file() else ""
    controller_path = (
        root / "src" / "experiment_controller" / "experiment_controller" / "run_episode.py"
    )
    controller_source = controller_path.read_text() if controller_path.is_file() else ""
    navigation_ready = (
        "G0-G7 have evidence" in status
        and "NavigateToPose" in controller_source
    )
    if not navigation_ready:
        blockers.append("navigation_platform: completion evidence or Nav2 execution boundary is missing")

    return Research1CompatibilityReport(
        repository=str(root),
        navigation_platform_ready=navigation_ready,
        route_catalog_ready=bool(development and validation),
        benchmark_routes_ready=benchmark_routes_ready,
        semantic_observation_ready=semantic_ready,
        compatible_landmark_categories=tuple(sorted(compatible)),
        bridge_landmark_categories=tuple(sorted(bridge_categories)),
        research1_semantic_categories=tuple(sorted(categories)),
        required_landmark_categories=tuple(sorted(_DATASET_LANDMARKS)),
        semantic_route_catalog_count=len(semantic_route_paths),
        development_route_count=len(development),
        validation_route_count=len(validation),
        unmatched_benchmark_routes=unmatched_routes,
        blockers=tuple(blockers),
    )


def _pose(payload: dict[str, Any]) -> Pose2D:
    return Pose2D(float(payload["x"]), float(payload["y"]), float(payload.get("yaw", 0.0)))
