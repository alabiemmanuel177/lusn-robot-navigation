import hashlib
import json
from pathlib import Path
import runpy

import pytest
import yaml

MODULE = runpy.run_path(str(Path(__file__).parents[1] / 'scripts/run_physical_campaign.py'))


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    provider = {'schema_version': 'research3-capture-provider-source/v1',
                'files': {'synthetic-provider.py': 'a' * 64}, 'complete': True}
    monkeypatch.setitem(MODULE['prepare'].__globals__, 'capture_provider_snapshot', lambda: provider)
    monkeypatch.setattr('language_nav.camera_configuration.capture_provider_snapshot', lambda: provider)
    def save(name, data):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        return {'path': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    # Entirely synthetic attestations for code-path tests, not real approvals.
    design = {'schema_version': 'research3-physical-experiment-design-draft/v2', 'status': 'frozen',
              'analysis_proposals': {'candidate_contrasts': ['B6_minus_B1'], 'primary_contrast': 'B6_minus_B1',
                                    'multiplicity_policy': 'synthetic', 'confirmatory_inference_method': 'synthetic'},
              'simulator_seed': {'confirmatory_seed_list': [1]}, 'replication': {'confirmatory_replications': 1},
              'power_inputs_requiring_freeze': {'repetitions_per_world': 1, 'target_effect': .1,
                  'target_power': .8, 'alpha': .05, 'baseline_completion': .5, 'paired_discordance': .3,
                  'world_intracluster_correlation': .2}}
    design_ref, calibration_ref = save('design.json', design), save('calibration.json', {'synthetic': True})
    files = [save(name, {'synthetic': name}) for name in (
        'scripts/run_physical_episode.py', 'scripts/run_physical_campaign.py',
        'scripts/run_approved_physical_episode.py', 'src/language_nav/campaign_authorization.py',
        'scripts/export_physical_campaign_outcomes.py', 'scripts/audit_physical_interruption.py',
        'src/language_nav/systems/variants.py', 'src/language_nav/planning/policy.py',
        'src/language_nav/live.py', 'ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py',
        'ros_ws/src/language_nav_bringup/launch/physical_sim.launch.py')]
    assets = [save('data/physical_worlds_v1/base-r001/' + name, {'synthetic': name}) for name in (
        'world.sdf', 'map.pgm', 'map.yaml', 'execution_catalog.json', 'landmark_scene.yaml',
        'manifest.json', 'verified_ordered_geometry.json')]
    coverage = {'schema_version': 'research3-physical-calibration-validation/v1',
                'passed': True, 'frozen': True, 'human_review_verified': True, 'protected_labels_used': False,
                'calibration_sha256': calibration_ref['sha256'], 'map_ids': ['r3geo_base_r001'],
                'scene_sha256': [next(r['sha256'] for r in assets if r['path'].endswith('landmark_scene.yaml'))]}
    coverage['scene_bindings'] = [{'map_id': 'r3geo_base_r001',
        'base_scene_sha256': coverage['scene_sha256'][0], 'runtime_scene_sha256': coverage['scene_sha256'][0],
        'camera_profile_sha256': None, 'camera_horizontal_fov': None,
        'source_sha256': {r['path']: r['sha256'] for r in files},
        'provider_source_snapshot': provider}]
    rows = [{'episode_id': 'episode-' + s, 'system_id': s, 'base_instruction_id': 'base-r001',
             'variant_id': 'base-r001-truthful_original-s0', 'partition': 'development', 'paired_block_index': 0,
             'condition': 'truthful_original', 'simulation_seed': 1, 'timeout_s': 60,
             'world_family': 'physical_worlds_v1'} for s in ('B1', 'B6')]
    manifest_ref = save('schedule.json', {'schema_version': 'research3-physical-comparison-plan/v1', 'episodes': rows})
    approval = {'schema_version': 'research3-physical-execution-approval/v1', 'status': 'approved_frozen',
                'authorization_scope': 'nonprotected_campaign', 'reviewer_type': 'human',
                'approved_by': 'synthetic-fixture-not-real-person', 'approved_at_utc': 'synthetic-test-only',
                'manifest_sha256': manifest_ref['sha256'], 'design': design_ref, 'calibration': calibration_ref,
                'calibration_validation': save('coverage.json', coverage),
                'gates': {gate: save(gate + '.json', {'passed': True}) for gate in MODULE['GATES']},
                'files': files + assets, 'campaign_id': 'synthetic', 'ros_domain_id': 89}
    save('approval.json', approval)
    return tmp_path, tmp_path / 'schedule.json', tmp_path / 'approval.json'


def test_approved_synthetic_plan_constructs_only_owned_whitelisted_argv(prepared):
    root, manifest, approval = prepared
    _, jobs = MODULE['prepare'](manifest, approval, root)
    assert len(jobs) == 2 and len({job['run_id'] for job in jobs}) == 2
    assert all('--allow-coexistence-trial' not in job['argv'] for job in jobs)
    assert all(job['argv'][2] == str(root / 'scripts/run_approved_physical_episode.py') for job in jobs)
    assert all(job['argv'][job['argv'].index('--campaign-authorization') + 1] == str(approval) for job in jobs)
    assert all(job['argv'][job['argv'].index('--campaign-manifest') + 1] == str(manifest) for job in jobs)


@pytest.mark.parametrize('change', [
    lambda a: a.update(status='draft'), lambda a: a.update(reviewer_type='machine'),
    lambda a: a.update(allow_coexistence_trial=True), lambda a: a.update(manifest_sha256='0' * 64),
    lambda a: a.update(files=[]), lambda a: a['gates'].pop('physical_inspection')])
def test_approval_and_source_gates_fail_closed(prepared, change):
    root, manifest, approval = prepared
    data = json.loads(approval.read_text())
    change(data)
    approval.write_text(json.dumps(data))
    with pytest.raises((ValueError, KeyError)):
        MODULE['prepare'](manifest, approval, root)


def test_changed_scene_or_calibration_fails_before_execution(prepared):
    root, manifest, approval = prepared
    (root / 'calibration.json').write_text('{}')
    with pytest.raises(ValueError, match='checksum'):
        MODULE['prepare'](manifest, approval, root)


def test_protected_schedule_refused_before_approval_read(prepared):
    root, manifest, approval = prepared
    data = json.loads(manifest.read_text())
    data['episodes'][0]['partition'] = 'test'
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='held-out'):
        MODULE['prepare'](manifest, root / 'nonexistent-approval', root)


