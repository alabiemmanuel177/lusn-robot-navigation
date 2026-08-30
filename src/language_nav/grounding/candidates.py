from __future__ import annotations

from language_nav.models import GroundingCandidate, ParseAlternative, SemanticEntity


def generate_candidates(
    hypothesis: ParseAlternative,
    entities: list[SemanticEntity],
    *,
    top_k: int = 3,
) -> list[GroundingCandidate]:
    """Score observed entities and retain a language-only predicted candidate."""
    if top_k < 1:
        raise ValueError("top_k must be positive")

    scored: list[GroundingCandidate] = []
    for entity in entities:
        category_score = 1.0 if entity.category == hypothesis.target else 0.05
        if hypothesis.attributes:
            matches = sum(entity.attributes.get(key) == value for key, value in hypothesis.attributes.items())
            attribute_score = matches / len(hypothesis.attributes)
        else:
            attribute_score = 1.0
        compatibility = (0.65 * category_score + 0.35 * attribute_score) * entity.confidence
        if compatibility >= 0.10:
            scored.append(
                GroundingCandidate(
                    entity_id=entity.entity_id,
                    region_id=entity.region_id,
                    prior=compatibility,
                    predicted=not entity.observed,
                    compatibility=compatibility,
                )
            )

    predicted_score = max(0.15, hypothesis.epistemic_strength * 0.45)
    predicted = GroundingCandidate(
        entity_id=f"predicted:{hypothesis.target}",
        region_id="unobserved",
        prior=predicted_score,
        predicted=True,
        compatibility=predicted_score,
    )
    # A language-only claim must remain explicit until evidence rejects it. If it
    # silently falls out of top-K, missing-evidence contradiction is impossible.
    observed_slots = max(0, top_k - 1)
    selected = sorted(scored, key=lambda candidate: (-candidate.prior, candidate.entity_id))[:observed_slots]
    selected.append(predicted)
    total = sum(candidate.prior for candidate in selected)
    return [
        GroundingCandidate(
            entity_id=candidate.entity_id,
            region_id=candidate.region_id,
            prior=candidate.prior / total,
            predicted=candidate.predicted,
            compatibility=candidate.compatibility,
        )
        for candidate in selected
    ]
