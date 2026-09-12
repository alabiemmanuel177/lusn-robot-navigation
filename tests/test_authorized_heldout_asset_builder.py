"""Actual transforms on procedurally generated synthetic fixtures, never test assets."""
import json
from pathlib import Path
import runpy
import sys

import pytest

from language_nav import physical_asset_authorization as auth
from language_nav.benchmark import CorruptionCondition
from language_nav.world.physical import build_world

ROOT = Path(__file__).parents[1]
BUILDER = runpy.run_path(str(ROOT / 'scripts/build_authorized_heldout_assets.py'))


def test_two_world_pair_blocks_are_unique_and_shared_only_across_systems(synthetic):
    root, approval, _, save = synthetic
    design=json.loads((root/approval['design']['path']).read_text())
    design['simulator_seed']['confirmatory_seed_list']=[1,2]
    design['replication']['confirmatory_replications']=2
    design['power_inputs_requiring_freeze']['repetitions_per_world']=2
    approval['design']=save(approval['design']['path'],design)
    plan=json.loads((root/approval['plan']['path']).read_text())
    first=plan['worlds'][0]
    record=json.loads((root/first['instructions']['path']).read_text())
    record=json.loads(json.dumps(record).replace('base-r015','base-r016').replace('r3geo_base_r015','r3geo_base_r016'))
    source=root/'synthetic_source/base-r016'
    build_world(source,record['canonical'])
    runpy.run_path(str(ROOT/'scripts/verify_physical_world.py'))['verify'](source)
    second=dict(first,base_instruction_id='base-r016',source_directory='synthetic_source/base-r016',
        source_sha256={name:auth.sha(source/name) for name in auth.FILES},
        instructions=save('synthetic_instructions_second.json',record))
    plan['worlds'].append(second)
    approval['plan']=save(approval['plan']['path'],plan)
    save('approval.json',approval)
    BUILDER['build'](root/'approval.json',auth.sha(root/'approval.json'),root=root)
    rows=json.loads((root/'data/synthetic_derivatives/runtime_schedule_template.json').read_text())['episodes']
    assert len(rows)==2*2*len(CorruptionCondition)*5
    assert len({(r['partition'],r['paired_block_index'],r['system_id']) for r in rows})==len(rows)
    slots={}
    for row in rows:
        key=(row['base_instruction_id'],row['condition'],row['simulation_seed'])
        slots.setdefault(key,set()).add(row['paired_block_index'])
    assert all(len(indices)==1 for indices in slots.values())
    assert len({next(iter(indices)) for indices in slots.values()})==len(slots)


@pytest.fixture
def synthetic(tmp_path):
    def save(name, value):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return {'path': name, 'sha256': auth.sha(path)}
    # These are synthetic choices solely to exercise frozen-design validation.
    design = {'schema_version': 'research3-physical-experiment-design-draft/v2', 'status': 'frozen',
        'analysis_proposals': {'candidate_contrasts': ['B6_minus_B1'], 'primary_contrast': 'B6_minus_B1',
            'multiplicity_policy': 'synthetic', 'confirmatory_inference_method': 'synthetic'},
        'simulator_seed': {'confirmatory_seed_list': [1]}, 'replication': {'confirmatory_replications': 1},
        'power_inputs_requiring_freeze': {'repetitions_per_world': 1, 'target_effect': .1, 'target_power': .8,
            'alpha': .05, 'baseline_completion': .5, 'paired_discordance': .3, 'world_intracluster_correlation': .2}}
    instruction = {'base_instruction_id': 'base-r015', 'partition': 'held_out',
        'anchor_attributes': {'color': 'red'}, 'anchor_entity_id': 'r3geo_base_r015_chair',
        'topology_side': 'left', 'terminal_category': 'laboratory_entrance',
        'canonical_text': 'Synthetic fixture only: pass red chair, second left laboratory.'}
    source = tmp_path / 'synthetic_source/base-r015'
    build_world(source, instruction)
    verify = runpy.run_path(str(ROOT / 'scripts/verify_physical_world.py'))['verify']
    verify(source)
    variants = [{'base_instruction_id': 'base-r015', 'variant_id': f'base-r015-{condition.value}-s0',
                 'raw_text': 'Synthetic deployable instruction ' + condition.value, 'provenance': 'synthetic-fixture'}
                for condition in CorruptionCondition]
    row = {'base_instruction_id': 'base-r015', 'source_directory': 'synthetic_source/base-r015',
           'source_sha256': {name: auth.sha(source / name) for name in auth.FILES},
           'instructions': save('synthetic_instructions.json', {'canonical': instruction, 'deployed_variants': variants}),
           'camera_horizontal_fov': 2., 'camera_color_tolerance': 10., 'timeout_s': 25.}
    approval = {'schema_version': 'research3-protected-asset-build-authorization/v1',
        'status': 'approved_frozen', 'authorization_scope': 'heldout_derivative_build_only',
        'reviewer_type': 'human', 'approved_by': 'synthetic-not-real-human-attestation',
        'approved_at_utc': 'synthetic-only', 'recipe': 'readable_and_exact_chair_absence/v1',
        'source_sha256': {name: auth.sha(ROOT / name) for name in auth.SOURCES},
        'shortest_path_source_sha256': auth.sha(Path('/home/eao/risk-calibrated-nav/rcn/shortest_path.py')),
        'design': save('synthetic_design.json', design),
        'plan': save('synthetic_plan.json', {'schema_version': 'research3-protected-asset-build-plan/v1',
                                           'output_directory': 'data/synthetic_derivatives', 'worlds': [row]})}
    save('synthetic_approval.json', approval)
    return tmp_path, approval, row, save


