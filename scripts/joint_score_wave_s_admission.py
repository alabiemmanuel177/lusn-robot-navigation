"""Primary-attempt admission boundary; caller owns simulator and ROS lifecycle.

This module does NOT launch a campaign. Use the context before simulator startup
so the persisted 90-second budget includes startup. A dedicated low-priority
process is required; every started attempt is consumed, including interruption.
"""
from contextlib import contextmanager
import fcntl
import json
import os
import time
from pathlib import Path

from fit_joint_score_wave_s import protocol_acceptance, validate_execution, sha
from prepare_joint_score_protocol import ROOT, SOURCE, validate_schedule
from joint_score_collection import OneFrameAttempt
from joint_score_components import digest
from language_nav.live_resources import coexistence_headroom


@contextmanager
def admitted_attempt(*, attempt_id, output_root, schedule_path, protocol_path,
                     protocol_review_path, execution_manifest_path, execution_approval_path):
    def read(path):
        return json.loads(Path(path).read_text())
    schedule = read(schedule_path)
    validate_schedule(schedule, read(ROOT/SOURCE))
    ps, ss = sha(protocol_path), sha(schedule_path)
    protocol_acceptance(read(protocol_review_path), ps, ss)
    manifest = read(execution_manifest_path)
    validate_execution(manifest, read(execution_approval_path), protocol_sha=ps, schedule_sha=ss)
    slots = [r for r in schedule['rows'] if r['wave'] == 'S']
    matches = [r for r in slots if r['attempt_id'] == attempt_id]
    if len(matches) != 1:
        raise PermissionError('only a scheduled Wave S attempt may be admitted')
    if os.getpriority(os.PRIO_PROCESS, 0) < 19:
        raise PermissionError('run in a dedicated nice-19 process; priority not changed implicitly')
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    # Shared across all output roots, not just this particular campaign directory.
    with (ROOT/'reports/.joint_score_collection.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            index = slots.index(matches[0])
            for earlier in slots[:index]:
                summary_path = root/earlier['attempt_id']/'summary.json'
                if not summary_path.is_file():
                    raise ValueError('earlier scheduled attempt not closed; no reordering')
                summary = read(summary_path)
                if summary.get('attempt_id') != earlier['attempt_id'] or summary.get('consumed') is not True:
                    raise ValueError('earlier accounting invalid')
            if any((root/later['attempt_id']).exists() for later in slots[index:]):
                raise ValueError('attempt already started or later attempt exists; no retries')
            sample = coexistence_headroom()
            attempt = OneFrameAttempt(root/attempt_id, attempt_id, time.monotonic())
            attempt.event('admission', time.monotonic(), resource_sample=sample,
                          execution_manifest_sha256=digest(manifest),
                          execution_approval_sha256=sha(execution_approval_path))
            try:
                yield attempt, matches[0]
            finally:
                if not attempt.closed:
                    attempt.interrupt(time.monotonic())
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
