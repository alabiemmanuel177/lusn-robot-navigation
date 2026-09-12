#!/usr/bin/env python3
"""Read-only evidence bridge; never fit labels or approve a coverage policy."""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re

SPEC = importlib.util.spec_from_file_location('physical_export_bridge',
    Path(__file__).with_name('export_physical_human_review.py'))
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def is_hash(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def timestamp(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('timezone-aware approval timestamp required')
    return result


def evidence_bindings(store, reviewed):
    """Only runs contributing accepted labels count; never infer transfer."""
    accepted = {row['observation_id'] for row in reviewed}
    latest = {row['item_index']: row for row in store.events()[1:]}
    bindings, blockers = {}, []
    for index, item in enumerate(store.items):
        if (item['observation_id'] not in accepted or index not in latest
                or latest[index]['correct'] is None):
            continue
        run = store.runs[item['run_id']]
        request = read(run / 'request.json')
        source = request.get('source_sha256')
        provider = request.get('provider_source_snapshot')
        base_scene = request.get('asset_sha256', {}).get('landmark_scene.yaml')
        runtime_scene = request.get('runtime_scene_sha256', base_scene)
        profile = request.get('camera_profile_sha256')
        fov = request.get('camera_horizontal_fov')
        if (not is_hash(base_scene) or not is_hash(runtime_scene) or not is_hash(profile)
                or not isinstance(source, dict) or not source or not all(is_hash(v) for v in source.values())
                or not isinstance(provider, dict) or provider.get('complete') is not True
                or provider.get('schema_version') != 'research3-capture-provider-source/v1'
                or not isinstance(provider.get('files'), dict) or not provider['files']
                or not all(is_hash(v) for v in provider['files'].values())
                or type(fov) not in (float, int) or not math.isfinite(fov) or not 0 < fov < math.pi):
            blockers.append('incomplete_exact_runtime_binding:' + item['run_id'])
            continue
        # Adapted scene bytes are retained locally; no protected world access.
        if request.get('runtime_scene_sha256'):
            scene = run / 'runtime_scene.yaml'
            if not scene.is_file() or scene.is_symlink() or sha(scene) != runtime_scene:
                raise ValueError('retained runtime scene missing or stale')
        binding = {'map_id': item['map_id'], 'base_scene_sha256': base_scene,
                   'runtime_scene_sha256': runtime_scene, 'camera_profile_sha256': profile,
                   'camera_horizontal_fov': fov, 'source_sha256': source,
                   'provider_source_snapshot': provider}
        key = json.dumps(binding, sort_keys=True)
        entry = bindings.setdefault(key, {**binding, 'run_ids': [], 'observation_ids': []})
        if item['run_id'] not in entry['run_ids']:
            entry['run_ids'].append(item['run_id'])
        entry['observation_ids'].append(item['observation_id'])
    return list(bindings.values()), blockers


def validate(*, inventory, qa, progress, export_directory, requirements=None,
             calibration=None, approval=None, evidence=None, policy=None):
    paths = {'inventory': inventory, 'qa': qa, 'progress': progress,
             'requirements': requirements, 'calibration': calibration, 'approval': approval,
             'evidence': evidence, 'policy': policy}
    missing = [key for key, path in paths.items() if path is None or not Path(path).is_file()]
    report = {'schema_version': 'research3-physical-calibration-validation/v1',
              'status': 'blocked_draft',
              'passed': False, 'frozen': False, 'human_review_verified': False,
              'protected_labels_used': False, 'human_identity_authenticated': False,
              'study_complete': False, 'calibration_fitted_by_this_tool': False,
              'blockers': ['missing_input:' + key for key in missing],
              'map_ids': [], 'scene_sha256': [], 'camera_profile_sha256': [], 'scene_bindings': [],
              'limit': 'Binding/policy checks do not authenticate typed human identity or establish recall, '
                       'natural error prevalence, held-out transfer, or out-of-sample calibration efficacy.'}
    if any(key in missing for key in ('inventory', 'qa', 'progress')):
        return report
    coverage_policy = read(requirements) if 'requirements' not in missing else None
    reviewed, samples, readiness = EXPORT.export_payload(inventory, qa, progress, coverage_policy,
        evidence=evidence if 'evidence' not in missing else None,
        policy=policy if 'policy' not in missing else None)
    report['blockers'].extend(readiness['blockers'])
    report['export_readiness'] = readiness
    contract = readiness.get('joint_review_contract')
    if (readiness.get('schema_version') != 'research3-physical-human-export/v2'
            or not isinstance(contract, dict)
            or contract.get('schema_version') != 'research3-joint-calibration-label-contract/v1'
            or contract.get('target') != EXPORT.JOINT_TARGET
            or contract.get('dimensions') != list(EXPORT._UI.DIMENSIONS)):
        report['blockers'].append('joint_observation_calibration_contract_required')
    report['joint_review_contract'] = contract
    expected = {'reviewed_tasks.jsonl': reviewed, 'calibration_samples.jsonl': samples,
                'readiness.json': readiness}
    pins = {key + '_sha256': sha(path) for key, path in paths.items() if key not in missing}
    if isinstance(contract, dict) and (contract.get('evidence_sha256') != pins.get('evidence_sha256')
                                      or contract.get('policy_sha256') != pins.get('policy_sha256')):
        raise ValueError('joint calibration contract does not bind supplied evidence/rubric')
    for name, content in expected.items():
        path = Path(export_directory) / name if export_directory else None
        if path is None or not path.is_file():
            report['blockers'].append('missing_export:' + name)
            continue
        actual = ([json.loads(line) for line in path.read_text().splitlines() if line.strip()]
                  if name.endswith('.jsonl') else read(path))
        if actual != content:
            raise ValueError('stale or conflicting export: ' + name)
        pins[name + '_sha256'] = sha(path)
    store = EXPORT._UI.ReviewStore(inventory, qa, progress, resume=True,
        evidence=evidence if 'evidence' not in missing else None,
        policy=policy if 'policy' not in missing else None)
    bindings, gaps = evidence_bindings(store, reviewed)
    report['blockers'].extend(gaps)
    report['scene_bindings'] = bindings
    report['input_sha256'] = pins
    if not bindings:
        report['blockers'].append('no_exact_reviewed_runtime_bindings')
    if 'calibration' not in missing:
        artifact = read(calibration)
        if (artifact.get('schema_version') != 'landmark-calibration/v1'
                or artifact.get('input_sha256') != pins.get('calibration_samples.jsonl_sha256')):
            raise ValueError('calibrator input is not the revalidated human export')
        if contract is None or artifact.get('joint_review_contract') != contract:
            raise ValueError('calibrator does not bind the revalidated joint observation target/rubric/evidence')
        selected = [row for row in samples if row['partition'] == artifact.get('partition')]
        if (artifact.get('partition') not in ('development', 'validation') or not selected
                or artifact.get('samples') != len(selected)
                or {row['correct'] for row in selected} != {0, 1}):
            report['blockers'].append('calibration_partition_or_binary_fit_coverage_incomplete')
        report['calibration_sha256'] = sha(calibration)
    if 'approval' not in missing:
        auth = read(approval)
        reviewer = auth.get('approved_by')
        if (auth.get('schema_version') != 'research3-physical-calibration-approval/v2'
                or auth.get('status') != 'approved_frozen' or auth.get('reviewer_type') != 'human'
                or auth.get('authorization_scope') != 'nonprotected_physical_calibration'
                or not isinstance(reviewer, str) or not reviewer.strip() or EXPORT.NONHUMAN.search(reviewer)):
            raise ValueError('explicit external human calibration approval required')
        required_pins = {key: value for key, value in pins.items() if key != 'approval_sha256'}
        if auth.get('input_sha256') != required_pins:
            raise ValueError('approval does not pin every current input/export')
        policy_time = timestamp(auth['coverage_policy_approved_at'])
        approval_time = timestamp(auth['approved_at'])
        events = store.events()[1:]
        if not events or policy_time > min(timestamp(row['recorded_at']) for row in events):
            report['blockers'].append('coverage_policy_not_prespecified_before_review')
        if events and approval_time < max(timestamp(row['recorded_at']) for row in events):
            report['blockers'].append('calibration_approval_predates_final_review')
        if auth.get('accepted_scene_bindings') != bindings:
            raise ValueError('approval runtime scope differs from actual reviewed evidence')
        if auth.get('fit_metrics_are_in_sample_only') is not True:
            report['blockers'].append('in_sample_metric_limit_not_acknowledged')
    fovs = {row['camera_horizontal_fov'] for row in bindings}
    if len(fovs) != 1:
        report['blockers'].append('single_campaign_fov_binding_required')
    report['camera_horizontal_fov'] = next(iter(fovs)) if len(fovs) == 1 else None
    report['map_ids'] = sorted({row['map_id'] for row in bindings})
    report['scene_sha256'] = sorted({row['runtime_scene_sha256'] for row in bindings})
    report['camera_profile_sha256'] = sorted({row['camera_profile_sha256'] for row in bindings})
    report['blockers'] = sorted(set(report['blockers']))
    passed = not report['blockers']
    report.update(passed=passed, frozen=passed, human_review_verified=passed,
                  status='validated_approved_scope_only' if passed else 'blocked_draft')
    # Detect saves or source rewrites racing the evidence check.
    for key, path in paths.items():
        if key not in missing and sha(path) != pins[key + '_sha256']:
            raise ValueError('input changed during validation: ' + key)
    for name in expected:
        if name + '_sha256' in pins and sha(Path(export_directory) / name) != pins[name + '_sha256']:
            raise ValueError('export changed during validation: ' + name)
    store.validate()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inventory', 'qa', 'progress', 'export-directory', 'requirements', 'calibration', 'approval', 'evidence', 'policy'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = vars(parser.parse_args())
    output = args.pop('output')
    report = validate(**args)
    with output.open('x') as stream:
        json.dump(report, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
    raise SystemExit(0 if report['passed'] else 2)


if __name__ == '__main__':
    main()
