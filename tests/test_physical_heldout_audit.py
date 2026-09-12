import hashlib
import json
from pathlib import Path
import runpy

import pytest

M = runpy.run_path(str(Path(__file__).parents[1] / 'scripts/audit_physical_heldout.py'))


@pytest.fixture
def setup(tmp_path):
    def save(name, value):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value))
        return {'path': name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    design = {'schema_version': 'research3-physical-experiment-design-draft/v2', 'status': 'frozen',
              'analysis_proposals': {'candidate_contrasts': ['B6_minus_B5'], 'primary_contrast': 'B6_minus_B5',
                                    'multiplicity_policy': 'fixture', 'confirmatory_inference_method': 'fixture'},
              'simulator_seed': {'confirmatory_seed_list': [1]}, 'replication': {'confirmatory_replications': 1},
              'power_inputs_requiring_freeze': {'repetitions_per_world': 1, 'target_effect': .1,
                  'target_power': .8, 'alpha': .05, 'baseline_completion': .5, 'paired_discordance': .3,
                  'world_intracluster_correlation': .2}}
    d = save('design.json', design)
    c = save('calibration.json', {'schema_version': 'landmark-calibration/v1', 'partition': 'validation'})
    row = {'episode_id': 'synthetic', 'partition': 'held_out', 'map_id': 'r3geo_base_r015',
           'system_id': 'B6', 'simulation_seed': 1, 'variant_id': 'base-r015-truthful_original-s0'}
    manifest = {'schema_version': 'research3-physical-heldout-schedule/v1',
                'evidence_scope': 'physical_world_heldout', 'design_sha256': d['sha256'],
                'calibration_sha256': c['sha256'], 'episodes': [row]}
    mr = save('manifest.json', manifest)
    approval = {'schema_version': 'research3-physical-heldout-authorization/v1',
                'status': 'approved_frozen', 'authorization_scope': 'physical_heldout_measurement_audit',
                'reviewer_type': 'human', 'approved_by': 'synthetic-test-only', 'approved_at_utc': 'fixture',
                'manifest_sha256': mr['sha256'], 'design': d, 'calibration': c}
    approval['execution_source_sha256'] = {
        name: save(name, {'synthetic_source_only': name})['sha256']
        for name in M['REQUIRED_EXECUTION_SOURCES']}
    # The audit executes these current source modules, not arbitrary Python
    # supplied by a staging directory. Copy source bytes, never protected data.
    for name in ('scripts/run_physical_episode.py', 'src/language_nav/live.py',
                 'src/language_nav/evaluation/ordered.py',
                 'src/language_nav/physical_heldout_authorization.py'):
        raw=(Path(__file__).parents[1]/name).read_bytes()
        (tmp_path/name).write_bytes(raw)
        approval['execution_source_sha256'][name]=hashlib.sha256(raw).hexdigest()
    save('approval.json', approval)
    save('assignments.json', [])
    return tmp_path, save, approval, manifest, row


def call(root):
    return M['audit'](root / 'manifest.json', root / 'assignments.json', root / 'approval.json', root=root)


@pytest.mark.parametrize('field,value', [('status', 'draft'), ('reviewer_type', 'machine'),
    ('authorization_scope', 'graph_evaluation'), ('approved_by', '')])
def test_denied_before_any_protected_read(setup, field, value):
    root, save, approval, _, _ = setup
    approval[field] = value
    save('approval.json', approval)
    (root / 'manifest.json').unlink()
    (root / 'assignments.json').unlink()
    with pytest.raises(PermissionError):
        call(root)


def test_missing_outcomes_are_unknown_not_failed_or_complete(setup):
    root, *_ = setup
    result = call(root)
    assert not result['complete'] and not result['passed']
    assert result['scheduled_count'] == 1 and result['audited_count'] == 0
    assert result['unresolved'][0]['reason'] == 'missing_assignment'
    assert not result['calibration_fitted'] and not result['human_labels_generated']


def test_graph_scope_and_unfrozen_calibration_rejected(setup):
    root, save, approval, manifest, _ = setup
    manifest['evidence_scope'] = 'protected_deterministic_graph_world'
    approval['manifest_sha256'] = save('manifest.json', manifest)['sha256']
    save('approval.json', approval)
    with pytest.raises(ValueError, match='physical held-out schedule'):
        call(root)


def test_duplicate_assignments_rejected(setup):
    root, save, *_ = setup
    save('assignments.json', [{'episode_id': 'synthetic'}] * 2)
    with pytest.raises(ValueError, match='duplicate'):
        call(root)


def test_summary_alone_cannot_certify_physical_execution(setup):
    root, save, *_ = setup
    save('assignments.json', [{'episode_id': 'synthetic', 'summary': save('summary.json', {'success': True})}])
    result = call(root)
    assert not result['complete'] and len(result['unresolved']) == 1


def test_invalid_schedule_membership_rejected(setup):
    root, save, approval, manifest, _ = setup
    manifest['episodes'][0]['map_id'] = 'r3geo_base_r010'
    approval['manifest_sha256'] = save('manifest.json', manifest)['sha256']
    save('approval.json', approval)
    with pytest.raises(ValueError, match='membership'):
        call(root)


def test_path_traversal_and_symlink_rejected(tmp_path):
    with pytest.raises(ValueError):
        M['local'](tmp_path, '../outside')
    (tmp_path / 'actual').write_text('fixture')
    (tmp_path / 'link').symlink_to(tmp_path / 'actual')
    with pytest.raises(ValueError):
        M['local'](tmp_path, 'link')


@pytest.fixture
def measured(setup):
    """Entire evaluator world is synthetic; no repository heldout asset access."""
    root,save,approval,manifest,row=setup
    assets={}
    for name in ('world.sdf','map.pgm','map.yaml','execution_catalog.json','landmark_scene.yaml'):
        assets[name]=save('world/'+name,{'synthetic_only':name})['sha256']
    entity=dict(entity_id='terminal',region_id='terminal_region',category='office_entrance',pose={'x':.4,'y':0.})
    world=dict(partition='held_out',map_id=row['map_id'],base_instruction_id='base-r015',
        map_sha256=assets['map.pgm'],expected_route_id='route',terminal_entities=[entity],
        candidates=[dict(route_id='route',terminal_entity_id='terminal',goal={'x':.4,'y':0.})])
    geometry=dict(schema_version='ordered-instruction-geometry/v1',geometry_verified=True,
        geometry_evidence='synthetic-only-directed-gate',map_sha256=assets['map.pgm'],
        base_instruction_id='base-r015',required_gate_ids=['gate'],forbidden_gate_ids=[],
        gates=[dict(gate_id='gate',a=[.2,1.],b=[.2,-1.],direction=1)])
    assets['manifest.json']=save('world/manifest.json',world)['sha256']
    assets['verified_ordered_geometry.json']=save('world/verified_ordered_geometry.json',geometry)['sha256']
    row['asset_sha256']=dict(assets)
    approval['manifest_sha256']=save('manifest.json',manifest)['sha256']
    save('approval.json',approval)
    request=dict(schema_version='research3-physical-live-request/v1',run_id='synthetic-run',
        partition='held_out',protected_test_routes_used=True,calibration_sha256=approval['calibration']['sha256'],
        allow_coexistence_trial=False,world_directory=str(root/'world'),asset_sha256=assets,
        source_sha256=approval['execution_source_sha256'],
        **{k:row[k] for k in ('map_id','variant_id','system_id','simulation_seed')})
    measurements=dict(schema_version='research3-live-measurements/v2',run_id='synthetic-run',
        ground_truth_positions=[[0.,0.],[.1,0.],[.2,0.],[.3,0.],[.4,0.]],
        ground_truth_timestamps_ns=[1000000000,1100000000,1200000000,1300000000,1400000000],
        episode_started_at_ns=1000000000,episode_ended_at_ns=1400000000,
        selected_route_id='route',collision_count=0,timeout=False,nav2_reported_success=True)
    evaluate=runpy.run_path(str(Path(__file__).parents[1]/'scripts/run_physical_episode.py'))['evaluate']
    sealed=save('measurements.pre_evaluation.json',measurements)
    context=M['HeldoutEvaluationContext'](request['run_id'],request['map_id'],dict(assets),
        root/sealed['path'],sealed['sha256'],M['digest'](root/'approval.json'))
    summary=evaluate(request,measurements,heldout_context=context)
    mr=save('measurements.json',measurements)
    summary.update(schema_version='research3-live-summary/v3',run_id='synthetic-run',
        evidence_scope='physical_world_heldout',protected_test_routes_used=True,infrastructure_failure=False,
        measurements_sha256=mr['sha256'],pre_evaluation_measurements_sha256=sealed['sha256'],
        **{k:request[k] for k in ('partition','map_id','variant_id','system_id')})
    assignment=dict(episode_id='synthetic',request=save('request.json',request),
        summary=save('summary.json',summary),measurements=mr,sealed_measurements=sealed)
    save('assignments.json',[assignment])
    return root,save,assignment,request,summary,measurements


def test_synthetic_physical_measurements_are_recomputed(measured):
    root,*_=measured
    report=call(root)
    assert report['complete'] and report['independent_measurement_verified']
    assert report['audited_episode_ids']==['synthetic']
    assert report['episodes'][0]['outcomes']['instruction_completion'] is True
    assert report['episodes'][0]['outcomes']['ordered_instruction_score']['matched_gate_ids']==['gate']


def test_forged_stored_summary_is_rejected_even_if_rehashed(measured):
    root,save,assignment,request,summary,measurements=measured
    summary['distance_travelled_m']=900.
    assignment['summary']=save('summary.json',summary)
    save('assignments.json',[assignment])
    result=call(root)
    assert not result['complete']
    assert 'differs from independent' in result['unresolved'][0]['reason']


@pytest.mark.parametrize('field,value',[('map_id','r3geo_base_r016'),('variant_id','other'),
    ('system_id','B5'),('simulation_seed',2)])
def test_wrong_request_identity_rejected(measured,field,value):
    root,save,assignment,request,*_=measured
    request[field]=value
    assignment['request']=save('request.json',request);save('assignments.json',[assignment])
    assert not call(root)['complete']


def test_measurement_run_identity_mismatch_must_not_pass(measured):
    root,save,assignment,request,summary,measurements=measured
    measurements['run_id']='another-run'
    assignment['measurements']=save('measurements.json',measurements)
    summary['measurements_sha256']=assignment['measurements']['sha256']
    assignment['summary']=save('summary.json',summary);save('assignments.json',[assignment])
    assert not call(root)['complete']


def test_missing_frozen_source_identity_must_not_pass(measured):
    root,save,assignment,request,*_=measured
    request.pop('source_sha256')
    assignment['request']=save('request.json',request);save('assignments.json',[assignment])
    assert not call(root)['complete']


def test_unknown_recomputed_completion_remains_unresolved(measured):
    root,save,assignment,request,summary,measurements=measured
    world=json.loads((root/'world/manifest.json').read_text())
    world['terminal_entities'][0]['pose']['x']=100.
    request['asset_sha256']['manifest.json']=save('world/manifest.json',world)['sha256']
    # Re-authorize only this synthetic changed asset to isolate unknown handling
    # from the independent frozen-asset substitution regression below.
    manifest=json.loads((root/'manifest.json').read_text())
    manifest['episodes'][0]['asset_sha256']=dict(request['asset_sha256'])
    approval=json.loads((root/'approval.json').read_text())
    approval['manifest_sha256']=save('manifest.json',manifest)['sha256'];save('approval.json',approval)
    evaluate=runpy.run_path(str(Path(__file__).parents[1]/'scripts/run_physical_episode.py'))['evaluate']
    # Start from the sealed telemetry, excluding all previous evaluator annotations.
    measurements=json.loads((root/assignment['sealed_measurements']['path']).read_text())
    sealed=save('measurements.pre_evaluation.json',measurements)
    context=M['HeldoutEvaluationContext'](request['run_id'],request['map_id'],dict(request['asset_sha256']),
        root/sealed['path'],sealed['sha256'],M['digest'](root/'approval.json'))
    summary.update(evaluate(request,measurements,heldout_context=context))
    assert summary['instruction_completion'] is None
    assignment['request']=save('request.json',request)
    assignment['measurements']=save('measurements.json',measurements)
    assignment['sealed_measurements']=sealed
    summary['pre_evaluation_measurements_sha256']=sealed['sha256']
    summary['measurements_sha256']=assignment['measurements']['sha256']
    assignment['summary']=save('summary.json',summary);save('assignments.json',[assignment])
    result=call(root)
    assert not result['complete']
    assert 'unknown physical endpoint' in result['unresolved'][0]['reason']


def test_self_consistent_substituted_world_rejected(measured):
    root,save,assignment,request,*_=measured
    request['asset_sha256']['world.sdf']=save('world/world.sdf',{'different_synthetic_world':True})['sha256']
    assignment['request']=save('request.json',request);save('assignments.json',[assignment])
    result=call(root)
    assert not result['complete']
    assert 'provenance mismatch' in result['unresolved'][0]['reason']


@pytest.mark.parametrize('field,value',[('partition','development'),('map_id','r3geo_base_r016'),
    ('variant_id','another-variant'),('system_id','B5')])
def test_summary_identity_cannot_impersonate_request(measured,field,value):
    root,save,assignment,request,summary,*_=measured
    summary[field]=value
    assignment['summary']=save('summary.json',summary);save('assignments.json',[assignment])
    assert not call(root)['complete']


def test_unpinned_execution_source_rejected_before_protected_read(setup):
    root,save,approval,*_=setup
    approval.pop('execution_source_sha256');save('approval.json',approval)
    (root/'manifest.json').unlink()
    with pytest.raises(PermissionError,match='source identity'):
        call(root)


@pytest.mark.parametrize('name',['scripts/run_physical_episode.py','src/language_nav/live.py',
                                'src/language_nav/evaluation/ordered.py'])
def test_freshly_approved_alternate_evaluator_rejected_before_protected_access(setup,name):
    root,save,approval,*_=setup
    # Internally consistent staging bytes and approval are still insufficient
    # when the actual evaluator running this audit has different source bytes.
    source=root/name
    source.write_bytes(source.read_bytes()+b'\n# synthetic different evaluator revision\n')
    approval['execution_source_sha256'][name]=hashlib.sha256(source.read_bytes()).hexdigest()
    save('approval.json',approval)
    (root/'manifest.json').unlink()
    with pytest.raises(PermissionError,match='actual evaluator source'):
        call(root)


def test_shadowed_imported_evaluator_module_is_rejected(setup,monkeypatch):
    import language_nav.live
    root,*_=setup
    monkeypatch.setattr(language_nav.live,'__file__',str(root/'src/language_nav/live.py'))
    (root/'manifest.json').unlink()
    with pytest.raises(PermissionError,match='unapproved location'):
        call(root)


@pytest.mark.parametrize('change',['bytes','summary_pin','run_id','missing_seal',
                                 'raw_payload','annotation'])
def test_sealed_telemetry_and_annotations_cannot_be_substituted(measured,change):
    root,save,assignment,request,summary,measurements=measured
    if change=='bytes':
        (root/assignment['sealed_measurements']['path']).write_text('{}')
    elif change=='missing_seal':
        assignment.pop('sealed_measurements')
    elif change=='summary_pin':
        summary['pre_evaluation_measurements_sha256']='0'*64
    elif change=='run_id':
        sealed=json.loads((root/assignment['sealed_measurements']['path']).read_text())
        sealed['run_id']='other-run'
        assignment['sealed_measurements']=save('measurements.pre_evaluation.json',sealed)
        summary['pre_evaluation_measurements_sha256']=assignment['sealed_measurements']['sha256']
    else:
        # Rehash the final record to prove the audit binds its payload, not only
        # the checksum. Annotations must be exactly independently recomputed.
        if change=='raw_payload':measurements['collision_count']=1
        else:measurements['commanded_goal']=[900.,900.]
        assignment['measurements']=save('measurements.json',measurements)
        summary['measurements_sha256']=assignment['measurements']['sha256']
    assignment['summary']=save('summary.json',summary)
    save('assignments.json',[assignment])
    report=call(root)
    assert not report['complete'] and report['unresolved']
    if change=='annotation':
        assert 'post-evaluation measurements' in report['unresolved'][0]['reason']


def test_valid_seal_is_retained_in_audit_provenance(measured):
    root,save,assignment,*_=measured
    report=call(root)
    assert report['complete']
    assert report['episodes'][0]['pre_evaluation_measurements_sha256']==assignment['sealed_measurements']['sha256']
