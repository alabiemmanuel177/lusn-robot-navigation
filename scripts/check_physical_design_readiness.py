#!/usr/bin/env python3
"""Inventory unresolved design choices and evidence; never approve a campaign."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import yaml

CHOICES = (
    "analysis_proposals.primary_contrast", "analysis_proposals.multiplicity_policy",
    "analysis_proposals.confirmatory_inference_method", "power_inputs_requiring_freeze.target_effect",
    "power_inputs_requiring_freeze.target_power", "power_inputs_requiring_freeze.alpha",
    "simulator_seed.confirmatory_seed_list", "replication.confirmatory_replications",
    "power_inputs_requiring_freeze.repetitions_per_world",
)
NUISANCE = ("power_inputs_requiring_freeze.baseline_completion",
            "power_inputs_requiring_freeze.paired_discordance",
            "power_inputs_requiring_freeze.world_intracluster_correlation")


def value_at(config, path):
    value = config
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def check(config):
    if config.get("schema_version") != "research3-physical-experiment-design-draft/v2":
        raise ValueError("supported physical design draft required")
    missing_choices = [path for path in CHOICES if value_at(config, path) is None]
    missing_nuisance = [path for path in NUISANCE if value_at(config, path) is None]
    invalid = []
    for path in CHOICES + NUISANCE:
        value = value_at(config, path)
        if value is None:
            continue
        if path.endswith("confirmatory_seed_list"):
            valid = (isinstance(value, list) and len(value) > 0
                     and all(type(seed) is int and 1 <= seed <= 2**32 - 1 for seed in value)
                     and len(set(value)) == len(value))
        elif path.endswith(("confirmatory_replications", "repetitions_per_world")):
            valid = type(value) is int and value > 0
        elif path.startswith("analysis_proposals."):
            valid = isinstance(value, str) and bool(value.strip())
            if path.endswith("primary_contrast"):
                valid &= value in config.get("analysis_proposals", {}).get("candidate_contrasts", [])
        else:
            valid = type(value) in (int, float) and math.isfinite(value)
            if valid:
                if path.endswith("world_intracluster_correlation"):
                    valid = -1 <= value <= 1
                elif path in NUISANCE:
                    valid = 0 <= value <= 1
                else:
                    valid = 0 < value < 1
        if not valid:
            invalid.append(path)
    seeds = value_at(config, "simulator_seed.confirmatory_seed_list")
    if isinstance(seeds, list) and seeds and "simulator_seed.confirmatory_seed_list" not in invalid:
        for path in ("replication.confirmatory_replications", "power_inputs_requiring_freeze.repetitions_per_world"):
            count = value_at(config, path)
            if count is not None and count != len(seeds):
                invalid.append(path + ":seed_count_mismatch")
    return {"schema_version": "research3-design-prerequisite-inventory/v1",
            "status": "draft_not_authorized", "campaign_authorized": False,
            "scientific_design_approved": False, "human_review_is_only_remaining_gate": False,
            "missing_scientific_choices": missing_choices,
            "missing_nonprotected_nuisance_estimates": missing_nuisance,
            "invalid_or_inconsistent_values": invalid,
            "supplied_design_fields_valid_and_complete": not (missing_choices or missing_nuisance or invalid),
            "independent_evidence_gates_not_verified_by_this_tool": [
                "physical_inspection_completion_and_post_completion_fresh_observation",
                "localization_and_point_goal_characterization_under_frozen_configuration",
                "nonprotected_condition_and_seed_validation",
                "new_world_detector_coverage_individual_visual_qa_and_genuine_human_labels",
                "calibration_fit_and_freeze_without_protected_labels",
                "scientific_design_approval_and_protocol_freeze",
                "resource_safe_campaign_execution_and_independent_outcome_audit",
                "separate_heldout_evaluator_access_control_and_authorization",
                "complete_source_asset_model_environment_evidence_release_inventory"],
            "limitations": ["Supplied numbers are not an approval, power calculation or valid nuisance estimate.",
                            "This checker does not inspect held-out content, execute experiments or change draft status.",
                            "Evidence gates are prerequisites, not assertions that no partial evidence currently exists."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] /
                        "configs/physical_experiment_design_draft_v2.yaml")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    raw = args.config.read_bytes()
    report = check(yaml.safe_load(raw))
    report["input_sha256"] = hashlib.sha256(raw).hexdigest()
    if args.output:
        with args.output.open("x") as stream:
            json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
