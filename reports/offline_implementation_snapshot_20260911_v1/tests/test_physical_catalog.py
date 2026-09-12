import json
from pathlib import Path
import shutil

import pytest

from language_nav.benchmark.physical_catalog import load_physical_runtime_catalog
from language_nav.grounding import build_semantic_route_candidates


ROOT = Path(__file__).parents[1] / "data/physical_worlds_v1"


def fixture(tmp_path):
    for name in ("execution_catalog.json", "map.pgm", "world.sdf"):
        shutil.copyfile(ROOT / "base-r010" / name, tmp_path / name)
    return tmp_path / "execution_catalog.json"


def test_runtime_loads_without_evaluator_files_and_keeps_four_alternatives(tmp_path):
    path = fixture(tmp_path)
    runtime = load_physical_runtime_catalog(path)
    assert len(runtime.execution) == len(runtime.semantic.routes) == 4
    assert {r.base_instruction_id for r in runtime.semantic.routes} == {"base-r010"}
    candidates = build_semantic_route_candidates([], [r.proposal for r in runtime.semantic.routes], [])
    assert len(candidates) == 4
    assert all(not c.nav2_eligible and c.observation_coverage == 0 for c in candidates)
    assert len({c.anchor_entity_id for c in candidates}) == 1


@pytest.mark.parametrize("change", ["protected", "oracle", "duplicate", "missing", "identity"])
def test_runtime_rejects_protected_leaked_or_incomplete_catalogues(tmp_path, change):
    path = fixture(tmp_path)
    data = json.loads(path.read_text())
    if change == "protected":
        data["partition"] = "held_out"
    elif change == "oracle":
        data["expected_route_id"] = data["routes"][0]["route_id"]
    elif change == "duplicate":
        data["routes"][1] = data["routes"][0]
    elif change == "missing":
        data["routes"].pop()
    else:
        data["routes"][0]["terminal_entity_id"] = "wrong"
    path.write_text(json.dumps(data))
    with pytest.raises((ValueError, PermissionError)):
        load_physical_runtime_catalog(path)


def test_runtime_rejects_changed_world(tmp_path):
    path = fixture(tmp_path)
    (tmp_path / "world.sdf").write_text("changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_physical_runtime_catalog(path)


def test_all_nonprotected_physical_catalogues_load():
    # Only development/validation; held-out content is not loaded for development.
    for index in range(1, 15):
        runtime = load_physical_runtime_catalog(ROOT / f"base-r{index:03d}/execution_catalog.json")
        assert len(runtime.execution) == 4


def test_absence_runtime_never_opens_evaluator_answers(tmp_path):
    from language_nav.benchmark.physical_catalog import validate_physical_launch_inputs
    source = ROOT.parent / 'physical_absence_worlds_v1/base-r010'
    for name in ('execution_catalog.json', 'map.pgm', 'map.yaml', 'world.sdf',
                 'landmark_scene.yaml', 'absence_intervention.json'):
        shutil.copyfile(source / name, tmp_path / name)
    runtime = validate_physical_launch_inputs(tmp_path / 'execution_catalog.json', tmp_path / 'landmark_scene.yaml')
    assert len(runtime.execution) == 4
    assert not (tmp_path / 'manifest.json').exists()
    # Missing provenance cannot be interpreted as a legitimate missing anchor.
    (tmp_path / 'absence_intervention.json').unlink()
    with pytest.raises(ValueError, match='association missing'):
        validate_physical_launch_inputs(tmp_path / 'execution_catalog.json', tmp_path / 'landmark_scene.yaml')


def test_absence_provenance_tamper_rejected(tmp_path):
    from language_nav.benchmark.physical_catalog import validate_physical_launch_inputs
    source = ROOT.parent / 'physical_absence_worlds_v1/base-r010'
    for name in ('execution_catalog.json', 'map.pgm', 'map.yaml', 'world.sdf',
                 'landmark_scene.yaml', 'absence_intervention.json'):
        shutil.copyfile(source / name, tmp_path / name)
    path = tmp_path / 'absence_intervention.json'
    report = json.loads(path.read_text())
    report['asset_sha256']['landmark_scene.yaml'] = '0' * 64
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match='hash mismatch'):
        validate_physical_launch_inputs(tmp_path / 'execution_catalog.json', tmp_path / 'landmark_scene.yaml')
