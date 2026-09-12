import pytest

from language_nav.contracts import MonitorLevel
from language_nav.live import (
    MonitorStreamGuard,
    validate_trajectory_evidence,
    base_instruction_id,
    measured_live_outcome,
    monitor_is_fresh,
    inspection_waypoint,
    has_post_inspection_anchor,
    terminal_identity_outcome,
    path_length,
    research2_ready_to_state,
    research2_warning_to_state,
)


def test_inspection_requires_fresh_anchor_not_decision_or_terminal_timestamp():
    import json
    anchor = {"route_id": "r", "anchor_observation_id": "obs-2",
              "anchor_observation_source": "rgbd", "anchor_observation_sequence": 2,
              "anchor_observed_at_ns": 20}
    check = lambda value: has_post_inspection_anchor(json.dumps([value]), "r", 10, 30)
    assert check(anchor)
    assert not check({**anchor, "anchor_observed_at_ns": 10, "terminal_observed_at_ns": 25})
    assert not check({**anchor, "anchor_observed_at_ns": 31})
    assert not check({**anchor, "anchor_observation_id": ""})
    assert not check({**anchor, "anchor_observation_sequence": -1})
    assert not has_post_inspection_anchor("not json", "r", 10, 30)
    assert not has_post_inspection_anchor(json.dumps([anchor, anchor]), "r", 10, 30)


def test_timestamped_trajectory_detects_gaps_jumps_and_missing_evidence():
    points = [(0, 0), (0.1, 0)]
    assert validate_trajectory_evidence(points, [1, 100000001], 1, 200000001)["valid"]
    assert not validate_trajectory_evidence(points, [1, 2000000001], 1, 2000000001)["valid"]
    assert not validate_trajectory_evidence([(0, 0), (3, 0)], [1, 2], 1, 2)["valid"]
    assert not validate_trajectory_evidence([], [], 1, 2)["valid"]
    for stamps in ([2, 1], [1, 1], [1, 3]):
        with pytest.raises(ValueError, match="timestamps"):
            validate_trajectory_evidence(points, stamps, 1, 2)
    with pytest.raises(ValueError, match="count"):
        validate_trajectory_evidence(points, [1], 1, 2)


def test_monitor_stream_rejects_replay_and_readiness_cannot_clear_failure():
    from dataclasses import replace
    guard = MonitorStreamGuard()
    ready = research2_ready_to_state({"event_type": "monitor_started", "engineering_smoke": "false"}, 10)
    assert guard.accept(ready, 10) == ready
    assert guard.accept(replace(ready, observed_at_ns=11), 11) is None
    warning = research2_warning_to_state({"risk_score": "0.8", "persistent": "true",
                                         "alarm": "true", "engineering_smoke": "false"}, 12)
    assert guard.accept(warning, 12) == warning
    with pytest.raises(ValueError, match="replayed"):
        guard.accept(warning, 13)
    assert guard.invalidate(13).failure_probability == 1.0
    assert guard.accept(replace(ready, observed_at_ns=14), 14) is None
    with pytest.raises(ValueError, match="future"):
        guard.accept(replace(warning, observed_at_ns=16), 15)
    assert guard.accept(replace(warning, observed_at_ns=15), 15)


def test_research2_warning_maps_frozen_payload() -> None:
    state = research2_warning_to_state(
        {
            "risk_score": "0.42",
            "persistent": "true",
            "alarm": "false",
            "engineering_smoke": "false",
            "diagnosed_signal_group": "localisation",
        },
        123,
    )
    assert state.level is MonitorLevel.CAUTION
    assert state.failure_probability == 0.42
    assert state.observed_at_ns == 123
    assert "signal_group:localisation" in state.reason_codes


def test_research2_warning_rejects_smoke_and_malformed_values() -> None:
    with pytest.raises(ValueError, match="engineering-smoke"):
        research2_warning_to_state(
            {
                "risk_score": "0.2",
                "persistent": "false",
                "alarm": "false",
                "engineering_smoke": "true",
            },
            1,
        )
    with pytest.raises(ValueError, match="missing"):
        research2_warning_to_state({}, 1)


def test_instruction_and_path_helpers() -> None:
    assert base_instruction_id("base-r010") == "base-r010"
    assert base_instruction_id("base-r010-truthful_original-s0") == "base-r010"
    assert path_length(((0.0, 0.0), (3.0, 4.0), (3.0, 5.0))) == 6.0


def test_monitor_freshness_rejects_future_expired_and_invalid_timestamps():
    assert monitor_is_fresh(1_000_000_000, 4_000_000_000, 3.0)
    assert not monitor_is_fresh(1_000_000_000, 4_000_000_001, 3.0)
    assert not monitor_is_fresh(2, 1, 3.0)
    assert not monitor_is_fresh(0, 1, 3.0)
    assert not monitor_is_fresh(1, 1, float("nan"))


def test_inspection_stops_between_start_and_goal_or_refuses_short_path():
    assert inspection_waypoint(((0, 0), (1, 0), (2, 0))) == (1, 0, 0)
    assert inspection_waypoint(((0, 0), (0.1, 0), (0.2, 0))) is None
    assert inspection_waypoint(((0, 0), (2, 0))) is None
    # A looping path cannot count proximity to its terminal goal as inspection.
    assert inspection_waypoint(((0, 0), (1, 0), (1.1, 0))) is None


def test_terminal_identity_keeps_overlapping_instances_ambiguous():
    target = {"entity_id": "lab-1", "region_id": "terminal-1", "category": "laboratory_entrance",
              "pose": {"x": 1, "y": 1}}
    other = {"entity_id": "office-1", "region_id": "terminal-2", "category": "office_entrance",
             "pose": {"x": 1.1, "y": 1}}
    assert terminal_identity_outcome([(1, 1)], [target], "terminal-1")["terminal_identity_correct"]
    result = terminal_identity_outcome([(1, 1)], [target, other], "terminal-1")
    assert result["terminal_identity_correct"] is None
    assert result["terminal_identity_ambiguous"]
    assert terminal_identity_outcome([], [target], "terminal-1")["terminal_identity_correct"] is None


def test_live_success_requires_measured_goal_and_preserves_unknown_semantics():
    values = dict(positions=((0, 0), (3, 4)), distance_m=5.0, goal=(3, 4),
                  goal_tolerance_m=0.35, collision=False, timeout=False, nav2_success=True)
    result = measured_live_outcome(**values)
    assert result["navigation_success"]
    assert result["instruction_completion"] is None
    assert result["wrong_goal"] is None
    assert result["distance_travelled_m"] == 5.0
    assert not measured_live_outcome(**{**values, "goal": (10, 10)})["navigation_success"]
    assert not measured_live_outcome(**{**values, "collision": True})["navigation_success"]
    assert not measured_live_outcome(**{**values, "timeout": True})["navigation_success"]
    missing = measured_live_outcome(**{**values, "positions": ()})
    assert not missing["navigation_success"]
    assert missing["distance_travelled_m"] is None
    assert missing["goal_reached"] is None


def test_research2_monitor_started_bootstraps_without_claiming_a_prediction() -> None:
    state = research2_ready_to_state(
        {"event_type": "monitor_started", "engineering_smoke": "false"}, 99
    )
    assert state.level is MonitorLevel.NOMINAL
    assert state.failure_probability == 0.0
    assert state.reason_codes == ("monitor_ready_pre_mission", "no_prediction_yet")
