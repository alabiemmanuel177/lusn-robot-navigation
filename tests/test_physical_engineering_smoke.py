import copy
import importlib.util
import json
import fcntl
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('engineering_smoke',ROOT/'scripts/physical_engineering_smoke.py')
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.fixture
def plan(tmp_path,monkeypatch):
    monkeypatch.setattr(MODULE,'LOCK',tmp_path/'unit-execution.lock')
    monkeypatch.setattr(MODULE,'require_no_live_runner',lambda:None)
    path=tmp_path/'engineering-plan.json'
    return path,MODULE.prepare_plan(path)


def test_exact_eleven_new_cases_and_retained_attribute_reference(plan):
    _,payload=plan
    cases=payload['cases']
    assert len(cases)==11
    assert len({case['run_id'] for case in cases})==11
    assert sum(case['system_id']=='B6' for case in cases)==7
    assert all(case['condition']!='attribute_corruption' for case in cases)
    assert payload['retained_attribute_reference']['condition']=='attribute_corruption'
    assert not payload['full_campaign_completed']
    assert not payload['power_or_seed_adequacy_claimed']
    missing=next(case for case in cases if case['condition']=='missing_landmark')
    assert 'physical_absence_worlds_v1' in missing['request_preflight']['world_directory']
    assert all(case['request_preflight']['partition']=='development' for case in cases)


def test_checked_command_preserves_runtime_sources_and_bounded_controls(plan):
    _,payload=plan
    for case in payload['cases']:
        command=MODULE.checked_command(payload,case,False)
        assert command[:4]==['nice','-n','15','python3']
        assert command[command.index('--timeout')+1]=='90'
        assert command[command.index('--simulation-seed')+1]=='1'
        assert command[command.index('--camera-horizontal-fov')+1]=='2.0'
        assert command[command.index('--ros-domain-id')+1]=='89'
        assert '--allow-coexistence-trial' not in command
        assert '--capture-only' not in command
    assert MODULE.checked_command(payload,payload['cases'][0],True)[-1]=='--allow-coexistence-trial'


@pytest.mark.parametrize('mutation',[
    lambda p,c:p.update(protected_data_used=True),
    lambda p,c:p.update(timeout_s=120),
    lambda p,c:p.update(profile_path='/tmp/arbitrary.yaml'),
    lambda p,c:c.update(run_id='../escape'),
    lambda p,c:c.update(condition='heldout'),
    lambda p,c:c['request_preflight']['source_sha256'].update({'fake.py':'bad'}),
])
def test_tampered_plan_rejected(plan,mutation):
    _,original=plan
    payload=copy.deepcopy(original)
    case=payload['cases'][0]
    mutation(payload,case)
    with pytest.raises(ValueError):
        MODULE.checked_command(payload,case,False)


def test_create_once_plan(plan):
    path,_=plan
    before=path.read_bytes()
    with pytest.raises(FileExistsError):
        MODULE.prepare_plan(path)
    assert path.read_bytes()==before


def test_serial_retains_normal_failure_skips_existing_and_halts_infrastructure(plan,tmp_path,monkeypatch):
    path,payload=plan
    runs=tmp_path/'synthetic-runs'
    runs.mkdir()
    monkeypatch.setattr(MODULE,'RUNS',runs)
    (runs/payload['cases'][0]['run_id']).mkdir()
    (runs/payload['cases'][0]['run_id']/'summary.json').write_text('{}')
    monkeypatch.setattr(MODULE,'coexistence_headroom',lambda:{'unit_test_only':True})
    monkeypatch.setattr(MODULE,'require_research2_idle',lambda:None)
    calls=[]
    def fake_run(command,env,log,lock_fd):
        assert env['OMP_NUM_THREADS']==env['OPENBLAS_NUM_THREADS']=='2'
        run_id=command[command.index('--run-id')+1]
        directory=runs/run_id
        directory.mkdir()
        calls.append(run_id)
        if len(calls)==2:
            return 1
        (directory/'measurements.json').write_text('{"unit_test_only":true}')
        (directory/'summary.json').write_text(json.dumps({
            'schema_version':'research3-live-summary/v3','run_id':run_id,'partition':'development',
            'infrastructure_failure':False,'collision':False,'timeout':False,'instruction_completion':False,
            'trajectory_quality':{'valid':True},'measurements_sha256':MODULE.digest(directory/'measurements.json')}))
        return 0
    monkeypatch.setattr(MODULE,'run_locked',fake_run)
    result=MODULE.execute_plan(path,tmp_path/'batch',max_cases=11)
    assert len(calls)==2
    assert result['attempts'][0]['status'].startswith('skipped_existing')
    assert result['attempts'][1]['status'].startswith('measured_engineering_outcome')
    assert result['attempts'][2]['status'].startswith('halted_resource')
    assert result['halted'] and result['not_attempted_count']==8


