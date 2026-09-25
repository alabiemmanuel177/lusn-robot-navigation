import importlib.util
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('two_worker_trial', SCRIPTS / 'test_two_worker_capture.py')
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)


def test_pair_preserves_scope_and_separates_domains():
    rows = trial.commands()
    assert len(rows) == 2
    assert len({r['run_id'] for r in rows}) == 2
    assert {r['argv'][r['argv'].index('--ros-domain-id') + 1] for r in rows} == {'90', '91'}
    for row in rows:
        assert '--capture-only' in row['argv']
        assert '--allow-coexistence-trial' not in row['argv']
        assert '--calibration' not in row['argv']
        assert row['run_id'].startswith('r3-parallel-engineering-')


def test_shared_transport_or_protected_partition_refused():
    pair = [dict(run_id=str(i), ros_domain_id=i, worker_id=str(i), partition='development',
                 protected_test_routes_used=False) for i in range(2)]
    trial.validate_pair(pair)
    for key in ('run_id', 'ros_domain_id', 'worker_id'):
        bad = [dict(r) for r in pair]
        bad[1][key] = bad[0][key]
        with pytest.raises(ValueError, match='workers share'):
            trial.validate_pair(bad)
    pair[1]['partition'] = 'validation'
    with pytest.raises(ValueError, match='development only'):
        trial.validate_pair(pair)
