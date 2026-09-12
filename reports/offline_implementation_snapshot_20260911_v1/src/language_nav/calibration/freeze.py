from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from language_nav.calibration.calibrators import IsotonicCalibrator, TemperatureScaler
from language_nav.evaluation.metrics import brier_score, expected_calibration_error


def build_calibration_artifact(
    rows: Iterable[dict[str, Any]],
    *,
    input_sha256: str,
    partition: str = "validation",
    minimum_samples: int = 20,
) -> dict[str, Any]:
    samples = list(rows)
    if partition not in {"development", "validation"}:
        raise ValueError("calibration partition must be development or validation")
    if any(str(row.get("partition")) in {"held_out", "test"} for row in samples):
        raise ValueError("protected samples are forbidden in calibration input")
    selected = [row for row in samples if row.get("partition") == partition]
    if len(selected) < minimum_samples:
        raise ValueError(f"calibration requires at least {minimum_samples} selected samples")
    identifiers = [str(row.get("observation_id", "")) for row in selected]
    if any(not identifier for identifier in identifiers) or len(identifiers) != len(set(identifiers)):
        raise ValueError("calibration observation IDs must be non-empty and unique")
    for row in selected:
        if row.get("schema_version") != "landmark-calibration-sample/v1":
            raise ValueError("unsupported landmark calibration sample schema")
        if any(key in row for key in ("oracle_route", "future_observations", "correct_grounding")):
            raise ValueError("evaluator-only navigation fields are forbidden in calibration samples")
    probabilities = [float(row["probability"]) for row in selected]
    labels = [int(row["correct"]) for row in selected]
    if set(labels) != {0, 1}:
        raise ValueError("calibration requires both correct and incorrect observations")

    temperature = TemperatureScaler.fit(probabilities, labels)
    isotonic = IsotonicCalibrator.fit(probabilities, labels)
    temperature_probabilities = temperature.predict(probabilities)
    isotonic_probabilities = isotonic.predict(probabilities)
    return {
        "schema_version": "landmark-calibration/v1",
        "evidence_scope": "landmark_detector_validation",
        "input_sha256": input_sha256,
        "partition": partition,
        "samples": len(selected),
        "labels": {"correct": sum(labels), "incorrect": len(labels) - sum(labels)},
        "categories": dict(sorted(Counter(str(row["category"]) for row in selected).items())),
        "uncalibrated": {
            "brier": brier_score(probabilities, labels),
            "ece": expected_calibration_error(probabilities, labels),
        },
        "temperature": {
            **temperature.to_dict(),
            "brier": brier_score(temperature_probabilities, labels),
            "ece": expected_calibration_error(temperature_probabilities, labels),
        },
        "isotonic": {
            **isotonic.to_dict(),
            "brier": brier_score(isotonic_probabilities, labels),
            "ece": expected_calibration_error(isotonic_probabilities, labels),
        },
        "deployment_default": "temperature",
        "freeze_rule": "create_once_and_verify_input_checksum",
    }
