"""Synthetic candidate-fit fixtures only; not approved research labels or settings."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location('joint_fit_test', ROOT / 'scripts/fit_physical_joint_calibration.py')
FIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIT)


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    paths = {}
    for name in ('inventory', 'qa', 'progress', 'evidence', 'policy', 'requirements'):
        path = tmp_path / (name + '.json')
        path.write_text('{}')
        paths[name] = path
    samples = [{'schema_version': 'landmark-calibration-sample/v1', 'observation_id': 'synthetic-' + str(label),
        'partition': 'validation', 'category': 'chair', 'probability': probability, 'correct': label}
        for label, probability in ((0, .8), (1, .7))]
    contract = {'schema_version': 'research3-joint-calibration-label-contract/v1', 'target': FIT.EXPORT.JOINT_TARGET,
        'evidence_sha256': FIT.EXPORT._UI.digest(paths['evidence']),
        'policy_sha256': FIT.EXPORT._UI.digest(paths['policy'])}
    readiness = {'schema_version': 'research3-physical-human-export/v2', 'blockers': [],
        'joint_review_contract': contract,
        **{key + '_sha256': FIT.EXPORT._UI.digest(paths[key]) for key in ('inventory', 'qa', 'progress')}}
    for name in ('reviewed_tasks.jsonl', 'calibration_samples.jsonl'):
        (tmp_path / name).write_text(''.join(json.dumps(row) + '\n' for row in samples))
    (tmp_path / 'readiness.json').write_text(json.dumps(readiness))
    monkeypatch.setattr(FIT.EXPORT, 'export_payload', lambda *a, **kw: (samples, samples, readiness))
    return {**paths, 'export_directory': tmp_path, 'partition': 'validation', 'minimum_samples': 2}, readiness


def test_revalidated_joint_candidate_preserves_target_without_deployment_approval(candidate):
    args, readiness = candidate
    result = FIT.fit(**args)
    assert result['joint_review_contract'] == readiness['joint_review_contract']
    assert result['samples'] == 2 and result['labels'] == {'correct': 1, 'incorrect': 1}
    assert result['deployment_approval_granted_by_this_tool'] is False
    assert result['fit_metrics_scope'] == 'in_sample_only'


@pytest.mark.parametrize('problem', ['blocked', 'legacy', 'stale_samples', 'insufficient', 'protected'])
def test_inadmissible_input_never_fits_deployable_candidate(candidate, problem):
    args, readiness = candidate
    if problem == 'blocked':
        readiness['blockers'] = ['coverage_incomplete']
    elif problem == 'legacy':
        readiness['joint_review_contract'] = None
    elif problem == 'stale_samples':
        (args['export_directory'] / 'calibration_samples.jsonl').write_text('{}\n')
    elif problem == 'insufficient':
        args['minimum_samples'] = 3
    else:
        args['partition'] = 'test'
    with pytest.raises(ValueError):
        FIT.fit(**args)
