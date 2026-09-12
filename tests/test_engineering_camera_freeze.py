import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from language_nav.camera_configuration import validate_camera_freeze

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('freeze_camera',
    ROOT/'scripts/freeze_engineering_camera_settings.py')
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PLAN=ROOT/'reports/stationary_capture_plan_v1/plan.json'


def evidence(tmp_path,monkeypatch):
    root=tmp_path/'unit_test_evidence'
    root.mkdir()
    monkeypatch.setattr(MODULE,'RUNS',root)
    directories=[]
    for index,world in enumerate((1,2,3,4,10,10)):
        directory=root/f'synthetic-unit-fixture-{index}'
        (directory/'perception_capture').mkdir(parents=True)
        (directory/'request.json').write_text(json.dumps({'partition':'development',
            'map_id':f'r3geo_base_r{world:03}','protected_test_routes_used':False,
            'capture_only':True,'camera_horizontal_fov':2.0}))
        (directory/'perception_capture/frame-000.json').write_text('{"unit_test_fixture":true}')
        (directory/'perception_capture/frame-000-rgb.bin').write_bytes(b'unit-test-not-live-image')
        directories.append(directory)
    return directories


def test_explicit_visual_attestation_required_before_any_read(tmp_path):
    with pytest.raises(ValueError,match='attestation'):
        MODULE.freeze(tmp_path/'missing.json',tmp_path/'output',[])
    assert not (tmp_path/'output').exists()


def test_freeze_validates_all_profiles_preserves_palette_and_generates_twelve_commands(tmp_path,monkeypatch):
    runs=evidence(tmp_path,monkeypatch)
    output=tmp_path/'output'
    payload,commands=MODULE.freeze(PLAN,output,runs,development_visual_check_complete=True)
    assert len(payload['profiles'])==14
    assert len(payload['development_evidence'])==6
    assert len(commands)==12
    assert not payload['confidence_calibration_frozen']
    assert not payload['human_labels_generated']
    for index in range(1,15):
        base=f'base-r{index:03}'
        profile=output/'profiles'/f'{base}.yaml'
        old=yaml.safe_load((PLAN.parent/'profiles'/f'{base}.yaml').read_text())
        new=yaml.safe_load(profile.read_text())
        assert new['camera_palette']==old['camera_palette']
        assert new['color_tolerance']==10
        assert new['partition_scope']==['development' if index<=10 else 'validation']
        assert validate_camera_freeze(output/'camera_settings_freeze.json',
            map_id=f'r3geo_base_r{index:03}',profile=profile,horizontal_fov=2.)
    assert all('--camera-settings-freeze' in row['command_argv'] for row in commands)
    assert all('--allow-coexistence-trial' not in row['command_argv'] for row in commands)
    with pytest.raises(FileExistsError):
        MODULE.freeze(PLAN,output,runs,development_visual_check_complete=True)


def test_evidence_tampering_invalidates_freeze(tmp_path,monkeypatch):
    runs=evidence(tmp_path,monkeypatch)
    output=tmp_path/'output'
    MODULE.freeze(PLAN,output,runs,development_visual_check_complete=True)
    (runs[0]/'perception_capture/frame-000-rgb.bin').write_bytes(b'changed')
    with pytest.raises(ValueError,match='evidence changed'):
        validate_camera_freeze(output/'camera_settings_freeze.json',map_id='r3geo_base_r011',
            profile=output/'profiles/base-r011.yaml',horizontal_fov=2.)


def test_nondevelopment_evidence_rejected_before_output(tmp_path,monkeypatch):
    runs=evidence(tmp_path,monkeypatch)
    request=runs[0]/'request.json'
    payload=json.loads(request.read_text())
    payload['partition']='validation'
    request.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='development stationary'):
        MODULE.freeze(PLAN,tmp_path/'output',runs,development_visual_check_complete=True)
    assert not (tmp_path/'output').exists()
