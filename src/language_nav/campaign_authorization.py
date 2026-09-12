"""Non-protected campaign admission, distinct from engineering camera freezes."""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import math
import os
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parents[2]
OPTIONS={'world','variant_id','run_id','ros_domain_id','simulation_seed','timeout',
         'system_id','calibration','camera_profile','camera_horizontal_fov',
         'campaign_authorization','campaign_manifest','campaign_episode_id'}
PATH_OPTIONS={'world','calibration','camera_profile','campaign_authorization','campaign_manifest'}
NUMERIC_OPTIONS={'ros_domain_id','simulation_seed','timeout','camera_horizontal_fov'}


def owned_physical_process(args, root=ROOT):
    """Exact R3 executable/launch identities, never a broad R2 substring match."""
    owned={str(Path(root)/'scripts'/name) for name in ('run_physical_episode.py',
        'run_approved_physical_episode.py', 'run_authorized_heldout_episode.py',
        'run_live_episode.py', 'validate_physical_navigation.py', 'validate_live_collision.py')}
    if owned.intersection(args):
        return True
    launches={'physical_sim.launch.py','live_adapters.launch.py','heldout_adapters.launch.py'}
    return any(Path(arg).name=='ros2' and args[i+1:i+3]==['launch','language_nav_bringup']
               and len(args)>i+3 and args[i+3] in launches for i,arg in enumerate(args))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def approved_jobs(manifest,approval,root):
    # prepare validates frozen human approval, design, calibration, all execution
    # gates and exact source/scene/profile tuples; it never calls this wrapper.
    prepare=runpy.run_path(str(ROOT/'scripts/run_physical_campaign.py'))['prepare']
    return prepare(manifest,approval,root)


def validate_campaign_episode(supplied,*,root=ROOT):
    """Return binding only when every runtime option equals one approved job."""
    root=Path(root).resolve()
    if not set(supplied)<=OPTIONS or any(not supplied.get(key) for key in
            ('campaign_authorization','campaign_manifest','campaign_episode_id')):
        raise ValueError('explicit campaign approval, manifest and episode identity required')
    manifest_path=Path(supplied['campaign_manifest']).resolve()
    approval_path=Path(supplied['campaign_authorization']).resolve()
    manifest,jobs=approved_jobs(manifest_path,approval_path,root)
    selected=[job for job in jobs if job['episode_id']==supplied['campaign_episode_id']]
    rows=[row for row in manifest['episodes'] if row['episode_id']==supplied['campaign_episode_id']]
    if len(selected)!=1 or len(rows)!=1 or rows[0]['partition'] not in {'development','validation'}:
        raise ValueError('unique non-protected approved episode required')
    job=selected[0]
    argv=job['argv']
    wrapper=str(root/'scripts/run_approved_physical_episode.py')
    if argv.count(wrapper)!=1:
        raise ValueError('approved job must use the owned campaign wrapper')
    tail=argv[argv.index(wrapper)+1:]
    if len(tail)%2:
        raise ValueError('approved job options must be explicit value pairs')
    expected={}
    for flag,value in zip(tail[::2],tail[1::2],strict=True):
        key=flag.removeprefix('--').replace('-','_')
        if not flag.startswith('--') or key not in OPTIONS or key in expected:
            raise ValueError('unsupported or duplicate approved runtime option')
        expected[key]=value
    actual={key:value for key,value in supplied.items() if value is not None}
    if set(actual)!=set(expected):
        raise ValueError('supplied runtime fields differ from approved episode')
    for key,value in expected.items():
        if key in PATH_OPTIONS:
            equal=Path(actual[key]).resolve()==Path(value).resolve()
        elif key in NUMERIC_OPTIONS:
            try:
                equal=type(actual[key]) is not bool and math.isfinite(float(actual[key])) and float(actual[key])==float(value)
            except (ValueError,TypeError):
                equal=False
        else:
            equal=actual[key]==value
        if not equal:
            raise ValueError('runtime option differs from approved episode: '+key)
    if 'camera_horizontal_fov' in actual and not .5<=float(actual['camera_horizontal_fov'])<=2.:
        raise ValueError('approved camera FOV must preserve tested0.5..2.0 range')
    return {'schema_version':'research3-approved-episode-binding/v1',
        'authorization_scope':'nonprotected_campaign','episode_id':job['episode_id'],
        'run_id':job['run_id'],'partition':rows[0]['partition'],
        'approval_path':str(approval_path),'approval_sha256':sha(approval_path),
        'manifest_path':str(manifest_path),'manifest_sha256':sha(manifest_path),
        'protected_data_used':False}


@contextmanager
def exclusive_campaign_runtime(root=ROOT,proc_root=Path('/proc')):
    """The actual wrapper owns the shared lock for its complete runtime lifetime."""
    root=Path(root)
    fd=os.open(root/'reports/.research3_physical_execution.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('another Research3 execution owner or surviving child holds the lock') from exc
        for entry in Path(proc_root).iterdir():
            if not entry.name.isdigit() or int(entry.name)==os.getpid():
                continue
            try:
                args=(entry/'cmdline').read_bytes().decode(errors='replace').split('\0')
            except FileNotFoundError:
                continue
            if owned_physical_process(args, root):
                raise RuntimeError('another owned Research3 live runner exists; campaign dispatch refused')
        yield
    finally:
        os.close(fd)
