"""Serial supervisor for the existing authorized Wave S driver, no retries.

Starts the fixed schedule once, then the existing offline inference pipeline.
Never fits models, fabricates reviews, or advances to Wave C/V.
"""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from prepare_joint_score_protocol import ROOT, sha
from joint_score_collection import write_once
from fit_joint_score_wave_s import validate_execution
from language_nav.live_resources import coexistence_headroom

CAPTURE = ROOT/'reports/joint_score_wave_s_primary_20260924_v1'
CONTROL = ROOT/'reports/joint_score_wave_s_supervisor_20260924_v1'
INFERENCE = ROOT/'reports/joint_score_wave_s_primary_inference_20260924_v1'
CONFIG = ROOT/'reports/joint_score_wave_s_assets_20260924_v3/driver_config.json'
MANIFEST = ROOT/'reports/joint_score_wave_s_execution_20260924_v1/execution_manifest.json'
APPROVAL = MANIFEST.parent/'execution_approval.json'


def read(path):
    return json.loads(path.read_text())


def capture_command(attempt_id):
    return [sys.executable, str(ROOT/'scripts/joint_score_wave_s_driver.py'), 'attempt',
            '--config', str(CONFIG), '--execution-manifest', str(MANIFEST),
            '--execution-approval', str(APPROVAL), '--output', str(CAPTURE),
            '--attempt-id', attempt_id]


def validate_closed(folder, attempt_id):
    summary, execution = read(folder/'summary.json'), read(folder/'execution.json')
    if summary['attempt_id'] != attempt_id or summary['consumed'] is not True:
        raise ValueError('closed attempt identity/accounting failed')
    if summary['status'] not in ('captured', 'infrastructure_failure'):
        raise ValueError('unexpected capture status')
    if not execution['owned_launches_exited'] or execution['cleanup']['forced_kill_count']:
        raise RuntimeError('unclean lifecycle; operator diagnosis required, no retry')
    return summary


def main():
    os.chdir(ROOT); os.nice(19)
    manifest = read(MANIFEST)
    validate_execution(manifest, read(APPROVAL),
        protocol_sha=sha(ROOT/'docs/SCORE_LEARNING_COLLECTION_PROTOCOL_20260924.md'),
        schedule_sha=sha(ROOT/'reports/joint_score_protocol_20260924_v1/schedule.json'))
    slots = [r for r in read(ROOT/'reports/joint_score_protocol_20260924_v1/schedule.json')['rows'] if r['wave']=='S']
    if len(slots) != 400 or any(r['partition'] != 'development' for r in slots):
        raise ValueError('exact development S schedule required')
    with (ROOT/'reports/.wave_s_supervisor.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if CAPTURE.exists() or INFERENCE.exists():
            raise FileExistsError('primary output already exists; never automatically retry or restart')
        CONTROL.mkdir(exist_ok=False)
        source_hash = sha(__file__)
        write_once(CONTROL/'launch.json', dict(pid=os.getpid(), started_at=time.time(),
            supervisor_sha256=source_hash, execution_manifest_file_sha256=sha(MANIFEST),
            execution_approval_file_sha256=sha(APPROVAL), capture_workers=1,
            detector_cpu_threads=4, ocr_cpu_threads=1, attempts=400,
            user_instruction='Proceed and use as much workers as resources permit, no more stalling go ahead please',
            constraint='Accepted protocol and bound execution manifest require serial collection.'))
        try:
            for i, slot in enumerate(slots):
                if sha(__file__) != source_hash: raise ValueError('supervisor source changed')
                coexistence_headroom()
                attempt_id = slot['attempt_id']
                with (CONTROL/f'capture-{i:03}.log').open('x') as log:
                    subprocess.run(capture_command(attempt_id), stdout=log, stderr=subprocess.STDOUT, check=True)
                summary = validate_closed(CAPTURE/attempt_id, attempt_id)
                write_once(CONTROL/f'closed-{i:03}.json', dict(index=i, attempt_id=attempt_id,
                    status=summary['status'], summary_sha256=sha(CAPTURE/attempt_id/'summary.json'),
                    completed_at=time.time()))
                print(f'{i+1}/400 {attempt_id} {summary["status"]}', flush=True)
            engine = str(ROOT/'scripts/joint_score_wave_s_inference.py')
            stages = [
                ('prepare', sys.executable, ['--capture-root',str(CAPTURE),'--config',str(CONFIG)]),
                ('detector', str(ROOT/'.venv_object_probe/bin/python'), []),
                ('ocr', str(ROOT/'.venv_ocr_probe/bin/python'), []),
                ('export', sys.executable, []),
            ]
            for action, python, extra in stages:
                coexistence_headroom()
                with (CONTROL/f'{action}.log').open('x') as log:
                    subprocess.run([python,engine,action,'--output',str(INFERENCE),*extra],
                                   stdout=log,stderr=subprocess.STDOUT,check=True)
                print('inference '+action+' completed',flush=True)
            write_once(CONTROL/'complete.json', dict(completed_at=time.time(), attempts=400,
                evidence_sha256=sha(INFERENCE/'evidence.json'), next_gate='Wave S human observation review',
                model_fitted=False, wave_c_or_v_started=False))
        except BaseException as exc:
            write_once(CONTROL/'blocked.json', dict(recorded_at=time.time(), reason=repr(exc),
                instruction='Preserve all attempts; no automatic retries, replacements or protocol changes.'))
            raise


if __name__ == '__main__': main()
