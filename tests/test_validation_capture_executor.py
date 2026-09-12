import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('validation_executor',
    ROOT/'scripts/run_stationary_capture_plan.py')
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PLAN=ROOT/'reports/engineering_camera_settings_v2/validation_commands.json'


def inputs():
    plan=json.loads(PLAN.read_text())
    return plan,{**plan['commands'][0],'partition':'validation'}


@pytest.fixture
def historical_source_fixture(monkeypatch):
    """Only these unit cases emulate their fixture's frozen historical sources.

    Never update the real freeze or use this mock in production. Current-source
    rejection is covered independently below.
    """
    import language_nav.camera_configuration as camera
    frozen = json.loads((PLAN.parent/'camera_settings_freeze.json').read_text())['source_sha256']
    monkeypatch.setattr(camera, 'capture_source_snapshot', lambda: dict(frozen))


def test_validation_requires_explicit_scope_and_freeze(historical_source_fixture):
    plan,view=inputs()
    with pytest.raises(ValueError):
        MODULE.checked_command(view,plan,PLAN,89,25,False)
    command=MODULE.checked_command(view,plan,PLAN,89,25,False,True)
    assert command[:4]==['nice','-n','15','python3']
    assert '--capture-only' in command
    assert command[command.index('--camera-horizontal-fov')+1]=='2.0'
    assert command[command.index('--camera-settings-freeze')+1]==str(PLAN.parent/'camera_settings_freeze.json')
    assert '--allow-coexistence-trial' not in command


@pytest.mark.parametrize('field,value',[
    ('--world','/tmp/other-world'),('--camera-settings-freeze','/tmp/fake-freeze'),
    ('--camera-profile','/tmp/unfrozen.yaml'),('--camera-horizontal-fov','1.2')])
def test_validation_cannot_substitute_world_profile_freeze_or_fov(field,value):
    plan,view=inputs()
    view=copy.deepcopy(view)
    index=view['command_argv'].index(field)
    view['command_argv'][index+1]=value
    with pytest.raises(ValueError):
        MODULE.checked_command(view,plan,PLAN,89,25,False,True)


def test_profile_hash_validation_is_mandatory(monkeypatch):
    plan,view=inputs()
    def mismatch(*args,**kwargs):
        raise ValueError('camera profile differs from frozen configuration')
    monkeypatch.setattr(MODULE,'validate_camera_freeze',mismatch)
    with pytest.raises(ValueError,match='profile differs'):
        MODULE.checked_command(view,plan,PLAN,89,25,False,True)


def test_validation_serial_lifecycle_incomplete_kept_then_infrastructure_halt(tmp_path,monkeypatch,historical_source_fixture):
    runs=tmp_path/'unit_test_runs'
    runs.mkdir()
    monkeypatch.setattr(MODULE,'RUNS',runs)
    monkeypatch.setattr(MODULE,'coexistence_headroom',lambda:{'unit_test_only':True})
    monkeypatch.setattr(MODULE,'require_research2_idle',lambda:pytest.fail('explicit coexistence should not demand idle'))
    calls=[]
    def fake_run(command,env,log):
        run_id=command[command.index('--run-id')+1]
        assert '--allow-coexistence-trial' in command
        assert env['OMP_NUM_THREADS']=='2'
        directory=runs/run_id
        directory.mkdir()
        calls.append(command)
        if len(calls)==1:
            (directory/'capture_summary.json').write_text(json.dumps({
                'schema_version':'research3-stationary-capture/v1','run_id':run_id,
                'complete':False,'collision_count':0}))
            return 0
        (directory/'failure.json').write_text('{"error":"unit test infrastructure failure"}')
        return 1
    monkeypatch.setattr(MODULE,'run_owned',fake_run)
    result=MODULE.execute_plan(PLAN,tmp_path/'output',maps=['base-r011'],
                              validation=True,allow_coexistence=True)
    assert result['partition']=='validation'
    assert result['camera_settings_freeze_sha256']
    assert result['halted'] and result['not_attempted_count']==1
    assert result['attempts'][0]['status'].startswith('capture_incomplete')
    assert result['attempts'][1]['status'].startswith('halted_resource')


