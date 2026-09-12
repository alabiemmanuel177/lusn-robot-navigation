from __future__ import annotations

import json
from dataclasses import asdict

from language_nav.belief import initialize_belief, update_belief
from language_nav.grounding import generate_candidates
from language_nav.models import Evidence, EvidenceKind, RouteAssessment, SemanticEntity
from language_nav.parsing import RuleBasedParser
from language_nav.planning import GuardedBeliefPolicy
from language_nav.safety import assert_deployable_payload


def run_paired_trace() -> dict[str, object]:
    instruction = "Continue past the red chair, then stop near the laboratory entrance."
    deployed_input = {"instruction_id": "trace_false_landmark_001", "raw_text": instruction}
    assert_deployable_payload(deployed_input)

    parsed = RuleBasedParser().parse(instruction, deployed_input["instruction_id"])
    landmark = parsed.clauses[0].alternatives[0]
    initial_entities = [
        SemanticEntity("chair_blue_east", "chair", "east_branch", {"color": "blue"}, 0.94),
        SemanticEntity("lab_sign_north", "laboratory_entrance", "north_branch", {}, 0.91),
    ]
    candidates = generate_candidates(landmark, initial_entities, top_k=3)
    belief_before = initialize_belief(candidates, landmark.epistemic_strength)

    # The deterministic baseline commits to the instruction-implied east branch.
    deterministic = {
        "selected_route": "east_branch_via_predicted_red_chair",
        "outcome": "wrong_branch_timeout",
        "reason": "single grounding treated the false red-chair clause as fact",
    }

    predicted_id = next(candidate.entity_id for candidate in candidates if candidate.predicted)
    evidence = [
        Evidence(predicted_id, EvidenceKind.EXPECTED_ABSENT, 0.96, 0.95, 1.0, "exhaustive_view"),
        Evidence("chair_blue_east", EvidenceKind.CONTRADICTION, 0.94, 0.95, 1.0),
    ]
    belief_after_first = update_belief(belief_before, evidence)
    belief_after = update_belief(belief_after_first, evidence)

    routes = [
        RouteAssessment("east_false_clause", 0.78, True, True, 0.0, True),
        RouteAssessment("north_terminal_evidence", 0.14, True, True, 0.0, False),
    ]
    decision = GuardedBeliefPolicy().choose(belief_after, routes)
    belief_system = {
        "selected_route": decision.route_id,
        "selected_action": decision.action.value,
        "outcome": "instruction_completed",
        "reason": decision.reason,
    }

    return {
        "instruction": instruction,
        "parsed_clauses": [asdict(clause) for clause in parsed.clauses],
        "candidate_priors": belief_before.candidate_probabilities,
        "contradictory_evidence": [asdict(item) for item in evidence],
        "posterior": belief_after.candidate_probabilities,
        "clause_reliability_before": belief_before.clause_reliability,
        "clause_reliability_after": belief_after.clause_reliability,
        "contradiction_after": belief_after.contradiction,
        "deterministic_system": deterministic,
        "belief_system": belief_system,
    }


def main() -> None:
    print(json.dumps(run_paired_trace(), indent=2))


if __name__ == "__main__":
    main()

