#!/usr/bin/env python3
"""Prepare a non-executable, source-bound expansion proposal; never label or run."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile

import yaml
from language_nav.capture_view import validate_capture_pose

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_COVERAGE = {'schema_version': 'research3-physical-calibration-coverage/v2',
    'outcome_coverage_scope': 'global_class', 'minimum_per_map_class_total': 1,
    'minimum_per_class_outcome': 5, 'minimum_per_class_confidence_bin': 5,
    'confidence_bin_edges': [0, .5, .8, 1], 'unreviewable_exclusion_policy': 'allow_with_counts'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def validate_amendment(value):
    if (value.get('schema_version') != 'research3-calibration-expansion-amendment/v1'
            or value.get('status') != 'draft_pending_human_approval'
            or any(value.get(k) is not False for k in ('execution_authorized',
                'calibration_freeze_authorized', 'protected_access_authorized'))):
        raise ValueError('draft-only unapproved amendment required')
    if value.get('coverage') != EXPECTED_COVERAGE:
        raise ValueError('original coverage requirements must remain unchanged')
    p = value['phase_2']
    if p['development_maps'] != list(range(1, 11)) or p['validation_maps'] != list(range(11, 15)):
        raise ValueError('exact nonprotected partition required before source reads')
    if p['classes'] != ['chair', 'doorway', 'laboratory_entrance', 'office_entrance']:
        raise ValueError('four original classes required')
    if (p['simulator_seeds'] != [1, 2] or p['primary_view_offsets_x_m'] != [0, -.5, .5, 1, 2]
            or p.get('entrance_last_offset_x_m') != -2):
        raise ValueError('prespecified fixed schedule required')
    if p['primary_attempts'] != 560 or value['diagnostic_panel']['attempts'] != 80:
        raise ValueError('fixed budget mismatch')
    for key in ('confidence_used_to_select_or_discard_observations', 'correctness_used_to_select_or_discard_observations'):
        if p[key] is not False:
            raise ValueError('outcome-conditioned selection forbidden')
    if (value['diagnostic_panel']['included_in_calibration_fit_or_primary_validation'] is not False
            or value['diagnostic_panel']['use_to_fill_primary_negative_quota'] is not False
            or value['phase_1']['existing_pilot_in_final_fit'] is not False
            or value['phase_1']['anonymous_narrative_counts_are_verified_labels'] is not False):
        raise ValueError('pilot/stress/narrative cannot become final calibration labels')


def read_nonprotected_run(root, run_id, number):
    if not re.fullmatch(r'r3-current-v1-r\d{3}-(chair|laboratory_entrance|office_entrance)', run_id):
        raise ValueError('unknown seed view run')
    directory = root / 'reports/physical_live_episodes' / run_id
    request = json.loads((directory / 'request.json').read_bytes())
    partition = 'development' if number <= 10 else 'validation'
    if (request.get('map_id') != f'r3geo_base_r{number:03}' or not 1 <= number <= 14
            or request.get('partition') != partition or request.get('protected_test_routes_used') is not False
            or request.get('run_id') != run_id):
        raise ValueError('nonprotected request identity required before scene read')
    path = directory / 'runtime_scene.yaml'
    if sha(path) != request.get('runtime_scene_sha256'):
        raise ValueError('scene/request mismatch')
    scene = yaml.safe_load(path.read_bytes())
    if scene['map_id'] != request['map_id'] or scene['partition'] != partition:
        raise ValueError('scene partition mismatch')
    return request, scene, sha(directory / 'request.json')


def frozen_profile(root, base, number, request):
    family = 'fresh_current_capture_20260911_v1' if number <= 10 else 'engineering_camera_settings_v3'
    profile = root / 'reports' / family / 'profiles' / (base + '.yaml')
    if sha(profile) != request['camera_profile_sha256']:
        raise ValueError('profile changed')
    return profile


def prepare(root, amendment_path):
    root = Path(root).resolve(); amendment_path = Path(amendment_path)
    a = yaml.safe_load(amendment_path.read_bytes()); validate_amendment(a)
    kit = root / a['phase_1']['kit']
    if sha(kit) != a['phase_1']['kit_sha256']:
        raise ValueError('original pilot kit changed')
    with zipfile.ZipFile(kit) as z:
        if json.loads(z.read('proposal.json'))['coverage'] != a['coverage']:
            raise ValueError('coverage differs from published kit')
    source = root / 'reports/fresh_current_capture_20260911_v1/plan.json'
    original = json.loads(source.read_bytes())
    if original.get('protected_content_read') is not False or len(original.get('views', [])) != 42:
        raise ValueError('complete nonprotected seed plan required')
    views = {(v['base_instruction_id'], v['category']): v for v in original['views']}
    expected = {(f'base-r{i:03}', c) for i in range(1, 15) for c in ('chair', 'laboratory_entrance', 'office_entrance')}
    if set(views) != expected: raise ValueError('seed view scope mismatch')
    rows = []
    for number in range(1, 15):
        base = f'base-r{number:03}'
        for category in a['phase_2']['classes']:
            v = views[(base, 'laboratory_entrance' if category == 'doorway' else category)]
            request, scene, request_hash = read_nonprotected_run(root, v['run_id'], number)
            entity = v['intended_entity_id']
            if category == 'doorway': entity = entity.removesuffix('_entrance') + '_doorway'
            targets = [e for e in scene['entities'] if e['entity_id'] == entity and e['category'] == category]
            if len(targets) != 1: raise ValueError('unique catalogue target required')
            target = targets[0]['pose']
            world = root / 'data/physical_worlds_readable_v1' / base
            hashes = {name: sha(world / name) for name in ('world.sdf', 'map.pgm', 'map.yaml', 'landmark_scene.yaml')}
            if any(request['asset_sha256'].get(name) != h for name, h in hashes.items()):
                raise ValueError('world changed since source-bound pilot')
            profile = frozen_profile(root, base, number, request)
            for seed in a['phase_2']['simulator_seeds']:
                for index, offset in enumerate(a['phase_2']['primary_view_offsets_x_m']):
                    if index == 4 and category != 'chair':
                        offset = a['phase_2']['entrance_last_offset_x_m']
                    pose = dict(v['capture_pose']); pose['x'] += offset
                    if offset:
                        pose['yaw'] = math.atan2(target['y']-pose['y'], target['x']-pose['x'])
                    gap = None
                    try: validate_capture_pose(world, **pose)
                    except ValueError as exc: gap = str(exc)
                    rows.append({'candidate_id': f'expansion-v1-r{number:03}-{category}-s{seed}-view{index}',
                        'partition': 'development' if number <= 10 else 'validation',
                        'map_id': request['map_id'], 'category': category, 'entity_id': entity,
                        'seed': seed, 'view_group': f'{base}-{category}-view{index}',
                        'capture_pose': pose, 'world_sha256': hashes, 'camera_profile_sha256': sha(profile),
                        'pilot_request_sha256': request_hash, 'pose_preflight': 'blocked' if gap else 'passed',
                        'pose_preflight_gap': gap, 'visibility_or_detection_guaranteed': False,
                        'human_label': None, 'execution_authorized': False})
    manifest = {'schema_version': 'research3-calibration-expansion-plan/v1',
        'status': 'proposal_only_not_executable', 'amendment_sha256': sha(amendment_path),
        'original_plan_sha256': sha(source), 'review_kit_sha256': sha(kit),
        'capture_source_snapshot_sha256': sha(root / 'reports/fresh_current_capture_20260911_v1/current_source_snapshot.json'),
        'coverage': a['coverage'], 'primary_attempts': len(rows), 'diagnostic_attempts': 80,
        'diagnostic_assets_status': 'not_built_not_preflighted', 'rows': rows,
        'pose_preflight_counts': dict(Counter(r['pose_preflight'] for r in rows)),
        'execution_authorized': False, 'human_labels_generated': False, 'protected_content_read': False,
        'blockers': list(a['prerequisites']),
        'no_execution_argv_generated': True}
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--amendment', type=Path, default=ROOT / 'configs/physical_calibration_expansion_amendment_v1.yaml')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    plan = prepare(ROOT, args.amendment)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'amendment.input.yaml').write_bytes(args.amendment.read_bytes())
    (args.output / 'plan.json').write_bytes(encode(plan))
    form = {'schema_version': 'research3-calibration-expansion-review/v1',
        'amendment_sha256': plan['amendment_sha256'], 'plan_sha256': sha(args.output / 'plan.json'),
        'reviewer_name': None, 'reviewer_role': None, 'reviewed_at': None,
        'protected_outcomes_consulted': False, 'phase_1_return_sha256': None,
        'phase_1_usability_audit_sha256': None, 'overall_decision': 'pending',
        'decisions': {k: {'decision': 'pending', 'rationale': None} for k in
            ('pilot_only', 'rubric_scope', 'unchanged_coverage', 'fixed_primary_schedule',
             'diagnostic_exclusion', 'partition_separation', 'fixed_budget_stopping', 'source_resource_guards')},
        'grants_execution_by_itself': False}
    (args.output / 'review.template.json').write_bytes(encode(form))
    print(json.dumps({'output': str(args.output), 'primary_attempts': plan['primary_attempts'],
        'pose_preflight': plan['pose_preflight_counts'], 'execution_authorized': False}))


if __name__ == '__main__': main()