def test_resource_guard_leaves_planned_rows_and_blocks_launch(prepared):
    root, manifest, approval = prepared
    def guard():
        raise RuntimeError('Research 2 active')
    launched = []
    directory = root / 'lifecycle'
    assert not MODULE['execute'](manifest, approval, directory, root=root,
                                 launch=lambda command: launched.append(command), resource_guard=guard)
    events = [json.loads(p.read_text()) for p in sorted(directory.glob('*.json'))]
    assert [e['state'] for e in events] == ['planned', 'planned', 'blocked_before_start']
    assert not launched


def test_unknown_started_attempt_halts_without_replacing_or_omitting_schedule(prepared):
    root, manifest, approval = prepared
    launched = []
    directory = root / 'lifecycle'
    assert not MODULE['execute'](manifest, approval, directory, root=root,
        launch=lambda command: launched.append(command) or 1, resource_guard=lambda: None)
    assert len(launched) == 1
    events = [json.loads(p.read_text()) for p in sorted(directory.glob('*.json'))]
    assert [e['state'] for e in events] == ['planned', 'planned', 'start', 'unknown']
    assert events[-1]['export_report']['unresolved_assignments']
    with pytest.raises(FileExistsError):
        MODULE['execute'](manifest, approval, directory, root=root, launch=lambda c: pytest.fail('retry'),
                          resource_guard=lambda: None)


