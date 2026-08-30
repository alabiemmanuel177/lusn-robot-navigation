from language_nav.models import ActionKind
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


def test_attribute_corruption_misleads_deterministic_but_b6_recovers() -> None:
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
    assert second_view.route_id == "left"
    assert second_view.action is ActionKind.IGNORE
    assert second_view.clause_reliability < 0.35


def test_nav2_ineligibility_cannot_be_overridden() -> None:
    inputs = _inputs(nav2_eligible=False)
    outputs = [variant.decide(inputs) for variant in build_central_variants()]
    assert all(output.action is ActionKind.ABSTAIN for output in outputs)
    assert all(not output.guard_passed for output in outputs)
