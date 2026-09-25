"""Read-only external-workload detection, including rewritten Gazebo argv[0]."""
from pathlib import Path
import json
import shlex

ROOT = Path(__file__).resolve().parents[1]


def simulator_command(args):
    for index,arg in enumerate(args):
        if Path(arg).name in {'gz','ign'} and index+1<len(args) and args[index+1]=='sim':
            return True
    # Gazebo can replace argv[0] with its entire display title and blank the
    # remaining argv slots. Never tokenize shell -c arguments as processes.
    if args:
        try: title=shlex.split(args[0])
        except ValueError:return False
        return len(title)>1 and Path(title[0]).name in {'gz','ign'} and title[1]=='sim'
    return False


def inspect(proc=Path('/proc')):
    found=[]
    for entry in proc.iterdir():
        if not entry.name.isdigit():continue
        try:
            args=(entry/'cmdline').read_bytes().decode(errors='replace').split('\0')
            simulation=simulator_command(args)
            campaign_candidate=any(Path(a).name=='run_campaign_worker.py' for a in args if a)
            if not simulation and not campaign_candidate:continue
            cwd=(entry/'cwd').resolve(strict=True)
        except (FileNotFoundError,ProcessLookupError):continue
        except PermissionError as exc:raise RuntimeError('cannot establish host workload visibility') from exc
        external=cwd!=ROOT and ROOT not in cwd.parents
        scra_campaign=(cwd==Path('/home/eao/scra-robot-navigation') and
                       campaign_candidate)
        if external and (simulation or scra_campaign):
            found.append(dict(pid=int(entry.name),cwd=str(cwd),simulator=simulation,campaign_driver=scra_campaign))
    return found


if __name__=='__main__':
    print(json.dumps(inspect(),indent=2))
