#!/usr/bin/env python3
"""Draft scheduled-cohort analysis; consumes outcomes, never launches experiments."""
import argparse
import hashlib
import json
from pathlib import Path

IDENTITY = ("episode_id", "variant_id", "system_id", "partition", "base_instruction_id", "paired_block_index")
METRICS = ("navigation_success", "instruction_completion", "terminal_identity_correct", "collision", "timeout")


def analyze(manifest, outcomes, baseline="B1"):
    if manifest.get("schema_version") != "research3-physical-comparison-plan/v1":
        raise ValueError("unsupported scheduled manifest schema")
    scheduled = manifest.get("episodes", [])
    if not scheduled:
        raise ValueError("nonempty scheduled manifest required")
    index, blocks, variant_worlds, world_partitions = {}, set(), {}, {}
    for row in scheduled:
        if any(key not in row for key in IDENTITY):
            raise ValueError("missing scheduled identity")
        if (any(not isinstance(row[key], str) or not row[key] for key in IDENTITY[:-1])
                or type(row["paired_block_index"]) is not int or row["paired_block_index"] < 0):
            raise ValueError("invalid scheduled identity types")
        if row["partition"] not in {"development", "validation"}:
            raise ValueError("this draft analyzer does not accept held-out outcomes")
        world = (row["partition"], row["base_instruction_id"])
        if variant_worlds.setdefault(row["variant_id"], world) != world:
            raise ValueError("variant/base identity mismatch across scheduled slots")
        if world_partitions.setdefault(row["base_instruction_id"], row["partition"]) != row["partition"]:
            raise ValueError("world partition mismatch across scheduled slots")
        key = (row["partition"], row["paired_block_index"], row["system_id"])
        if row["episode_id"] in index or key in blocks:
            raise ValueError("duplicate scheduled episode or block-system")
        index[row["episode_id"]] = row
        blocks.add(key)
    by_id = {}
    for outcome in outcomes:
        if outcome.get("schema_version") != "research3-physical-campaign-outcome/v1":
            raise ValueError("unsupported outcome schema")
        episode_id = outcome.get("episode_id")
        if episode_id not in index or episode_id in by_id:
            raise ValueError("unscheduled or duplicate outcome")
        if any(outcome.get(key) != index[episode_id][key] or type(outcome.get(key)) is not type(index[episode_id][key]) for key in IDENTITY):
            raise ValueError("outcome identity mismatch")
        for key in ("condition", "base_instruction_id"):
            if key in index[episode_id] and outcome.get(key) != index[episode_id][key]:
                raise ValueError(f"outcome identity mismatch: {key}")
        for key in ("attempted", "dispatched", "infrastructure_failure"):
            if type(outcome.get(key)) is not bool:
                raise ValueError("explicit boolean lifecycle fields required")
        if outcome["dispatched"] and not outcome["attempted"]:
            raise ValueError("dispatch requires an attempt")
        if outcome["infrastructure_failure"] and not outcome["attempted"]:
            raise ValueError("infrastructure failure requires an attempt")
        for metric in METRICS:
            if metric not in outcome or (outcome[metric] is not None and type(outcome[metric]) is not bool):
                raise ValueError("explicit boolean/null outcome endpoints required")
        if not outcome["dispatched"] and any(outcome[key] is not None for key in METRICS):
            raise ValueError("undispatched episode cannot supply measured endpoints")
        row = dict(outcome)
        row["reported_instruction_completion"] = outcome["instruction_completion"]
        row["reported_navigation_success"] = outcome["navigation_success"]
        failed = outcome["collision"] is True or outcome["timeout"] is True
        if failed:
            row["instruction_completion"] = row["navigation_success"] = False
        else:
            if (outcome["infrastructure_failure"] or outcome["terminal_identity_correct"] is None
                    or outcome["collision"] is None or outcome["timeout"] is None):
                row["instruction_completion"] = None
            elif outcome["terminal_identity_correct"] is False:
                row["instruction_completion"] = False
            if outcome["infrastructure_failure"] or outcome["collision"] is None or outcome["timeout"] is None:
                row["navigation_success"] = None
        by_id[episode_id] = row
    rows = [{**s, "outcome": by_id.get(s["episode_id"])} for s in scheduled]
    summaries = {}
    for system in sorted({s["system_id"] for s in scheduled}):
        cohort = [r["outcome"] for r in rows if r["system_id"] == system]
        summaries[system] = {"scheduled": len(cohort), "missing_records": sum(r is None for r in cohort),
                             **{key: sum(r is not None and r[key] for r in cohort)
                                for key in ("attempted", "dispatched", "infrastructure_failure")},
                             "endpoints": {m: {"true": sum(r is not None and r[m] is True for r in cohort),
                                               "false": sum(r is not None and r[m] is False for r in cohort),
                                               "unknown": sum(r is None or r[m] is None for r in cohort)}
                                           for m in METRICS}}
    comparisons, sensitivity = [], []
    if baseline not in summaries:
        raise ValueError("baseline absent from scheduled manifest")
    for system in sorted(set(summaries) - {baseline}):
        a = {(r["partition"], r["paired_block_index"]): r for r in rows if r["system_id"] == baseline}
        b = {(r["partition"], r["paired_block_index"]): r for r in rows if r["system_id"] == system}
        common = sorted(a.keys() & b.keys())
        for key in common:
            if (a[key]["variant_id"] != b[key]["variant_id"]
                    or a[key]["base_instruction_id"] != b[key]["base_instruction_id"]):
                raise ValueError("paired block variant mismatch")
        for metric in METRICS:
            differences = []
            for key in common:
                left, right = a[key]["outcome"], b[key]["outcome"]
                if left is not None and right is not None and left[metric] is not None and right[metric] is not None:
                    differences.append(int(right[metric]) - int(left[metric]))
            comparisons.append({"baseline": baseline, "system": system, "endpoint": metric,
                                "scheduled_pairs": len(common), "complete_pairs": len(differences),
                                "incomplete_pairs": len(common) - len(differences),
                                "unmatched_scheduled_blocks": len(a.keys() ^ b.keys()),
                                "mean_paired_difference": sum(differences) / len(differences) if differences else None,
                                "direction": "system minus baseline; lower is better only for collision/timeout"})
        world_slots = {}
        for key in common:
            world = (key[0], a[key]["base_instruction_id"])
            left, right = a[key]["outcome"], b[key]["outcome"]
            lv = None if left is None else left["instruction_completion"]
            rv = None if right is None else right["instruction_completion"]
            lo = (0 if rv is None else int(rv)) - (1 if lv is None else int(lv))
            hi = (1 if rv is None else int(rv)) - (0 if lv is None else int(lv))
            world_slots.setdefault(world, []).append((lo, hi, int(lv is None) + int(rv is None)))
        world_bounds = [{"partition": world[0], "base_instruction_id": world[1],
                         "scheduled_pairs": len(slots), "unknown_arm_values": sum(s[2] for s in slots),
                         "lower_mean_contrast": sum(s[0] for s in slots) / len(slots),
                         "upper_mean_contrast": sum(s[1] for s in slots) / len(slots)}
                        for world, slots in sorted(world_slots.items())]
        sensitivity.append({"baseline": baseline, "system": system, "endpoint": "instruction_completion",
                            "number_of_worlds": len(world_bounds), "scheduled_pairs": len(common),
                            "unmatched_scheduled_blocks_excluded": len(a.keys() ^ b.keys()),
                            "lower_mean_contrast": sum(w["lower_mean_contrast"] for w in world_bounds) / len(world_bounds) if world_bounds else None,
                            "upper_mean_contrast": sum(w["upper_mean_contrast"] for w in world_bounds) / len(world_bounds) if world_bounds else None,
                            "worlds": world_bounds, "confidence_interval": False,
                            "interpretation": "system minus baseline; fixed observed outcomes, unknown arms bounded [0,1]; equal slot weights within world, equal world weights; not a predeclared primary contrast"})
    return {"schema_version": "research3-physical-campaign-analysis/v1", "status": "draft_not_final",
            "final_research_release": False, "independent_raw_evidence_audit_performed": False,
            "systems": summaries, "paired_descriptive_differences": comparisons,
            "world_equal_weight_sensitivity_bounds": sensitivity, "episodes": rows,
            "limitations": ["Supplied outcome records are not independently re-audited against trajectories or contact evidence.",
                            "Complete-pair descriptive differences are not causal or confirmatory findings; missingness is retained.",
                            "No uncertainty estimates or repeated-seed independence assumptions are manufactured.",
                            "Protocol, detector calibration, live safety and release gates require separate verification."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--outcomes", type=Path, required=True, help="JSON list of outcome records")
    parser.add_argument("--baseline", default="B1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw_manifest, raw_outcomes = args.manifest.read_bytes(), args.outcomes.read_bytes()
    result = analyze(json.loads(raw_manifest), json.loads(raw_outcomes), args.baseline)
    result["input_sha256"] = {"manifest": hashlib.sha256(raw_manifest).hexdigest(), "outcomes": hashlib.sha256(raw_outcomes).hexdigest()}
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
