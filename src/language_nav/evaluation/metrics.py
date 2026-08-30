from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class BootstrapInterval:
    estimate: float
    lower: float
    upper: float
    samples: int


def brier_score(probabilities: list[float], labels: list[int]) -> float:
    if len(probabilities) != len(labels) or not probabilities:
        raise ValueError("probabilities and labels must have equal non-zero length")
    return sum((probability - label) ** 2 for probability, label in zip(probabilities, labels, strict=True)) / len(labels)


def expected_calibration_error(probabilities: list[float], labels: list[int], bins: int = 10) -> float:
    if len(probabilities) != len(labels) or not probabilities:
        raise ValueError("probabilities and labels must have equal non-zero length")
    if bins < 1:
        raise ValueError("bins must be positive")
    total = len(probabilities)
    error = 0.0
    for index in range(bins):
        low, high = index / bins, (index + 1) / bins
        members = [
            (probability, label)
            for probability, label in zip(probabilities, labels, strict=True)
            if low <= probability <= high and (index == bins - 1 or probability < high)
        ]
        if not members:
            continue
        confidence = sum(item[0] for item in members) / len(members)
        accuracy = sum(item[1] for item in members) / len(members)
        error += len(members) / total * abs(confidence - accuracy)
    return error


def reliability_curve(probabilities: list[float], labels: list[int], bins: int = 10) -> list[dict[str, float | int]]:
    if len(probabilities) != len(labels) or not probabilities:
        raise ValueError("probabilities and labels must have equal non-zero length")
    curve = []
    for index in range(bins):
        low, high = index / bins, (index + 1) / bins
        members = [
            (probability, label)
            for probability, label in zip(probabilities, labels, strict=True)
            if low <= probability <= high and (index == bins - 1 or probability < high)
        ]
        if members:
            curve.append(
                {
                    "bin_lower": low,
                    "bin_upper": high,
                    "count": len(members),
                    "mean_confidence": sum(item[0] for item in members) / len(members),
                    "accuracy": sum(item[1] for item in members) / len(members),
                }
            )
    return curve


def risk_coverage_curve(probabilities: list[float], labels: list[int]) -> list[dict[str, float | int]]:
    if len(probabilities) != len(labels) or not probabilities:
        raise ValueError("probabilities and labels must have equal non-zero length")
    ordered = sorted(zip(probabilities, labels, strict=True), key=lambda item: (-item[0], -item[1]))
    errors = 0
    curve = []
    for accepted, (threshold, label) in enumerate(ordered, start=1):
        errors += int(label == 0)
        curve.append(
            {
                "coverage": accepted / len(ordered),
                "risk": errors / accepted,
                "threshold": threshold,
                "accepted": accepted,
            }
        )
    return curve


def spl(success: bool, shortest_path_distance: float, executed_distance: float) -> float:
    if shortest_path_distance < 0 or executed_distance < 0:
        raise ValueError("distances must be non-negative")
    if not success:
        return 0.0
    denominator = max(shortest_path_distance, executed_distance, 1e-12)
    return shortest_path_distance / denominator


def route_fidelity(executed: tuple[str, ...], reference: tuple[str, ...]) -> float:
    """Normalized DTW-style node fidelity in [0, 1]."""
    if not executed or not reference:
        return 0.0
    rows, columns = len(executed), len(reference)
    table = [[math.inf] * (columns + 1) for _ in range(rows + 1)]
    table[0][0] = 0.0
    for row in range(1, rows + 1):
        for column in range(1, columns + 1):
            cost = 0.0 if executed[row - 1] == reference[column - 1] else 1.0
            table[row][column] = cost + min(
                table[row - 1][column], table[row][column - 1], table[row - 1][column - 1]
            )
    return math.exp(-table[rows][columns] / len(reference))


def paired_risk_difference(first: list[int], second: list[int]) -> float:
    if len(first) != len(second) or not first:
        raise ValueError("paired outcomes must have equal non-zero length")
    return sum(a - b for a, b in zip(first, second, strict=True)) / len(first)


def contradiction_recovery_rate(detected: list[bool], completed: list[bool]) -> float:
    if len(detected) != len(completed) or not detected:
        raise ValueError("detected and completed must have equal non-zero length")
    indices = [index for index, value in enumerate(detected) if value]
    if not indices:
        return 0.0
    return sum(completed[index] for index in indices) / len(indices)


def hierarchical_bootstrap(
    records: list[dict[str, Any]],
    metric: Callable[[dict[str, Any]], float],
    *,
    hierarchy: tuple[str, ...] = ("map_id", "route_id", "base_instruction_id"),
    samples: int = 2000,
    seed: int = 0,
) -> BootstrapInterval:
    if not records or samples < 1:
        raise ValueError("records and positive sample count are required")
    rng = random.Random(seed)

    def resample(rows: list[dict[str, Any]], depth: int) -> list[dict[str, Any]]:
        if depth == len(hierarchy):
            return [rng.choice(rows) for _ in rows]
        groups: dict[object, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[row[hierarchy[depth]]].append(row)
        keys = sorted(groups, key=str)
        output = []
        for _ in keys:
            selected = rng.choice(keys)
            output.extend(resample(groups[selected], depth + 1))
        return output

    estimate = sum(metric(record) for record in records) / len(records)
    draws = []
    for _ in range(samples):
        sampled = resample(records, 0)
        draws.append(sum(metric(record) for record in sampled) / len(sampled))
    draws.sort()
    lower = draws[max(0, int(0.025 * samples) - 1)]
    upper = draws[min(samples - 1, int(0.975 * samples))]
    return BootstrapInterval(estimate, lower, upper, samples)
