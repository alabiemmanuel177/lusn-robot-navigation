#!/usr/bin/env python3
"""Audit v2 live summaries against retained raw measurements, retaining failures."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from language_nav.live import path_length, terminal_identity_outcome, measured_live_outcome, validate_trajectory_evidence
from language_nav.evaluation.ordered import score_ordered_instruction


def audit_summary(path):
    row = json.loads(path.read_text())
    if row.get("schema_version") not in {"research3-live-summary/v2", "research3-live-summary/v3"}:
        raise ValueError(f"{path}: v2 or v3 measurements required")
    if row.get("protected_test_routes_used") is not False or row.get("partition") not in {"development", "validation"}:
        raise ValueError("only non-protected measured episodes are accepted")
    if row.get("infrastructure_failure"):
        raise ValueError(f"{path}: retained infrastructure failure requires audit; do not drop or retry")
    evidence_path = path.parent / "measurements.json"
    raw = evidence_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != row.get("measurements_sha256"):
        raise ValueError(f"{path}: measurements checksum mismatch")
    evidence = json.loads(raw)
    if evidence["run_id"] != row["run_id"]:
        raise ValueError("evidence identity mismatch")
    positions = evidence["ground_truth_positions"]
    trajectory_valid = True
    if row["schema_version"] == "research3-live-summary/v3":
        if evidence.get("schema_version") != "research3-live-measurements/v2":
            raise ValueError("timestamped measurement schema required")
        for key in ("episode_started_at_ns", "episode_ended_at_ns", "timeout"):
            if row[key] != evidence[key]:
                raise ValueError(f"episode evidence mismatch: {key}")
        quality = validate_trajectory_evidence(positions, evidence["ground_truth_timestamps_ns"],
                                              evidence["episode_started_at_ns"], evidence["episode_ended_at_ns"])
        if quality != row["trajectory_quality"]:
            raise ValueError("trajectory quality mismatch")
        trajectory_valid = quality["valid"]
        if evidence["commanded_goal"] is None:
            if evidence["nav2_reported_success"] is not False or evidence.get("selected_route_id") is not None:
                raise ValueError("unconfirmed commanded goal cannot support navigation success")
            navigation = dict(navigation_success=False, nav2_reported_success=False,
                              goal_error_m=None, goal_reached=None,
                              goal_tolerance_m=evidence["goal_tolerance_m"])
        else:
            navigation = measured_live_outcome(
                positions=positions, distance_m=path_length(positions), goal=evidence["commanded_goal"],
                goal_tolerance_m=evidence["goal_tolerance_m"], collision=bool(evidence["collision_count"]),
                timeout=evidence["timeout"], nav2_success=evidence["nav2_reported_success"])
        navigation["navigation_success"] &= trajectory_valid
        for key in ("navigation_success", "nav2_reported_success", "goal_error_m", "goal_reached", "goal_tolerance_m"):
            if row[key] != navigation[key]:
                raise ValueError(f"navigation measurement mismatch: {key}")
    if len(positions) != row["ground_truth_samples"]:
        raise ValueError("ground-truth sample count mismatch")
    if positions and not math.isclose(path_length(positions), row["distance_travelled_m"], abs_tol=1e-7):
        raise ValueError("ground-truth path length mismatch")
    if bool(evidence["collision_count"]) != row["collision"]:
        raise ValueError("collision evidence mismatch")
    if len(evidence["predictions"]) != row["episode_prediction_count"]:
        raise ValueError("prediction count mismatch")
    for prediction in evidence["predictions"]:
        if not row["episode_started_at_ns"] <= prediction["observed_at_ns"] <= row["episode_ended_at_ns"]:
            raise ValueError("prediction outside episode window")
    terminal = terminal_identity_outcome(positions, evidence["terminal_ground_truth"],
                                         evidence["expected_terminal_region_id"], row["terminal_radius_m"])
    if any(row[key] != value for key, value in terminal.items()):
        raise ValueError("terminal identity score mismatch")
    if evidence.get("ordered_geometry") is not None:
        ordered = score_ordered_instruction(
            positions, evidence["ordered_geometry"], terminal_identity_correct=row["terminal_identity_correct"],
            collision=row["collision"], timeout=row["timeout"],
        )
        completion = ordered["instruction_completion"] if trajectory_valid else None
        if row.get("ordered_instruction_score") != ordered or row["instruction_completion"] != completion:
            raise ValueError("ordered instruction score mismatch")
        if row.get("semantic_outcome_measured") is not (completion is not None):
            raise ValueError("semantic measurement flag mismatch")
    elif (row.get("instruction_completion") is not None
          or row.get("semantic_outcome_measured") is True
          or row.get("ordered_instruction_score") is not None):
        raise ValueError("semantic completion requires ordered geometry evidence")
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [audit_summary(path) for path in args.summary]
    if len({r["run_id"] for r in rows}) != len(rows):
        raise ValueError("duplicate run identity")
    report = {
        "schema_version": "research3-measured-live-analysis/v1",
        "evidence_scope": "development_validation_engineering_pilots",
        "episodes": len(rows),
        "navigation_successes": sum(r["navigation_success"] for r in rows),
        "collisions": sum(r["collision"] for r in rows),
        "timeouts": sum(r["timeout"] for r in rows),
        "terminal_identity_correct": sum(r["terminal_identity_correct"] is True for r in rows),
        "terminal_identity_unknown": sum(r["terminal_identity_correct"] is None for r in rows),
        "full_instruction_completion_measured": all(r.get("semantic_outcome_measured") is True for r in rows),
        "inputs": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                   for p in args.summary],
    }
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