def test_resource_guard_halts_before_any_launch(plan,tmp_path,monkeypatch):
    path,_=plan
    monkeypatch.setattr(MODULE,'RUNS',tmp_path/'no-runs')
    def fail():
        raise RuntimeError('resource limit')
    monkeypatch.setattr(MODULE,'coexistence_headroom',fail)
    monkeypatch.setattr(MODULE,'run_locked',lambda *args:pytest.fail('unexpected live launch'))
    result=MODULE.execute_plan(path,tmp_path/'batch')
    assert result['halted'] and result['not_attempted_count']==10


def test_child_inherited_lock_survives_parent_descriptor_close(tmp_path):
    lock=tmp_path/'inherited.lock'
    fd=os.open(lock,os.O_CREAT|os.O_RDWR,0o600)
    fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    # Benign child only: wait on stdin, no simulation or external state.
    child=subprocess.Popen([sys.executable,'-c',
        'import sys; print("ready",flush=True); sys.stdin.read()'],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,pass_fds=(fd,))
    other=None
    try:
        assert child.stdout.readline().strip()=='ready'
        os.close(fd)
        fd=None
        other=os.open(lock,os.O_RDWR)
        with pytest.raises(BlockingIOError):
            fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
        child.communicate('',timeout=3)
        fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=3)
        if fd is not None:os.close(fd)
        if other is not None:os.close(other)


def test_live_runner_guard_matches_argv_not_shell_text(tmp_path):
    for pid,args in ((101,['python3',str(MODULE.RUNNER),'--run-id','owned']),
                     (102,['zsh','-c','ps mentions '+str(MODULE.RUNNER)]),
                     (103,['python3','/home/eao/failure-prediction/scripts/run_campaign_parallel.py'])):
        directory=tmp_path/str(pid)
        directory.mkdir()
        (directory/'cmdline').write_bytes(('\0'.join(args)+'\0').encode())
    assert MODULE.live_runner_pids(tmp_path)==[101]


def test_explicit_retry_keeps_original_and_never_replaces_completed_case(plan,tmp_path,monkeypatch):
    _,payload=plan
    case=next(case for case in payload['cases'] if case['condition']=='false_inserted_clause')
    runs=tmp_path/'retry-fixtures'
    monkeypatch.setattr(MODULE,'RUNS',runs)
    original=runs/case['run_id']
    original.mkdir(parents=True)
    failure=original/'failure.json'
    failure.write_text('{"error_type":"KeyboardInterrupt","dispatched":false}')
    before=failure.read_bytes()
    retry=case['run_id']+'-retry-a'
    command=MODULE.checked_command(payload,case,False,retry)
    assert command[command.index('--run-id')+1]==retry
    assert failure.read_bytes()==before
    (original/'summary.json').write_text('{}')
    with pytest.raises(ValueError,match='completed outcomes'):
        MODULE.checked_command(payload,case,False,retry)


def test_active_runner_rejected_before_plan_or_output_access(tmp_path,monkeypatch):
    monkeypatch.setattr(MODULE,'LOCK',tmp_path/'unit.lock')
    def active():
        raise RuntimeError('owned live runner still exists')
    monkeypatch.setattr(MODULE,'require_no_live_runner',active)
    with pytest.raises(RuntimeError,match='still exists'):
        MODULE.execute_plan(tmp_path/'no-plan',tmp_path/'no-output')
    assert not (tmp_path/'no-output').exists()


def test_runtime_child_receives_lock_descriptor(monkeypatch,tmp_path):
    recorded={}
    class Child:
        def wait(self,timeout):return 0
    def popen(command,**kwargs):
        recorded.update(kwargs)
        return Child()
    monkeypatch.setattr(MODULE.subprocess,'Popen',popen)
    assert MODULE.run_locked(['fake'],{},None,42)==0
    assert recorded['pass_fds']==(42,)
    assert recorded['start_new_session'] is True
