"""Synthetic approval bindings only; never manufacture production human labels."""
import copy
import importlib.util
import io
from pathlib import Path
import zipfile

import pytest

SPEC = importlib.util.spec_from_file_location('handoff', Path(__file__).resolve().parents[1]
                                            / 'scripts/package_expansion_handoff.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


@pytest.fixture
def approval():
    bindings = {key: key.encode() for key in ('amendment_sha256', 'plan_sha256',
                'phase_1_return_sha256', 'phase_1_usability_audit_sha256')}
    value = {'schema_version': 'research3-calibration-expansion-review/v1',
             'overall_decision': 'accept', 'grants_execution_by_itself': False,
             'protected_outcomes_consulted': False, 'reviewer_role': 'Researcher',
             'reviewer_name': 'Synthetic test fixture', 'reviewed_at': '2026-09-12T00:24:00Z',
             'decisions': {k: {'decision': 'accept', 'rationale': 'Fixture only.'} for k in M.GATES},
             **{k: M.digest(v) for k, v in bindings.items()}}
    return value, copy.deepcopy(value), bindings


def test_bound_acceptance(approval):
    M.validate_decision(*approval)


@pytest.mark.parametrize('key', ['amendment_sha256', 'plan_sha256',
                               'phase_1_return_sha256', 'phase_1_usability_audit_sha256'])
def test_changed_artifact_refused(approval, key):
    value, template, bindings = approval
    bindings[key] += b'changed'
    with pytest.raises(ValueError, match='hash mismatch'):
        M.validate_decision(value, template, bindings)


@pytest.mark.parametrize('key', ['grants_execution_by_itself', 'protected_outcomes_consulted'])
def test_cannot_expand_authority(approval, key):
    approval[0][key] = True
    with pytest.raises(ValueError, match='scope'):
        M.validate_decision(*approval)


def test_pending_or_missing_gate_refused(approval):
    approval[0]['decisions']['pilot_only']['decision'] = 'pending'
    with pytest.raises(ValueError, match='all gates'):
        M.validate_decision(*approval)
    del approval[0]['decisions']['pilot_only']
    with pytest.raises(ValueError, match='eight gates'):
        M.validate_decision(*approval)


def test_other_proposal_refused(approval):
    approval[1]['plan_sha256'] = 'wrong proposal'
    with pytest.raises(ValueError, match='another frozen'):
        M.validate_decision(*approval)


def test_timezone_required(approval):
    approval[0]['reviewed_at'] = '2026-09-12T00:24:00'
    with pytest.raises(ValueError, match='timezone'):
        M.validate_decision(*approval)


@pytest.mark.parametrize('name', ['../escape', '/tmp/escape', 'dir\\escape'])
def test_unsafe_kit_refused(tmp_path, name):
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, 'w') as archive:
        archive.writestr(name, b'no')
    with pytest.raises(ValueError, match='unsafe'):
        M.safe_unpack_kit(raw.getvalue(), tmp_path)
