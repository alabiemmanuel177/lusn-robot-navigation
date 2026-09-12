"""All decisions here are synthetic fixtures, never genuine research labels."""
import importlib.util
import json
from pathlib import Path

import pytest


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


ROOT = Path(__file__).resolve().parents[1]
EXPORT = module('physical_export', ROOT / 'scripts/export_physical_human_review.py')
FIXTURE = module('physical_server_fixture', ROOT / 'tests/test_physical_review_server.py')
capture, store = FIXTURE.capture, FIXTURE.store


def payload(store, requirements=None):
    return EXPORT.export_payload(store.inventory, store.qa, store.progress, requirements,
                                  evidence=store.evidence, policy=store.policy)


def event(store, verdict='correct', reviewer='Alice Example'):
    if store.evidence:
        dimensions = dict.fromkeys(EXPORT._UI.DIMENSIONS, 'correct')
        if verdict == 'incorrect':
            dimensions['entity_association'] = 'incorrect'
        elif verdict == 'unreviewable':
            dimensions['pose'] = 'unreviewable'
        return store.review(0, {'reviewer_id': reviewer, 'dimension_verdicts': dimensions, 'notes': ''})
    return store.review(0, {'reviewer_id': reviewer, 'verdict': verdict, 'notes': ''})


@pytest.fixture
def joint_store(capture):
    """Real evidence builder on synthetic capture/reference files, not human research labels."""
    ui = EXPORT._UI
    request_path = capture / 'request.json'
    request = json.loads(request_path.read_text())
    scene = {'map_id': request['map_id'], 'partition': request['partition'],
        'entities': [{'entity_id': 'chair1', 'region_id': 'region1', 'category': 'chair',
                      'pose': {'x': 2., 'y': 0., 'yaw': 0.}}]}
    (capture / 'runtime_scene.yaml').write_text(json.dumps(scene))
    request.update(runtime_scene_sha256=ui.digest(capture / 'runtime_scene.yaml'),
                   capture_pose={'x': 0., 'y': 0., 'yaw': 0.})
    request_path.write_text(json.dumps(request))
    media = capture / 'perception_capture'
    frame = json.loads((media / 'frame-000.json').read_text())
    observation = dict(frame['trigger_observations'][0], x=2., y=0., yaw=0.,
                       covariance=[.1, 0., 0., .1], frame_id='map')
    index = {'schema_version': 'research3-captured-frame-observations/v1', 'frames': [{
        'frame': 'frame-000.json', 'frame_sha256': ui.digest(media / 'frame-000.json'),
        'rgb_stamp_ns': frame['rgb_stamp_ns'], 'observations': [observation]}]}
    (media / 'observation_index.json').write_text(json.dumps(index))
    (media / 'summary.json').write_text(json.dumps({'frames': ['frame-000.json'],
        'observation_index': {'file': 'observation_index.json', 'sha256': ui.digest(media / 'observation_index.json')}}))
    qa = FIXTURE.FIXTURES.synthetic_qa(capture)
    qa_path = capture / 'qa.jsonl'
    qa_path.write_text(json.dumps(qa))
    inventory = ui._INVENTORY.consolidate([capture], [qa])
    inventory_path = capture / 'inventory.json'
    inventory_path.write_text(json.dumps(inventory))
    evidence = capture / 'joint-evidence.json'
    evidence.write_text(json.dumps(ui._JOINT.build(inventory_path)))
    policy = capture / 'joint-policy.json'
    policy.write_text(json.dumps({'schema_version': 'research3-joint-review-policy/v1',
        'status': 'approved', 'approved_by': 'Alice Example', 'reviewer_type': 'human',
        'approved_at': '2020-01-01T00:00:00+00:00', 'protected_data_used': False,
        **dict.fromkeys(('category_rule', 'entity_association_rule', 'pose_rule', 'yaw_rule'),
                        'Synthetic fixture rule only; not an approved research tolerance')}))
    return ui.ReviewStore(inventory_path, qa_path, capture / 'joint-progress.jsonl', evidence=evidence, policy=policy)


def test_empty_header_only_readonly_and_blocked(store):
    before = store.progress.read_bytes()
    rows, samples, report = payload(store)
    assert rows == samples == []
    assert report['status'] == 'blocked'
    assert report['excluded_counts'] == {'pending_human_review': 1}
    assert store.progress.read_bytes() == before


