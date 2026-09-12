import importlib.util
import math
from pathlib import Path

import pytest
import yaml

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('stationary_plan',
    ROOT/'scripts/prepare_stationary_capture_plan.py')
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_all_views_clear_validation_gated_profiles_unvalidated(tmp_path):
    output=tmp_path/'plan'
    plan=MODULE.prepare_plan(ROOT/'data/physical_worlds_readable_v1',output)
    assert len(plan['views'])==42
    assert sum(v['command_argv'] is not None for v in plan['views'])==30
    assert len({v['run_id'] for v in plan['views']})==42
    for view in plan['views']:
        assert view['pose_occupancy_validated']
        assert view['frame_budget']==1
        assert view['full_context_retained']
        assert not view['visibility_and_detector_success_guaranteed']
        if view['partition']=='validation':
            assert view['command_argv'] is None
        else:
            assert '--capture-only' in view['command_argv']
            assert '--allow-coexistence-trial' not in view['command_argv']
    lab=next(v for v in plan['views'] if v['base_instruction_id']=='base-r010'
             and v['category']=='laboratory_entrance')
    assert lab['capture_pose']==dict(x=7.5,y=-.6,yaw=math.pi/2)
    for index in range(1,15):
        profile=yaml.safe_load((output/'profiles'/f'base-r{index:03}.yaml').read_text())
        assert not profile['confidence_calibration_validated']
        assert profile['chair_prototype_status'].startswith('predicted_unvalidated')
        assert profile['color_tolerance']==10
        assert profile['partition_scope']==(['development'] if index<=10 else [])
    assert not plan['protected_content_read']
    assert not plan['simulation_launched']


def test_create_once_and_no_heldout_reads(tmp_path,monkeypatch):
    original_bytes,original_text=Path.read_bytes,Path.read_text
    def guard(path):
        assert not any(f'base-r{i:03}' in path.parts for i in range(15,21))
    def read_bytes(path,*args,**kwargs):
        guard(path)
        return original_bytes(path,*args,**kwargs)
    def read_text(path,*args,**kwargs):
        guard(path)
        return original_text(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_bytes',read_bytes)
    monkeypatch.setattr(Path,'read_text',read_text)
    output=tmp_path/'plan'
    MODULE.prepare_plan(ROOT/'data/physical_worlds_readable_v1',output)
    with pytest.raises(FileExistsError):
        MODULE.prepare_plan(ROOT/'data/physical_worlds_readable_v1',output)


def test_category_targeting_only_when_runner_supports_it(tmp_path):
    runner=tmp_path/'runner.py'
    runner.write_text("parser.add_argument('--capture-target-category')\n")
    plan=MODULE.prepare_plan(ROOT/'data/physical_worlds_readable_v1',tmp_path/'plan',runner=runner)
    for view in plan['views']:
        assert view['category_targeting_supported']
        if view['command_argv']:
            assert view['command_argv'][-2:]==['--capture-target-category',view['category']]


@pytest.mark.parametrize('domain',[0,102,True])
def test_invalid_domain_rejected(tmp_path,domain):
    with pytest.raises(ValueError):
        MODULE.prepare_plan(ROOT/'data/physical_worlds_readable_v1',tmp_path/'plan',domain)
