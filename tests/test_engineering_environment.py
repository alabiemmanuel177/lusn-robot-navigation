import importlib.metadata
import importlib.util
import json
from pathlib import Path

import pytest


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


ROOT = Path(__file__).resolve().parents[1]
ENV = module('environment_capture', ROOT/'scripts/capture_engineering_environment.py')
PACK = module('environment_packager', ROOT/'scripts/package_physical_engineering.py')


def test_capture_allowlist_and_unknown_gpu(tmp_path, monkeypatch):
    monkeypatch.setenv('SECRET_API_KEY', 'never-include-this')
    monkeypatch.setattr(ENV, 'revision', lambda path: {'status': 'unavailable', 'revision': None})
    report = ENV.capture(tmp_path/'research3', tmp_path/'ros', lambda name: '1.2.3')
    assert set(report['python_packages']) == {'numpy', 'scipy', 'PyYAML', 'pytest'}
    assert set(report['repositories']) == {'R1', 'R2', 'R3'}
    assert report['gpu']['status'] == 'unknown'
    assert report['gpu']['utilization'] is None
    assert 'never-include-this' not in json.dumps(report)
    assert report['protected_data_read'] is False
    assert all(row['sha256'] is None for row in report['installed_files'].values())


def test_ordinary_interface_and_belief_installed_copies_are_explicitly_recorded():
    for package in ('language_interface', 'semantic_belief_map'):
        assert ('R3', f'ros_ws/src/{package}/{package}/node.py') in ENV.SOURCE_FILES
        assert ('R3', f'ros_ws/install/{package}/lib/python3.12/site-packages/{package}/node.py') in ENV.INSTALL_FILES


def test_known_symlink_overlay_build_paths_are_explicitly_recorded():
    for package, filename in (('language_nav_runtime', 'nav2_adapter.py'),
                              ('language_nav_runtime', 'monitor_bridge.py'),
                              ('language_nav_runtime', 'semantic_routes.py'),
                              ('language_nav_planner', 'node.py')):
        assert ('R3', f'ros_ws/build/{package}/{package}/{filename}') in ENV.INSTALL_FILES


def test_missing_and_non_version_package_metadata_not_leaked(tmp_path, monkeypatch):
    monkeypatch.setattr(ENV, 'revision', lambda path: {})
    def versions(name):
        if name == 'numpy':
            raise importlib.metadata.PackageNotFoundError(name)
        return 'https://private-token@private.example/package'
    report = ENV.capture(tmp_path/'r3', tmp_path/'ros', versions)
    assert all(row['version'] is None for row in report['python_packages'].values())
    assert 'private-token' not in json.dumps(report)


def test_ros_package_xml_and_selected_source_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(ENV, 'revision', lambda path: {})
    root = tmp_path/'r3'
    (root/'scripts').mkdir(parents=True)
    script = root/'scripts/run_physical_episode.py'
    script.write_bytes(b'pass\n')
    ros = tmp_path/'ros'
    package = ros/'share/rclpy/package.xml'
    package.parent.mkdir(parents=True)
    package.write_text('<package><name>rclpy</name><version>7.1.2</version></package>')
    report = ENV.capture(root, ros, lambda name: '1.2')
    assert report['ros_packages']['rclpy']['version'] == '7.1.2'
    assert report['source_files']['R3:scripts/run_physical_episode.py']['sha256'] == PACK.digest(b'pass\n')


def test_report_is_create_once(tmp_path):
    path = tmp_path/'report.json'
    ENV.write_once(path, {'fixture': True})
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        ENV.write_once(path, {'fixture': False})
    assert path.read_bytes() == before


def test_packaging_report_is_explicit_and_hash_bound(tmp_path, monkeypatch):
    monkeypatch.setattr(PACK, 'standard_paths', lambda root: [])
    path = tmp_path/'report.json'
    report = {'schema_version': 'research3-engineering-environment/v1',
              'environment_variables_collected': False, 'private_package_urls_collected': False,
              'protected_data_read': False}
    path.write_text(json.dumps(report))
    files, manifest = PACK.collect(tmp_path, environment_report=path)
    assert set(files) == {'report.json'}
    assert manifest['environment_report']['sha256'] == PACK.digest(path.read_bytes())
    report['environment_variables_collected'] = True
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match='environment report'):
        PACK.collect(tmp_path, environment_report=path)
