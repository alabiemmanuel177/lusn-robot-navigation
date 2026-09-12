"""Small synthetic source trees only; no real provider file discovery."""
import importlib.util
import json
from pathlib import Path

import pytest
from language_nav import camera_configuration as camera

SPEC = importlib.util.spec_from_file_location('source_archive', Path(__file__).parents[1]/'scripts/snapshot_capture_sources.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


@pytest.fixture
def source_tree(tmp_path, monkeypatch):
    root, provider = tmp_path/'r3', tmp_path/'provider'
    root.mkdir();provider.mkdir()
    monkeypatch.setattr(camera,'CAPTURE_SOURCE_PATHS',('scripts/synthetic.py',))
    names=tuple('extensions/research3_landmark_bridge/research3_landmark_bridge/'+name for name in M.BRIDGE_FILES)
    names+=tuple('src/semantic_perception/semantic_perception/'+name for name in M.TRANSFORM_FILES)
    monkeypatch.setattr(camera,'PROVIDER_SOURCE_FILES',names,raising=False)
    path=root/'scripts/synthetic.py';path.parent.mkdir();path.write_bytes(b'# synthetic R3 source\n')
    external, active, transforms = {}, {}, {}
    for name in names:
        path=provider/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'# synthetic provider\n')
        external[name]=M.PACKAGE.digest(path.read_bytes())
        build=(root/'ros_ws/build/research3_landmark_bridge/research3_landmark_bridge'/path.name
               if path.name in M.BRIDGE_FILES else provider/'build/semantic_perception/semantic_perception'/path.name)
        build.parent.mkdir(parents=True,exist_ok=True);build.write_bytes(path.read_bytes())
        (active if path.name in M.BRIDGE_FILES else transforms)[path.name]={'path':str(build),'resolved_path':str(build.resolve()),'sha256':external[name]}
    snapshot={'schema_version':'research3-capture-source-snapshot/v1',
        'source_sha256':{'scripts/synthetic.py':M.PACKAGE.digest((root/'scripts/synthetic.py').read_bytes())},
        'provider_source_snapshot':{'files':external,'active_build_files':active,
                                  'active_transform_files':transforms,
                                  'transform_source_build_match':{name:True for name in M.TRANSFORM_FILES},
                                  'source_build_match':{name:True for name in M.BRIDGE_FILES},'complete':True}}
    monkeypatch.setattr(camera,'capture_source_snapshot',lambda directory:dict(snapshot['source_sha256']))
    return root,provider,snapshot


def test_pre_capture_bytes_retained_create_once_and_packageable(source_tree):
    root,provider,snapshot=source_tree
    files,manifest=M.capture(snapshot,root=root,provider_root=provider)
    assert len(files)==11 and all(name.startswith(('research3/','external_provider/')) for name in files)
    output=root/'snapshot.tar.gz'
    M.PACKAGE.write_bundle(output,files,manifest)
    assert M.PACKAGE.capture_source_archive_paths(root,output)==[output]
    assert not manifest['external_environment_closure_complete']
    with pytest.raises(FileExistsError):M.PACKAGE.write_bundle(output,files,manifest)


def test_changed_provider_bytes_fail_before_archive_creation(source_tree):
    root,provider,snapshot=source_tree
    path=provider/next(iter(snapshot['provider_source_snapshot']['files']))
    path.write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed'):
        M.capture(snapshot,root=root,provider_root=provider)


def test_arbitrary_provider_or_private_input_is_rejected(source_tree):
    root,provider,snapshot=source_tree
    snapshot['provider_source_snapshot']['files']['private.yaml']='0'*64
    with pytest.raises(ValueError,match='allowlist'):
        M.capture(snapshot,root=root,provider_root=provider)


def test_active_build_mismatch_rejected(source_tree):
    root,provider,snapshot=source_tree
    snapshot['provider_source_snapshot']['source_build_match']['node.py']=False
    with pytest.raises(ValueError,match='matching'):
        M.capture(snapshot,root=root,provider_root=provider)


def test_archive_cannot_smuggle_unlisted_yaml(source_tree):
    root,provider,snapshot=source_tree
    files,manifest=M.capture(snapshot,root=root,provider_root=provider)
    files['external_provider/private.yaml']=b'not allowed'
    manifest['files']['external_provider/private.yaml']={'sha256':M.PACKAGE.digest(b'not allowed'),'bytes':11}
    output=root/'bad.tar.gz';M.PACKAGE.write_bundle(output,files,manifest)
    with pytest.raises(ValueError,match='allowlist'):
        M.PACKAGE.capture_source_archive_paths(root,output)


def test_package_binds_each_capture_request_to_its_archived_sources(source_tree,monkeypatch):
    root,provider,snapshot=source_tree
    files,manifest=M.capture(snapshot,root=root,provider_root=provider)
    archive=root/'snapshot.tar.gz';M.PACKAGE.write_bundle(archive,files,manifest)
    run=root/'reports/run';run.mkdir(parents=True)
    request=dict(run_id='run',partition='development',map_id='r3geo_base_r001',
        protected_test_routes_used=False,source_sha256=snapshot['source_sha256'],
        provider_source_snapshot=snapshot['provider_source_snapshot'])
    (run/'request.json').write_text(json.dumps(request))
    monkeypatch.setattr(M.PACKAGE,'standard_paths',lambda root:[])
    _,result=M.PACKAGE.collect(root,runs=[run],capture_source_snapshots=[archive])
    binding=result['selected_runs'][0]['capture_source_archive_bindings'][0]
    assert binding['r3_source_pins_match'] and binding['provider_source_build_pins_match']
    assert result['explicit_external_provider_source_archive_included']
    request['provider_source_snapshot']=None;(run/'request.json').write_text(json.dumps(request))
    _,result=M.PACKAGE.collect(root,runs=[run],capture_source_snapshots=[archive])
    assert not result['selected_runs'][0]['capture_source_archive_bindings'][0]['provider_source_build_pins_match']


def test_active_transform_byte_mismatch_is_rejected(source_tree):
    root,provider,snapshot=source_tree
    path=provider/'build/semantic_perception/semantic_perception/projection.py'
    path.write_bytes(b'# changed active module\n')
    with pytest.raises(ValueError,match='changed'):
        M.capture(snapshot,root=root,provider_root=provider)
