"""Reproduce and test a resource-guard proposal in memory; never edits frozen code."""
import hashlib
import json
from pathlib import Path
import run_stage1_feasibility as base

SOURCE = base.ROOT / 'src/language_nav/live_resources.py'


class Entry:
    name = '123'
    def __init__(self, error=None, payload=b'ordinary-process\0'):
        self.error, self.payload = error, payload
    def __truediv__(self, part):return self
    def read_bytes(self):
        if self.error:raise self.error
        return self.payload


class Proc:
    def __init__(self, *entries):self.entries = entries
    def iterdir(self):return iter(self.entries)


def probe():
    actual = SOURCE.read_text()
    old = 'except FileNotFoundError:  # A process exiting during inspection is normal.'
    new = 'except (FileNotFoundError, ProcessLookupError):  # A process exiting during inspection is normal.'
    raw = actual.replace(new,old)
    if raw.count(old) != 1:raise ValueError('unexpected guard source')
    proposed = raw.replace(old,new)
    original, candidate = {}, {}
    exec(compile(raw,str(SOURCE),'exec'),original)
    exec(compile(proposed,'unapplied-resource-guard-proposal','exec'),candidate)
    # Inject a deterministic /proc race without changing pathlib globally.
    original['Path'] = candidate['Path'] = lambda value: value if isinstance(value,Proc) else Path(value)
    try:
        original['research2_execution_pids'](Proc(Entry(ProcessLookupError(3,'No such process'))))
    except ProcessLookupError:
        reproduced = True
    else:raise AssertionError('original defect not reproduced')
    for error in (FileNotFoundError(), ProcessLookupError(3,'No such process')):
        assert candidate['research2_execution_pids'](Proc(Entry(error))) == []
    try:
        candidate['research2_execution_pids'](Proc(Entry(PermissionError())))
    except RuntimeError:
        permission_fail_closed = True
    else:raise AssertionError('permission guard weakened')
    driver = b'/home/eao/failure-prediction/scripts/run_campaign_parallel.py\0'
    assert candidate['research2_execution_pids'](Proc(Entry(payload=driver))) == [123]
    assert SOURCE.read_text() == actual
    return dict(original_race_reproduced=reproduced, candidate_handles_vanished_process=True,
        permission_fail_closed=permission_fail_closed, active_research2_detection_preserved=True,
        frozen_source_unchanged=True, patch_applied=False, live_verification=False,
        source_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        proposed_source_sha256=hashlib.sha256(proposed.encode()).hexdigest())


if __name__ == '__main__':
    result = probe()
    base.write(base.ROOT / 'reports/resource_guard_race_proposal_20260922.json',result)
    print(json.dumps(result))
