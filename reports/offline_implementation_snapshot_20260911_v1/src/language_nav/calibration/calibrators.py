from __future__ import annotations

import math
from dataclasses import dataclass


def _clip(probability: float) -> float:
    return min(1.0 - 1e-9, max(1e-9, probability))


def _temperature_probability(probability: float, temperature: float) -> float:
    clipped = _clip(probability)
    logit = math.log(clipped / (1.0 - clipped)) / temperature
    return 1.0 / (1.0 + math.exp(-logit))


@dataclass(frozen=True)
class TemperatureScaler:
    temperature: float = 1.0
    calibration_version: str = "temperature/v1"

    @classmethod
    def fit(cls, probabilities: list[float], labels: list[int]) -> TemperatureScaler:
        _validate(probabilities, labels)
        # Deterministic log-spaced search is sufficient for a one-parameter
        # calibrator and reproduces exactly across supported Python platforms.
        candidates = [math.exp(math.log(0.2) + index / 1000 * math.log(25.0)) for index in range(1001)]
        best = min(candidates, key=lambda temperature: _nll(probabilities, labels, temperature))
        return cls(best)

    def predict(self, probabilities: list[float]) -> list[float]:
        return [_temperature_probability(probability, self.temperature) for probability in probabilities]

    def to_dict(self) -> dict[str, float | str]:
        return {"calibration_version": self.calibration_version, "temperature": self.temperature}


@dataclass(frozen=True)
class IsotonicCalibrator:
    upper_bounds: tuple[float, ...]
    values: tuple[float, ...]
    calibration_version: str = "isotonic/v1"

    @classmethod
    def fit(cls, probabilities: list[float], labels: list[int]) -> IsotonicCalibrator:
        _validate(probabilities, labels)
        ordered = sorted(zip(probabilities, labels, strict=True))
        blocks: list[dict[str, float]] = []
        for probability, label in ordered:
            blocks.append({"upper": probability, "sum": float(label), "count": 1.0})
            while len(blocks) >= 2:
                previous = blocks[-2]["sum"] / blocks[-2]["count"]
                current = blocks[-1]["sum"] / blocks[-1]["count"]
                if previous <= current:
                    break
                right = blocks.pop()
                left = blocks.pop()
                blocks.append(
                    {
                        "upper": right["upper"],
                        "sum": left["sum"] + right["sum"],
                        "count": left["count"] + right["count"],
                    }
                )
        return cls(
            tuple(block["upper"] for block in blocks),
            tuple(block["sum"] / block["count"] for block in blocks),
        )

    def predict(self, probabilities: list[float]) -> list[float]:
        outputs = []
        for probability in probabilities:
            index = next(
                (index for index, upper in enumerate(self.upper_bounds) if probability <= upper),
                len(self.upper_bounds) - 1,
            )
            outputs.append(self.values[index])
        return outputs

    def to_dict(self) -> dict[str, object]:
        return {
            "calibration_version": self.calibration_version,
            "upper_bounds": self.upper_bounds,
            "values": self.values,
        }


def _nll(probabilities: list[float], labels: list[int], temperature: float) -> float:
    calibrated = [_clip(_temperature_probability(probability, temperature)) for probability in probabilities]
    return -sum(
        label * math.log(probability) + (1 - label) * math.log(1 - probability)
        for probability, label in zip(calibrated, labels, strict=True)
    ) / len(labels)


def _validate(probabilities: list[float], labels: list[int]) -> None:
    if len(probabilities) != len(labels) or not probabilities:
        raise ValueError("probabilities and labels must have equal non-zero length")
    if any(not 0.0 <= probability <= 1.0 for probability in probabilities):
        raise ValueError("probabilities must be in [0, 1]")
    if any(label not in {0, 1} for label in labels):
        raise ValueError("labels must be binary")

