from language_nav.live_resources import research2_execution_pids
import pytest


@pytest.mark.parametrize('pressure,memory,load,allowed', [
    (1., 24 * 1024**2, 3., True), (21., 24 * 1024**2, 3., False),
    (1., 7 * 1024**2, 3., False), (1., 24 * 1024**2, 20., False)])
def test_coexistence_limits(tmp_path, monkeypatch, pressure, memory, load, allowed):
    from language_nav import live_resources
    (tmp_path / 'pressure').mkdir()
    (tmp_path / 'pressure/cpu').write_text(f'some avg10={pressure} avg60=0 avg300=0 total=1\n')
    (tmp_path / 'meminfo').write_text(f'MemAvailable: {memory} kB\n')
    monkeypatch.setattr(live_resources.os, 'getloadavg', lambda: (load, load, load))
    monkeypatch.setattr(live_resources.os, 'cpu_count', lambda: 24)
    if allowed:
        assert live_resources.coexistence_headroom(tmp_path)['cpu_pressure_avg10'] == pressure
    else:
        with pytest.raises(RuntimeError, match='resource limit'):
            live_resources.coexistence_headroom(tmp_path)


def test_only_scoped_experiment_drivers_block(tmp_path):
    for pid, command in enumerate((
        '/usr/bin/python3\0/home/eao/failure-prediction/scripts/run_campaign_parallel.py\0',
        'python\0/home/eao/failure-prediction/scripts/manual_audit_app.py\0',
        'python\0/tmp/run_campaign_parallel.py\0',
        'python\0/home/eao/failure-prediction/scripts/run_recovery_plan.py\0',
    ), 10):
        directory = tmp_path / str(pid)
        directory.mkdir()
        (directory / 'cmdline').write_bytes(command.encode())
    (tmp_path / '99').mkdir()  # Simulate an exiting process.
    assert research2_execution_pids(tmp_path) == [10, 13]
