import hashlib
import json
from pathlib import Path
import sys
import zipfile
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verify_stage1_bundle import verify,safe_name


def make_bundle(path,raw=b'evidence',digest=None):
    manifest=dict(schema_version='research3-engineering-evidence-bundle/v1',scientific_release_complete=False,
        calibration_eligible=False,files=[dict(path='evidence.json',bytes=len(raw),sha256=digest or hashlib.sha256(raw).hexdigest())])
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr('evidence.json',raw)
        archive.writestr('bundle_manifest.json',json.dumps(manifest))


def test_verified_without_extracting_or_claiming_scientific_completion(tmp_path):
    path=tmp_path/'bundle.zip';make_bundle(path)
    result=verify(path,hashlib.sha256(path.read_bytes()).hexdigest())
    assert result['integrity_passed'] and not result['scientific_release_complete']
    assert list(tmp_path.iterdir())==[path]


def test_tampered_payload_or_outer_digest_rejected(tmp_path):
    path=tmp_path/'bundle.zip';make_bundle(path,digest='0'*64)
    with pytest.raises(ValueError,match='member checksum'):verify(path)
    with pytest.raises(ValueError,match='archive SHA'):verify(path,'0'*64)


@pytest.mark.parametrize('name',['../escape','/absolute','a//b','a/./b','a\\b',''])
def test_noncanonical_paths_rejected(name):assert not safe_name(name)
