import copy
import itertools
import json
import pytest
import distance_lighting_pilot as pilot


def test_fixed_factorial():
    rows=pilot.build_rows()
    actual={(r['map_id'],r['category'],r['distance_fraction'],r['yaw_offset_rad'],r['lighting_scale']) for r in rows}
    expected={(f'r3geo_base_r{n:03}',c,d,y,l) for n in (1,6) for c in pilot.CLASSES
              for d in (.5,1.) for y in (0.,.65 if n==1 else -.65) for l in (1.,.9,.8)}
    assert actual==expected and len(rows)==96
    assert rows==pilot.build_rows()
    assert all(r['simulator_seed']==9 and not r['calibration_eligible'] and r['human_verdict'] is None for r in rows)


def test_capture_only_arguments():
    args=pilot.arguments(pilot.build_rows()[0],100)
    assert args[args.index('--simulation-seed')+1]=='9'
    assert '--capture-only' in args and '--calibration' not in args
    assert '--diagnostic-derivative' not in args
    with pytest.raises(ValueError):pilot.arguments(pilot.build_rows()[0],99)


def test_no_import_mutation():
    import importlib
    import run_physical_episode as runner
    original=runner.physical_simulation_command
    importlib.reload(pilot)
    assert runner.physical_simulation_command is original


def test_diagnosed_support_saturation_is_recorded_not_labels():
    report=json.loads((pilot.ROOT/'reports/redesign_stage_a_20260923_v1/score_reconstruction.json').read_bytes())
    rows=[r for r in report['rows'] if r['category'] in ('laboratory_entrance','office_entrance')]
    assert len(rows)==58
    assert all(r['support_score']==1 and r['probability']>=.5 and r['score_reconstruction_matches'] for r in rows)
    assert report['human_labels_generated'] is False


def test_conditional_mechanism_not_guaranteed_detection():
    # A fixed algebraic illustration, not a fabricated observation/prediction.
    p=lambda s,c,d:(.45*s+.55*c)*(1-d/3)
    assert p(1,.25,.1)>.5
    assert p(.5,.25,.1)<.5
    assert p(.5,.92,.1)>.5


@pytest.mark.parametrize('key,value', [('simulation_seed',7),('capture_only',False),
    ('capture_target_entity_id','wrong'),('protected_test_routes_used',True)])
def test_independent_audit_rejects_request_drift(key,value):
    from finalize_distance_lighting_pilot import check_request
    path=pilot.OUTPUT/'execution_plan.json'
    if not path.exists():pytest.skip('requires prepared live request evidence')
    request=copy.deepcopy(json.loads(path.read_bytes())['rows'][0]['request'])
    row=pilot.rows()[0];check_request(request,row)
    request[key]=value
    with pytest.raises(ValueError):check_request(request,row)
