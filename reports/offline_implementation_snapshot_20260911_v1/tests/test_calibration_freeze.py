import pytest

from language_nav.calibration import build_calibration_artifact


def _rows(count: int = 20):
    return [
        {
            "schema_version": "landmark-calibration-sample/v1",
            "observation_id": f"obs-{index}",
            "partition": "validation",
            "category": "chair" if index % 2 else "door",
            "probability": 0.8 if index % 3 else 0.7,
            "correct": index % 2,
        }
        for index in range(count)
    ]


def test_calibration_artifact_is_deterministic_and_records_provenance() -> None:
    first = build_calibration_artifact(_rows(), input_sha256="abc")
    second = build_calibration_artifact(_rows(), input_sha256="abc")
    assert first == second
    assert first["input_sha256"] == "abc"
    assert first["samples"] == 20
    assert first["deployment_default"] == "temperature"


def test_calibration_rejects_protected_and_duplicate_samples() -> None:
    protected = _rows()
    protected.append({**protected[0], "observation_id": "held", "partition": "held_out"})
    with pytest.raises(ValueError, match="Protected|protected"):
        build_calibration_artifact(protected, input_sha256="abc")
    duplicate = _rows()
    duplicate[1]["observation_id"] = duplicate[0]["observation_id"]
    with pytest.raises(ValueError, match="unique"):
        build_calibration_artifact(duplicate, input_sha256="abc")
