"""Source-freeze checks use synthetic provider files; never run ROS."""
import json
from pathlib import Path
import runpy

import pytest
from language_nav import camera_configuration as CAMERA

ROOT = Path(__file__).parents[1]


def test_snapshot_covers_missing_active_semantic_and_provider_wrapper():
    snapshot = CAMERA.capture_source_snapshot()
    assert 'ros_ws/src/language_nav_runtime/language_nav_runtime/semantic_routes.py' in snapshot
    assert 'ros_ws/src/language_nav_bringup/language_nav_bringup/landmark_bridge_runner.py' in snapshot
    assert 'ros_ws/src/semantic_belief_map/semantic_belief_map/node.py' in snapshot
    assert 'src/language_nav/belief/store.py' in snapshot
    assert 'ros_ws/src/language_nav_interfaces/msg/SemanticObservation.msg' in snapshot


def test_runner_and_freeze_share_one_source_map():
    runner = runpy.run_path(str(ROOT / 'scripts/run_physical_episode.py'))
    request, _, _ = runner['prepare'](ROOT / 'data/physical_worlds_readable_v1/base-r001',
        'base-r001-truthful_original-s0', 'synthetic-source-contract', 89)
    assert request['source_sha256'] == CAMERA.capture_source_snapshot()
    assert 'provider_source_snapshot' in request


def test_capture_source_freeze_rejects_source_drift(tmp_path, monkeypatch):
    monkeypatch.setattr(CAMERA, 'capture_source_snapshot', lambda: {'owned.py': 'a' * 64})
    monkeypatch.setattr(CAMERA, 'capture_provider_snapshot', lambda: {'complete': True, 'source_files': {}})
    frozen = {'schema_version': 'research3-capture-source-snapshot/v1',
              'source_sha256': {'owned.py': 'a' * 64},
              'provider_source_snapshot': CAMERA.capture_provider_snapshot(),
              'protected_data_used': False, 'human_labels_generated': False}
    path = tmp_path / 'freeze.json'
    path.write_text(json.dumps(frozen))
    CAMERA.validate_capture_source_freeze(path)
    monkeypatch.setattr(CAMERA, 'capture_source_snapshot', lambda: {'owned.py': 'b' * 64})
    with pytest.raises(ValueError, match='source snapshot changed'):
        CAMERA.validate_capture_source_freeze(path)


def test_provider_snapshot_requires_source_and_active_build_match(tmp_path):
    r1_root = tmp_path / 'r1'
    provider = r1_root / 'extensions/research3_landmark_bridge/research3_landmark_bridge'
    build = tmp_path / 'build'
    provider.mkdir(parents=True)
    build.mkdir()
    for name in ('__init__.py', 'core.py', 'node.py'):
        (provider / name).write_text('# synthetic provider')
        (build / name).symlink_to(provider / name)
    for name in CAMERA.PROVIDER_SOURCE_FILES:
        path = r1_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text('# synthetic dependency')
    transforms = r1_root / 'build/semantic_perception/semantic_perception'
    transforms.mkdir(parents=True)
    for name in ('live_risk_node.py', 'projection.py'):
        (transforms / name).symlink_to(r1_root / 'src/semantic_perception/semantic_perception' / name)
    result = CAMERA.capture_provider_snapshot(r1_root, build)
    assert result['complete']
    (build / 'core.py').unlink()
    (build / 'core.py').write_text('# stale synthetic build')
    assert not CAMERA.capture_provider_snapshot(r1_root, build)['complete']


def test_capture_freeze_fails_before_any_ros_import_or_launch(monkeypatch, tmp_path):
    runner = runpy.run_path(str(ROOT / 'scripts/run_physical_episode.py'))
    def reject(*args, **kwargs):
        assert kwargs['check_import_resolution'] is True
        raise ValueError('synthetic frozen source changed')
    monkeypatch.setitem(runner['execute'].__globals__, 'validate_capture_source_freeze', reject)
    with pytest.raises(ValueError, match='frozen source changed'):
        runner['execute']({'capture_source_freeze': 'synthetic', 'capture_only': True},
                          None, None, tmp_path, 'B6')


def test_provider_transform_and_dependency_bytes_are_required():
    snapshot = CAMERA.capture_provider_snapshot()
    assert len(snapshot['files']) == 16
    assert set(snapshot['active_transform_files']) == {'live_risk_node.py', 'projection.py'}
    assert snapshot['complete']
