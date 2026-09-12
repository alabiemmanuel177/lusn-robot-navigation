"""Synthetic-only joint review tests; no real human verdicts."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('joint_ui_test', ROOT / 'scripts/serve_physical_review.py')
UI = importlib.util.module_from_spec(spec)
spec.loader.exec_module(UI)


def test_joint_dimensions_not_category_alone():
    assert UI.joint_verdict(dict(category='correct', entity_association='incorrect', pose='correct')) == 'incorrect'
    assert UI.joint_verdict(dict(category='correct', entity_association='correct', pose='unreviewable')) == 'unreviewable'
    assert UI.joint_verdict(dict.fromkeys(UI.DIMENSIONS, 'correct')) == 'correct'
    with pytest.raises(ValueError):
        UI.joint_verdict({'category': 'correct'})


def test_no_automatic_policy_approval():
    policy = {'schema_version': 'research3-joint-review-policy/v1', 'status': 'draft'}
    assert not UI._JOINT.validate_policy(policy)
    policy.update(status='approved', approved_by='Example Person', reviewer_type='human',
                  approved_at='2020-01-01T00:00:00+00:00', protected_data_used=False,
                  **dict.fromkeys(('category_rule', 'entity_association_rule', 'pose_rule', 'yaw_rule'), 'Fixture rule'))
    assert UI._JOINT.validate_policy(policy)
    for patch in ({'approved_by': 'Automated agent'}, {'approved_at': '2099-01-01T00:00:00+00:00'},
                  {'approved_at': '2020-01-01'}, {'pose_rule': ''}, {'reviewer_type': 'machine'}):
        assert not UI._JOINT.validate_policy({**policy, **patch})


def test_missing_evidence_retained_without_labels(tmp_path):
    run = tmp_path / 'run'; run.mkdir()
    (run / 'request.json').write_text(json.dumps({'map_id': 'r3geo_base_r015', 'protected_test_routes_used': True}))
    inventory = tmp_path / 'inventory.json'
    inventory.write_text(json.dumps({'protected_data_used': False,
        'runs': [{'run_id': 'fixture', 'directory': str(run)}], 'items': [{
            'status': 'ready_for_human_review', 'run_id': 'fixture', 'observation_id': 'obs',
            'frame_sha256': 'frame', 'task_sha256': 'task'}]}))
    result = UI._JOINT.build(inventory)
    assert result['items'][0]['gaps'] == ['protected or unidentified run']
    assert result['items'][0]['evidence_complete'] is False
    assert result['human_labels_generated'] is False
    assert 'correct' not in result['items'][0]


def test_request_cannot_authorize_its_own_changed_scene(tmp_path):
    run = tmp_path / 'run'; run.mkdir()
    (run / 'request.json').write_text(json.dumps({'map_id': 'r3geo_base_r001',
        'partition': 'development', 'protected_test_routes_used': False,
        'runtime_scene_sha256': 'self-asserted-changed-scene'}))
    inventory = tmp_path / 'inventory.json'
    inventory.write_text(json.dumps({'protected_data_used': False,
        'runs': [{'run_id': 'fixture', 'directory': str(run), 'request_sha256': 'original'}],
        'items': [{'status': 'ready_for_human_review', 'run_id': 'fixture',
                   'observation_id': 'obs', 'frame_sha256': 'frame', 'task_sha256': 'task',
                   'request_sha256': 'original'}]}))
    result = UI._JOINT.build(inventory)
    assert result['items'][0]['gaps'] == ['request differs from immutable inventory binding']
    assert not result['items'][0]['evidence_complete']


def test_joint_event_bound_and_missing_policy_blocks_binary(tmp_path, monkeypatch):
    item = {'run_id': 'fixture', 'observation_id': 'obs', 'task_sha256': 'task', 'frame_sha256': 'frame'}
    store = object.__new__(UI.ReviewStore)
    import threading
    store.lock = threading.Lock()
    store.evidence = tmp_path / 'evidence.json'; store.progress = tmp_path / 'progress.jsonl'
    store.evidence_hash = 'evidence'; store.policy_hash = 'policy'
    monkeypatch.setattr(store, 'validate', lambda: ([item], {}))
    row = {'evidence_complete': True}
    monkeypatch.setattr(store, 'validate_joint', lambda: ([row], {}, False))
    fields = {'reviewer_id': 'Synthetic reviewer', 'notes': '', 'dimension_verdicts': dict.fromkeys(UI.DIMENSIONS, 'correct')}
    with pytest.raises(ValueError, match='preview only'):
        store.review(0, fields)
    with pytest.raises(ValueError, match='preview only'):
        store.review(0, {**fields, 'dimension_verdicts': dict.fromkeys(UI.DIMENSIONS, 'unreviewable')})
    assert not store.progress.exists()
    monkeypatch.setattr(store, 'validate_joint', lambda: ([row], {}, True))
    event = store.review(0, fields)
    assert event['correct'] is True
    assert event['item_evidence_sha256'] == UI._JOINT.object_hash(row)
    assert event['policy_sha256'] == 'policy'


def test_approved_policy_missing_reference_cannot_be_positive(tmp_path, monkeypatch):
    store = object.__new__(UI.ReviewStore)
    import threading
    store.lock = threading.Lock(); store.evidence = tmp_path / 'evidence'
    store.progress = tmp_path / 'progress'; store.evidence_hash = 'e'; store.policy_hash = 'p'
    item = dict(run_id='fixture', observation_id='obs', task_sha256='t', frame_sha256='f')
    monkeypatch.setattr(store, 'validate', lambda: ([item], {}))
    monkeypatch.setattr(store, 'validate_joint', lambda: ([{'evidence_complete': False}], {}, True))
    with pytest.raises(ValueError, match='unreviewable only'):
        store.review(0, dict(reviewer_id='Synthetic fixture', notes='', dimension_verdicts=dict.fromkeys(UI.DIMENSIONS, 'correct')))
    assert not store.progress.exists()


def test_entire_browser_script_parses():
    import shutil
    import subprocess
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node not installed')
    script = UI.PAGE.split('<script>', 1)[1].split('</script>', 1)[0]
    subprocess.run([node, '--check'], input=script, text=True, capture_output=True, check=True)


def test_joint_hidden_controls_and_reference_layout_regression():
    assert '[hidden]{display:none!important}' in UI.PAGE
    assert '||state?.joint_review' in UI.PAGE
    assert '#joint-reference{grid-column:1 / -1' in UI.PAGE
    assert 'id="coordinate-legend"' in UI.PAGE
    assert 'text.textContent=String(index+1)' in UI.PAGE
    assert 'text.textContent=ref.entity_id' not in UI.PAGE


def test_loaded_image_message_respects_pending_policy():
    import re
    import shutil
    import subprocess
    helper = re.search(r'^function imageStatus.*$', UI.PAGE, re.M)
    assert helper is not None
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node unavailable')
    script = helper.group() + "\nconsole.log(JSON.stringify([imageStatus(true,true,false),imageStatus(true,true,true),imageStatus(false,true,false)]));"
    rows = json.loads(subprocess.run([node, '-e', script], text=True, capture_output=True, check=True).stdout)
    assert 'preview only' in rows[0].lower()
    assert 'You may review' not in rows[0]
    assert 'You may review' in rows[1]
    assert 'could not load' in rows[2]


def test_joint_ui_requires_three_choices_and_explains_yaw():
    assert 'catalogue, not an independent orientation estimate' in UI.PAGE
    assert 'Choose a judgment' in UI.PAGE
    assert 'Save three judgments' in UI.PAGE
    assert 'Only Unreviewable can be saved' in UI.PAGE