def test_legacy_category_only_positive_cannot_become_joint_calibration_label(store):
    event(store, 'correct')
    before = store.progress.read_bytes()
    rows, samples, report = payload(store)
    assert rows == samples == []
    assert 'joint_observation_review_required' in report['blockers']
    assert report['excluded_counts']['legacy_category_only_not_joint_review'] == 1
    assert store.progress.read_bytes() == before


@pytest.mark.parametrize('verdict,correct', [('correct', 1), ('incorrect', 0)])
def test_provider_schema_and_immutable_original_fields(joint_store, verdict, correct):
    store = joint_store
    event(store, verdict)
    original = json.loads((next(iter(store.runs.values())) / 'landmark_review_tasks.jsonl').read_text())
    before = store.progress.read_bytes()
    rows, samples, report = payload(store)
    assert rows[0] == {**original, 'review_status': 'human_verified',
                       'reviewer_id': 'Alice Example', 'correct': correct}
    assert samples[0] == {'schema_version': 'landmark-calibration-sample/v1',
                         'observation_id': 'obs1', 'partition': 'development', 'category': 'chair',
                         'probability': .8, 'correct': correct}
    assert not report['calibration_fitted']
    assert report['schema_version'] == 'research3-physical-human-export/v2'
    assert report['joint_review_contract']['target'] == EXPORT.JOINT_TARGET
    assert report['joint_review_contract']['accepted_label_bindings'][0]['dimension_verdicts']['category'] == 'correct'
    assert store.progress.read_bytes() == before


@pytest.mark.parametrize('mutation', ['dimensions', 'missing_dimension', 'evidence', 'rubric', 'item', 'preapproval'])
def test_joint_dimension_and_rubric_tampering_rejected(joint_store, mutation):
    event(joint_store)
    lines = joint_store.events()
    row = lines[-1]
    if mutation == 'dimensions':
        row['dimension_verdicts']['pose'] = 'incorrect'
    elif mutation == 'missing_dimension':
        row['dimension_verdicts'].pop('pose')
    elif mutation == 'preapproval':
        row['recorded_at'] = '2019-01-01T00:00:00+00:00'
    else:
        row[{'evidence': 'evidence_sha256', 'rubric': 'policy_sha256', 'item': 'item_evidence_sha256'}[mutation]] = '0' * 64
    joint_store.progress.write_text(''.join(json.dumps(row) + '\n' for row in lines))
    with pytest.raises(ValueError):
        payload(joint_store)


def test_uncertain_pose_is_not_a_joint_positive_or_negative(joint_store):
    event(joint_store, 'unreviewable')
    rows, samples, report = payload(joint_store)
    assert rows == samples == []
    assert report['excluded_counts'] == {'human_unreviewable': 1}


def test_draft_rubric_cannot_support_hand_appended_binary_events(joint_store):
    event(joint_store)
    policy = json.loads(joint_store.policy.read_text())
    policy['status'] = 'draft'
    joint_store.policy.write_text(json.dumps(policy))
    lines = joint_store.events()
    for row in lines:
        row['policy_sha256'] = EXPORT._UI.digest(joint_store.policy)
    joint_store.progress.write_text(''.join(json.dumps(row) + '\n' for row in lines))
    with pytest.raises(ValueError, match='approved rubric'):
        payload(joint_store)


def test_unreviewable_excluded_not_incorrect_and_latest_event_wins(store):
    event(store, 'correct')
    event(store, 'unreviewable')
    rows, samples, report = payload(store)
    assert rows == samples == []
    assert report['excluded_counts'] == {'human_unreviewable': 1}
    assert report['superseded_events'] == 1
    assert report['excluded'][0]['correct'] is None


@pytest.mark.parametrize('reviewer', ['Synthetic test reviewer', 'Codex', 'AI agent', 'automated bot'])
def test_explicit_nonhuman_labels_rejected(store, reviewer):
    event(store, reviewer=reviewer)
    with pytest.raises(ValueError, match='non-human'):
        payload(store)


@pytest.mark.parametrize('field,value', [('task_sha256', 'stale'), ('correct', False),
                                       ('review_status', 'machine_verified'), ('item_index', True)])
def test_stale_or_conflicting_audit_rejected(store, field, value):
    event(store)
    lines = store.events()
    lines[-1][field] = value
    store.progress.write_text(''.join(json.dumps(row) + '\n' for row in lines))
    with pytest.raises(ValueError):
        payload(store)


def test_duplicate_event_rejected(store):
    event(store)
    rows = store.events()
    with store.progress.open('a') as stream:
        stream.write(json.dumps(rows[-1]) + '\n')
    with pytest.raises(ValueError, match='duplicate'):
        payload(store)


