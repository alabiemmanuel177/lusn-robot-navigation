"""Synthetic approvals and outcomes only; never reads real protected evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('release_gate', Path(__file__).parents[1]/'scripts/check_physical_release_readiness.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


@pytest.fixture
def candidate(tmp_path):
    refs = {}
    def save(name, value):
        path = tmp_path/(name+'.json')
        path.write_text(json.dumps(value))
        refs[name] = {'path': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        return refs[name]
    approval = dict(status='approved_frozen', reviewer_type='human',
                    approved_by='synthetic-fixture-not-real-human', approved_at_utc='synthetic-time')
    design = dict(schema_version='research3-physical-experiment-design-draft/v2', status='frozen',
        analysis_proposals=dict(candidate_contrasts=['B6_minus_B1'], primary_contrast='B6_minus_B1',
             multiplicity_policy='synthetic', confirmatory_inference_method='synthetic'),
        simulator_seed=dict(confirmatory_seed_list=[1]), replication=dict(confirmatory_replications=1),
        power_inputs_requiring_freeze=dict(repetitions_per_world=1,target_effect=.1,target_power=.8,
             alpha=.05,baseline_completion=.5,paired_discordance=.3,world_intracluster_correlation=.2))
    save('design', design)
    save('calibration', {'synthetic': True})
    save('calibration_validation', dict(schema_version='research3-physical-calibration-validation/v1',
        passed=True,frozen=True,human_review_verified=True,protected_labels_used=False,
        calibration_sha256=refs['calibration']['sha256']))
    rows = [dict(episode_id=system, system_id=system,base_instruction_id='base-r001',
        variant_id='base-r001-truthful_original-s0',partition='development',paired_block_index=0,
        condition='truthful_original') for system in ('B1','B6')]
    save('schedule',dict(schema_version='research3-physical-comparison-plan/v1',episodes=rows))
    save('outcomes',[dict(row,schema_version='research3-physical-campaign-outcome/v1',
        attempted=True,dispatched=True,infrastructure_failure=False,evaluation_mode='physical_live',
        navigation_success=False,instruction_completion=False,terminal_identity_correct=False,
        collision=False,timeout=True) for row in rows])
    save('design_approval',dict(approval,schema_version='research3-physical-execution-approval/v1',
        authorization_scope='nonprotected_campaign',manifest_sha256=refs['schedule']['sha256'],
        **{k:refs[k] for k in ('design','calibration','calibration_validation')}))
    save('heldout_report',dict(schema_version='research3-physical-heldout-audit/v1',
        evidence_scope='physical_world_heldout',passed=True,complete=True,authorized=True,
        independent_measurement_verified=True,scheduled_count=1,audited_count=1,
        unresolved=[],
        audited_episode_ids=['synthetic-heldout-slot'],scheduled_episode_ids=['synthetic-heldout-slot'],
        design_sha256=refs['design']['sha256'],calibration_sha256=refs['calibration']['sha256']))
    save('heldout_authorization',dict(approval,schema_version='research3-physical-heldout-authorization/v1',
        authorization_scope='physical_heldout_report_verification',heldout_report=refs['heldout_report'],
        scheduled_episode_ids=['synthetic-heldout-slot'],design_sha256=refs['design']['sha256'],
        calibration_sha256=refs['calibration']['sha256']))
    save('inference',dict(approval,schema_version='research3-physical-final-inference/v1',
        evaluation_mode='physical_live',design_sha256=refs['design']['sha256'],schedule_sha256=refs['schedule']['sha256'],
        outcomes_sha256=refs['outcomes']['sha256'],heldout_report_sha256=refs['heldout_report']['sha256'],
        primary_contrast='B6_minus_B1',multiplicity_policy='synthetic',confirmatory_inference_method='synthetic',
        scheduled_missingness_accounted=True,full_schedule_analyzed=True,limitations=['Synthetic only'],
        results={'synthetic_result':0}))
    save('inventory',dict(schema_version='research3-local-file-manifest/v1',files=list(refs.values())))
    return tmp_path,dict(schema_version='research3-scientific-release-candidate/v1',inputs=refs),save


def test_missing_inputs_default_deny_no_protected_access(tmp_path, monkeypatch):
    monkeypatch.setattr(Path,'read_bytes',lambda self:pytest.fail('no supplied inputs should be read'))
    result=M.check(tmp_path,dict(schema_version='research3-scientific-release-candidate/v1',inputs={}))
    assert not result['scientific_release_complete'] and not result['protected_report_read']
    assert 'missing_input:heldout_report' in result['blockers']


def test_default_protected_report_unopened(candidate, monkeypatch):
    root,c,_=candidate
    original=Path.read_bytes
    def guarded(path):
        if path.name in ('heldout_report.json','heldout_authorization.json','inventory.json'):
            pytest.fail('default gate must not open protected report or inventory')
        return original(path)
    monkeypatch.setattr(Path,'read_bytes',guarded)
    result=M.check(root,c)
    assert not result['scientific_release_complete'] and not result['protected_report_read']


def test_all_synthetic_gates_pass_even_when_navigation_failed(candidate):
    root,c,_=candidate
    result=M.check(root,c,allow_authorized_heldout_report=True)
    assert result['blockers']==[]
    assert result['byte_integrity_passed'] and result['scientific_release_complete']
    assert not result['inference_generated']


@pytest.mark.parametrize('change', ['graph','partial','unknown','duplicate','calibration','design','method'])
def test_prerequisite_failure_blocks_before_protected(candidate,change,monkeypatch):
    root,c,save=candidate
    name='outcomes' if change in ('graph','partial','unknown','duplicate') else 'calibration_validation' if change=='calibration' else 'design' if change=='design' else 'inference'
    value=json.loads((root/(name+'.json')).read_text())
    if change=='graph':value[0]['evaluation_mode']='graph'
    elif change=='partial':value.pop()
    elif change=='unknown':value[0]['collision']=None
    elif change=='duplicate':value[1]=dict(value[0])
    elif change=='calibration':value['human_review_verified']=False
    elif change=='design':value['status']='draft'
    else:value['confirmatory_inference_method']='different'
    save(name,value)
    original=Path.read_bytes
    def guarded(path):
        if path.name=='heldout_report.json':pytest.fail('protected read before prerequisites')
        return original(path)
    monkeypatch.setattr(Path,'read_bytes',guarded)
    result=M.check(root,c,allow_authorized_heldout_report=True)
    assert result['blockers'] and not result['protected_report_read']


def test_unauthorized_report_not_opened(candidate,monkeypatch):
    root,c,save=candidate
    value=json.loads((root/'heldout_authorization.json').read_text());value['reviewer_type']='assistant';save('heldout_authorization',value)
    original=Path.read_bytes
    def guarded(path):
        if path.name=='heldout_report.json':pytest.fail('unauthorized protected read')
        return original(path)
    monkeypatch.setattr(Path,'read_bytes',guarded)
    result=M.check(root,c,allow_authorized_heldout_report=True)
    assert not result['protected_report_read'] and not result['scientific_release_complete']


def test_byte_integrity_alone_never_suffices(candidate):
    root,c,_=candidate
    (root/'unexpected.txt').write_text('synthetic extra')
    result=M.check(root,c,allow_authorized_heldout_report=True)
    assert not result['byte_integrity_passed'] and not result['scientific_release_complete']


def test_hash_tamper_blocks(candidate):
    root,c,_=candidate
    (root/'outcomes.json').write_text('[]')
    result=M.check(root,c,allow_authorized_heldout_report=True)
    assert any('checksum mismatch' in b for b in result['blockers'])
    assert not result['protected_report_read']


def test_protected_schedule_rejected_before_outcome_read(candidate,monkeypatch):
    root,c,save=candidate
    schedule=json.loads((root/'schedule.json').read_text())
    schedule['episodes'][0]['partition']='test'
    save('schedule',schedule)
    original=Path.read_bytes
    def guarded(path):
        if path.name in ('outcomes.json','heldout_report.json'):
            pytest.fail('protected schedule must fail before outcome access')
        return original(path)
    monkeypatch.setattr(Path,'read_bytes',guarded)
    result=M.check(root,c,allow_authorized_heldout_report=True)
    assert result['blockers'] and not result['protected_report_read']


@pytest.mark.parametrize('change',['graph','partial','wrong_ids'])
def test_heldout_audit_is_not_automatically_completion(candidate,change):
    root,c,save=candidate
    report=json.loads((root/'heldout_report.json').read_text())
    if change=='graph':report['evidence_scope']='graph'
    elif change=='partial':report['complete']=False
    else:report['audited_episode_ids']=['not-authorized']
    save('heldout_report',report)
    authorization=json.loads((root/'heldout_authorization.json').read_text())
    authorization['heldout_report']=c['inputs']['heldout_report'];save('heldout_authorization',authorization)
    inference=json.loads((root/'inference.json').read_text())
    inference['heldout_report_sha256']=c['inputs']['heldout_report']['sha256'];save('inference',inference)
    result=M.check(root,c,allow_authorized_heldout_report=True)
    assert result['protected_report_read']
    assert not result['scientific_release_complete']
    assert any('complete authorized physical' in b for b in result['blockers'])
