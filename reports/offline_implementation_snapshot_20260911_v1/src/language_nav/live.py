from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from language_nav.contracts import FailureMonitorState, MonitorLevel


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValueError(f"invalid boolean: {value!r}")


def research2_warning_to_state(
    values: Mapping[str, str], observed_at_ns: int
) -> FailureMonitorState:
    """Translate the deployed Research 2 diagnostic payload without guessing fields."""
    required = {"risk_score", "persistent", "alarm", "engineering_smoke"}
    missing = required - set(values)
    if missing:
        raise ValueError("Research 2 warning missing: " + ", ".join(sorted(missing)))
    if parse_bool(values["engineering_smoke"]):
        raise ValueError("engineering-smoke Research 2 warnings are not research evidence")
    probability = float(values["risk_score"])
    alarm = parse_bool(values["alarm"])
    persistent = parse_bool(values["persistent"])
    if alarm:
        level = MonitorLevel.FAILURE_LIKELY
    elif persistent:
        level = MonitorLevel.CAUTION
    else:
        level = MonitorLevel.NOMINAL
    reasons = ["research2_alarm" if alarm else "research2_nominal"]
    signal_group = values.get("diagnosed_signal_group", "").strip()
    if signal_group:
        reasons.append(f"signal_group:{signal_group}")
    return FailureMonitorState(
        schema_version="failure-monitor/v1",
        level=level,
        failure_probability=probability,
        reason_codes=tuple(reasons),
        observed_at_ns=observed_at_ns,
    )


def research2_ready_to_state(
    values: Mapping[str, str], observed_at_ns: int
) -> FailureMonitorState:
    """Represent a verified frozen monitor that is ready but has no mission window yet."""
    if values.get("event_type") != "monitor_started":
        raise ValueError("Research 2 readiness requires monitor_started")
    if "engineering_smoke" not in values:
        raise ValueError("Research 2 readiness is missing engineering_smoke")
    if parse_bool(values["engineering_smoke"]):
        raise ValueError("engineering-smoke Research 2 readiness is not research evidence")
    return FailureMonitorState(
        schema_version="failure-monitor/v1",
        level=MonitorLevel.NOMINAL,
        failure_probability=0.0,
        reason_codes=("monitor_ready_pre_mission", "no_prediction_yet"),
        observed_at_ns=observed_at_ns,
    )


def base_instruction_id(instruction_id: str) -> str:
    """Resolve deployed benchmark variants while preserving bare base IDs."""
    parts = instruction_id.split("-")
    if len(parts) >= 2 and parts[0] == "base" and parts[1].startswith("r"):
        return "-".join(parts[:2])
    raise ValueError(f"unsupported instruction identity: {instruction_id!r}")


def monitor_is_fresh(observed_at_ns: int, now_ns: int, timeout_s: float) -> bool:
    """Reject missing, future and expired monitor timestamps."""
    return (
        math.isfinite(timeout_s) and timeout_s > 0 and observed_at_ns > 0
        and 0 <= now_ns - observed_at_ns <= timeout_s * 1_000_000_000
    )


class MonitorStreamGuard:
    """One readiness event, then strictly newer predictions; invalid data closes motion."""

    def __init__(self):
        self.last_prediction_ns = 0
        self.readiness_consumed = False

    def invalidate(self, now_ns):
        self.readiness_consumed = True
        self.last_prediction_ns = max(self.last_prediction_ns, now_ns)
        return FailureMonitorState("failure-monitor/v1", MonitorLevel.FAILURE_LIKELY,
                                   1.0, ("monitor_stream_invalid",), now_ns)

    def accept(self, state, now_ns):
        ready = "no_prediction_yet" in state.reason_codes
        if ready and self.readiness_consumed:
            return None
        if not monitor_is_fresh(state.observed_at_ns, now_ns, 120.0 if ready else 3.0):
            raise ValueError("monitor timestamp is missing, future or stale")
        if not ready and state.observed_at_ns <= self.last_prediction_ns:
            raise ValueError("monitor prediction is replayed or out of order")
        self.readiness_consumed = True
        if not ready:
            self.last_prediction_ns = state.observed_at_ns
        return state


def path_length(points: Sequence[tuple[float, float]]) -> float:
    return sum(
        math.hypot(x1 - x0, y1 - y0)
        for (x0, y0), (x1, y1) in zip(points, points[1:])
    )


def validate_trajectory_evidence(positions, stamps, started_ns, ended_ns,
                                 max_gap_s=1.0, max_step_m=0.5):
    """Engineering validity gate, not a substitute for a frozen campaign protocol."""
    if (not math.isfinite(max_gap_s) or max_gap_s <= 0
            or not math.isfinite(max_step_m) or max_step_m <= 0):
        raise ValueError("trajectory limits must be finite and positive")
    if len(positions) != len(stamps):
        raise ValueError("trajectory timestamp count mismatch")
    if not all(len(p) == 2 and all(math.isfinite(v) for v in p) for p in positions):
        raise ValueError("trajectory must contain finite 2D positions")
    if (started_ns <= 0 or ended_ns < started_ns
            or any(type(t) is not int or not started_ns <= t <= ended_ns for t in stamps)
            or any(b <= a for a, b in zip(stamps, stamps[1:]))):
        raise ValueError("trajectory timestamps must be ordered within the episode")
    gaps = [b - a for a, b in zip([started_ns, *stamps], [*stamps, ended_ns])]
    max_gap = max(gaps, default=0) / 1e9
    max_step = max((math.dist(a, b) for a, b in zip(positions, positions[1:])), default=0.0)
    return {"valid": len(stamps) >= 2 and max_gap <= max_gap_s and max_step <= max_step_m,
            "max_gap_s": max_gap, "max_step_m": max_step,
            "gap_limit_s": max_gap_s, "step_limit_m": max_step_m}


