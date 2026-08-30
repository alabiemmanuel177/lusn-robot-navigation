from __future__ import annotations

import math

from language_nav.models import BeliefState, Evidence, EvidenceKind, GroundingCandidate


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _logit(probability: float) -> float:
    probability = _clamp(probability, 1e-6, 1.0 - 1e-6)
    return math.log(probability / (1.0 - probability))


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def initialize_belief(candidates: list[GroundingCandidate], clause_reliability: float = 0.85) -> BeliefState:
    if not candidates:
        raise ValueError("at least one grounding candidate is required")
    total = sum(candidate.prior for candidate in candidates)
    if not math.isfinite(total) or total <= 0:
        raise ValueError("candidate priors must have a positive finite sum")
    probabilities = {candidate.entity_id: candidate.prior / total for candidate in candidates}
    return BeliefState(probabilities, _clamp(clause_reliability, 0.0, 1.0), 0.0)


def update_belief(
    state: BeliefState,
    evidence: list[Evidence],
    *,
    max_log_odds_contribution: float = 1.25,
) -> BeliefState:
    """Apply capped evidence in log-odds space, then normalize candidates."""
    logits = {candidate_id: _logit(probability) for candidate_id, probability in state.candidate_probabilities.items()}
    reliability_logit = _logit(state.clause_reliability)
    contradiction_mass = 0.0

    for item in evidence:
        if item.candidate_id not in logits:
            continue
        confidence = _clamp(item.semantic_confidence, 0.0, 1.0)
        coverage = _clamp(item.observation_coverage, 0.0, 1.0)
        compatibility = _clamp(item.compatibility, 0.0, 1.0)
        magnitude = min(max_log_odds_contribution, 1.5 * confidence * coverage * compatibility)
        if item.kind is EvidenceKind.SUPPORT:
            logits[item.candidate_id] += magnitude
            if item.affects_clause_reliability:
                reliability_logit += 0.35 * magnitude
        else:
            logits[item.candidate_id] -= magnitude
            if item.affects_clause_reliability:
                reliability_logit -= 0.75 * magnitude
                contradiction_mass += magnitude / max_log_odds_contribution

    raw = {candidate_id: _sigmoid(value) for candidate_id, value in logits.items()}
    total = sum(raw.values())
    normalized = {candidate_id: value / total for candidate_id, value in raw.items()}
    contradiction = _clamp(0.55 * state.contradiction + 0.45 * min(1.0, contradiction_mass), 0.0, 1.0)
    return BeliefState(
        candidate_probabilities=normalized,
        clause_reliability=_clamp(_sigmoid(reliability_logit), 0.0, 1.0),
        contradiction=contradiction,
        update_index=state.update_index + 1,
    )
