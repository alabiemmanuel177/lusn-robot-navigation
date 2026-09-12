import math

from language_nav.evaluation import brier_score, expected_calibration_error


def test_metric_fixtures() -> None:
    probabilities = [0.0, 0.25, 0.75, 1.0]
    labels = [0, 0, 1, 1]
    assert math.isclose(brier_score(probabilities, labels), 0.03125)
    assert math.isclose(expected_calibration_error(probabilities, labels, bins=4), 0.125)