def test_explicit_setupfailure_recorded_and_campaign_halts(prepared):
    root, manifest, approval = prepared
    def launch(command):
        run_id = command[command.index('--run-id') + 1]
        directory = root / 'reports/physical_live_episodes' / run_id
        directory.mkdir(parents=True)
        (directory / 'request.json').write_text(json.dumps({'run_id': run_id, 'system_id': 'B1',
            'variant_id': 'base-r001-truthful_original-s0', 'partition': 'development',
            'map_id': 'r3geo_base_r001', 'protected_test_routes_used': False}))
        (directory / 'failure.json').write_text(json.dumps({'dispatched': False}))
        return 1
    directory = root / 'lifecycle'
    assert not MODULE['execute'](manifest, approval, directory, root=root, launch=launch, resource_guard=lambda: None)
    events = [json.loads(p.read_text()) for p in sorted(directory.glob('*.json'))]
    assert events[-1]['state'] == 'setupfailure'
    assert events[-1]['outcome']['collision'] is None


def test_serial_audited_navigation_failures_are_retained_without_stopping_other_pairs(prepared, monkeypatch):
    root, manifest, approval = prepared
    def synthetic_export(schedule, assignments):
        row = {'episode_id': assignments[0]['episode_id'], 'dispatched': True,
               'infrastructure_failure': False, 'navigation_success': False, 'collision': True}
        return {'standalone_outcome_list_exportable': True, 'outcomes': [row], 'sources': [],
                'dispatch_definition': 'synthetic policy dispatch'}
    monkeypatch.setitem(MODULE['execute'].__globals__, 'EXPORT', synthetic_export)
    calls = []
    directory = root / 'lifecycle'
    assert MODULE['execute'](manifest, approval, directory, root=root,
                             launch=lambda argv: calls.append(argv) or 0, resource_guard=lambda: None)
    assert len(calls) == 2
    events = [json.loads(p.read_text()) for p in sorted(directory.glob('*.json'))]
    assert [e['state'] for e in events] == ['planned', 'planned', 'start', 'dispatch', 'outcome', 'start', 'dispatch', 'outcome']
    assert all(e['outcome']['navigation_success'] is False for e in events if e['state'] == 'outcome')


def test_changed_approval_between_runs_blocks_next_launch(prepared, monkeypatch):
    root, manifest, approval = prepared
    monkeypatch.setitem(MODULE['execute'].__globals__, 'EXPORT', lambda *args: {
        'standalone_outcome_list_exportable': True, 'outcomes': [{'dispatched': True, 'infrastructure_failure': False}],
        'sources': [], 'dispatch_definition': 'synthetic'})
    calls = []
    def launch(argv):
        calls.append(argv)
        approval.write_text(approval.read_text() + '\n')
        return 0
    directory = root / 'lifecycle'
    assert not MODULE['execute'](manifest, approval, directory, root=root, launch=launch, resource_guard=lambda: None)
    assert len(calls) == 1
    events = [json.loads(p.read_text()) for p in sorted(directory.glob('*.json'))]
    assert events[-1]['state'] == 'blocked_before_start' and 'changed' in events[-1]['reason']


def test_calibration_coverage_must_cover_exact_scene_not_just_map_id(prepared):
    root, manifest, approval = prepared
    coverage_path = root / 'coverage.json'
    coverage = json.loads(coverage_path.read_text())
    coverage['scene_bindings'] = []
    coverage_path.write_text(json.dumps(coverage))
    authorization = json.loads(approval.read_text())
    authorization['calibration_validation']['sha256'] = hashlib.sha256(coverage_path.read_bytes()).hexdigest()
    approval.write_text(json.dumps(authorization))
    with pytest.raises(ValueError, match='exact runtime scene'):
        MODULE['prepare'](manifest, approval, root)


def repin(prepared, relative, payload):
    root, manifest, approval = prepared
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    auth = json.loads(approval.read_text())
    if path == manifest:
        auth['manifest_sha256'] = digest
    elif relative == 'coverage.json':
        auth['calibration_validation']['sha256'] = digest
    else:
        auth['files'] = [row for row in auth['files'] if row['path'] != relative]
        auth['files'].append({'path': relative, 'sha256': digest})
    approval.write_text(json.dumps(auth))
    return digest


