"""Read-only development-world checks and create-once source-bound driver config."""
import argparse
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import yaml

from prepare_joint_score_protocol import ROOT, sha, validate_schedule, SOURCE
from joint_score_collection import write_once
from run_four_class_deferred_capture import mounts
from language_nav.capture_view import validate_capture_pose


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    schedule_path = ROOT/'reports/joint_score_protocol_20260924_v1/schedule.json'
    schedule = json.loads(schedule_path.read_text())
    validate_schedule(schedule, json.loads((ROOT/SOURCE).read_text()))
    readiness_path = ROOT/'reports/four_class_perception_readiness_20260924_v1/manifest.json'
    readiness = json.loads(readiness_path.read_text())
    for path, h in readiness['input_sha256'].items():
        if sha(ROOT/path) != h:
            raise ValueError('readiness source changed: '+path)
    auth_path = ROOT/'reports/joint_score_wave_s_authorization_20260924.json'
    auth = json.loads(auth_path.read_text())
    if auth['schedule_sha256'] != sha(schedule_path) or auth['protocol_sha256'] != sha(ROOT/'docs/SCORE_LEARNING_COLLECTION_PROTOCOL_20260924.md'):
        raise ValueError('authorization binds another protocol')
    if auth.get('agent_may_bind_exact_manifest_after_preflight') is not True:
        raise PermissionError('prospective preflight authority missing')
    root = args.output.resolve(); root.mkdir(parents=True, exist_ok=False)
    pins = {}; groups = dict(worlds=[], scenes=[], maps=[], expanded_robot=[], camera_bridge=[],
        detector_ocr_assets=[], environment=[], collection_scoring_sources=[])
    def pin(path, group):
        path = Path(path).resolve(); pins[str(path)] = sha(path)
        if str(path) not in groups[group]: groups[group].append(str(path))
    clearance = []
    for slot in schedule['rows']:
        if slot['wave'] != 'S': continue
        world = ROOT/slot['world_directory']
        spec = yaml.safe_load((world/'map.yaml').read_text())
        if spec['resolution'] != .05 or spec['origin'] != [-1.0, -5.0, 0.0]:
            raise ValueError('occupancy checker requires the pinned map coordinates')
        pose = validate_capture_pose(world, **slot['capture_pose'])
        clearance.append(dict(attempt_id=slot['attempt_id'], capture_pose=pose, clearance_passed=True))
        for name, group in [('world.sdf','worlds'), ('landmark_scene.yaml','scenes'), ('map.yaml','maps'), ('map.pgm','maps')]:
            pin(world/name, group)
    write_once(root/'static_clearance_audit.json', dict(rows=clearance, passed=len(clearance)==400,
        required_attempts=400, checked_attempts=len(clearance), footprint_radius_m=.30,
        source_sha256={k: h for k, h in pins.items()}, protected_or_validation_world_read=False))
    previous = ROOT/'reports/four_class_deferred_capture_20260924_v1/view-00-chair'
    assets = {}
    for name in ('robot.sdf', 'robot.urdf', 'bridge.yaml'):
        path = root/name
        with path.open('xb') as stream: stream.write((previous/name).read_bytes())
        assets[name] = str(path)
        pin(path, 'camera_bridge' if name == 'bridge.yaml' else 'expanded_robot')
    robot = ET.fromstring((root/'robot.sdf').read_text())
    fovs = robot.findall('.//sensor/camera/horizontal_fov')
    if len(fovs) != 2 or any(float(x.text) != 2. for x in fovs):
        raise ValueError('unchanged two-camera FOV required')
    nominal, rendered = mounts((root/'robot.sdf').read_text(), (root/'robot.urdf').read_text())
    detector_assets = ROOT/'reports/grounding_candidate_assets_20260923_v3.json'
    inventory = json.loads(detector_assets.read_text())
    pin(detector_assets, 'detector_ocr_assets')
    for name, expected in inventory['files'].items():
        path = Path(inventory['model_path'])/name
        if sha(path) != expected: raise ValueError('detector asset changed')
        pin(path, 'detector_ocr_assets')
    ocr_plan = json.loads((ROOT/'reports/four_class_live_ocr_20260924_v1/plan.json').read_text())
    for path, expected in ocr_plan['input_sha256'].items():
        if '.venv_ocr_probe/' in path:
            if sha(path) != expected: raise ValueError('OCR asset changed')
            pin(path, 'detector_ocr_assets')
    environment = {}
    for name, python in [('system','/usr/bin/python3'), ('detector',str(ROOT/'.venv_object_probe/bin/python')),
                         ('ocr',str(ROOT/'.venv_ocr_probe/bin/python'))]:
        command = [python, '-c', 'import sys,importlib.metadata as m,json; print(json.dumps({"python":sys.version,"packages":sorted(((d.metadata.get("Name"),d.version) for d in m.distributions()),key=lambda x:(str(x[0]),str(x[1])))}))']
        environment[name] = json.loads(subprocess.run(command, capture_output=True, text=True, check=True).stdout)
    write_once(root/'environment.json', environment); pin(root/'environment.json', 'environment')
    for path in (ROOT/'scripts').glob('joint_score_*.py'): pin(path,'collection_scoring_sources')
    for name in ('fit_joint_score_wave_s.py','prepare_joint_score_protocol.py','prepare_joint_score_wave_s_driver.py',
        'bound_pose_sim.launch.py','run_live_episode.py','run_four_class_deferred_capture.py',
        'four_class_broad_detector_engine.py','run_entrance_context_candidate.py','run_grounding_candidate.py',
        'four_class_candidate_runtime_v3.py','four_class_perception_candidate.py','four_class_perception_candidate_v3.py',
        'candidate_depth_support.py','candidate_portal_depth.py','candidate_instance_association.py',
        'chair_foreground_band_candidate.py','readable_sign_reference_candidate.py','candidate_rendering_transform.py',
        'integrate_object_depth_candidate.py','expansion_camera_model.py','entrance_context_candidate.py',
        'bound_pose_observer.py','expansion_rendered_checks.py','joint_score_method_candidate.py'):
        pin(ROOT/'scripts'/name, 'collection_scoring_sources')
    for name in ('live_resources.py','capture_view.py'):
        pin(ROOT/'src/language_nav'/name,'collection_scoring_sources')
    r1 = Path('/home/eao/risk-calibrated-nav')
    for name in ('configs/nav2/nav2_common.yaml','configs/systems/s0.yaml',
        'src/experiment_controller/experiment_controller/run_episode.py',
        'src/experiment_controller/experiment_controller/preflight.py',
        'src/episode_logger/episode_logger/monitor.py','src/simulation_worlds/launch/nav2.launch.py'):
        pin(r1/name,'collection_scoring_sources')
    write_once(root/'driver_config.json', dict(schema_version='research3-jsc-driver-config/v1',
        input_sha256=pins, asset_groups=groups, assets=assets, nominal_mount=nominal.tolist(),
        rendered_mount=rendered.tolist(), ros_domain_id=218, static_clearance_audit=str(root/'static_clearance_audit.json'),
        detector_model_path=inventory['model_path'], source_manifest_authorized=False))
    print(json.dumps(dict(poses_checked=len(clearance), source_files_pinned=len(pins), output=str(root)), indent=2))


if __name__ == '__main__': main()