def test_validation_rejects_protected_filter_before_file_reads(tmp_path):
    with pytest.raises(ValueError):
        MODULE.execute_plan(tmp_path/'no-file',tmp_path/'output',maps=['base-r015'],validation=True)


def test_validation_cannot_change_pose_after_freeze(historical_source_fixture):
    plan,view=inputs()
    view=copy.deepcopy(view)
    index=view['command_argv'].index('--capture-pose')
    # Valid free-space tweak must still fail frozen view identity.
    view['command_argv'][index+1]=str(float(view['command_argv'][index+1])+.01)
    with pytest.raises(ValueError,match='frozen view'):
        MODULE.checked_command(view,plan,PLAN,89,25,False,True)


def test_legacy_v1_camera_freeze_cannot_authorize_validation_execution():
    path=ROOT/'reports/engineering_camera_settings_v1/validation_commands.json'
    plan=json.loads(path.read_text())
    view={**plan['commands'][0],'partition':'validation'}
    with pytest.raises(ValueError,match='v2 bound'):
        MODULE.checked_command(view,plan,path,89,25,False,True)


def test_validation_source_change_rejected_before_launch(monkeypatch):
    import language_nav.camera_configuration as camera
    plan,view=inputs()
    original=camera.capture_source_snapshot
    monkeypatch.setattr(camera,'capture_source_snapshot',lambda:{**original(),'scripts/run_physical_episode.py':'0'*64})
    with pytest.raises(ValueError,match='source identity changed'):
        MODULE.checked_command(view,plan,PLAN,89,25,False,True)


def test_future_serial_batch_stops_when_source_snapshot_changes(tmp_path,monkeypatch,historical_source_fixture):
    runs=tmp_path/'runs'
    runs.mkdir()
    monkeypatch.setattr(MODULE,'RUNS',runs)
    monkeypatch.setattr(MODULE,'coexistence_headroom',lambda:{'synthetic':True})
    monkeypatch.setattr(MODULE,'require_research2_idle',lambda:None)
    changed=[False]
    monkeypatch.setattr(MODULE,'capture_source_snapshot',lambda:{'synthetic_source':'new' if changed[0] else 'old'})
    launches=[]
    def run(command,env,log):
        run_id=command[command.index('--run-id')+1]
        directory=runs/run_id
        directory.mkdir()
        (directory/'capture_summary.json').write_text(json.dumps({
            'schema_version':'research3-stationary-capture/v1','run_id':run_id,
            'complete':False,'collision_count':0}))
        launches.append(run_id)
        changed[0]=True
        return 0
    monkeypatch.setattr(MODULE,'run_owned',run)
    result=MODULE.execute_plan(PLAN,tmp_path/'output',maps=['base-r011'],validation=True)
    assert len(launches)==1 and result['halted']
    assert 'source snapshot changed' in result['attempts'][-1]['error']
    assert result['not_attempted_count']==1


def test_historical_real_v2_freeze_refuses_current_changed_runtime():
    import language_nav.camera_configuration as camera
    frozen = json.loads((PLAN.parent/'camera_settings_freeze.json').read_text())['source_sha256']
    assert frozen != camera.capture_source_snapshot(), 'this regression requires the known runtime revision change'
    plan, view = inputs()
    with pytest.raises(ValueError, match='source identity changed'):
        MODULE.checked_command(view, plan, PLAN, 89, 25, False, True)


def test_capture_snapshot_covers_every_owned_runner_prepare_source():
    import runpy
    from language_nav.camera_configuration import capture_source_snapshot
    runner=runpy.run_path(str(ROOT/'scripts/run_physical_episode.py'))
    request,_,_=runner['prepare'](ROOT/'data/physical_worlds_readable_v1/base-r001',
        'base-r001-truthful_original-s0','source-subset-preflight',89)
    snapshot=capture_source_snapshot()
    assert all(snapshot.get(name)==digest for name,digest in request['source_sha256'].items())
