import copy
import importlib
import pytest


def test_fixed_stage_a_only():
    import run_redesign_stage_a as a
    rows=a.assignments()
    assert len(rows)==144
    assert {r['map_id'] for r in rows}=={'r3geo_base_r001','r3geo_base_r006'}
    assert all(r['simulator_seed']==7 and not r['calibration_eligible'] for r in rows)
    a.validate_pins()


@pytest.mark.parametrize('key,value',[
    ('partition','validation'),('entity_id','wrong'),('lighting_scale',.7),
    ('simulator_seed',11),('panel','primary_candidate'),('capture_pose',dict(x=0,y=0,yaw=0))])
def test_reject_unscheduled(key,value):
    import run_redesign_stage_a as a
    row=copy.deepcopy(a.assignments()[0]);row[key]=value
    with pytest.raises(ValueError):a.validate_row(row)


def test_lighting_assets_and_no_import_patch():
    import run_physical_episode as r
    original=r.physical_simulation_command
    import run_redesign_stage_a as a
    importlib.reload(a)
    assert r.physical_simulation_command is original
    seen=set()
    for row in a.assignments():
        if row['derivative_world_path'] not in seen:
            a.validate_row(row);seen.add(row['derivative_world_path'])
    assert len(seen)==6


def test_stationary_command():
    import run_redesign_stage_a as a
    command=a.runner_args(a.assignments()[0],100)
    assert '--capture-only' in command and '--calibration' not in command
    assert '--diagnostic-derivative' not in command
    with pytest.raises(ValueError):a.runner_args(a.assignments()[0],1)


@pytest.mark.parametrize('key,value',[
    ('simulation_seed',1),('capture_only',False),('calibration_sha256','fake'),
    ('capture_target_entity_id','wrong'),('camera_horizontal_fov',1.),
    ('protected_test_routes_used',True)])
def test_independent_request_audit_rejects_drift(key,value):
    import json
    import run_redesign_stage_a as a
    from audit_redesign_stage_a import check_request
    plan=json.loads((a.OUTPUT/'execution_plan.json').read_bytes())
    request=copy.deepcopy(plan['rows'][0]['request'])
    check_request(request,a.assignments()[0])
    request[key]=value
    with pytest.raises(ValueError):check_request(request,a.assignments()[0])
