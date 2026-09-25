from types import SimpleNamespace
from pathlib import Path
import pytest
from joint_score_wave_s_driver import use_primed_tf, preflight_child_command, remaining


def test_reuses_exact_prearm_buffer_and_detaches_unused_listener():
    detached=[]
    old=SimpleNamespace(unregister=lambda:detached.append(True))
    recorder=SimpleNamespace(tf_buffer='empty-new-buffer',tf_listener=old)
    buffer=object(); listener=object()
    use_primed_tf(recorder,buffer,listener)
    assert recorder.tf_buffer is buffer and recorder.tf_listener is listener
    assert detached==[True]


def test_each_preflight_is_a_fresh_process_command(tmp_path):
    cmd=preflight_child_command(tmp_path/'config.json',tmp_path/'view',2)
    assert cmd[2]=='preflight-one' and cmd[-2:]==['--view','2']
    assert Path(cmd[1]).name=='joint_score_wave_s_driver.py'
    assert str((tmp_path/'config.json').resolve()) in cmd


def test_closed_attempt_cannot_gain_more_startup_budget():
    attempt=SimpleNamespace(closed=True,advance=lambda now:None)
    with pytest.raises(TimeoutError):remaining(attempt)
