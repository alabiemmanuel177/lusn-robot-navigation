"""Synthetic byte fixtures, not generated production labels or approvals."""
import base64
import importlib.util
import io
import json
from pathlib import Path
import zipfile

import pytest
from cryptography.exceptions import InvalidTag

SPEC=importlib.util.spec_from_file_location('seal',Path(__file__).resolve().parents[1]/'scripts/seal_validation_review.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


@pytest.fixture
def bundle():
    kit=M.encoded({'schema_version':'research3-portable-review-kit/v1',
                   'expansion_partition':'validation','diagnostic_or_pilot_included':False})
    files={name:b'synthetic fixture only' for name in M.RETURN_NAMES-{'return_manifest.json'}}
    files['return_manifest.json']=M.encoded({'schema_version':'research3-portable-review-return/v1',
        'kit_sha256':M.sha(kit),'files':{k:M.sha(v) for k,v in files.items()}})
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        for name,value in files.items():z.writestr(name,value)
    return stream.getvalue(),kit


def gate(envelope):
    return {'schema_version':'research3-validation-release-gate/v1',
            'status':'approved_development_model_frozen','reviewer_type':'human','approved_by':'Synthetic fixture',
            'approved_at':'2026-09-12T10:00:00+00:00','validation_used_for_fitting_or_selection':False,
            'sealed_validation_sha256':M.sha(envelope),'development_model_sha256':M.sha(b'model'),
            'calibration_protocol_sha256':M.sha(b'protocol')}


def test_roundtrip_requires_gate(bundle):
    raw,kit=bundle;envelope,key=M.seal(raw,kit)
    assert b'synthetic fixture only' not in envelope
    assert M.open_sealed(envelope,key,gate(envelope),b'model',b'protocol')==raw
    with pytest.raises(ValueError,match='freeze'):
        M.open_sealed(envelope,key,{},b'model',b'protocol')


def test_changed_model_refused(bundle):
    envelope,key=M.seal(*bundle)
    with pytest.raises(ValueError,match='freeze'):
        M.open_sealed(envelope,key,gate(envelope),b'different model',b'protocol')


def test_wrong_key_rejected(bundle):
    envelope,key=M.seal(*bundle)
    with pytest.raises(InvalidTag):M.open_sealed(envelope,b'0'*32,gate(envelope),b'model',b'protocol')


def test_ciphertext_tamper_rejected_even_with_rehashed_gate(bundle):
    envelope,key=M.seal(*bundle);obj=json.loads(envelope)
    ciphertext=bytearray(base64.b64decode(obj['ciphertext']));ciphertext[0]^=1
    obj['ciphertext']=M.b64(ciphertext);changed=M.encoded(obj)
    with pytest.raises(InvalidTag):M.open_sealed(changed,key,gate(changed),b'model',b'protocol')


def test_fresh_key_and_nonce_each_seal(bundle):
    a,ka=M.seal(*bundle);b,kb=M.seal(*bundle)
    assert ka!=kb and json.loads(a)['nonce']!=json.loads(b)['nonce']


def test_wrong_partition_refused_before_return_access(bundle):
    raw,kit=bundle;value=json.loads(kit);value['expansion_partition']='development'
    with pytest.raises(ValueError,match='validation-only'):M.seal(raw,M.encoded(value))


def test_create_once_private_output(tmp_path):
    path=tmp_path/'key';M.write_private_once(path,b'fixture key')
    assert path.stat().st_mode&0o777==0o600
    with pytest.raises(FileExistsError):M.write_private_once(path,b'replacement')
