import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('offline_package', ROOT / 'scripts/package_offline_implementation.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_snapshot_refuses_recursive_destination_before_writes():
    with pytest.raises(ValueError, match='inside an input tree'):
        module.package(ROOT / 'src/never-created-snapshot')
    assert not (ROOT / 'src/never-created-snapshot').exists()


def test_snapshot_requires_complete_inputs_before_output(tmp_path):
    with pytest.raises(ValueError, match='missing snapshot input'):
        module.package(tmp_path / 'output', root=tmp_path)
    assert not (tmp_path / 'output').exists()
