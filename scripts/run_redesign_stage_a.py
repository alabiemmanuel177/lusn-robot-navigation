"""Explicit, hash-bound Stage A lighting adapter; never a primary collector."""
import argparse
import json
from pathlib import Path
import sys
from run_stage1_feasibility import ROOT, sha
from prepare_calibration_redesign import lighting_variant

PLAN = ROOT/'reports/calibration_redesign_20260923_v1/plan.json'
EXPECTED = '960b6251e526a5d17e200b8716f05c7c9ad1c8f0c75b000fdbb6b23f7d1212bc'
APPROVAL = ROOT/'reports/redesign_stage_a_approval_20260923.json'
OUTPUT = ROOT/'reports/redesign_stage_a_20260923_v1'
SNAPSHOT = ROOT/'reports/expansion_instrumentation_snapshot_20260922_v8/snapshot.json'


def assignments():
    if sha(PLAN) != EXPECTED:
        raise ValueError('approved plan changed')
    approval = json.loads(APPROVAL.read_bytes())
    if (approval.get('stage') != 'A' or approval.get('authorized') is not True
            or approval.get('plan_sha256') != EXPECTED or approval.get('attempts') != 144
            or approval.get('primary_collection_authorized') is not False
            or approval.get('protected_access_authorized') is not False):
        raise PermissionError('exact Stage A approval required')
    for name, digest in approval['input_sha256'].items():
        if sha(ROOT/name) != digest:
            raise ValueError('approved protocol changed')
    plan = json.loads(PLAN.read_bytes())
    rows = plan['panels']['design_feasibility']
    if len(rows) != 144 or len({r['candidate_id'] for r in rows}) != 144:
        raise ValueError('fixed schedule')
    for row in rows:
        if (row['partition'] != 'development' or row['map_id'] not in ('r3geo_base_r001','r3geo_base_r006')
                or row['simulator_seed'] != 7 or row['calibration_eligible'] is not False):
            raise ValueError('Stage A scope')
    return rows


def validate_row(row):
    if row not in assignments():
        raise ValueError('unapproved assignment')
    plan = json.loads(PLAN.read_bytes())
    world = ROOT/row['world_directory']
    for name, digest in plan['source_sha256'].items():
        if name.startswith(row['world_directory']+'/') and sha(ROOT/name) != digest:
            raise ValueError('source asset changed')
    derivative = ROOT/row['derivative_world_path']
    if derivative.read_bytes() != lighting_variant((world/'world.sdf').read_bytes(),row['lighting_scale']):
        raise ValueError('lighting-only invariant failed')
    if sha(ROOT/row['camera_profile']) != row['camera_profile_sha256']:
        raise ValueError('profile changed')


def validate_pins():
    pins = json.loads((OUTPUT/'source_binding.json').read_bytes())
    for name, digest in pins['input_sha256'].items():
        if sha(ROOT/name) != digest:
            raise ValueError('Stage A executed source/input changed: '+name)


def runner_args(row, domain):
    if domain not in (100,101):
        raise ValueError('isolated Stage A domain required')
    world = ROOT/row['world_directory']
    return ['--world',str(world),'--variant-id',world.name+'-truthful_original-s0',
        '--run-id',row['candidate_id'],'--ros-domain-id',str(domain),'--simulation-seed','7',
        '--timeout','90','--capture-only','--capture-frame-budget','1',
        '--capture-pose',*[str(row['capture_pose'][k]) for k in ('x','y','yaw')],
        '--capture-target-category',row['category'],'--capture-entity-id',row['entity_id'],
        '--camera-profile',str(ROOT/row['camera_profile']),'--camera-horizontal-fov','2.0',
        '--expansion-instrumentation-snapshot',str(SNAPSHOT)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-id',required=True)
    parser.add_argument('--domain',type=int,choices=(100,101),required=True)
    parser.add_argument('--prepare-only',action='store_true')
    args = parser.parse_args()
    row = next(r for r in assignments() if r['candidate_id'] == args.candidate_id)
    validate_row(row); validate_pins()
    import run_physical_episode as runner
    original_command, original_execute, original_argv = runner.physical_simulation_command, runner.execute, sys.argv
    def simulation_command(request, start):
        validate_row(row); validate_pins()
        # Existing generic world-path transport; NOT diagnostic sphere admission.
        request['diagnostic_world_sdf'] = str(ROOT/row['derivative_world_path'])
        request['lighting_redesign'] = dict(stage='A',plan_sha256=EXPECTED,
            approval_sha256=sha(APPROVAL),source_binding_sha256=sha(OUTPUT/'source_binding.json'),
            world_sha256=sha(ROOT/row['derivative_world_path']),calibration_eligible=False)
        return original_command(request,start)
    def execute(request, variant, catalog, report_dir, system_id, calibration=None):
        validate_pins(); validate_row(row)
        if calibration is not None or not request.get('capture_only') or request['partition'] != 'development':
            raise PermissionError('stationary uncalibrated development only')
        return original_execute(request,variant,catalog,report_dir,system_id,calibration)
    try:
        runner.physical_simulation_command = simulation_command
        runner.execute = execute
        sys.argv = [str(Path(runner.__file__))]+runner_args(row,args.domain)+(['--prepare-only'] if args.prepare_only else [])
        runner.main()
    finally:
        runner.physical_simulation_command, runner.execute, sys.argv = original_command, original_execute, original_argv


if __name__ == '__main__':
    main()
