"""Read-only preflight for known Research 2 experiment drivers.

This is a conservative launch guard, not a host-wide scheduler or reservation.
Run on the host: a container with a private /proc cannot establish host idleness.
"""
from pathlib import Path


def research2_execution_pids(proc_root=Path('/proc'), root=Path('/home/eao/failure-prediction')):
    drivers = {str(root / 'scripts' / name) for name in (
        'run_campaign_parallel.py', 'run_research2_episode.py', 'run_recovery_plan.py')}
    found = []
    for entry in Path(proc_root).iterdir():
        if not entry.name.isdigit():
            continue
        try:
            args = (entry / 'cmdline').read_bytes().decode(errors='replace').split('\0')
        except FileNotFoundError:  # A process exiting during inspection is normal.
            continue
        except PermissionError as exc:
            raise RuntimeError('cannot establish Research 2 idleness: process visibility denied') from exc
        if drivers.intersection(args):
            found.append(int(entry.name))
    return sorted(found)


def require_research2_idle():
    active = research2_execution_pids()
    if active:
        raise RuntimeError(f'Research 2 experiment drivers active (PIDs {active}); no Research 3 simulator authorized')