def test_coverage_bins_and_missing_outcomes_remain_blockers(store):
    event(store)
    requirements = {'schema_version': 'research3-physical-calibration-coverage/v1',
                    'minimum_per_map_class_outcome': 1, 'minimum_per_class_confidence_bin': 1,
                    'confidence_bin_edges': [0, .5, 1]}
    _, _, report = payload(store, requirements)
    assert 'map_class_binary_outcome_coverage_incomplete' in report['blockers']
    assert 'class_confidence_coverage_incomplete' in report['blockers']
    assert not report['human_identity_authenticated']


def test_create_once_outputs_and_missing_progress_not_created(store, tmp_path):
    event(store)
    rows, samples, report = payload(store)
    output = tmp_path / 'export'
    EXPORT.write_export(output, rows, samples, report)
    before = (output / 'reviewed_tasks.jsonl').read_bytes()
    with pytest.raises(FileExistsError):
        EXPORT.write_export(output, rows, samples, report)
    assert (output / 'reviewed_tasks.jsonl').read_bytes() == before
    missing = tmp_path / 'missing-human-progress.jsonl'
    with pytest.raises(FileNotFoundError):
        EXPORT.export_payload(store.inventory, store.qa, missing)
    assert not missing.exists()


def test_invalid_confidence_policy_rejected():
    with pytest.raises(ValueError):
        EXPORT.validate_requirements({'schema_version': 'research3-physical-calibration-coverage/v1',
             'minimum_per_map_class_outcome': 0, 'minimum_per_class_confidence_bin': 1,
             'confidence_bin_edges': [0, 1]})


def v2_policy(**overrides):
    return {'schema_version': 'research3-physical-calibration-coverage/v2',
            'outcome_coverage_scope': 'global_class', 'minimum_per_map_class_total': 1,
            'minimum_per_class_outcome': 1, 'minimum_per_class_confidence_bin': 1,
            'confidence_bin_edges': [0, .5, 1], 'unreviewable_exclusion_policy': 'allow_with_counts',
            **overrides}


def test_v2_global_outcome_coverage_does_not_require_errors_in_every_map():
    counts = [{'map_id': 'map1', 'category': 'chair', 'correct': 2, 'incorrect': 0},
              {'map_id': 'map2', 'category': 'chair', 'correct': 0, 'incorrect': 2}]
    assert EXPORT.coverage_blockers(counts, [], v2_policy()) == []
    blockers = EXPORT.coverage_blockers(counts, [], v2_policy(outcome_coverage_scope='map_class'))
    assert blockers == ['map_class_binary_outcome_coverage_incomplete']


def test_v2_unreviewable_policy_explicit_pending_always_blocks():
    counts = [{'map_id': 'map1', 'category': 'chair', 'correct': 1, 'incorrect': 1}]
    exclusion = [{'reason': 'human_unreviewable', 'correct': None}]
    assert EXPORT.coverage_blockers(counts, exclusion, v2_policy()) == []
    assert EXPORT.coverage_blockers(counts, exclusion,
        v2_policy(unreviewable_exclusion_policy='block')) == ['unreviewable_exclusions_blocked_by_protocol']
    assert EXPORT.coverage_blockers(counts, [{'reason': 'pending_human_review'}],
        v2_policy()) == ['pending_human_review']


def test_v2_requires_per_map_total_even_when_global_outcomes_pass():
    counts = [{'map_id': 'map1', 'category': 'chair', 'correct': 2, 'incorrect': 2},
              {'map_id': 'map2', 'category': 'chair', 'correct': 0, 'incorrect': 0}]
    assert EXPORT.coverage_blockers(counts, [], v2_policy()) == ['map_class_total_coverage_incomplete']


@pytest.mark.parametrize('field,value', [('outcome_coverage_scope', 'auto'),
    ('unreviewable_exclusion_policy', 'ignore'), ('minimum_per_map_class_total', 0),
    ('minimum_per_class_outcome', True)])
def test_v2_invalid_or_implicit_choices_rejected(field, value):
    with pytest.raises(ValueError):
        EXPORT.validate_requirements(v2_policy(**{field: value}))


def test_v2_export_keeps_policy_hash_and_no_automatic_fit(store):
    event(store)
    _, _, report = payload(store, v2_policy())
    assert report['requirements_sha256'] == EXPORT._UI._INVENTORY.task_digest(v2_policy())
    assert report['status'] == 'blocked'
    assert not report['calibration_fitted']
