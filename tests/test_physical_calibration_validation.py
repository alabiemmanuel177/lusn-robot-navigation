"""Synthetic-only approval and label fixtures; no research evidence is generated."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


BRIDGE = module('physical_calibration_bridge', ROOT / 'scripts/validate_physical_calibration.py')
FIXTURE = module('physical_calibration_store', ROOT / 'tests/test_physical_review_server.py')
capture, store = FIXTURE.capture, FIXTURE.store


def test_absent_live_inputs_block_without_writing(tmp_path):
    result = BRIDGE.validate(inventory=None, qa=None, progress=None, export_directory=None)
    assert not result['passed'] and not result['frozen']
    assert 'missing_input:approval' in result['blockers']
    assert list(tmp_path.iterdir()) == []


def test_real_provenance_validator_keeps_pending_review_blocked(store, tmp_path):
    before = store.progress.read_bytes()
    result = BRIDGE.validate(inventory=store.inventory, qa=store.qa, progress=store.progress,
                             export_directory=tmp_path / 'absent')
    assert not result['passed']
    assert 'no_accepted_human_binary_labels' in result['blockers']
    assert result['map_ids'] == []
    assert store.progress.read_bytes() == before


def test_stale_export_rejected(store, tmp_path):
    (tmp_path / 'reviewed_tasks.jsonl').write_text('{}\n')
    with pytest.raises(ValueError, match='stale or conflicting export'):
        BRIDGE.validate(inventory=store.inventory, qa=store.qa, progress=store.progress,
                        export_directory=tmp_path)


@pytest.fixture
def approved_fixture(tmp_path, monkeypatch):
    """Exercise bridge protocol in isolation; exporter has separate provenance tests."""
    paths = {}
    for name in ('inventory', 'qa', 'progress', 'requirements', 'calibration', 'approval', 'evidence', 'policy'):
        paths[name] = tmp_path / (name + '.json')
        paths[name].write_text('{}')
    samples = [{'partition': 'validation', 'correct': n, 'observation_id': str(n)} for n in (0, 1)]
    contract = {'schema_version': 'research3-joint-calibration-label-contract/v1',
        'target': BRIDGE.EXPORT.JOINT_TARGET, 'dimensions': list(BRIDGE.EXPORT._UI.DIMENSIONS),
        'evidence_sha256': BRIDGE.sha(paths['evidence']), 'policy_sha256': BRIDGE.sha(paths['policy'])}
    readiness = {'schema_version': 'research3-physical-human-export/v2', 'blockers': [],
                 'joint_review_contract': contract}
    for name, data in [('reviewed_tasks.jsonl', samples), ('calibration_samples.jsonl', samples)]:
        (tmp_path / name).write_text(''.join(json.dumps(row) + '\n' for row in data))
    (tmp_path / 'readiness.json').write_text(json.dumps(readiness))
    paths['calibration'].write_text(json.dumps({'schema_version': 'landmark-calibration/v1',
        'input_sha256': BRIDGE.sha(tmp_path / 'calibration_samples.jsonl'),
        'partition': 'validation', 'samples': 2, 'joint_review_contract': contract}))
    binding = {'map_id': 'r3geo_base_r011', 'base_scene_sha256': 'a' * 64,
               'runtime_scene_sha256': 'b' * 64, 'camera_profile_sha256': 'c' * 64,
               'camera_horizontal_fov': 1.2, 'source_sha256': {'source.py': 'd' * 64},
               'run_ids': ['synthetic'], 'observation_ids': ['0', '1']}
    pins = {name + '_sha256': BRIDGE.sha(path) for name, path in paths.items() if name != 'approval'}
    pins.update({name + '_sha256': BRIDGE.sha(tmp_path / name)
                 for name in ('reviewed_tasks.jsonl', 'calibration_samples.jsonl', 'readiness.json')})
    approval = {'schema_version': 'research3-physical-calibration-approval/v2',
                'status': 'approved_frozen', 'reviewer_type': 'human', 'approved_by': 'Alice Example',
                'authorization_scope': 'nonprotected_physical_calibration', 'input_sha256': pins,
                'coverage_policy_approved_at': '2026-09-01T00:00:00+00:00',
                'approved_at': '2026-09-11T00:00:00+00:00',
                'accepted_scene_bindings': [binding], 'fit_metrics_are_in_sample_only': True}
    paths['approval'].write_text(json.dumps(approval))
    class Store:
        def events(self):
            return [{}, {'recorded_at': '2026-09-10T00:00:00+00:00'}]
        def validate(self):
            pass
    monkeypatch.setattr(BRIDGE.EXPORT, 'export_payload', lambda *a, **kw: (samples, samples, readiness))
    monkeypatch.setattr(BRIDGE.EXPORT._UI, 'ReviewStore', lambda *a, **kw: Store())
    monkeypatch.setattr(BRIDGE, 'evidence_bindings', lambda *a: ([binding], []))
    return {**paths, 'export_directory': tmp_path}


def test_fully_pinned_synthetic_approval_emits_campaign_contract(approved_fixture):
    result = BRIDGE.validate(**approved_fixture)
    assert result['passed'] and result['frozen'] and result['human_review_verified']
    assert not result['human_identity_authenticated']
    assert result['map_ids'] == ['r3geo_base_r011']
    assert result['scene_sha256'] == ['b' * 64]
    assert not result['study_complete']


@pytest.mark.parametrize('mutation', ['stale', 'invented_scope', 'nonhuman', 'posthoc'])
def test_approval_cannot_invent_or_relax_evidence(approved_fixture, mutation):
    path = approved_fixture['approval']
    auth = json.loads(path.read_text())
    if mutation == 'stale':
        auth['input_sha256']['progress_sha256'] = '0' * 64
    elif mutation == 'invented_scope':
        auth['accepted_scene_bindings'][0]['map_id'] = 'r3geo_base_r014'
    elif mutation == 'nonhuman':
        auth['approved_by'] = 'Codex'
    else:
        auth['coverage_policy_approved_at'] = '2026-09-11T00:00:00+00:00'
    path.write_text(json.dumps(auth))
    if mutation == 'posthoc':
        assert 'coverage_policy_not_prespecified_before_review' in BRIDGE.validate(**approved_fixture)['blockers']
    else:
        with pytest.raises(ValueError):
            BRIDGE.validate(**approved_fixture)


def test_wrong_calibration_input_rejected(approved_fixture):
    path = approved_fixture['calibration']
    artifact = json.loads(path.read_text())
    artifact['input_sha256'] = '0' * 64
    path.write_text(json.dumps(artifact))
    with pytest.raises(ValueError, match='calibrator input'):
        BRIDGE.validate(**approved_fixture)


def test_legacy_category_calibrator_cannot_be_admitted_as_joint_observation_calibration(approved_fixture):
    path = approved_fixture['calibration']
    artifact = json.loads(path.read_text())
    artifact.pop('joint_review_contract')
    path.write_text(json.dumps(artifact))
    with pytest.raises(ValueError, match='joint observation target'):
        BRIDGE.validate(**approved_fixture)


def test_bindings_require_retained_runtime_bytes_and_run_scoped_label(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    scene = run / 'runtime_scene.yaml'
    scene.write_text('synthetic runtime scene')
    request = {'asset_sha256': {'landmark_scene.yaml': 'a' * 64},
               'runtime_scene_sha256': BRIDGE.sha(scene), 'camera_profile_sha256': 'c' * 64,
               'camera_horizontal_fov': 1.2, 'source_sha256': {'source.py': 'd' * 64},
               'provider_source_snapshot': {
                   'schema_version': 'research3-capture-provider-source/v1', 'complete': True,
                   'files': {'synthetic-provider.py': 'e' * 64}}}
    (run / 'request.json').write_text(json.dumps(request))
    class Store:
        items = [{'observation_id': 'duplicate', 'run_id': 'accepted', 'map_id': 'r3geo_base_r011'},
                 {'observation_id': 'duplicate', 'run_id': 'excluded', 'map_id': 'r3geo_base_r012'}]
        runs = {'accepted': run}
        def events(self):
            return [{}, {'item_index': 0, 'correct': True}, {'item_index': 1, 'correct': None}]
    bindings, blockers = BRIDGE.evidence_bindings(Store(), [{'observation_id': 'duplicate'}])
    assert not blockers
    assert len(bindings) == 1 and bindings[0]['map_id'] == 'r3geo_base_r011'
    assert bindings[0]['runtime_scene_sha256'] == BRIDGE.sha(scene)
    assert bindings[0]['provider_source_snapshot'] == request['provider_source_snapshot']
    request.pop('provider_source_snapshot')
    (run / 'request.json').write_text(json.dumps(request))
    assert BRIDGE.evidence_bindings(Store(), [{'observation_id': 'duplicate'}])[0] == []
    request['provider_source_snapshot'] = bindings[0]['provider_source_snapshot']
    (run / 'request.json').write_text(json.dumps(request))
    scene.write_text('changed')
    with pytest.raises(ValueError, match='scene missing or stale'):
        BRIDGE.evidence_bindings(Store(), [{'observation_id': 'duplicate'}])


def test_missing_exact_scene_never_becomes_map_coverage(store):
    store.review(0, {'reviewer_id': 'Alice Example', 'verdict': 'correct', 'notes': ''})
    bindings, blockers = BRIDGE.evidence_bindings(store, [{'observation_id': 'obs1'}])
    assert bindings == []
    assert blockers[0].startswith('incomplete_exact_runtime_binding:')
