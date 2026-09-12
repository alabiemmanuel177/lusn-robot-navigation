from language_nav.contracts import Pose2D, RouteEligibility, SemanticObservationContract
from language_nav.grounding import SemanticRouteProposal, build_semantic_route_candidates


def _observation(entity_id: str, category: str, region_id: str, confidence: float):
    return SemanticObservationContract(
        "semantic-observation/v1",
        "obs-" + entity_id,
        entity_id,
        category,
        {"color": "red"} if category == "chair" else {},
        Pose2D(1, 2),
        (0.1, 0.0, 0.0, 0.1),
        confidence,
        10,
        "map",
        "landmark-bridge",
        1,
        region_id,
    )


def test_route_candidates_require_nav2_and_join_anchor_and_terminal_evidence() -> None:
    proposal = SemanticRouteProposal("route-a", "junction-a", "terminal-a", 4.0, 0.1, 0.9, True, 2, "left")
    observations = (
        _observation("chair-low", "chair", "junction-a", 0.6),
        _observation("chair-high", "chair", "junction-a", 0.9),
        _observation("lab", "laboratory_entrance", "terminal-a", 0.8),
    )
    nav2 = RouteEligibility("route-a", True, True, 3.5, 0.2, "path available")
    candidate = build_semantic_route_candidates(observations, (proposal,), (nav2,))[0]
    assert candidate.anchor_entity_id == "chair-high"
    assert candidate.terminal_category == "laboratory_entrance"
    assert candidate.nav2_eligible and candidate.traversability_observed
    assert candidate.distance == 3.5
    assert candidate.risk == 0.2


def test_missing_eligibility_fails_closed_even_when_landmark_is_visible() -> None:
    proposal = SemanticRouteProposal("route-a", "junction-a", "terminal-a", 4.0, 0.1, 0.9, True, 2, "left")
    candidate = build_semantic_route_candidates(
        (_observation("chair", "chair", "junction-a", 0.9),), (proposal,), ()
    )[0]
    assert not candidate.nav2_eligible
    assert not candidate.traversability_observed
    assert candidate.risk == 1.0
