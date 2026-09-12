from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from language_nav.benchmark.splits import SplitRecord, assert_split_integrity


@dataclass(frozen=True)
class Paraphrase:
    variant_id: str
    text: str
    author_group: str
    template_family: str


@dataclass(frozen=True)
class RouteInstruction:
    route_id: str
    platform_route_id: str
    map_id: str
    partition: str
    base_instruction_id: str
    canonical_text: str
    anchor_entity_id: str
    anchor_category: str
    anchor_attributes: dict[str, str]
    relation: str
    topology_ordinal: str
    topology_side: str
    terminal_category: str
    terminal_region_id: str
    correct_groundings: tuple[str, ...]
    ambiguity_allowed: bool
    paraphrases: tuple[Paraphrase, ...]


_ROUTE_ROWS = (
    ("r001", "dev_01", "development", "red", "left", "laboratory_entrance"),
    ("r002", "dev_01", "development", "blue", "right", "office_entrance"),
    ("r003", "dev_02", "development", "green", "left", "laboratory_entrance"),
    ("r004", "dev_02", "development", "yellow", "right", "office_entrance"),
    ("r005", "dev_03", "development", "red", "right", "laboratory_entrance"),
    ("r006", "dev_03", "development", "blue", "left", "office_entrance"),
    ("r007", "dev_04", "development", "green", "right", "laboratory_entrance"),
    ("r008", "dev_04", "development", "yellow", "left", "office_entrance"),
    ("r009", "dev_05", "development", "red", "left", "laboratory_entrance"),
    ("r010", "dev_00", "development", "blue", "right", "office_entrance"),
    ("r011", "val_01", "validation", "green", "left", "laboratory_entrance"),
    ("r012", "val_01", "validation", "yellow", "right", "office_entrance"),
    ("r013", "val_02", "validation", "red", "right", "laboratory_entrance"),
    ("r014", "val_00", "validation", "blue", "left", "office_entrance"),
    ("r015", "test_01", "held_out", "green", "right", "laboratory_entrance"),
    ("r016", "test_01", "held_out", "yellow", "left", "office_entrance"),
    ("r017", "test_02", "held_out", "red", "left", "laboratory_entrance"),
    ("r018", "test_02", "held_out", "blue", "right", "office_entrance"),
    ("r019", "test_00", "held_out", "green", "left", "laboratory_entrance"),
    ("r020", "test_00", "held_out", "yellow", "right", "office_entrance"),
)


def build_corpus() -> tuple[RouteInstruction, ...]:
    corpus = []
    route_index_by_map: dict[str, int] = {}
    for route_id, map_id, partition, color, side, terminal in _ROUTE_ROWS:
        base_id = f"base-{route_id}"
        anchor_id = f"{map_id}-{route_id}-{color}-chair"
        terminal_words = terminal.replace("_", " ")
        canonical = (
            f"Go through the corridor, then continue past the {color} chair, "
            f"then take the second doorway on the {side}, then stop near the {terminal_words}."
        )
        prefix = {"development": "dev", "validation": "val", "held_out": "test"}[partition]
        platform_index = route_index_by_map.get(map_id, 0)
        route_index_by_map[map_id] = platform_index + 1
        paraphrases = (
            Paraphrase(
                f"{base_id}-p1",
                f"Walk along the corridor, then go past the {color} chair, then take the second doorway on the {side}, then stop at the {terminal_words}.",
                f"{prefix}-authors-a",
                f"{prefix}-template-a",
            ),
            Paraphrase(
                f"{base_id}-p2",
                f"Move down the corridor, then continue past the {color} chair, then use the second doorway on the {side}, then stop beside the {terminal_words}.",
                f"{prefix}-authors-b",
                f"{prefix}-template-b",
            ),
            Paraphrase(
                f"{base_id}-p3",
                f"Go along the corridor, then go past the {color} chair, then take the second doorway on the {side}, then stop near the {terminal_words}.",
                f"{prefix}-authors-c",
                f"{prefix}-template-c",
            ),
        )
        corpus.append(
            RouteInstruction(
                route_id=route_id,
                platform_route_id=f"{map_id}_r{platform_index}",
                map_id=map_id,
                partition=partition,
                base_instruction_id=base_id,
                canonical_text=canonical,
                anchor_entity_id=anchor_id,
                anchor_category="chair",
                anchor_attributes={"color": color},
                relation="past",
                topology_ordinal="second",
                topology_side=side,
                terminal_category=terminal,
                terminal_region_id=f"{map_id}-{route_id}-terminal",
                correct_groundings=(anchor_id,),
                ambiguity_allowed=False,
                paraphrases=paraphrases,
            )
        )
    _validate_corpus(corpus)
    return tuple(corpus)


def _validate_corpus(corpus: list[RouteInstruction]) -> None:
    if len(corpus) < 20:
        raise ValueError("Protocol 1.0 requires at least twenty base instructions")
    if any(len(item.paraphrases) < 3 for item in corpus):
        raise ValueError("each base instruction requires three paraphrases")
    records = []
    for item in corpus:
        for paraphrase in item.paraphrases:
            records.append(
                SplitRecord(
                    item.partition,
                    item.map_id,
                    item.route_id,
                    item.base_instruction_id,
                    paraphrase.author_group,
                    paraphrase.template_family,
                )
            )
    assert_split_integrity(records)


def write_corpus_manifest(path: Path, seed: int = 0) -> None:
    from language_nav.benchmark.annotations import annotate_grounding
    from language_nav.benchmark.corruptions import CorruptionEngine, manifest_as_dict

    corpus = build_corpus()
    generated = [
        (route, variant)
        for route in corpus
        for variant in CorruptionEngine().generate_all(route, seed)
    ]
    payload = {
        "schema_version": "instruction-benchmark/v1",
        "protocol_version": "1.0",
        "seed": seed,
        "instructions": [asdict(item) for item in corpus],
        "deployed_variants": [asdict(variant.deployed) for _, variant in generated],
        "evaluator_only": {
            "corruption_manifests": [manifest_as_dict(variant.evaluator_manifest) for _, variant in generated],
            "grounding_annotations": [asdict(annotate_grounding(route, variant)) for route, variant in generated],
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
