"""Source admission rejects provider/core drift without rewriting history."""
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import snapshot_expansion_instrumentation as pin


@pytest.fixture
def sources(tmp_path, monkeypatch):
    monkeypatch.setattr(pin, 'ROOT', tmp_path)
    approval = tmp_path / 'reports/human_method_decisions_20260912_v1/decision_record.json'
    approval.parent.mkdir(parents=True)
    approval.write_text(json.dumps({'P4': {
        'capture_instrumentation_source_revision_authorized': True,
        'named_candidates': list(pin.FILES)}}))
    wrapper=tmp_path/'reports/human_wrapper_decision_20260912_v1/decision_record.json'
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text(json.dumps({'authorized': True}))
    prior = tmp_path / 'reports/fresh_current_capture_20260911_v1/current_source_snapshot.json'
    prior.parent.mkdir(parents=True)
    prior.write_text(json.dumps({'source_sha256': {'scripts/run_physical_episode.py': 'old'},
                                'provider_source_snapshot': {'provider': 'fixed'}}))
    for name in pin.FILES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('pass\n')
    core = {'scripts/run_physical_episode.py': 'new'}
    provider = {'provider': 'fixed'}
    monkeypatch.setattr(pin, 'capture_source_snapshot', lambda: dict(core))
    monkeypatch.setattr(pin, 'capture_provider_snapshot', lambda: dict(provider))
    return tmp_path, prior, core, provider


def test_exact_scope_create_once_and_validation(sources):
    root, prior, _, _ = sources
    old = prior.read_bytes()
    output = root / 'pin'
    record = pin.snapshot(output)
    assert record['changed_historical_files'] == ['scripts/run_physical_episode.py']
    assert prior.read_bytes() == old
    assert pin.validate(output / 'snapshot.json') == hashlib.sha256((output / 'snapshot.json').read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        pin.snapshot(output)
    (root / pin.FILES[0]).write_text('pass # changed\n')
    with pytest.raises(ValueError, match='instrumentation changed'):
        pin.validate(output / 'snapshot.json')


@pytest.mark.parametrize('kind', ['core', 'provider'])
def test_out_of_scope_changes_refused_before_output(sources, kind):
    root, _, core, provider = sources
    (core if kind == 'core' else provider)['unapproved'] = 'changed'
    with pytest.raises(ValueError):
        pin.snapshot(root / 'pin')
    assert not (root / 'pin').exists()


def test_provider_drift_after_pin_refused(sources):
    root, _, _, provider = sources
    pin.snapshot(root / 'pin')
    provider['provider'] = 'drift'
    with pytest.raises(ValueError, match='snapshot mismatch'):
        pin.validate(root / 'pin/snapshot.json')
