from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, runtime_checkable


class MonitorLevel(StrEnum):
    NOMINAL = "nominal"
    CAUTION = "caution"
    FAILURE_LIKELY = "failure_likely"


@dataclass(frozen=True)
class Pose2D:
    x: float
    y: float
    yaw: float = 0.0


@dataclass(frozen=True)
class SemanticObservationContract:
    """Versioned landmark boundary expected from a Research 1-compatible bridge."""

    schema_version: str
    observation_id: str
    entity_id: str
    category: str
    attributes: dict[str, str]
    pose: Pose2D
    covariance: tuple[float, float, float, float]
    confidence: float
    observed_at_ns: int
    frame_id: str
    source: str
    sequence: int
    region_id: str

    def __post_init__(self) -> None:
        if self.schema_version != "semantic-observation/v1":
            raise ValueError("unsupported semantic observation schema")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("semantic confidence must be in [0, 1]")
        if len(self.covariance) != 4 or any(value < 0 for value in self.covariance):
            raise ValueError("2D covariance must contain four non-negative values")


@dataclass(frozen=True)
class RouteRequest:
    request_id: str
    target_region_id: str
    semantic_intent: str
    maximum_risk: float

    def __post_init__(self) -> None:
        if not self.request_id or not self.target_region_id:
            raise ValueError("route request identifiers must be non-empty")
        if not 0.0 <= self.maximum_risk <= 1.0:
            raise ValueError("maximum route risk must be in [0, 1]")


@dataclass(frozen=True)
class RouteEligibility:
    request_id: str
    eligible: bool
    traversability_observed: bool
    estimated_cost: float
    risk: float
    reason: str

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("route eligibility request_id must be non-empty")
        if self.estimated_cost < 0.0:
            raise ValueError("estimated route cost must be non-negative")
        if not 0.0 <= self.risk <= 1.0:
            raise ValueError("route risk must be in [0, 1]")


@dataclass(frozen=True)
class RouteExecutionResult:
    request_id: str
    succeeded: bool
    visited_regions: tuple[str, ...]
    distance: float
    collision: bool = False
    infrastructure_failure: bool = False
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("route execution request_id must be non-empty")
        if self.distance < 0.0:
            raise ValueError("route execution distance must be non-negative")


@dataclass(frozen=True)
class FailureMonitorState:
    schema_version: str
    level: MonitorLevel
    failure_probability: float
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    observed_at_ns: int = 0

    def __post_init__(self) -> None:
        if self.schema_version != "failure-monitor/v1":
            raise ValueError("unsupported failure monitor schema")
        if not 0.0 <= self.failure_probability <= 1.0:
            raise ValueError("failure probability must be in [0, 1]")


@runtime_checkable
class SemanticObservationSource(Protocol):
    def observe(self) -> tuple[SemanticObservationContract, ...]: ...


@runtime_checkable
class RouteExecutor(Protocol):
    def check(self, request: RouteRequest) -> RouteEligibility: ...

    def execute(self, request: RouteRequest) -> RouteExecutionResult: ...


@runtime_checkable
class FailureMonitor(Protocol):
    def state(self) -> FailureMonitorState: ...
