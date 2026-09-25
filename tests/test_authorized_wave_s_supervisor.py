import json
import pytest
from run_authorized_wave_s import capture_command, validate_closed


def test_command_uses_bound_driver_and_exact_identity():
    command = capture_command('synthetic-slot')
    assert command[command.index('--attempt-id')+1] == 'synthetic-slot'
    assert 'attempt' in command
    assert '--execution-manifest' in command and '--execution-approval' in command
    assert 'preflight' not in command


@pytest.mark.parametrize('status', ['captured', 'infrastructure_failure'])
def test_retains_both_closed_outcomes(tmp_path, status):
    (tmp_path/'summary.json').write_text(json.dumps(dict(attempt_id='synthetic',consumed=True,status=status)))
    (tmp_path/'execution.json').write_text(json.dumps(dict(owned_launches_exited=True,cleanup=dict(forced_kill_count=0))))
    assert validate_closed(tmp_path,'synthetic')['status'] == status
    with pytest.raises(ValueError): validate_closed(tmp_path,'wrong')


def test_unclean_cleanup_blocks_next_attempt(tmp_path):
    (tmp_path/'summary.json').write_text(json.dumps(dict(attempt_id='synthetic',consumed=True,status='captured')))
    (tmp_path/'execution.json').write_text(json.dumps(dict(owned_launches_exited=False,cleanup=dict(forced_kill_count=0))))
    with pytest.raises(RuntimeError): validate_closed(tmp_path,'synthetic')