def test_real_synthetic_transforms_preserve_partitions_geometry_and_complete_pending_schedule(synthetic):
    root, _, row, _ = synthetic
    approval = root / 'synthetic_approval.json'
    result = BUILDER['build'](approval, auth.sha(approval), root=root)
    output = root / 'data/synthetic_derivatives'
    assert result['passed'] is True and result['episode_count'] == 40
    assert result['live_execution_authorized'] is False
    schedule = json.loads((output / 'runtime_schedule_template.json').read_text())
    assert schedule['calibration_sha256'] is None
    assert len(schedule['episodes']) == 40
    assert {row['system_id'] for row in schedule['episodes']} == {'B1', 'B2', 'B4', 'B5', 'B6'}
    assert len({row['condition'] for row in schedule['episodes']}) == 8
    for family in ('readable', 'missing_landmark'):
        directory = output / family / 'base-r015'
        import yaml
        assert json.loads((directory / 'manifest.json').read_text())['partition'] == 'held_out'
        assert json.loads((directory / 'execution_catalog.json').read_text())['partition'] == 'held_out'
        assert yaml.safe_load((directory / 'landmark_scene.yaml').read_text())['partition'] == 'test'
        visual = json.loads((directory / 'visual_derivative_audit.json').read_text())
        assert visual['collision_geometry_unchanged'] and len(visual['signs']) == 8
    absence = json.loads((output / 'missing_landmark/base-r015/absence_intervention.json').read_text())
    assert absence['protected_content_used'] is True and len(absence['removed_models']) == 6
    assert absence['geometry_audit_passed'] is True
    assert all(auth.sha(output / 'missing_landmark/base-r015' / name) == digest
               for name, digest in absence['asset_sha256'].items())
    assert all(auth.sha(root / row['source_directory'] / name) == digest
               for name, digest in row['source_sha256'].items())
    with pytest.raises(PermissionError, match='new contained'):
        BUILDER['build'](approval, auth.sha(approval), root=root)


@pytest.mark.parametrize('change', [lambda a: a.update(status='draft'), lambda a: a.update(reviewer_type='machine'),
    lambda a: a.update(source_sha256={}), lambda a: a.update(shortest_path_source_sha256='0' * 64)])
def test_bad_approval_never_opens_protected_plan_or_source(synthetic, monkeypatch, change):
    root, approval, _, save = synthetic
    change(approval)
    save('synthetic_approval.json', approval)
    original = Path.read_bytes
    def guarded(path):
        if path.name == 'synthetic_plan.json' or 'synthetic_source' in path.parts:
            pytest.fail('protected build input opened before admission')
        return original(path)
    monkeypatch.setattr(Path, 'read_bytes', guarded)
    with pytest.raises(PermissionError):
        BUILDER['build'](root / 'synthetic_approval.json', auth.sha(root / 'synthetic_approval.json'), root=root)


def test_changed_protected_input_fails_without_creating_output(synthetic):
    root, _, _, _ = synthetic
    (root / 'synthetic_source/base-r015/world.sdf').write_text('changed')
    approval = root / 'synthetic_approval.json'
    with pytest.raises(PermissionError, match='changed before transformation'):
        BUILDER['build'](approval, auth.sha(approval), root=root)
    assert not (root / 'data/synthetic_derivatives').exists()


def test_default_builders_still_deny_protected_absence_and_readable_before_source_open(tmp_path):
    readable = runpy.run_path(str(ROOT / 'scripts/build_readable_physical_worlds.py'))['build']
    with pytest.raises(PermissionError):
        readable(tmp_path / 'base-r015', tmp_path / 'out')
    with pytest.raises(PermissionError):
        build_world(tmp_path / 'out', {'partition': 'held_out'}, anchor_present=False)


def test_generated_synthetic_assets_pass_separate_runtime_admission_without_relabeling(synthetic):
    from language_nav import physical_heldout_authorization as runtime_auth
    from language_nav.benchmark.physical_catalog import validate_physical_launch_inputs
    root, build_approval, _, save = synthetic
    approval_path = root / 'synthetic_approval.json'
    BUILDER['build'](approval_path, auth.sha(approval_path), root=root)
    schedule = json.loads((root / 'data/synthetic_derivatives/runtime_schedule_template.json').read_text())
    calibration = save('synthetic_calibration.json', {'schema_version': 'landmark-calibration/v1', 'partition': 'validation'})
    schedule['calibration_sha256'] = calibration['sha256']
    approval = {'schema_version': 'research3-physical-heldout-runtime-authorization/v1',
        'status': 'approved_frozen', 'authorization_scope': 'physical_heldout_live_execution',
        'reviewer_type': 'human', 'approved_by': 'synthetic-fixture-only', 'approved_at_utc': 'synthetic',
        'gates': {gate: True for gate in runtime_auth.GATES}, 'design': build_approval['design'],
        'calibration': calibration, 'schedule': save('synthetic_runtime_schedule.json', schedule), 'ros_domain_id': 89,
        'execution_source_sha256': {name: auth.sha(ROOT / name) for name in runtime_auth.SOURCE_FILES},
        'provider_source_sha256': {name: auth.sha(runtime_auth.R1 / name) for name in runtime_auth.PROVIDER_FILES}}
    save('synthetic_runtime_approval.json', approval)
    for condition in ('truthful_original', 'missing_landmark'):
        row = next(row for row in schedule['episodes'] if row['condition'] == condition)
        path = root / 'synthetic_runtime_approval.json'
        context = runtime_auth.authorize(path, auth.sha(path), row['episode_id'], root=root)
        world = root / row['world_directory']
        catalog = validate_physical_launch_inputs(world / 'execution_catalog.json', world / 'landmark_scene.yaml',
                                                  heldout_authorization=context)
        assert catalog.semantic.partition == 'held_out' and len(catalog.execution) == 4