def test_independent_lists_cannot_cross_combine_scene_fov_or_map(prepared):
    root, manifest, approval = prepared
    coverage = json.loads((root / 'coverage.json').read_text())
    binding = coverage['scene_bindings'][0]
    coverage['scene_bindings'] = [{**binding, 'camera_horizontal_fov': 1.2},
                                  {**binding, 'map_id': 'r3geo_base_r002'}]
    repin(prepared, 'coverage.json', coverage)
    with pytest.raises(ValueError, match='exact runtime scene/profile/FOV binding'):
        MODULE['prepare'](manifest, approval, root)


def test_approved_current_source_still_rejected_if_review_used_old_source(prepared):
    root, manifest, approval = prepared
    repin(prepared, 'src/language_nav/live.py', {'synthetic': 'changed after capture'})
    with pytest.raises(ValueError, match='reviewed runtime source'):
        MODULE['prepare'](manifest, approval, root)


@pytest.mark.parametrize('change', ['missing', 'changed', 'incomplete'])
def test_review_provider_identity_cannot_be_omitted_or_substituted(prepared, change):
    root, manifest, approval = prepared
    coverage = json.loads((root / 'coverage.json').read_text())
    binding = coverage['scene_bindings'][0]
    if change == 'missing':
        binding.pop('provider_source_snapshot')
    elif change == 'changed':
        binding['provider_source_snapshot']['files']['synthetic-provider.py'] = 'b' * 64
    else:
        binding['provider_source_snapshot']['complete'] = False
    repin(prepared, 'coverage.json', coverage)
    with pytest.raises(ValueError, match='reviewed runtime source'):
        MODULE['prepare'](manifest, approval, root)


def test_actual_palette_adaptation_not_raw_scene_hash(prepared, tmp_path):
    from language_nav.adapters.landmark_palette import adapt_scene_palette
    root, manifest, approval = prepared
    scene_name = 'data/physical_worlds_v1/base-r001/landmark_scene.yaml'
    base_sha = repin(prepared, scene_name, {'entities': [{'category': 'chair', 'marker_rgb': [1, 2, 3]}]})
    profile_sha = repin(prepared, 'camera.json', {'schema_version': 'landmark-capture-profile/v1',
        'camera_palette': {'chair': [4, 5, 6]}, 'provider_revision': 'synthetic', 'profile_id': 'synthetic'})
    repin(prepared, 'src/language_nav/adapters/landmark_palette.py', {'synthetic': 'pinned palette source'})
    expected = tmp_path / 'expected-runtime.yaml'
    adapt_scene_palette(root / scene_name, expected, root / 'camera.json')
    runtime_sha = hashlib.sha256(expected.read_bytes()).hexdigest()
    assert runtime_sha != base_sha
    schedule = json.loads(manifest.read_text())
    for row in schedule['episodes']:
        row.update(camera_profile='camera.json', camera_horizontal_fov=1.2)
    repin(prepared, 'schedule.json', schedule)
    coverage = json.loads((root / 'coverage.json').read_text())
    coverage['scene_bindings'][0].update(base_scene_sha256=base_sha, runtime_scene_sha256=runtime_sha,
                                         camera_profile_sha256=profile_sha, camera_horizontal_fov=1.2)
    repin(prepared, 'coverage.json', coverage)
    before = (root / scene_name).read_bytes()
    _, jobs = MODULE['prepare'](manifest, approval, root)
    assert '--camera-profile' in jobs[0]['argv']
    assert (root / scene_name).read_bytes() == before
    coverage['scene_bindings'][0]['runtime_scene_sha256'] = base_sha
    repin(prepared, 'coverage.json', coverage)
    with pytest.raises(ValueError, match='exact runtime scene/profile/FOV binding'):
        MODULE['prepare'](manifest, approval, root)
