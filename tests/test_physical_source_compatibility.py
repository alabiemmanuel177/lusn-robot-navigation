"""Synthetic archive/source comparisons; never read real protected assets."""
import hashlib
import io
import json
from pathlib import Path
import runpy
import tarfile

import pytest

SCRIPT = Path(__file__).parents[1] / 'scripts/compare_physical_sources.py'


def make_archive(path, members, *, corrupt=False):
    manifest = {'schema_version': 'research3-nonprotected-engineering-bundle/v1',
                'protected_data_included': False,
                'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
                          for name, raw in members.items()}}
    if corrupt:
        manifest['files'][next(iter(members))]['sha256'] = '0' * 64
    with tarfile.open(path, 'w:gz') as archive:
        for name, raw in {'MANIFEST.json': json.dumps(manifest).encode(), **members}.items():
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def setup(tmp_path):
    tool = runpy.run_path(str(SCRIPT))
    members = {name: b'# synthetic baseline\n' for name in tool['SOURCES']}
    for name, raw in members.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    archive = tmp_path / 'baseline.tar.gz'
    spec = {'schema_version': 'research3-source-comparison-request/v1',
            'archive_sha256': make_archive(archive, members), 'runs': []}
    return tool, tmp_path, archive, spec, members


def test_unchanged_sources_do_not_self_approve(setup):
    tool, root, archive, spec, _ = setup
    report = tool['compare'](archive, spec, root)
    assert report['status'] == 'blocked_for_equivalence_approval'
    assert report['source_files_changed'] == []
    assert not report['deployment_eligible'] and not report['equivalence_approved']
    assert report['capture_evidence_validity'] == 'not_assessed_no_explicit_runs'


def test_changed_sources_are_reported_without_rewriting_baseline(setup):
    tool, root, archive, spec, _ = setup
    target = root / tool['SOURCES'][0]
    target.write_text('# synthetic authorized branch\n')
    before = archive.read_bytes()
    report = tool['compare'](archive, spec, root)
    assert report['source_files_changed'] == [tool['SOURCES'][0]]
    assert archive.read_bytes() == before


def test_unpinned_archive_rejected(setup):
    tool, root, archive, spec, _ = setup
    spec['archive_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='archive checksum'):
        tool['compare'](archive, spec, root)


def test_corrupt_selected_member_rejected(setup):
    tool, root, archive, spec, members = setup
    spec['archive_sha256'] = make_archive(archive, members, corrupt=True)
    with pytest.raises(ValueError, match='member checksum'):
        tool['compare'](archive, spec, root)


def test_protected_request_refused_before_scene_access(setup):
    tool, root, archive, spec, members = setup
    request = 'reports/physical_live_episodes/synthetic/request.json'
    members[request] = json.dumps({'map_id': 'r3geo_base_r015', 'partition': 'held_out',
                                 'protected_test_routes_used': True}).encode()
    spec['archive_sha256'] = make_archive(archive, members)
    spec['runs'] = [{'request_member': request}]
    with pytest.raises(ValueError, match='non-protected request'):
        tool['compare'](archive, spec, root)


@pytest.mark.parametrize('profile_family', ['engineering_camera_settings_v2', 'stationary_capture_plan_v1', 'dev10_stress'])
def test_exact_capture_bindings_environment_and_absent_request_pin(setup, profile_family):
    tool, root, archive, spec, members = setup
    prefix = 'reports/physical_live_episodes/synthetic/'
    profile = ('configs/physical_dev10_camera_profile_v1.yaml' if profile_family == 'dev10_stress'
               else f'reports/{profile_family}/profiles/base-r010.yaml')
    scene = prefix + 'runtime_scene.yaml'
    members[profile], members[scene] = b'synthetic profile', b'synthetic scene'
    request = {'map_id': 'r3geo_base_r010', 'partition': 'development',
               'protected_test_routes_used': False, 'camera_horizontal_fov': 1.2,
               'runtime_scene_sha256': hashlib.sha256(members[scene]).hexdigest(),
               'camera_profile_sha256': hashlib.sha256(members[profile]).hexdigest(),
               'source_sha256': {name: hashlib.sha256(members[name]).hexdigest() for name in tool['SOURCES'][:-1]}}
    members[prefix + 'request.json'] = json.dumps(request).encode()
    environment = 'reports/engineering_environment_synthetic_v1.json'
    members[environment] = json.dumps({'schema_version': 'research3-engineering-environment/v1',
        'python': {'version': 'synthetic'}, 'python_packages': {'numpy': 'synthetic'},
        'ros_packages': {'rclpy': 'synthetic'},
        'source_files': {'R1:research3_landmark_bridge/core.py': {'sha256': 'a' * 64}}}).encode()
    for name, raw in members.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    spec.update(archive_sha256=make_archive(archive, members),
                baseline_environment_member=environment, current_environment_path=environment,
                runs=[{'request_member': prefix + 'request.json', 'scene_member': scene, 'profile_member': profile}])
    report = tool['compare'](archive, spec, root)
    assert report['capture_evidence_validity'] == 'selected_bindings_unchanged_full_media_review_not_reaudited'
    assert report['runs'][0]['source_archive_matches_capture'][tool['SOURCES'][-1]] is None
    assert 'capture_request_source_provenance_incomplete_for_compared_files' in report['blockers']
    assert report['capture_source_reconstruction'][tool['SOURCES'][-1]]['unrecorded_runs'] == 1
    assert report['environment_comparison']['provider_hashes_unchanged']
    assert not report['deployment_eligible']
    (root / scene).write_text('changed current scene')
    changed = tool['compare'](archive, spec, root)
    assert changed['capture_evidence_validity'] == 'selected_bindings_changed_or_incomplete'
    assert not changed['runs'][0]['scene']['unchanged']


def test_current_source_symlink_rejected(setup):
    tool, root, archive, spec, _ = setup
    target = root / tool['SOURCES'][0]
    target.unlink()
    target.symlink_to(root / tool['SOURCES'][1])
    with pytest.raises(ValueError, match='symlinked'):
        tool['compare'](archive, spec, root)


def test_protected_path_rejected_without_open(setup):
    tool, root, archive, spec, _ = setup
    spec['runs'] = [{'request_member': 'data/physical_worlds_v1/base-r020/landmark_scene.yaml'}]
    with pytest.raises(ValueError, match='protected input path'):
        tool['compare'](archive, spec, root)
