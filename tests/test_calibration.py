from language_nav.calibration import IsotonicCalibrator, TemperatureScaler
from language_nav.evaluation import brier_score


def test_temperature_scaling_is_reproducible_and_improves_overconfident_fixture() -> None:
    probabilities = [0.99, 0.9, 0.8, 0.2, 0.1, 0.01]
    labels = [1, 0, 1, 1, 0, 0]
    first = TemperatureScaler.fit(probabilities, labels)
    second = TemperatureScaler.fit(probabilities, labels)
    assert first == second
    assert brier_score(first.predict(probabilities), labels) < brier_score(probabilities, labels)


def test_isotonic_outputs_monotonic_probabilities_and_serializes() -> None:
    calibrator = IsotonicCalibrator.fit([0.1, 0.2, 0.3, 0.4], [0, 1, 0, 1])
    predicted = calibrator.predict([0.1, 0.2, 0.3, 0.4])
    assert predicted == sorted(predicted)
    assert calibrator.to_dict()["calibration_version"] == "isotonic/v1"

