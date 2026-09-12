#!/usr/bin/env python3
"""Audit retained physical development pilots; never infer comparative effects."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
audit_summary = runpy.run_path(str(ROOT / "scripts/analyze_measured_live.py"))["audit_summary"]
DEFAULT_EPISODES = tuple(ROOT / "reports/physical_live_episodes" /
                         f"r3-stage1-physical-dev10-v{i}" for i in (1, 2, 3))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(episodes):
    rows = []
    seen = set()
    for directory in episodes:
        directory = Path(directory)
        request = json.loads((directory / "request.json").read_text())
        if request.get("partition") not in {"development", "validation"} or request.get("protected_test_routes_used") is not False:
            raise ValueError("only explicitly non-protected development/validation pilots accepted")
        summary = audit_summary(directory / "summary.json")
        if summary["run_id"] != request["run_id"] or summary["partition"] != request["partition"]:
            raise ValueError("request/summary identity mismatch")
        if summary["run_id"] in seen:
            raise ValueError("duplicate run identity")
        seen.add(summary["run_id"])
        row = {key: summary.get(key) for key in (
            "run_id", "system_id", "variant_id", "partition", "route_id",
            "navigation_success", "nav2_reported_success", "goal_reached", "goal_error_m",
            "goal_tolerance_m", "instruction_completion", "terminal_identity_correct",
            "collision", "collision_count", "timeout", "distance_travelled_m", "trajectory_quality")}
        row["ordered_instruction_score"] = summary.get("ordered_instruction_score")
        row["inputs"] = {name: {"path": str(directory / name), "sha256": digest(directory / name)}
                         for name in ("request.json", "capture.json", "measurements.json", "summary.json")}
        row["source_revision"] = request.get("source_revision")
        row["source_sha256"] = request.get("source_sha256", {})
        rows.append(row)
    if not rows:
        raise ValueError("at least one pilot required")
    fields = ("navigation_success", "goal_reached", "instruction_completion",
              "terminal_identity_correct", "collision", "timeout")
    counts = {key: {"true": sum(r[key] is True for r in rows),
                    "false": sum(r[key] is False for r in rows),
                    "unknown": sum(r[key] is None for r in rows)} for key in fields}
    return {"schema_version": "research3-physical-pilot-analysis/v1",
            "evidence_scope": "unpaired_noncomparative_development_validation_engineering",
            "protected_test_routes_used": False, "episodes": rows, "counts": counts,
            "comparative_effect_estimates": None, "final_research_release": False,
            "limitations": [
                "All supplied failures are retained; counts describe only the supplied pilot inventory.",
                "Pilot iterations can straddle policy, scheduling and detector changes; not paired repetitions.",
                "Navigation point accuracy, ordered completion, terminal identity and collisions are separate endpoints.",
                "No detector accuracy, calibrated confidence, held-out generalization or comparative effect claim.",
                "Source hashes are recorded subsets, not a complete historical execution environment.",
                "Shared-host scheduling does not establish timing-comparable campaign conditions."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode", type=Path, action="append")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.episode or DEFAULT_EPISODES)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(result["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
