import hashlib
import json
import runpy
from pathlib import Path

import pytest

from language_nav.live import terminal_identity_outcome, measured_live_outcome, validate_trajectory_evidence

audit_summary = runpy.run_path(str(Path(__file__).parents[1] / "scripts/analyze_measured_live.py"))["audit_summary"]


def test_audit_retains_collision_timeout_and_rejects_tampering(tmp_path):
    target = {"entity_id": "lab", "region_id": "terminal", "category": "laboratory_entrance",
              "pose": {"x": 1, "y": 0}}
    evidence = {"run_id": "failure", "ground_truth_positions": [[0, 0], [1, 0]],
                "collision_count": 1, "predictions": [], "terminal_ground_truth": [target],
                "expected_terminal_region_id": "terminal"}
    data = json.dumps(evidence).encode()
    (tmp_path / "measurements.json").write_bytes(data)
    summary = {"schema_version": "research3-live-summary/v2", "run_id": "failure",
               "partition": "development", "protected_test_routes_used": False,
               "measurements_sha256": hashlib.sha256(data).hexdigest(),
               "ground_truth_samples": 2, "distance_travelled_m": 1.0, "collision": True,
               "timeout": True, "episode_prediction_count": 0,
               **terminal_identity_outcome(evidence["ground_truth_positions"], [target], "terminal")}
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(summary))
    assert audit_summary(path)["collision"]
    assert audit_summary(path)["timeout"]
    summary["semantic_outcome_measured"] = True
    path.write_text(json.dumps(summary))
    with pytest.raises(ValueError, match="ordered geometry"):
        audit_summary(path)
    del summary["semantic_outcome_measured"]
    path.write_text(json.dumps(summary))
    (tmp_path / "measurements.json").write_text("{}")
    with pytest.raises(ValueError, match="checksum"):
        audit_summary(path)


def test_v3_audit_recomputes_navigation_and_sampling_validity(tmp_path):
    target = {"entity_id": "lab", "region_id": "terminal", "category": "laboratory_entrance",
              "pose": {"x": .1, "y": 0}}
    positions = [[0, 0], [.1, 0]]
    evidence = {"schema_version": "research3-live-measurements/v2", "run_id": "timed",
                "ground_truth_positions": positions, "ground_truth_timestamps_ns": [1, 100000001],
                "episode_started_at_ns": 1, "episode_ended_at_ns": 200000001,
                "commanded_goal": [.1, 0], "goal_tolerance_m": .35,
                "nav2_reported_success": True, "timeout": False, "collision_count": 0,
                "predictions": [], "terminal_ground_truth": [target], "expected_terminal_region_id": "terminal"}
    data = json.dumps(evidence).encode()
    (tmp_path / "measurements.json").write_bytes(data)
    row = {"schema_version": "research3-live-summary/v3", "run_id": "timed",
           "partition": "development", "protected_test_routes_used": False,
           "measurements_sha256": hashlib.sha256(data).hexdigest(), "episode_prediction_count": 0,
           "episode_started_at_ns": 1, "episode_ended_at_ns": 200000001,
           "trajectory_quality": validate_trajectory_evidence(positions, [1, 100000001], 1, 200000001),
           **measured_live_outcome(positions=positions, distance_m=.1, goal=(.1, 0),
                                  goal_tolerance_m=.35, collision=False, timeout=False, nav2_success=True),
           **terminal_identity_outcome(positions, [target], "terminal")}
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(row))
    assert audit_summary(path)["navigation_success"]
    for key, value in (("goal_error_m", 10), ("navigation_success", False), ("goal_tolerance_m", 20)):
        path.write_text(json.dumps({**row, key: value}))
        with pytest.raises(ValueError, match="navigation measurement"):
            audit_summary(path)
    path.write_text(json.dumps({**row, "trajectory_quality": {"valid": True}}))
    with pytest.raises(ValueError, match="trajectory quality"):
        audit_summary(path)
    evidence.update(commanded_goal=None, nav2_reported_success=False, selected_route_id=None)
    data = json.dumps(evidence).encode()
    (tmp_path / "measurements.json").write_bytes(data)
    row.update(measurements_sha256=hashlib.sha256(data).hexdigest(), navigation_success=False,
               nav2_reported_success=False, goal_error_m=None, goal_reached=None)
    path.write_text(json.dumps(row))
    assert not audit_summary(path)["navigation_success"]
    path.write_text(json.dumps({**row, "navigation_success": True}))
    with pytest.raises(ValueError, match="navigation measurement"):
        audit_summary(path)
