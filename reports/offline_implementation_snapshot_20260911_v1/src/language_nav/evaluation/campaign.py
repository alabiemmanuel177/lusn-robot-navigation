from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict

from language_nav.runner.episode import EpisodeRecord


def summarize_campaign(records: tuple[EpisodeRecord, ...]) -> dict[str, object]:
    if not records:
        raise ValueError("campaign has no records")
    grouped: dict[tuple[str, str], list[EpisodeRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.system_id, record.corruption_condition)].append(record)

    cells = []
    for (system_id, condition), rows in sorted(grouped.items()):
        count = len(rows)
        cells.append(
            {
                "system_id": system_id,
                "condition": condition,
                "episodes": count,
                "completion_rate": sum(row.outcome.instruction_completion for row in rows) / count,
                "critical_failure_rate": sum(row.outcome.hallucination_induced_critical_failure for row in rows) / count,
                "abstention_rate": sum(row.outcome.abstained for row in rows) / count,
                "mean_interventions": sum(sum(row.interventions.values()) for row in rows) / count,
            }
        )

    paired: dict[tuple[str, str, int, str], dict[str, EpisodeRecord]] = defaultdict(dict)
    for record in records:
        key = (record.map_id, record.route_id, record.seed, record.corruption_condition)
        paired[key][record.system_id] = record
    b2_b6 = [systems for systems in paired.values() if "B2" in systems and "B6" in systems]
    completion_difference = (
        sum(
            pair["B6"].outcome.instruction_completion - pair["B2"].outcome.instruction_completion
            for pair in b2_b6
        )
        / len(b2_b6)
        if b2_b6
        else None
    )
    critical_risk_difference = (
        sum(
            pair["B6"].outcome.hallucination_induced_critical_failure
            - pair["B2"].outcome.hallucination_induced_critical_failure
            for pair in b2_b6
        )
        / len(b2_b6)
        if b2_b6
        else None
    )
    return {
        "schema_version": "campaign-summary/v1",
        "episodes": len(records),
        "cells": cells,
        "paired_b6_minus_b2": {
            "blocks": len(b2_b6),
            "completion_difference": completion_difference,
            "critical_risk_difference": critical_risk_difference,
        },
        "caution": "Graph-world development results are not confirmatory robot-navigation evidence.",
    }

