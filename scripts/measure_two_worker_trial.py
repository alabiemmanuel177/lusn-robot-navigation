"""Measure host resources around the fixed, guarded two-worker trial."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'reports/two_worker_capture_trial_20260921_v1'


def cpu():
    values = [int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    return sum(values), values[3] + values[4]


def sample(previous):
    current = cpu()
    total = current[0] - previous[0]
    memory = dict((line.split(':')[0], int(line.split()[1]))
                  for line in Path('/proc/meminfo').read_text().splitlines())
    device = Path('/sys/class/drm/card0/device')
    power = next((device / 'hwmon').glob('hwmon*/power1_average'))
    row = dict(time=time.time(), cpu_busy_percent=100 * (1 - (current[1] - previous[1]) / total) if total else 0,
               gpu_busy_percent=int((device / 'gpu_busy_percent').read_text()),
               gpu_power_w=int(power.read_text()) / 1e6,
               vram_used_bytes=int((device / 'mem_info_vram_used').read_text()),
               memory_available_gib=memory['MemAvailable'] / 1024**2,
               load1=os.getloadavg()[0])
    return current, row


if __name__ == '__main__':
    # Create-once telemetry: never silently overwrite a prior attempt.
    with (OUTPUT / 'resource_samples.jsonl').open('x') as output:
        previous = cpu()
        time.sleep(1)
        previous, baseline = sample(previous)
        output.write(json.dumps(dict(baseline, phase='baseline')) + '\n'); output.flush()
        print(json.dumps(dict(baseline, phase='baseline')), flush=True)
        process = subprocess.Popen(['python3', str(ROOT / 'scripts/test_two_worker_capture.py'), '--execute'], cwd=ROOT)
        while process.poll() is None:
            time.sleep(1)
            previous, row = sample(previous)
            output.write(json.dumps(dict(row, phase='trial')) + '\n'); output.flush()
        print(json.dumps(dict(trial_exit_code=process.returncode)), flush=True)
        raise SystemExit(process.returncode)
