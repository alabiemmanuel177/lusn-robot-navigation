"""Synthetic fixtures only; no research approval or human labels."""
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import portable_physical_review as KIT


@pytest.fixture
def kit(tmp_path):
    KIT.write_once(tmp_path / 'proposal.json', KIT.encoded(KIT.proposal()))
    KIT.write_once(tmp_path / 'kit_manifest.json', KIT.encoded({
        'schema_version': 'research3-portable-review-kit/v1',
        'files': {'proposal.json': KIT.sha((tmp_path / 'proposal.json').read_bytes())}}))
    return tmp_path


def test_proposals_never_approve():
    p = KIT.proposal()
    assert p['status'] == 'proposed_not_approved'
    assert not p['campaign_authorized'] and not p['human_labels_generated']
    assert set(p['rules']) == {'category_rule', 'entity_association_rule', 'pose_rule', 'yaw_rule'}
    assert p['coverage']['minimum_per_class_outcome'] == 5


@pytest.mark.parametrize('name,role,accepted', [('', 'Researcher', True),
    ('Codex agent', 'Researcher', True), ('Example Person', 'Researcher', False),
    ('Example Person', 'Robot', True)])
def test_no_implicit_or_nonhuman_acceptance(kit, name, role, accepted):
    with pytest.raises(ValueError): KIT.approve(kit, name, role, accepted)
    assert not (kit / 'review_output').exists()


def test_synthetic_explicit_acceptance_bound_and_create_once(kit):
    KIT.approve(kit, 'Example Person', 'Researcher', True)
    policy, requirements = KIT.check_acceptance(kit, kit / 'review_output')
    assert policy['approved_by'] == 'Example Person'
    assert requirements == KIT.COVERAGE
    assert not (kit / 'review_output/progress.jsonl').exists()
    with pytest.raises(FileExistsError): KIT.approve(kit, 'Example Person', 'Researcher', True)
    path = kit / 'review_output/requirements.json'
    path.write_text('{}')
    with pytest.raises(ValueError): KIT.check_acceptance(kit, kit / 'review_output')


def test_tampered_kit_rejected(kit):
    (kit / 'proposal.json').write_text('{}')
    with pytest.raises(ValueError, match='checksum'): KIT.verify_kit(kit)


def test_escaping_kit_member_rejected(kit):
    (kit / 'kit_manifest.json').write_bytes(KIT.encoded({
        'schema_version': 'research3-portable-review-kit/v1', 'files': {'../escape': 'x'}}))
    with pytest.raises(ValueError, match='unsafe'): KIT.verify_kit(kit)


def test_return_rejects_unexpected_paths(kit):
    path = kit / 'return.zip'
    with zipfile.ZipFile(path, 'w') as z: z.writestr('../escape', 'x')
    with pytest.raises(ValueError, match='unexpected'): KIT.validate_return(kit, path)


def test_return_roundtrip_preserves_exact_bytes_and_kit_binding(kit, monkeypatch):
    KIT.approve(kit, 'Example Person', 'Researcher', True)
    progress = kit / 'review_output/progress.jsonl'
    progress.write_text('synthetic isolated test bytes\n')
    before = progress.read_bytes()
    def check(root, out):
        assert (out / 'progress.jsonl').read_bytes() == before
        KIT.check_acceptance(root, out)
        return {'test_only': True}
    monkeypatch.setattr(KIT, 'check_review', check)
    path = kit / 'result.zip'
    KIT.return_review(kit, path)
    assert KIT.validate_return(kit, path) == {'test_only': True}
    assert progress.read_bytes() == before
    with pytest.raises(FileExistsError): KIT.return_review(kit, path)
    manifest = json.loads((kit / 'kit_manifest.json').read_text()); manifest['changed'] = True
    (kit / 'kit_manifest.json').write_bytes(KIT.encoded(manifest))
    with pytest.raises(ValueError, match='another kit'): KIT.validate_return(kit, path)


def test_canonical_paths_ignore_extraction_location(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(KIT, 'ORIGINAL_CONSOLIDATE', lambda *a, **k: {
        'runs': [{'run_id': 'fixture', 'directory': str(tmp_path / 'runs/fixture')}]})
    assert KIT.canonical_consolidate()['runs'][0]['directory'] == 'runs/fixture'
    monkeypatch.setattr(KIT, 'ORIGINAL_CONSOLIDATE', lambda *a, **k: {
        'runs': [{'run_id': 'fixture', 'directory': '/elsewhere/fixture'}]})
    with pytest.raises(ValueError, match='outside'): KIT.canonical_consolidate()


def test_actual_exporter_roundtrip_on_synthetic_observation(kit, monkeypatch):
    spec = importlib.util.spec_from_file_location('portable_synthetic_export_fixture',
        Path(__file__).with_name('test_physical_human_export.py'))
    fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
    run = kit / 'runs/synthetic'; run.mkdir(parents=True)
    fixture.capture.__wrapped__(run)
    fixture.joint_store.__wrapped__(run)
    inventory = json.loads((run / 'inventory.json').read_bytes())
    inventory['runs'][0]['directory'] = 'runs/synthetic'
    (kit / 'inventory.json').write_bytes(KIT.encoded(inventory))
    (kit / 'qa.jsonl').write_bytes((run / 'qa.jsonl').read_bytes())
    monkeypatch.chdir(kit)
    monkeypatch.setattr(KIT._UI._INVENTORY, 'consolidate', KIT.canonical_consolidate)
    (kit / 'evidence.json').write_bytes(KIT.encoded(KIT._UI._JOINT.build(kit / 'inventory.json')))
    KIT.approve(kit, 'Alice Example', 'Researcher', True)
    out = kit / 'review_output'
    store = KIT._UI.ReviewStore(kit / 'inventory.json', kit / 'qa.jsonl', out / 'progress.jsonl',
        evidence=kit / 'evidence.json', policy=out / 'policy.json')
    store.review(0, {'reviewer_id': 'Alice Example', 'notes': 'Synthetic fixture only.',
        'dimension_verdicts': {'category': 'correct', 'entity_association': 'incorrect', 'pose': 'unreviewable'}})
    path = kit / 'returned.zip'
    before = (out / 'progress.jsonl').read_bytes()
    result = KIT.return_review(kit, path)
    assert result['reviewed_binary_labels'] == 1
    assert result['readiness']['blockers']  # one fixture is not adequate coverage
    assert KIT.validate_return(kit, path) == result
    assert (out / 'progress.jsonl').read_bytes() == before
    with zipfile.ZipFile(path) as z: files = {name: z.read(name) for name in z.namelist()}
    events = [json.loads(line) for line in files['progress.jsonl'].splitlines()]
    events[1]['correct'] = True  # malicious aggregate contradicts dimension judgments
    files['progress.jsonl'] = ('\n'.join(json.dumps(row) for row in events)+'\n').encode()
    manifest = json.loads(files['return_manifest.json'])
    manifest['files']['progress.jsonl'] = KIT.sha(files['progress.jsonl'])
    files['return_manifest.json'] = KIT.encoded(manifest)
    corrupt = kit / 'corrupt.zip'
    with zipfile.ZipFile(corrupt, 'w') as z:
        for name, raw in files.items(): z.writestr(name, raw)
    with pytest.raises(ValueError, match='conflict'): KIT.validate_return(kit, corrupt)
