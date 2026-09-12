import copy
from pathlib import Path
import runpy

import pytest

MODULE = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/analyze_physical_campaign.py"))


def fixtures():
    scheduled = [{"episode_id": f"v{block}-{system}", "variant_id": f"v{block}",
                  "system_id": system, "partition": "development", "base_instruction_id": f"world{block}",
                  "paired_block_index": block}
                 for block in range(2) for system in ("B1", "B6")]
    outcomes = [{**row, "schema_version": "research3-physical-campaign-outcome/v1",
                 "attempted": True, "dispatched": True, "infrastructure_failure": False,
                 "navigation_success": True, "instruction_completion": True,
                 "terminal_identity_correct": True, "collision": False, "timeout": False}
                for row in scheduled]
    return {"schema_version": "research3-physical-comparison-plan/v1", "episodes": scheduled}, outcomes


def test_complete_pairs_and_missingness_remain_separate():
    plan, outcomes = fixtures()
    outcomes[1]["instruction_completion"] = False
    report = MODULE["analyze"](plan, outcomes[:3])
    row = next(r for r in report["paired_descriptive_differences"] if r["endpoint"] == "instruction_completion")
    assert row["complete_pairs"] == row["incomplete_pairs"] == 1
    assert row["mean_paired_difference"] == -1
    assert report["systems"]["B6"]["scheduled"] == 2
    assert report["systems"]["B6"]["missing_records"] == 1
    assert report["systems"]["B6"]["endpoints"]["instruction_completion"]["unknown"] == 1
    assert report["status"] == "draft_not_final"
    assert not report["final_research_release"]


@pytest.mark.parametrize("failure", ["collision", "timeout"])
def test_known_failure_dominates_unknown_terminal_and_infrastructure(failure):
    plan, outcomes = fixtures()
    outcomes[0].update(terminal_identity_correct=None, instruction_completion=None,
                       infrastructure_failure=True)
    outcomes[0][failure] = True
    report = MODULE["analyze"](plan, outcomes)
    row = report["episodes"][0]["outcome"]
    assert row["instruction_completion"] is False
    assert row["navigation_success"] is False
    assert row["terminal_identity_correct"] is None
    assert report["systems"]["B1"]["infrastructure_failure"] == 1
    assert outcomes[0]["instruction_completion"] is None  # input remains untouched


def test_attempted_undispatched_and_absent_records_not_success_or_failure():
    plan, outcomes = fixtures()
    row = outcomes[0]
    row.update(dispatched=False, infrastructure_failure=True)
    row.update({m: None for m in MODULE["METRICS"]})
    report = MODULE["analyze"](plan, [row])
    assert report["systems"]["B1"]["attempted"] == 1
    assert report["systems"]["B1"]["dispatched"] == 0
    assert report["systems"]["B1"]["missing_records"] == 1
    assert all(r["mean_paired_difference"] is None for r in report["paired_descriptive_differences"])


@pytest.mark.parametrize("mutation", [
    lambda p, o: p["episodes"].append(copy.deepcopy(p["episodes"][0])),
    lambda p, o: o.append(copy.deepcopy(o[0])),
    lambda p, o: o[0].update(episode_id="unplanned"),
    lambda p, o: o[0].update(system_id="B2"),
    lambda p, o: o[0].update(attempted=False),
    lambda p, o: o[0].update(collision=0),
    lambda p, o: p["episodes"][0].update(partition="test"),
    lambda p, o: (p["episodes"][1].update(variant_id="different"), o[1].update(variant_id="different")),
])
def test_invalid_identities_lifecycle_endpoints_and_pairing_rejected(mutation):
    plan, outcomes = fixtures()
    mutation(plan, outcomes)
    with pytest.raises(ValueError):
        MODULE["analyze"](plan, outcomes)


def test_missing_collision_observation_prevents_success_claim():
    plan, outcomes = fixtures()
    outcomes[0]["collision"] = None
    row = MODULE["analyze"](plan, outcomes)["episodes"][0]["outcome"]
    assert row["instruction_completion"] is None
    assert row["navigation_success"] is None


def test_scheduled_condition_cannot_be_changed_or_omitted():
    plan, outcomes = fixtures()
    plan["episodes"][0]["condition"] = "truthful_original"
    with pytest.raises(ValueError, match="condition"):
        MODULE["analyze"](plan, outcomes)
    outcomes[0]["condition"] = "truthful_original"
    report = MODULE["analyze"](plan, outcomes)
    assert report["systems"]["B1"]["endpoints"]["collision"] == {"true": 0, "false": 2, "unknown": 0}


def test_world_equal_weight_bounds_include_unknown_arms_without_ci_claim():
    plan, outcomes = fixtures()
    # World 0 has two condition slots, world 1 one. Weight worlds equally,
    # not the three slots equally. World0 contrast=-1; world1 unknown [-1,1].
    for row in outcomes[:2]:
        row["instruction_completion"] = row["system_id"] == "B1"
    for row in list(plan["episodes"][:2]):
        plan["episodes"].append({**row, "episode_id": row["episode_id"] + "-extra",
                                 "variant_id": "extra-condition", "paired_block_index": 2})
    for row in outcomes[:2]:
        outcomes.append({**row, "episode_id": row["episode_id"] + "-extra",
                         "variant_id": "extra-condition", "paired_block_index": 2})
    report = MODULE["analyze"](plan, outcomes[:2] + outcomes[4:])
    bound = report["world_equal_weight_sensitivity_bounds"][0]
    assert bound["number_of_worlds"] == 2
    assert bound["scheduled_pairs"] == 3
    assert bound["lower_mean_contrast"] == -1
    assert bound["upper_mean_contrast"] == 0  # slot weighting would incorrectly give -1/3
    assert bound["worlds"][1]["unknown_arm_values"] == 2
    assert not bound["confidence_interval"]


def test_fully_observed_world_bounds_collapse_to_equal_weight_contrast():
    plan, outcomes = fixtures()
    outcomes[1]["instruction_completion"] = False
    bound = MODULE["analyze"](plan, outcomes)["world_equal_weight_sensitivity_bounds"][0]
    assert bound["lower_mean_contrast"] == bound["upper_mean_contrast"] == -.5


def test_variant_cannot_move_between_worlds_even_when_both_pair_arms_match():
    plan, outcomes = fixtures()
    for row in plan["episodes"][2:]:
        row["variant_id"] = "v0"
    for row in outcomes[2:]:
        row["variant_id"] = "v0"
    with pytest.raises(ValueError, match="variant/base"):
        MODULE["analyze"](plan, outcomes)
