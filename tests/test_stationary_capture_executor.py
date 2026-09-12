import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('stationary_executor',
    ROOT/'scripts/run_stationary_capture_plan.py')
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PLAN=ROOT/'reports/stationary_capture_plan_v1/plan.json'


def test_checked_argv_uses_owned_runner_bounded_resources_and_explicit_override():
    plan=json.loads(PLAN.read_text())
    view=plan['views'][0]
    command=MODULE.checked_command(view,plan,PLAN,89,25,False)
    assert command[:4]==['nice','-n','15','python3']
    assert command[command.index('--timeout')+1]=='25'
    assert command[command.index('--ros-domain-id')+1]=='89'
    assert '--allow-coexistence-trial' not in command
    assert MODULE.checked_command(view,plan,PLAN,89,25,True)[-1]=='--allow-coexistence-trial'


@pytest.mark.parametrize('mutation',[
    lambda v:v['command_argv'].__setitem__(0,'bash'),
    lambda v:v['command_argv'].__setitem__(1,'/tmp/arbitrary.py'),
    lambda v:v['command_argv'].extend(['--allow-coexistence-trial']),
    lambda v:v.update(partition='validation'),
    lambda v:v.update(run_id='../escape'),
])
def test_tampered_plan_commands_rejected(mutation):
    plan=json.loads(PLAN.read_text())
    view=copy.deepcopy(plan['views'][0])
    mutation(view)
    with pytest.raises(ValueError):
        MODULE.checked_command(view,plan,PLAN,89,25,False)


def setup_execution(monkeypatch,tmp_path):
    monkeypatch.setattr(MODULE,'RUNS',tmp_path/'runs')
    MODULE.RUNS.mkdir()
    monkeypatch.setattr(MODULE,'checked_command',lambda *args:['nice','-n','15','fake'])
    monkeypatch.setattr(MODULE,'coexistence_headroom',lambda:{'cpu_pressure_avg10':1})
    monkeypatch.setattr(MODULE,'require_research2_idle',lambda:None)
    return [v for v in json.loads(PLAN.read_text())['views']
            if v['base_instruction_id']=='base-r001']


def test_serial_incomplete_retained_existing_skipped_and_infra_halts(monkeypatch,tmp_path):
    views=setup_execution(monkeypatch,tmp_path)
    (MODULE.RUNS/views[0]['run_id']).mkdir()
    calls=[]
    def fake_run(command,env,log):
        assert env['OMP_NUM_THREADS']==env['OPENBLAS_NUM_THREADS']=='2'
        view=views[len(calls)+1]
        calls.append(command)
        directory=MODULE.RUNS/view['run_id']
        directory.mkdir()
        if len(calls)==1:
            (directory/'capture_summary.json').write_text(json.dumps({
                'schema_version':'research3-stationary-capture/v1','run_id':view['run_id'],
                'complete':False,'collision_count':0,'frames_captured':0,'context_frames':1}))
            return 0
        (directory/'failure.json').write_text(json.dumps({'error':'resource limit exceeded'}))
        return 1
    monkeypatch.setattr(MODULE,'run_owned',fake_run)
    result=MODULE.execute_plan(PLAN,tmp_path/'output',maps=['base-r001'])
    assert len(calls)==2
    assert result['attempts'][0]['status'].startswith('skipped_existing')
    assert result['attempts'][1]['status'].startswith('capture_incomplete')
    assert result['attempts'][2]['status'].startswith('halted_resource')
    assert result['halted']
    with pytest.raises(FileExistsError):
        MODULE.execute_plan(PLAN,tmp_path/'output',maps=['base-r001'])


def test_resource_failure_stops_before_any_subprocess(monkeypatch,tmp_path):
    setup_execution(monkeypatch,tmp_path)
    def resource_failure():
        raise RuntimeError('insufficient headroom')
    monkeypatch.setattr(MODULE,'coexistence_headroom',resource_failure)
    monkeypatch.setattr(MODULE,'run_owned',lambda *args:pytest.fail('unexpected simulator launch'))
    result=MODULE.execute_plan(PLAN,tmp_path/'output',maps=['base-r001'])
    assert result['halted']
    assert result['not_attempted_count']==2
    assert len(result['attempts'])==1


def test_heldout_filter_rejected_before_reading_plan(tmp_path):
    with pytest.raises(ValueError):
        MODULE.execute_plan(tmp_path/'does-not-exist.json',tmp_path/'output',maps=['base-r015'])
