import copy
import importlib.util
import json
from pathlib import Path

import pytest

import language_nav.campaign_authorization as AUTH

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('synthetic_approved_campaign_fixture',ROOT/'tests/test_physical_campaign_executor.py')
FIXTURE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)
prepared=FIXTURE.prepared


def supplied_for(job):
    argv=job['argv'][3:]
    return {key[2:].replace('-','_'):value for key,value in zip(argv[::2],argv[1::2],strict=True)}


def test_existing_full_approval_gates_are_reused_for_exact_episode(prepared):
    root,manifest,approval=prepared
    _,jobs=AUTH.approved_jobs(manifest,approval,root)
    supplied=supplied_for(jobs[0])
    binding=AUTH.validate_campaign_episode(supplied,root=root)
    assert binding['episode_id']==jobs[0]['episode_id']
    assert binding['authorization_scope']=='nonprotected_campaign'
    payload=json.loads(approval.read_text())
    payload['status']='draft'
    approval.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='approval'):
        AUTH.validate_campaign_episode(supplied,root=root)


@pytest.mark.parametrize('key,value',[
    ('run_id','different'),('world','/tmp/unapproved'),('system_id','B5'),
    ('timeout',999),('calibration','/tmp/other.json'),('camera_horizontal_fov',2.0),
    ('campaign_episode_id','not-approved'),('allow_coexistence_trial',True),
])
def test_exact_runtime_options_cannot_be_changed(prepared,key,value):
    root,manifest,approval=prepared
    _,jobs=AUTH.approved_jobs(manifest,approval,root)
    supplied=supplied_for(jobs[0])
    supplied[key]=value
    with pytest.raises(ValueError):
        AUTH.validate_campaign_episode(supplied,root=root)


def test_validation_fov_requires_full_campaign_binding_not_engineering_freeze(tmp_path,monkeypatch):
    approval,manifest=tmp_path/'synthetic-approval',tmp_path/'synthetic-manifest'
    approval.write_text('synthetic-unit-fixture')
    manifest.write_text('synthetic-unit-fixture')
    supplied=dict(world=str(tmp_path/'data/base-r011'),variant_id='base-r011-truthful_original-s0',
        run_id='synthetic-val-run',ros_domain_id=89,simulation_seed=1,timeout=90,
        system_id='B6',calibration=str(tmp_path/'synthetic-calibration'),
        camera_profile=str(tmp_path/'synthetic-profile'),camera_horizontal_fov=2.,
        campaign_authorization=str(approval),campaign_manifest=str(manifest),campaign_episode_id='synthetic-val')
    argv=['python3','-u',str(tmp_path/'scripts/run_approved_physical_episode.py')]
    for key,value in supplied.items():argv.extend(['--'+key.replace('_','-'),str(value)])
    def checked_jobs(*args):
        return {'episodes':[{'episode_id':'synthetic-val','partition':'validation'}]},[
            {'episode_id':'synthetic-val','run_id':'synthetic-val-run','argv':argv}]
    monkeypatch.setattr(AUTH,'approved_jobs',checked_jobs)
    assert AUTH.validate_campaign_episode(supplied,root=tmp_path)['partition']=='validation'
    with pytest.raises(ValueError):
        AUTH.validate_campaign_episode({**supplied,'camera_horizontal_fov':1.5},root=tmp_path)


def test_campaign_lock_rejects_live_engineering_runner(tmp_path):
    (tmp_path/'reports').mkdir()
    proc=tmp_path/'synthetic-proc'
    entry=proc/'77777777'
    entry.mkdir(parents=True)
    (entry/'cmdline').write_bytes(('python3\0'+str(tmp_path/'scripts/run_physical_episode.py')+'\0').encode())
    with pytest.raises(RuntimeError,match='live runner'):
        with AUTH.exclusive_campaign_runtime(tmp_path,proc):
            pytest.fail('should not enter runtime')


def test_wrapper_prepare_supports_authorized_validation_without_editing_engineering_cli(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('approved_wrapper_unit',ROOT/'scripts/run_approved_physical_episode.py')
    wrapper=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wrapper)
    calibration=tmp_path/'synthetic-calibration.json'
    calibration.write_text('{"synthetic_unit_test":true}')
    supplied=dict(world=str(ROOT/'data/physical_worlds_readable_v1/base-r011'),
        variant_id='base-r011-truthful_original-s0',run_id='synthetic-approved-val',
        ros_domain_id=89,simulation_seed=1,timeout=90,system_id='B6',
        calibration=str(calibration),camera_profile=str(ROOT/'reports/engineering_camera_settings_v1/profiles/base-r011.yaml'),
        camera_horizontal_fov=2.)
    monkeypatch.setattr(wrapper,'validate_campaign_episode',lambda value:{
        'partition':'validation','run_id':'synthetic-approved-val','synthetic_unit_fixture':True})
    _,request,_,_=wrapper.prepare_approved(supplied)
    assert request['partition']=='validation' and request['capture_only'] is False
    assert request['camera_horizontal_fov']==2.
    assert request['allow_coexistence_trial'] is False
    assert 'camera_horizontal_fov:=2.0' in request['simulation_launch_argv']
    assert 'scripts/run_approved_physical_episode.py' in request['source_sha256']
    assert 'src/language_nav/campaign_authorization.py' in request['source_sha256']
