import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

SPEC=importlib.util.spec_from_file_location('human_return',Path(__file__).resolve().parents[1]/'scripts/return_human_decisions.py')
M=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)


@pytest.fixture
def packet(tmp_path):
    raw=b'PENDING\n'
    (tmp_path/'response.template.md').write_bytes(raw)
    (tmp_path/'YOUR_RESPONSE.md').write_bytes(raw)
    (tmp_path/'manifest.json').write_text(json.dumps({
        'schema_version':'research3-human-action-packet/v1',
        'files':{'response.template.md':M.sha(raw)}}))
    return tmp_path


def test_unedited_response_refused(packet):
    with pytest.raises(ValueError,match='unchanged'):M.package(packet,packet/'return.zip')


def test_partial_response_never_grants_authority(packet):
    (packet/'YOUR_RESPONSE.md').write_text('Synthetic fixture: DEFER all decisions')
    result=M.package(packet,packet/'return.zip')
    assert result['execution_authorized'] is False
    assert result['scientific_content_validated'] is False
    with zipfile.ZipFile(packet/'return.zip') as z:
        assert len(z.namelist())==3
    with pytest.raises(FileExistsError):M.package(packet,packet/'return.zip')


def test_modified_fixed_input_refused(packet):
    (packet/'response.template.md').write_text('tampered')
    with pytest.raises(ValueError,match='changed'):M.package(packet,packet/'return.zip')
