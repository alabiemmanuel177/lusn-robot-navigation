"""Synthetic orchestration fixtures; no ROS dispatch, QA or genuine labels."""
import fcntl
import hashlib
import json
from pathlib import Path
import runpy

import pytest

TOOL = runpy.run_path(str(Path(__file__).parents[1] / 'scripts/prepare_current_capture_plan.py'))


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    root = tmp_path
    directory = root / 'plan'
    (directory / 'profiles').mkdir(parents=True)
    runs = root / 'runs'
    runs.mkdir()
    world = root / 'data/physical_worlds_readable_v1/base-r001'
    world.mkdir(parents=True)
    hashes = {}
    for name in TOOL['ASSETS']:
        path = world / name
        path.write_text('synthetic world bytes')
        hashes[name] = TOOL['sha'](path)
    profile = directory / 'profiles/base-r001.yaml'
    profile.write_text('synthetic profile bytes')
    snapshot = {'source_sha256': {'synthetic.py': 'a' * 64},
                'provider_source_snapshot': {'files': {'synthetic-provider.py': 'b' * 64}}}
    (directory / 'current_source_snapshot.json').write_text(json.dumps(snapshot))
    (directory / 'plan.json').write_text('{}')
    view = {'run_id': 'r3-current-fixture-r001-chair', 'map_id': 'r3geo_base_r001',
            'base_instruction_id': 'base-r001', 'partition': 'development', 'phase': 'development',
            'category': 'chair', 'world_directory': str(world), 'asset_sha256': hashes,
            'profile_file': 'profiles/base-r001.yaml', 'profile_sha256': TOOL['sha'](profile),
            'capture_pose': {'x': 1.15, 'y': -.3, 'yaw': .8}}
    plan = {'views': [view], 'protected_data_used': False, 'snapshot_sha256': TOOL['sha'](directory / 'current_source_snapshot.json'),
            'original_plan_sha256': TOOL['sha'](directory / 'plan.json'), 'orchestration_source_sha256': {}}
    (directory / 'recapture_plan.json').write_text(json.dumps(plan))
    shared = TOOL['command'].__globals__
    monkeypatch.setitem(shared, 'ROOT', root)
    monkeypatch.setitem(shared, 'RUNS', runs)
    monkeypatch.setitem(shared, 'RUNNER', root / 'scripts/run_physical_episode.py')
    monkeypatch.setitem(shared, 'validate_capture_source_freeze', lambda path: plan['snapshot_sha256'])
    smoke = {**TOOL['SMOKE'], 'LOCK': root / 'owned.lock',
             'require_no_live_runner': lambda: None, 'coexistence_headroom': lambda: {},
             'require_research2_idle': lambda: None}
    monkeypatch.setitem(shared, 'SMOKE', smoke)
    return directory, plan, view, runs, smoke


def test_command_reconstructed_from_fields_ignores_embedded_arbitrary_argv(fixture):
    directory, plan, view, _, _ = fixture
    view['command_argv'] = ['do-not-execute-arbitrary-command']
    argv = TOOL['command'](plan, view, directory, True)
    assert argv[:4] == ['nice', '-n', '15', 'python3']
    assert '--capture-only' in argv and '--capture-source-freeze' in argv
    assert argv[argv.index('--timeout') + 1] == '25'
    assert '--allow-coexistence-trial' in argv
    assert 'do-not-execute-arbitrary-command' not in argv


def test_changed_profile_and_protected_scope_fail_before_dispatch(fixture):
    directory, plan, view, _, _ = fixture
    (directory / view['profile_file']).write_text('changed')
    with pytest.raises(ValueError, match='profile/world changed'):
        TOOL['command'](plan, view, directory, False)
    view['partition'] = 'held_out'
    with pytest.raises(ValueError, match='nonprotected'):
        TOOL['command'](plan, view, directory, False)


def test_single_dispatch_passes_inherited_lock_and_thread_caps(fixture, tmp_path):
    directory, plan, view, _, smoke = fixture
    calls = []
    def run(argv, env, log, fd):
        assert fd >= 0
        assert all(env[key] == '2' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'))
        calls.append(argv)
        return 0
    smoke['run_locked'] = run
    output = tmp_path / 'dispatch'
    result = TOOL['dispatch'](directory, view['run_id'], TOOL['sha'](directory / 'recapture_plan.json'), output)
    assert result == 0 and len(calls) == 1
    assert (output / 'start.json').is_file() and (output / 'finish.json').is_file()
    with pytest.raises(FileExistsError):
        TOOL['dispatch'](directory, view['run_id'], TOOL['sha'](directory / 'recapture_plan.json'), output)
    assert len(calls) == 1


def test_existing_run_never_relaunched(fixture, tmp_path):
    directory, _, view, runs, _ = fixture
    (runs / view['run_id']).mkdir()
    with pytest.raises(ValueError, match='existing runs'):
        TOOL['dispatch'](directory, view['run_id'], TOOL['sha'](directory / 'recapture_plan.json'), tmp_path / 'out')


def test_child_holding_lock_prevents_dispatch(fixture, tmp_path):
    directory, _, view, _, smoke = fixture
    with Path(smoke['LOCK']).open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            TOOL['dispatch'](directory, view['run_id'], TOOL['sha'](directory / 'recapture_plan.json'), tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_old_capture_missing_provider_and_checkpoints_cannot_pass_audit(fixture, tmp_path, monkeypatch):
    directory, plan, view, runs, _ = fixture
    snapshot = json.loads((directory / 'current_source_snapshot.json').read_text())
    run = runs / view['run_id']
    run.mkdir()
    request = {**view, 'source_sha256': snapshot['source_sha256'], 'protected_test_routes_used': False,
               'camera_profile_sha256': view['profile_sha256'], 'camera_horizontal_fov': 2.0}
    (run / 'request.json').write_text(json.dumps(request))
    archive = tmp_path / 'synthetic.archive'
    archive.write_text('synthetic pinned bytes')
    monkeypatch.setitem(TOOL['audit'].__globals__, 'PACK', {
        'capture_source_archive_paths': lambda *a: None,
        'verify_archive': lambda *a: {'capture_source_snapshot': snapshot,
                                    'source_snapshot_input_sha256': plan['snapshot_sha256']}})
    monkeypatch.setitem(TOOL['audit'].__globals__, 'validate_capture_source_freeze',
                        lambda *a: pytest.fail('historical audit must not substitute current source hashes'))
    report = TOOL['audit'](directory, archive, TOOL['sha'](archive))
    assert not report['all_46_source_bound']
    assert 'missing_or_mismatched_provider_source_snapshot' in report['rows'][0]['gaps']
    assert 'source_guard_checkpoint_evidence_missing_or_mismatched' in report['rows'][0]['gaps']
