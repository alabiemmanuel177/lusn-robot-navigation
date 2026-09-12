#!/usr/bin/env python3
"""Read-only allowlisted environment provenance; no environment-variable dump."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PYTHON_PACKAGES = ('numpy', 'scipy', 'PyYAML', 'pytest')
ROS_PACKAGES = ('rclpy', 'nav2_bringup', 'nav2_controller', 'nav2_planner',
                'ros_gz_sim', 'sensor_msgs', 'geometry_msgs', 'tf2_ros')
SOURCE_FILES = (
    ('R3', 'ros_ws/src/language_interface/language_interface/node.py'),
    ('R3', 'ros_ws/src/semantic_belief_map/semantic_belief_map/node.py'),
    ('R3', 'ros_ws/src/language_nav_bringup/language_nav_bringup/landmark_bridge_runner.py'),
    ('R3', 'scripts/run_physical_episode.py'),
    ('R3', 'scripts/run_authorized_heldout_episode.py'),
    ('R3', 'src/language_nav/physical_heldout_authorization.py'),
    ('R3', 'ros_ws/src/language_nav_bringup/launch/heldout_adapters.launch.py'),
    ('R3', 'ros_ws/src/language_nav_bringup/language_nav_bringup/heldout_landmark_bridge.py'),
    ('R3', 'scripts/physical_perception_capture.py'),
    ('R3', 'ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py'),
    ('R3', 'ros_ws/src/language_nav_runtime/language_nav_runtime/monitor_bridge.py'),
    ('R3', 'ros_ws/src/language_nav_runtime/language_nav_runtime/semantic_routes.py'),
    ('R3', 'ros_ws/src/language_nav_planner/language_nav_planner/node.py'),
    ('R1', 'extensions/research3_landmark_bridge/research3_landmark_bridge/core.py'),
    ('R1', 'extensions/research3_landmark_bridge/research3_landmark_bridge/node.py'),
)
INSTALL_FILES = (
    ('R3', 'ros_ws/build/language_nav_runtime/language_nav_runtime/nav2_adapter.py'),
    ('R3', 'ros_ws/build/language_nav_runtime/language_nav_runtime/monitor_bridge.py'),
    ('R3', 'ros_ws/build/language_nav_runtime/language_nav_runtime/semantic_routes.py'),
    ('R3', 'ros_ws/build/language_nav_planner/language_nav_planner/node.py'),
    ('R3', 'ros_ws/install/language_interface/lib/python3.12/site-packages/language_interface/node.py'),
    ('R3', 'ros_ws/install/semantic_belief_map/lib/python3.12/site-packages/semantic_belief_map/node.py'),
    ('R3', 'ros_ws/build/language_nav_bringup/language_nav_bringup/landmark_bridge_runner.py'),
    ('R3', 'ros_ws/install/language_nav_bringup/share/language_nav_bringup/launch/heldout_adapters.launch.py'),
    ('R3', 'ros_ws/build/language_nav_bringup/language_nav_bringup/heldout_landmark_bridge.py'),
    ('R3', 'ros_ws/build/research3_landmark_bridge/research3_landmark_bridge/__init__.py'),
    ('R3', 'ros_ws/build/research3_landmark_bridge/research3_landmark_bridge/core.py'),
    ('R3', 'ros_ws/build/research3_landmark_bridge/research3_landmark_bridge/node.py'),
    ('R3', 'ros_ws/install/language_nav_runtime/lib/python3.12/site-packages/language_nav_runtime/nav2_adapter.py'),
    ('R3', 'ros_ws/install/language_nav_runtime/lib/python3.12/site-packages/language_nav_runtime/monitor_bridge.py'),
    ('R3', 'ros_ws/install/language_nav_runtime/lib/python3.12/site-packages/language_nav_runtime/semantic_routes.py'),
    ('R3', 'ros_ws/install/language_nav_planner/lib/python3.12/site-packages/language_nav_planner/node.py'),
    ('R3', 'ros_ws/install/research3_landmark_bridge/lib/python3.12/site-packages/research3_landmark_bridge/core.py'),
    ('R3', 'ros_ws/install/research3_landmark_bridge/lib/python3.12/site-packages/research3_landmark_bridge/node.py'),
    ('R1', 'ros_ws/install/research3_landmark_bridge/lib/python3.12/site-packages/research3_landmark_bridge/core.py'),
    ('R1', 'ros_ws/install/research3_landmark_bridge/lib/python3.12/site-packages/research3_landmark_bridge/node.py'),
)


def file_record(path):
    path = Path(path)
    if not path.is_file():
        return {'path': str(path), 'status': 'unavailable', 'sha256': None}
    raw = path.read_bytes()
    return {'path': str(path), 'resolved_path': str(path.resolve()),
            'status': 'retained_hash_only', 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def revision(path):
    try:
        result = subprocess.run(['git', '-C', str(path), 'rev-parse', 'HEAD'],
                                capture_output=True, text=True, timeout=5, check=True)
        value = result.stdout.strip()
        if not re.fullmatch('[a-f0-9]{40,64}', value):
            raise ValueError('invalid revision')
        return {'status': 'observed', 'revision': value}
    except (OSError, subprocess.SubprocessError, ValueError):
        return {'status': 'unavailable', 'revision': None}


def capture(root=ROOT, ros_root=Path('/opt/ros/jazzy'), version_reader=importlib.metadata.version):
    root, ros_root = Path(root).resolve(), Path(ros_root)
    repositories = {'R3': root, 'R1': root.parent/'risk-calibrated-nav',
                    'R2': root.parent/'failure-prediction'}
    packages = {}
    for name in PYTHON_PACKAGES:
        try:
            version = version_reader(name)
            if not re.fullmatch(r'[a-zA-Z0-9.+_-]+', version):
                raise ValueError('non-version metadata rejected')
            packages[name] = {'status': 'observed', 'version': version}
        except (importlib.metadata.PackageNotFoundError, ValueError):
            packages[name] = {'status': 'unavailable', 'version': None}
    ros_packages = {}
    for name in ROS_PACKAGES:
        path = ros_root/'share'/name/'package.xml'
        record = file_record(path)
        if path.is_file():
            tree = ET.fromstring(path.read_bytes())
            record['declared_name'] = tree.findtext('name')
            record['version'] = tree.findtext('version')
        else:
            record['version'] = None
        ros_packages[name] = record
    sources = {f'{repo}:{name}': file_record(repositories[repo]/name) for repo, name in SOURCE_FILES}
    installed = {f'{repo}:{name}': file_record(repositories[repo]/name) for repo, name in INSTALL_FILES}
    return {'schema_version': 'research3-engineering-environment/v1',
            'captured_at_utc': datetime.now(timezone.utc).isoformat(),
            'scope': 'allowlisted metadata and code hashes; not full runtime reconstruction',
            'python': {'version': platform.python_version(), 'implementation': platform.python_implementation(),
                       'executable': sys.executable},
            'python_packages': packages, 'ros_distribution_metadata_root': str(ros_root),
            'ros_packages': ros_packages,
            'repositories': {name: {'path': str(path), **revision(path)} for name, path in repositories.items()},
            'source_files': sources, 'installed_files': installed,
            'gpu': {'status': 'unknown', 'device': None, 'utilization': None,
                    'reason': 'GPU state not queried; no inference from package installation'},
            'environment_variables_collected': False, 'private_package_urls_collected': False,
            'protected_data_read': False, 'human_labels_generated': False,
            'study_complete': False, 'runtime_reconstruction_complete': False,
            'limitations': ['Versions describe the reporting Python interpreter, not every ROS subprocess.',
                'ROS versions are from explicit package.xml files; active overlay selection is not inferred.',
                'Git HEAD does not identify dirty source bytes; selected source/install hashes supplement it.',
                'Missing known install files remain unavailable; no broad filesystem search is performed.']}


def write_once(output, report):
    with Path(output).open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = capture()
    write_once(args.output, report)
    print(json.dumps({'output': str(args.output), 'gpu_status': 'unknown',
                      'environment_variables_collected': False}))


if __name__ == '__main__':
    main()
