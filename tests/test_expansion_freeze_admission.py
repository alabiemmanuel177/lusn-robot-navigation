"""Synthetic admission fixtures only; no production human labels or approvals."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import fit_expansion_calibration as fit


def model():
    return dict(schema_version='research3-expansion-development-calibration-candidate/v1',
        status='numerical_candidate_not_frozen',partition='development',method='classwise_temperature_scaling_p2',
        coverage=dict(passed=True),classes={c:dict(temperature=1.0) for c in fit.classwise.CLASSES},
        validation_used=False,pilot_or_diagnostic_rows_included=False,export_readiness=dict(blockers=[]))


def gate():
    return dict(schema_version='research3-validation-release-gate/v1',status='approved_development_model_frozen',
        reviewer_type='human',approved_by='Example Reviewer',approved_at='2026-09-22T12:00:00+00:00',
        validation_used_for_fitting_or_selection=False,development_model_sha256='a'*64,
        calibration_protocol_sha256='b'*64)


def test_failed_fit_never_invites_freeze_or_key_release():
    value=model();value.update(status='coverage_blocked',classes=None);value['coverage']['passed']=False
    assert fit.development_model_ready(value) is False
    instruction=fit.freeze_next_action(value)
    assert 'Do not freeze' in instruction and 'do not release' in instruction


def test_canonical_sealing_gate_is_accepted_for_evaluation():
    fit.require_evaluation_gate(gate(),'a'*64,'b'*64)


@pytest.mark.parametrize('field,value',[('status','approved'),('reviewer_type','assistant'),('approved_at','2026-09-22'),('calibration_protocol_sha256','c'*64),('validation_used_for_fitting_or_selection',True)])
def test_invalid_or_incompatible_release_gate_rejected(field,value):
    record=gate();record[field]=value
    with pytest.raises((ValueError,PermissionError)):
        fit.require_evaluation_gate(record,'a'*64,'b'*64)


@pytest.mark.parametrize('temperature',[0.0,float('nan'),float('inf'),True])
def test_invalid_temperature_blocks_model(temperature):
    value=model();value['classes'][fit.classwise.CLASSES[0]]['temperature']=temperature
    assert not fit.development_model_ready(value)


@pytest.mark.parametrize('blocked', [True, False])
def test_validation_entrypoint_checks_gate_before_accessing_labels(tmp_path, monkeypatch, blocked):
    import json
    from types import SimpleNamespace
    candidate=model()
    candidate['provenance']={'protocol_doc_sha256':fit.sha_file(fit.PROTOCOL_DOC)}
    if blocked:
        candidate.update(status='coverage_blocked',classes=None)
        candidate['coverage']['passed']=False
    model_path=tmp_path/'synthetic-model.json'
    model_path.write_text(json.dumps(candidate))
    decision=gate()
    decision.update(development_model_sha256=fit.sha_file(model_path),
                    calibration_protocol_sha256=fit.sha_file(fit.PROTOCOL_DOC))
    gate_path=tmp_path/'synthetic-gate.json'
    gate_path.write_text(json.dumps(decision))
    calls=[]
    class ReachedSyntheticLabels(Exception):pass
    def sentinel(*args):
        calls.append(args)
        raise ReachedSyntheticLabels
    monkeypatch.setattr(fit,'labelled_rows',sentinel)
    args=SimpleNamespace(output=tmp_path/'output',development_model=model_path,
                         release_gate=gate_path,kit='SYNTHETIC-KIT',return_zip='SYNTHETIC-RETURN')
    with pytest.raises(ValueError if blocked else ReachedSyntheticLabels):
        fit.validate(args)
    assert bool(calls) is (not blocked)
