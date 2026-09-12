from language_nav.live_resources import research2_execution_pids


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
