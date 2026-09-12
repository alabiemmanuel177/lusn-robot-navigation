import hashlib
import json
import pytest
from language_nav.camera_configuration import validate_camera_freeze


def fixture(tmp_path):
    profile=tmp_path/'profile.yaml'; profile.write_text('palette: draft\n')
    run=tmp_path/'run'; run.mkdir()
    (run/'request.json').write_text(json.dumps(dict(map_id='r3geo_base_r001', partition='development',protected_test_routes_used=False)))
    (run/'frame-000-rgb.bin').write_bytes(b'raw')
    payload=dict(schema_version='research3-engineering-camera-freeze/v1',
        protected_data_used=False, confidence_calibration_frozen=False,
        human_labels_generated=False,horizontal_fov=2.,
        profiles={f'r3geo_base_r{i:03d}':hashlib.sha256(profile.read_bytes()).hexdigest() for i in range(1,15)},
        development_evidence=[dict(run_directory=str(run),sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir()})])
    freeze=tmp_path/'freeze.json';freeze.write_text(json.dumps(payload))
    return freeze,profile,payload,run


def test_engineering_freeze_binds_profile_and_raw_evidence(tmp_path):
    freeze,profile,_,run=fixture(tmp_path)
    assert len(validate_camera_freeze(freeze,map_id='r3geo_base_r011',profile=profile,horizontal_fov=2.))==64
    (run/'frame-000-rgb.bin').write_bytes(b'changed')
    with pytest.raises(ValueError,match='evidence changed'):
        validate_camera_freeze(freeze,map_id='r3geo_base_r011',profile=profile,horizontal_fov=2.)


@pytest.mark.parametrize('change', ['profile','fov','protected','empty_evidence','calibration'])
def test_invalid_freeze_fails_closed(tmp_path,change):
    freeze,profile,payload,_=fixture(tmp_path)
    if change=='profile': profile.write_text('changed')
    if change=='empty_evidence': payload['development_evidence']=[]
    if change=='calibration': payload['confidence_calibration_frozen']=True
    freeze.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        validate_camera_freeze(freeze,map_id='r3geo_base_r015' if change=='protected' else 'r3geo_base_r011',
                              profile=profile,horizontal_fov=1. if change=='fov' else 2.)


def test_protected_evidence_map_rejected_before_any_media_read(tmp_path, monkeypatch):
    freeze, profile, payload, run = fixture(tmp_path)
    request = run / 'request.json'
    request.write_text(json.dumps(dict(map_id='r3geo_base_r015', partition='development', protected_test_routes_used=False)))
    payload['development_evidence'][0]['sha256']['request.json'] = hashlib.sha256(request.read_bytes()).hexdigest()
    freeze.write_text(json.dumps(payload))
    original = type(request).read_bytes
    def guarded(path):
        if path.name.endswith('-rgb.bin'):
            pytest.fail('protected evidence media accessed')
        return original(path)
    monkeypatch.setattr(type(request), 'read_bytes', guarded)
    with pytest.raises(ValueError, match='development evidence'):
        validate_camera_freeze(freeze, map_id='r3geo_base_r011', profile=profile, horizontal_fov=2.)


def test_protected_requested_map_rejected_before_freeze_read(tmp_path):
    with pytest.raises(ValueError, match='non-protected'):
        validate_camera_freeze(tmp_path/'does-not-exist', map_id='r3geo_base_r015',
                               profile=tmp_path/'missing-profile', horizontal_fov=2.)