def inspection_waypoint(points: Sequence[tuple[float, float]], separation_m: float = 0.5):
    """Choose a distinct intermediate pose on a Nav2-approved path, or abstain."""
    if len(points) < 3 or separation_m <= 0:
        return None
    total = path_length(points)
    travelled = 0.0
    candidates = []
    for index in range(1, len(points) - 1):
        travelled += math.dist(points[index - 1], points[index])
        if (math.dist(points[index], points[0]) >= separation_m
                and math.dist(points[index], points[-1]) >= separation_m):
            candidates.append((abs(travelled - total / 2), index))
    if not candidates:
        return None
    index = min(candidates)[1]
    x, y = points[index]
    next_x, next_y = points[index + 1]
    return x, y, math.atan2(next_y - y, next_x - x)


def has_post_inspection_anchor(candidates_json, route_id, completed_at_ns, now_ns):
    """A decision timestamp or terminal-only refresh is not an anchor observation."""
    try:
        candidates = json.loads(candidates_json)
        if not isinstance(candidates, list):
            return False
        selected = [candidate for candidate in candidates if candidate.get("route_id") == route_id]
        if len(selected) != 1:
            return False
        anchor = selected[0]
        stamp = anchor.get("anchor_observed_at_ns")
        sequence = anchor.get("anchor_observation_sequence")
        return (bool(anchor.get("anchor_observation_id"))
                and bool(anchor.get("anchor_observation_source"))
                and type(sequence) is int and sequence >= 0
                and type(stamp) is int and completed_at_ns < stamp
                and monitor_is_fresh(stamp, now_ns, 3.0))
    except (TypeError, ValueError, AttributeError):
        return False


def measured_live_outcome(
    *, positions: Sequence[tuple[float, float]], distance_m: float,
    goal: tuple[float, float], goal_tolerance_m: float,
    collision: bool, timeout: bool, nav2_success: bool,
) -> dict:
    """Summarize independent measurements without inferring semantic completion."""
    if not math.isfinite(goal_tolerance_m) or goal_tolerance_m <= 0:
        raise ValueError("goal tolerance must be finite and positive")
    if not math.isfinite(distance_m) or distance_m < 0:
        raise ValueError("measured distance must be finite and nonnegative")
    if not all(math.isfinite(value) for point in (*positions, goal) for value in point):
        raise ValueError("ground-truth positions and goal must be finite")
    goal_error = math.dist(positions[-1], goal) if positions else None
    reached = goal_error <= goal_tolerance_m if goal_error is not None else None
    return {
        "navigation_success": bool(nav2_success and reached and not collision and not timeout),
        "nav2_reported_success": bool(nav2_success),
        "instruction_completion": None,
        "wrong_goal": None,
        "collision": bool(collision),
        "timeout": bool(timeout),
        "distance_travelled_m": distance_m if positions else None,
        "ground_truth_samples": len(positions),
        "goal_error_m": goal_error,
        "goal_tolerance_m": goal_tolerance_m,
        "goal_reached": reached,
        "semantic_outcome_measured": False,
    }


def terminal_identity_outcome(positions, entities, expected_region_id, radius_m=0.75):
    """Score terminal proximity from provider ground truth, never detector belief.

    Multiple nearby terminal instances remain ambiguous. This measures only the
    terminal clause; it cannot establish ordered instruction completion.
    """
    if not math.isfinite(radius_m) or radius_m <= 0:
        raise ValueError("terminal radius must be finite and positive")
    expected = [entity for entity in entities if entity["region_id"] == expected_region_id]
    if len(expected) != 1:
        raise ValueError("terminal ground truth must resolve to exactly one stable entity")
    target = expected[0]
    candidates = []
    if positions:
        for entity in entities:
            if entity["category"] not in {"laboratory_entrance", "office_entrance"}:
                continue
            distance = math.dist(positions[-1], (entity["pose"]["x"], entity["pose"]["y"]))
            if distance <= radius_m:
                candidates.append(entity["entity_id"])
    observed = candidates[0] if len(candidates) == 1 else None
    return {
        "expected_terminal_entity_id": target["entity_id"],
        "nearby_terminal_entity_ids": sorted(candidates),
        "measured_terminal_entity_id": observed,
        "terminal_identity_correct": observed == target["entity_id"] if observed else None,
        "terminal_identity_ambiguous": len(candidates) > 1,
        "terminal_radius_m": radius_m,
        "terminal_measurement_source": "provider scene ground truth and measured final position",
    }


@dataclass(frozen=True)
class ImmutableEpisodeRecord:
    schema_version: str
    run_id: str
    instruction_id: str
    route_id: str
    action: str
    navigation_success: bool
    collision: bool
    timeout: bool
    infrastructure_failure: bool
    distance: float
    reason: str
    started_at_ns: int
    completed_at_ns: int

    def to_json(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))
