import math

from language_nav.grounding import generate_candidates
from language_nav.models import ParseAlternative, SemanticEntity


def test_grounding_retains_top_k_and_predicted_hypothesis() -> None:
    hypothesis = ParseAlternative(1.0, "continue", "chair", "past", {"color": "red"})
    entities = [
        SemanticEntity("red", "chair", "r1", {"color": "red"}, 0.9),
        SemanticEntity("blue", "chair", "r2", {"color": "blue"}, 0.9),
    ]
    candidates = generate_candidates(hypothesis, entities, top_k=3)
    assert len(candidates) == 3
    assert any(candidate.predicted for candidate in candidates)
    assert candidates[0].entity_id == "red"
    assert math.isclose(sum(candidate.prior for candidate in candidates), 1.0)

