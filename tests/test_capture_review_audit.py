"""Synthetic report invariants; underlying join/source validators have own tests."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

SPEC=importlib.util.spec_from_file_location('fresh_packet_audit',Path(__file__).parents[1]/'scripts/audit_capture_review_packet.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


@pytest.fixture
def packet(tmp_path,monkeypatch):
    def save(path,value):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))
    plan=tmp_path/'plan';packet=tmp_path/'packet';packet.mkdir()
    world=tmp_path/'world';world.mkdir();(world/'world.sdf').write_text('synthetic')
    directories=[]
    for n in range(46):
        run=tmp_path/'runs'/f'run-{n}';directories.append(run)
        save(run/'request.json',dict(run_id=run.name,map_id=f'r3geo_base_r{n%14+1:03d}',
            partition='development' if n%14<10 else 'validation',protected_test_routes_used=False,
            capture_only=True,world_directory=str(world),asset_sha256={'world.sdf':M.PACK.digest((world/'world.sdf').read_bytes())}))
        save(run/'capture_summary.json',dict(run_id=run.name,complete=True,collision_count=0,
            motion_commands_sent=False,navigation_episode=False,protected_test_routes_used=False,human_labels_generated=False))
        save(run/'resource_guard.json',dict(samples=[dict(available_memory_kib=1000+n,cpu_pressure_avg10=n/10,load1=n/5)]))
    save(plan/'recapture_plan.json',dict(views=[dict(run_id=run.name) for run in directories]))
    save(packet/'packet_manifest.json',dict(run_directories=[str(path) for path in directories]))
    items=[dict(run_id=directories[n%46].name,observation_id=f'observation-{n}',correct=None,human_reviewer_id='') for n in range(60)]
    inventory=dict(status='ready_for_human_review',coverage_complete=True,selected_ready_items=60,
        selected_missing_items=0,coverage=[{} for _ in range(56)],items=items,selected_ready=items,
        qa_input_sha256=M.PACK.digest(b''))
    save(packet/'inventory.json',inventory);save(packet/'sampling_policy.json',dict(targets=[{} for _ in range(60)]))
    (packet/'combined_visual_qa.jsonl').write_bytes(b'')
    monkeypatch.setattr(M.PACK,'current_capture_plan_paths',lambda *a:[])
    monkeypatch.setattr(M.PACK,'review_packet_paths',lambda *a:([],{'packet_manifest_sha256':'synthetic'}))
    monkeypatch.setattr(M.SOURCE,'audit',lambda *a:{'all_46_source_bound':True})
    monkeypatch.setattr(M.PREP.CONSOLIDATE,'consolidate',lambda *a,**k:copy.deepcopy(inventory))
    return tmp_path,packet,plan,directories,inventory,save


def call(fixture):
    root,packet,plan,*_=fixture
    return M.audit(packet,plan,root/'unused-synthetic-archive','synthetic-sha',root=root)


def test_synthetic_46_run_resource_aggregation_and_claim_limits(packet):
    result=call(packet)
    assert result['runs']==46 and result['targets']==60
    assert result['minimum_available_memory_kib']==1000
    assert result['maximum_cpu_pressure_avg10']==4.5
    assert result['maximum_load1']==9.
    assert not result['research2_performance_unchanged_proven']
    assert not result['human_labels_generated'] and not result['independent_visual_inspection_performed']


@pytest.mark.parametrize('field,value',[('complete',False),('collision_count',1),('motion_commands_sent',True)])
def test_capture_failure_or_motion_blocks_report(packet,field,value):
    root,p,plan,dirs,inventory,save=packet
    summary=json.loads((dirs[0]/'capture_summary.json').read_text());summary[field]=value
    save(dirs[0]/'capture_summary.json',summary)
    with pytest.raises(ValueError,match='stationary capture'):call(packet)


def test_source_binding_failure_blocks_report(packet,monkeypatch):
    monkeypatch.setattr(M.SOURCE,'audit',lambda *a:{'all_46_source_bound':False})
    with pytest.raises(ValueError,match='archived source'):call(packet)


def test_selected_duplicate_rejected(packet):
    root,p,plan,dirs,inventory,save=packet
    inventory['selected_ready'][1]['observation_id']=inventory['selected_ready'][0]['observation_id']
    save(p/'inventory.json',inventory)
    with pytest.raises(ValueError,match='globally unique'):call(packet)


def test_labelled_inventory_is_not_reported_unlabelled(packet):
    root,p,plan,dirs,inventory,save=packet
    inventory['items'][0]['correct']=True
    save(p/'inventory.json',inventory)
    with pytest.raises(ValueError,match='human labels'):call(packet)


def test_protected_request_rejected_before_source_audit(packet,monkeypatch):
    root,p,plan,dirs,inventory,save=packet
    request=json.loads((dirs[0]/'request.json').read_text());request['map_id']='r3geo_base_r015'
    save(dirs[0]/'request.json',request)
    monkeypatch.setattr(M.SOURCE,'audit',lambda *a:pytest.fail('source audit must not see protected request'))
    with pytest.raises(ValueError,match='protected'):call(packet)
