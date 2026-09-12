"""Synthetic source archives and default refusal fixtures only."""
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import runpy
import tarfile
from types import SimpleNamespace

import pytest

TOOL = runpy.run_path(str(Path(__file__).parents[1] / 'scripts/check_nonprotected_catalog_differential.py'))


def test_canonical_dataclass_is_module_identity_independent():
    @dataclass
    class First:
        value: int
    @dataclass
    class Second:
        value: int
    assert TOOL['canonical'](First(3)) == TOOL['canonical'](Second(3))


def test_synthetic_refusals_require_permission_before_missing_assets():
    def deny(path):
        assert path.is_file()
        assert not (path.parent / 'map.pgm').exists()
        raise PermissionError('synthetic refusal')
    rows = TOOL['default_refusals'](SimpleNamespace(load_physical_runtime_catalog=deny),
                                    SimpleNamespace(load_physical_runtime_catalog=deny))
    assert len(rows) == 3 and all(row['both_refuse_before_asset_access'] for row in rows)


def test_source_member_requires_both_archive_and_member_hash(tmp_path):
    path = tmp_path / 'synthetic.tar.gz'
    source = b'# synthetic code, never executed\n'
    manifest = {'schema_version': 'research3-nonprotected-engineering-bundle/v1',
                'protected_data_included': False, 'files': {TOOL['SOURCE']: {
                    'sha256': hashlib.sha256(source).hexdigest(), 'bytes': len(source)}}}
    with tarfile.open(path, 'w:gz') as archive:
        for name, raw in [('MANIFEST.json', json.dumps(manifest).encode()), (TOOL['SOURCE'], source)]:
            item = tarfile.TarInfo(name)
            item.size = len(raw)
            archive.addfile(item, io.BytesIO(raw))
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert TOOL['archived_source'](path, expected)[0] == source
    with pytest.raises(ValueError, match='archive checksum'):
        TOOL['archived_source'](path, '0' * 64)


def test_ast_ignores_positions_but_exposes_changed_constructors_and_methods():
    before = 'class Node:\n def __init__(self): self.x=1\n def callback(self): return self.x\n'
    after = '\n\nclass Node:\n def __init__(self): self.x=2\n def callback(self): return self.x\n def new(self): pass\n'
    result = TOOL['callback_comparison'](before, after)
    assert result['unchanged_nonconstructor_method_bodies'] == ['Node.callback']
    assert result['changed_constructor_bodies'] == ['Node.__init__']
    assert result['added_methods'] == ['Node.new']
    changed = TOOL['callback_comparison'](before, after.replace('return self.x', 'return 42'))
    assert changed['changed_nonconstructor_method_bodies'] == ['Node.callback']


def test_supplement_cannot_read_unrequested_archive_members(tmp_path):
    with pytest.raises(ValueError, match='not explicitly allowlisted'):
        TOOL['archived_source'](tmp_path / 'not-opened', '0' * 64,
                               'data/physical_worlds_v1/base-r020/execution_catalog.json')
