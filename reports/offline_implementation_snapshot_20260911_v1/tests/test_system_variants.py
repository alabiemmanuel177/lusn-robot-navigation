from language_nav.models import ActionKind
from dataclasses import replace
from itertools import permutations
import pytest
from language_nav.systems import B6ContradictionAware, SemanticRouteCandidate, SystemInput, build_central_variants


def _inputs(color: str = "red", nav2_eligible: bool = True) -> SystemInput:
    return SystemInput(
        "i-1",
        f"Go through the corridor, then continue past the {color} chair, then stop near the laboratory entrance.",
        (
            SemanticRouteCandidate("left", "left", "red-chair", "chair", {"color": "red"}, "laboratory_entrance", 0.95, 0.95, 2, 0.1, True, nav2_eligible),
            SemanticRouteCandidate("right", "right", "blue-chair", "chair", {"color": "blue"}, "office_entrance", 0.94, 0.95, 2, 0.1, True, nav2_eligible),
        ),
    )


def test_all_central_variants_run_on_same_deployable_contract() -> None:
    outputs = [variant.decide(_inputs()) for variant in build_central_variants()]
    assert [output.system_id for output in outputs] == ["B1", "B2", "B4", "B5", "B6"]
    assert all(output.guard_passed for output in outputs)
    assert all(output.route_id == "left" for output in outputs)


def test_attribute_corruption_requests_inspection_without_inventing_evidence() -> None:
    outputs = {variant.system_id: variant.decide(_inputs("blue")) for variant in build_central_variants()}
    assert outputs["B2"].route_id == "right"
    assert outputs["B6"].action is ActionKind.INSPECT
    second_view = B6ContradictionAware().decide(
        SystemInput(
            _inputs("blue").instruction_id,
            _inputs("blue").raw_text,
            _inputs("blue").candidates,
            step_index=1,
        )
    )
    assert second_view == outputs["B6"]


def test_nav2_ineligibility_cannot_be_overridden() -> None:
    inputs = _inputs(nav2_eligible=False)
    outputs = [variant.decide(inputs) for variant in build_central_variants()]
    assert all(output.action is ActionKind.ABSTAIN for output in outputs)
    assert all(not output.guard_passed for output in outputs)


def test_four_shared_anchor_routes_remain_distinct_and_order_independent():
    candidates = tuple(replace(_inputs().candidates[0], route_id=f"{side}-{branch}",
                               side=side, branch_index=branch)
                       for side in ("left", "right") for branch in (1, 2))
    text = ("Continue past the red chair, then take the second doorway on the right, "
            "then stop near the laboratory entrance.")
    for ordering in permutations(candidates):
        for variant in build_central_variants()[2:]:
            decision = variant.decide(SystemInput("shared", text, ordering))
            assert decision.route_id == "right-2"
            assert set(decision.candidate_probabilities) == {c.route_id for c in candidates}
            assert sum(decision.candidate_probabilities.values()) == pytest.approx(1.0)


def test_duplicate_route_ids_rejected_and_empty_belief_abstains():
    candidate = _inputs().candidates[0]
    with pytest.raises(ValueError, match="unique route IDs"):
        SystemInput("duplicate", _inputs().raw_text, (candidate, candidate))
    for variant in build_central_variants()[2:]:
        assert variant.decide(SystemInput("empty", _inputs().raw_text, ())).action is ActionKind.ABSTAIN
