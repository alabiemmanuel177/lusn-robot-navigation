from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from language_nav.evaluation.metrics import hierarchical_bootstrap


_TRUTHFUL = {"truthful_original", "truthful_paraphrase"}


def analyze_paired_graph_records(
    records: Iterable[dict[str, Any]],
    *,
    bootstrap_samples: int = 2000,
    seed: int = 0,
) -> dict[str, Any]:
    rows = list(records)
    if not rows:
        raise ValueError("graph analysis requires records")
    systems: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        systems[str(row["system_id"])].append(row)
    if "B2" not in systems or "B6" not in systems:
        raise ValueError("paired graph analysis requires B2 and B6")

    paired: dict[tuple[object, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if row["system_id"] not in {"B2", "B6"}:
            continue
        key = (
            row["map_id"], row["route_id"], row["base_instruction_id"],
            row["variant_id"], row["seed"],
        )
        paired[key][row["system_id"]] = row
    complete_pairs = [pair for pair in paired.values() if set(pair) == {"B2", "B6"}]
    if not complete_pairs:
        raise ValueError("no complete B2/B6 pairs")

    pair_rows = []
    for pair in complete_pairs:
        b2, b6 = pair["B2"], pair["B6"]
        pair_rows.append(
            {
                "map_id": b2["map_id"],
                "route_id": b2["route_id"],
                "base_instruction_id": b2["base_instruction_id"],
                "condition": b2["corruption_condition"],
                "completion_difference": int(b6["outcome"]["instruction_completion"])
                - int(b2["outcome"]["instruction_completion"]),
                "critical_risk_difference": int(
                    b6["outcome"]["hallucination_induced_critical_failure"]
                )
                - int(b2["outcome"]["hallucination_induced_critical_failure"]),
            }
        )

    def system_summary(system_id: str) -> dict[str, float | int]:
        system_rows = systems[system_id]
        count = len(system_rows)
        corrupted = [row for row in system_rows if row["corruption_condition"] not in _TRUTHFUL]
        return {
            "episodes": count,
            "completion_rate": _mean(system_rows, "instruction_completion"),
            "critical_failure_rate": _mean(system_rows, "hallucination_induced_critical_failure"),
            "corrupted_completion_rate": _mean(corrupted, "instruction_completion"),
            "corrupted_critical_failure_rate": _mean(
                corrupted, "hallucination_induced_critical_failure"
            ),
            "mean_interventions": sum(
                sum(int(value) for value in row["interventions"].values()) for row in system_rows
            ) / count,
        }

    completion = hierarchical_bootstrap(
        pair_rows,
        lambda row: float(row["completion_difference"]),
        samples=bootstrap_samples,
        seed=seed,
    )
    critical = hierarchical_bootstrap(
        pair_rows,
        lambda row: float(row["critical_risk_difference"]),
        samples=bootstrap_samples,
        seed=seed + 1,
    )
    return {
        "episodes": len(rows),
        "maps": len({row["map_id"] for row in rows}),
        "routes": len({row["route_id"] for row in rows}),
        "paired_blocks": len(pair_rows),
        "systems": {name: system_summary(name) for name in sorted(systems)},
        "paired_b6_minus_b2": {
            "completion_difference": completion.__dict__,
            "critical_risk_difference": critical.__dict__,
        },
    }


def _mean(rows: list[dict[str, Any]], field: str) -> float:
    if not rows:
        return 0.0
    return sum(bool(row["outcome"][field]) for row in rows) / len(rows)
