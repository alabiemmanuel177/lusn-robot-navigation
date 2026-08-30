from __future__ import annotations

EVALUATOR_ONLY_FIELDS = frozenset(
    {
        "corruption_manifest",
        "corruption_type",
        "correct_grounding",
        "oracle_goal_pose",
        "oracle_route",
        "future_observations",
        "intended_terminal_region",
        "evaluator_label",
    }
)


def assert_deployable_payload(payload: dict[str, object]) -> None:
    leaked = sorted(EVALUATOR_ONLY_FIELDS.intersection(payload))
    if leaked:
        raise ValueError(f"evaluator-only fields reached deployed input: {', '.join(leaked)}")

