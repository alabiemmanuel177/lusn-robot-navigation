import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from language_nav.benchmark.physical_catalog import validate_physical_launch_inputs

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('readable_worlds',
    ROOT/'scripts/build_readable_physical_worlds.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_visual_derivative_preserves_all_original_elements_and_ids(tmp_path):
    source = ROOT/'data/physical_worlds_v1/base-r010'
    before = {name: (source/name).read_bytes() for name in MODULE.FILES}
    output = tmp_path/'base-r010'
    audit = MODULE.build(source, output)
    assert before == {name: (source/name).read_bytes() for name in MODULE.FILES}
    for name in MODULE.FILES:
        if name not in ('world.sdf','manifest.json','execution_catalog.json'):
            assert (output/name).read_bytes() == before[name]
    original = ET.fromstring(before['world.sdf'])
    derivative = ET.parse(output/'world.sdf').getroot()
    world = derivative.find('world')
    new_models = [node for node in world.findall('model')
                  if node.get('name','').startswith('readable_')]
    assert len(new_models) == 8
    for node in new_models:
        assert not node.findall('.//collision')
        assert not node.findall('.//plugin')
        world.remove(node)
    assert MODULE.canonical(original) == MODULE.canonical(derivative)
    for name in ('manifest.json','execution_catalog.json'):
        old, new = json.loads(before[name]), json.loads((output/name).read_text())
        assert new.pop('world_sha256') != old.pop('world_sha256')
        assert new == old
    assert audit['visual_only']
    assert audit['collision_geometry_unchanged']
    assert not audit['live_readability_validated']
    runtime = validate_physical_launch_inputs(output/'execution_catalog.json',
        output/'landmark_scene.yaml',output/'map.yaml')
    assert len(runtime.execution) == 4


def test_sign_text_and_facing_both_corridor_and_room(tmp_path):
    audit = MODULE.build(ROOT/'data/physical_worlds_v1/base-r010', tmp_path/'base-r010')
    assert sorted(sign['text'] for sign in audit['signs']) == ['LAB']*4+['OFFICE']*4
    for sign in audit['signs']:
        normal_y = sign['front_normal'][1]
        side = 1 if sign['position'][1] > 0 else -1
        assert normal_y * side == pytest.approx(
            -1 if sign['model_name'].endswith('_corridor') else 1)
        assert sign['position'][2] == 1.43
        assert sign['collision_count'] == 0


def test_creation_is_once_and_protected_rejected_before_read(tmp_path, monkeypatch):
    output = tmp_path/'base-r010'
    MODULE.build(ROOT/'data/physical_worlds_v1/base-r010', output)
    with pytest.raises(FileExistsError):
        MODULE.build(ROOT/'data/physical_worlds_v1/base-r010', output)
    def forbidden_read(_path):
        pytest.fail('protected source was opened')
    monkeypatch.setattr(Path, 'read_bytes', forbidden_read)
    with pytest.raises(PermissionError):
        MODULE.build(tmp_path/'base-r015', tmp_path/'protected-output')


def test_font_is_selfcontained_binary_seven_by_five():
    assert set('LABOFFICE') <= set(MODULE.FONT)
    for rows in MODULE.FONT.values():
        assert len(rows) == 7
        assert all(len(row) == 5 and set(row) <= {'0','1'} for row in rows)
