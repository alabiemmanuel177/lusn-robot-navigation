from __future__ import annotations

import hashlib
import random
from dataclasses import asdict, dataclass
from enum import StrEnum

from language_nav.benchmark.corpus import RouteInstruction


class CorruptionCondition(StrEnum):
    TRUTHFUL_ORIGINAL = "truthful_original"
    TRUTHFUL_PARAPHRASE = "truthful_paraphrase"
    AMBIGUOUS_REFERENCE = "ambiguous_reference"
    MISSING_LANDMARK = "missing_landmark"
    ATTRIBUTE_CORRUPTION = "attribute_corruption"
    RELATION_CORRUPTION = "relation_corruption"
    TOPOLOGY_CORRUPTION = "topology_corruption"
    FALSE_INSERTED_CLAUSE = "false_inserted_clause"


@dataclass(frozen=True)
class EditOperation:
    start: int
    end: int
    before: str
    after: str


@dataclass(frozen=True)
class CorruptionManifest:
    schema_version: str
    manifest_id: str
    condition: CorruptionCondition
    seed: int
    source_instruction_id: str
    edits: tuple[EditOperation, ...]
    environment_edits: tuple[dict[str, str], ...]
    intended_effect: str
    evaluator_only: bool = True


@dataclass(frozen=True)
class InstructionVariant:
    variant_id: str
    base_instruction_id: str
    raw_text: str
    provenance: str


@dataclass(frozen=True)
class GeneratedVariant:
    deployed: InstructionVariant
    evaluator_manifest: CorruptionManifest


class CorruptionEngine:
    """Seeded benchmark transformations with evaluator manifests kept separate."""

    COLORS = ("red", "blue", "green", "yellow")
    RELATIONS = {"past": "near", "near": "past", "before": "after", "after": "before"}

    def generate_all(self, route: RouteInstruction, seed: int) -> tuple[GeneratedVariant, ...]:
        return tuple(self.apply(route, condition, seed) for condition in CorruptionCondition)

    def apply(self, route: RouteInstruction, condition: CorruptionCondition, seed: int) -> GeneratedVariant:
        rng = random.Random(f"{route.base_instruction_id}:{condition.value}:{seed}")
        text = route.canonical_text
        edits: list[EditOperation] = []
        environment_edits: list[dict[str, str]] = []
        effect = "no semantic change"

        if condition is CorruptionCondition.TRUTHFUL_PARAPHRASE:
            paraphrase = route.paraphrases[rng.randrange(len(route.paraphrases))]
            edits.append(EditOperation(0, len(text), text, paraphrase.text))
            text = paraphrase.text
            effect = "meaning-preserving wording and syntax change"
        elif condition is CorruptionCondition.AMBIGUOUS_REFERENCE:
            color = route.anchor_attributes["color"]
            text, edit = _replace_exact(text, f"{color} chair", "chair")
            edits.append(edit)
            environment_edits.append({"operation": "add_decoy", "category": "chair", "attribute": color})
            effect = "two category-compatible landmarks are plausible"
        elif condition is CorruptionCondition.MISSING_LANDMARK:
            environment_edits.append({"operation": "remove_entity", "entity_id": route.anchor_entity_id})
            effect = "referenced landmark is absent after sufficient observation coverage"
        elif condition is CorruptionCondition.ATTRIBUTE_CORRUPTION:
            old = route.anchor_attributes["color"]
            # Match the fixed decoy palette used by graph worlds; the world does
            # not change between paired systems or instruction variants.
            new = self.COLORS[(self.COLORS.index(old) + 1) % len(self.COLORS)]
            text, edit = _replace_exact(text, old, new)
            edits.append(edit)
            effect = f"landmark color changed from {old} to {new}"
        elif condition is CorruptionCondition.RELATION_CORRUPTION:
            new_relation = self.RELATIONS[route.relation]
            text, edit = _replace_exact(text, route.relation, new_relation)
            edits.append(edit)
            effect = f"spatial relation changed from {route.relation} to {new_relation}"
        elif condition is CorruptionCondition.TOPOLOGY_CORRUPTION:
            replacement = "first" if route.topology_ordinal == "second" else "second"
            text, edit = _replace_exact(text, route.topology_ordinal, replacement)
            edits.append(edit)
            effect = "branch ordinal describes a different doorway"
        elif condition is CorruptionCondition.FALSE_INSERTED_CLAUSE:
            marker = ", then stop"
            insertion = ", then continue past the black sign"
            index = text.lower().index(marker)
            edits.append(EditOperation(index, index, "", insertion))
            text = text[:index] + insertion + text[index:]
            effect = "plausible route-inconsistent landmark clause inserted"

        manifest_material = f"{route.base_instruction_id}:{condition.value}:{seed}:{text}"
        manifest_id = hashlib.sha256(manifest_material.encode()).hexdigest()[:20]
        variant = InstructionVariant(
            variant_id=f"{route.base_instruction_id}-{condition.value}-s{seed}",
            base_instruction_id=route.base_instruction_id,
            raw_text=text,
            provenance="benchmark-v0.1",
        )
        manifest = CorruptionManifest(
            schema_version="corruption-manifest/v1",
            manifest_id=manifest_id,
            condition=condition,
            seed=seed,
            source_instruction_id=route.base_instruction_id,
            edits=tuple(edits),
            environment_edits=tuple(environment_edits),
            intended_effect=effect,
        )
        return GeneratedVariant(variant, manifest)


def _replace_exact(text: str, before: str, after: str) -> tuple[str, EditOperation]:
    start = text.lower().index(before.lower())
    end = start + len(before)
    actual = text[start:end]
    return text[:start] + after + text[end:], EditOperation(start, end, actual, after)


def manifest_as_dict(manifest: CorruptionManifest) -> dict[str, object]:
    return asdict(manifest)
