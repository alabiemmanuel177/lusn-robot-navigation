from __future__ import annotations

from dataclasses import dataclass

from language_nav.benchmark.corpus import RouteInstruction
from language_nav.benchmark.corruptions import CorruptionCondition, GeneratedVariant


@dataclass(frozen=True)
class GroundingAnnotation:
    schema_version: str
    variant_id: str
    clause_index: int
    intended_entity_id: str
    acceptable_entity_ids: tuple[str, ...]
    ambiguity_flag: bool
    reviewer_status: str
    evaluator_only: bool = True


def annotate_grounding(route: RouteInstruction, generated: GeneratedVariant) -> GroundingAnnotation:
    ambiguous = generated.evaluator_manifest.condition is CorruptionCondition.AMBIGUOUS_REFERENCE
    acceptable = list(route.correct_groundings)
    if ambiguous:
        acceptable.append(f"{route.route_id}-ambiguous-chair")
    return GroundingAnnotation(
        schema_version="grounding-annotation/v1",
        variant_id=generated.deployed.variant_id,
        clause_index=1,
        intended_entity_id=route.anchor_entity_id,
        acceptable_entity_ids=tuple(acceptable),
        ambiguity_flag=ambiguous,
        reviewer_status="requires_second_reviewer",
    )

