import importlib.util
import json
from pathlib import Path
import sys

import pytest
import yaml

from language_nav.world.physical import build_world

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('absence', ROOT / 'scripts/build_physical_absence_worlds.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def instruction(index=0):
    return json.loads((ROOT / 'data/manifests/instruction_benchmark_v0.1.json').read_text())['instructions'][index]


def test_absence_changes_only_chair_and_preserves_task(tmp_path):
    row = instruction()
    original, destination = tmp_path / 'original', tmp_path / 'absent'
    build_world(original, row)
    module.verify(original)
    report = module.build_absence(original, destination, row)
    assert len(report['removed_models']) == 6
    assert report['geometry_audit_passed']
    assert report['execution_authorized'] is False
    assert report['source_sha256']['map.pgm'] != report['asset_sha256']['map.pgm']
    entities = yaml.safe_load((destination / 'landmark_scene.yaml').read_text())['entities']
    assert len(entities) == 8
    assert all(e['category'] != 'chair' for e in entities)
    # The new map only frees occupancy; it does not add other obstacles.
    before = (original / 'map.pgm').read_bytes().split(b'255\n', 1)[1]
    after = (destination / 'map.pgm').read_bytes().split(b'255\n', 1)[1]
    assert len(before) == len(after)
    assert all(old == new or (old == 0 and new == 254) for old, new in zip(before, after))
    with pytest.raises(FileExistsError):
        module.build_absence(original, destination, row)


def test_protected_relabelled_id_rejected_before_read(tmp_path):
    row = {**instruction(), 'base_instruction_id': 'base-r015'}
    with pytest.raises(PermissionError):
        module.build_absence(tmp_path / 'missing', tmp_path / 'out', row)
    assert not (tmp_path / 'out').exists()


def test_base_generator_refuses_protected_absence(tmp_path):
    row = {**instruction(), 'partition': 'held_out'}
    with pytest.raises(PermissionError):
        build_world(tmp_path / 'out', row, anchor_present=False)
    assert not (tmp_path / 'out').exists()
