import importlib.util
import json
from pathlib import Path
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('engineering_package',
    ROOT/'scripts/package_physical_engineering.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def manifest(files):
    return {'study_complete': False, 'calibration_frozen': False,
            'files': {name: {'sha256': MODULE.digest(raw), 'bytes': len(raw)}
                      for name, raw in files.items()}}


def test_reproducible_sorted_archive_and_create_once(tmp_path):
    files = {'scripts/example.py': b'print(1)\n', 'data/example.bin': b'\x00\xff'}
    first, second = tmp_path/'first.tar.gz', tmp_path/'second.tar.gz'
    assert MODULE.write_bundle(first, files, manifest(files)) == MODULE.write_bundle(
        second, dict(reversed(list(files.items()))), manifest(files))
    assert first.read_bytes() == second.read_bytes()
    assert MODULE.verify_archive(first)['study_complete'] is False
    with tarfile.open(first) as archive:
        assert all(member.mtime == 0 and member.uid == 0 and member.mode == 0o644
                   for member in archive.getmembers())
    before = first.read_bytes()
    with pytest.raises(FileExistsError):
        MODULE.write_bundle(first, files, manifest(files))
    assert first.read_bytes() == before


def test_manifest_mismatch_rejected_before_output_creation(tmp_path):
    output = tmp_path/'bad.tar.gz'
    with pytest.raises(ValueError, match='manifest'):
        MODULE.write_bundle(output, {'one': b'changed'}, manifest({'one': b'old'}))
    assert not output.exists()


def make_run(tmp_path, partition='development', map_id='r3geo_base_r010'):
    run = tmp_path/'reports'/'explicit-run'
    run.mkdir(parents=True)
    (run/'request.json').write_text(json.dumps({'run_id': 'explicit-run', 'partition': partition,
        'map_id': map_id, 'protected_test_routes_used': False}))
    return run


def test_selected_run_uses_allowlist_not_recursive_sweep(tmp_path):
    run = make_run(tmp_path)
    (run/'old.reviewed.jsonl').write_text('must not be included')
    (run/'.env').write_text('must not be included')
    (run/'human_progress.jsonl').write_text('must not be included')
    camera = run/'perception_capture'
    camera.mkdir()
    for name in ('frame-000.json', 'frame-000-rgb.bin', 'frame-000-depth.bin', 'summary.json'):
        (camera/name).write_bytes(b'fixture')
    (camera/'arbitrary-secret.json').write_text('must not be included')
    files, records = MODULE.run_paths(tmp_path, [run])
    assert len(files) == 5
    assert records[0]['map_id'] == 'r3geo_base_r010'
    assert not any('secret' in path.name or 'reviewed' in path.name or path.name == '.env' for path in files)


def test_protected_run_rejected_without_evidence_access(tmp_path):
    run = make_run(tmp_path, 'development', 'r3geo_base_r015')
    with pytest.raises(ValueError, match='protected'):
        MODULE.run_paths(tmp_path, [run])


def test_labels_and_duplicate_runs_rejected(tmp_path):
    run = make_run(tmp_path)
    with pytest.raises(ValueError, match='duplicate'):
        MODULE.run_paths(tmp_path, [run, run])
    (run/'landmark_review_tasks.jsonl').write_text(json.dumps({'correct': True}))
    with pytest.raises(ValueError, match='labelled'):
        MODULE.run_paths(tmp_path, [run])


def test_symlink_and_traversal_rejected(tmp_path):
    target = tmp_path/'actual'
    target.mkdir()
    (tmp_path/'link').symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        MODULE.safe_path(tmp_path, tmp_path/'link'/'file')
    with pytest.raises(ValueError):
        MODULE.safe_path(tmp_path, '../outside')


def test_standard_inventory_names_only_nonprotected_assets():
    paths = MODULE.standard_paths(ROOT)
    worlds = [path for path in paths if path.name == 'world.sdf']
    assert len(worlds) == 51
    assert ROOT/'data/physical_worlds_v1/base-r014/world.sdf' in worlds
    assert ROOT/'data/physical_shape_stress_dev10_v3/chair/base-r010/world.sdf' in worlds
    assert not any('base-r015' in path.parts or 'heldout_landmark_bridge_v1' in path.parts for path in paths)
    assert ROOT/'scripts/serve_physical_review.py' in paths
    assert ROOT/'scripts/export_physical_human_review.py' in paths
    assert ROOT/'reports/engineering_camera_settings_v2/validation_commands.json' in paths
    assert ROOT/'reports/engineering_camera_settings_v1/validation_commands.json' not in paths
    historical = MODULE.standard_paths(ROOT, include_historical_settings_v1=True)
    assert ROOT/'reports/engineering_camera_settings_v1/validation_commands.json' in historical
    assert not any(path.name.endswith('.reviewed.jsonl') for path in paths)


def test_byte_limit_before_read_and_current_snapshot_flags(tmp_path, monkeypatch):
    source = tmp_path/'example.py'
    source.write_bytes(b'abc')
    monkeypatch.setattr(MODULE, 'standard_paths', lambda root: [source])
    with pytest.raises(ValueError, match='budget'):
        MODULE.collect(tmp_path, max_bytes=2)
    files, result = MODULE.collect(tmp_path, max_bytes=3)
    assert files == {'example.py': b'abc'}
    assert result['study_complete'] is False
    assert result['calibration_validated'] is False


def test_source_changes_detected(tmp_path, monkeypatch):
    source = tmp_path/'example.py'
    source.write_bytes(b'abc')
    monkeypatch.setattr(MODULE, 'standard_paths', lambda root: [source])
    original = Path.read_bytes
    calls = 0
    def mutate_on_second_read(path):
        nonlocal calls
        calls += 1
        return b'xyz' if calls > 1 else original(path)
    monkeypatch.setattr(Path, 'read_bytes', mutate_on_second_read)
    with pytest.raises(ValueError, match='source changed'):
        MODULE.collect(tmp_path)


def packet_fixture(tmp_path, *, correct=None, map_id='r3geo_base_r010'):
    directory = tmp_path/'packet'
    directory.mkdir()
    values = {'inventory.json': json.dumps({'protected_data_used': False, 'items': [
        {'map_id': map_id, 'partition': 'development', 'correct': correct, 'human_reviewer_id': ''}]}).encode(),
        'combined_visual_qa.jsonl': b'{}\n', 'sampling_policy.json': b'{}'}
    for name, raw in values.items():
        (directory/name).write_bytes(raw)
    manifest = {'schema_version': 'research3-physical-review-packet/v1',
                'protected_data_used': False, 'human_labels_generated': False,
                'files': {name: MODULE.digest(raw) for name, raw in values.items()}}
    (directory/'packet_manifest.json').write_text(json.dumps(manifest))
    return directory


def test_review_packet_allowlist_and_hashes(tmp_path):
    directory = packet_fixture(tmp_path)
    (directory/'human_progress.jsonl').write_text('excluded')
    paths, record = MODULE.review_packet_paths(tmp_path, directory)
    assert len(paths) == 4
    assert not any(path.name == 'human_progress.jsonl' for path in paths)
    assert record['packet_manifest_sha256'] == MODULE.digest((directory/'packet_manifest.json').read_bytes())
    (directory/'sampling_policy.json').write_text('changed')
    with pytest.raises(ValueError, match='checksum'):
        MODULE.review_packet_paths(tmp_path, directory)


@pytest.mark.parametrize('kwargs', [{'correct': True}, {'map_id': 'r3geo_base_r015'}])
def test_review_packet_refuses_labels_or_protected_items(tmp_path, kwargs):
    directory = packet_fixture(tmp_path, **kwargs)
    with pytest.raises(ValueError, match='protected or labelled'):
        MODULE.review_packet_paths(tmp_path, directory)


def test_known_run_diagnostics_retained_without_sweep(tmp_path):
    run = make_run(tmp_path)
    names = ('failure.json', 'resource_guard.json', 'logs/controller.log',
             'logs/nav2.log', 'logs/research3.log', 'research3/explicit-run.json',
             'research3/explicit-run.trace.json')
    for name in (*names, 'logs/private.log', 'logs/sim.log', 'research3/human_progress.jsonl'):
        path = run/name
        path.parent.mkdir(exist_ok=True)
        path.write_text('synthetic diagnostic')
    paths, _ = MODULE.run_paths(tmp_path, [run])
    assert {str(path.relative_to(run)) for path in paths} == {'request.json', *names}


def evidence(tmp_path, name='physical_review_packet_20260911_audit_v1.json', **updates):
    path = tmp_path/'reports'/name
    path.parent.mkdir(parents=True, exist_ok=True)
    value = dict(schema_version='research3-review-packet-provenance-audit/v1',
                 protected_data_used=False, human_labels_generated=False,
                 human_labels_present=0, limits=['No held-out data were read.'])
    value.update(updates)
    path.write_text(json.dumps(value))
    return path


def test_explicit_audit_included_and_bound(tmp_path, monkeypatch):
    path = evidence(tmp_path)
    monkeypatch.setattr(MODULE, 'standard_paths', lambda root: [])
    files, manifest = MODULE.collect(tmp_path, engineering_evidence=[path])
    relative = str(path.relative_to(tmp_path))
    assert set(files) == {relative}
    assert manifest['engineering_evidence'][0]['sha256'] == MODULE.digest(path.read_bytes())
    assert manifest['study_complete'] is False
    with pytest.raises(ValueError, match='duplicate'):
        MODULE.collect(tmp_path, engineering_evidence=[path, path])


@pytest.mark.parametrize('updates', [dict(protected_data_used=True), dict(correct=False),
    dict(human_labels_present=1), dict(partition='heldout'), dict(map_id='r3geo_base_r015'),
    dict(schema_version='human-review/v1')])
def test_evidence_protected_labels_and_unknown_schema_rejected(tmp_path, updates):
    path = evidence(tmp_path, **updates)
    with pytest.raises(ValueError):
        MODULE.engineering_evidence_paths(tmp_path, [path], [])


def test_unknown_report_name_rejected_before_read(tmp_path, monkeypatch):
    path = tmp_path/'reports/human_progress.jsonl'
    monkeypatch.setattr(Path, 'read_bytes', lambda self: pytest.fail('must not read unknown report'))
    with pytest.raises(ValueError, match='filename'):
        MODULE.engineering_evidence_paths(tmp_path, [path], [])


@pytest.mark.parametrize('name,schema', [
    ('physical_source_comparison', 'research3-physical-source-comparison/v1'),
    ('physical_nonprotected_differential', 'research3-nonprotected-catalog-differential/v1'),
    ('physical_nonprotected_source_supplement', 'research3-nonprotected-source-supplement/v1')])
def test_explicit_source_comparisons_remain_unapproved(tmp_path, name, schema):
    path = tmp_path/'reports'/f'{name}_20260911_v2.json'
    path.parent.mkdir()
    value = dict(schema_version=schema, protected_data_used=False,
                 deployment_eligible=False, equivalence_approved=False)
    path.write_text(json.dumps(value))
    assert MODULE.engineering_evidence_paths(tmp_path, [path], [])[0] == [path]
    for update in ({'protected_data_used': True}, {'schema_version': 'unknown/v1'},
                   {'deployment_eligible': True}, {'equivalence_approved': True},
                   {'study_complete': True}, {'correct': False}, {'map_id': 'base-r015'}):
        path.write_text(json.dumps(value | update))
        with pytest.raises(ValueError):
            MODULE.engineering_evidence_paths(tmp_path, [path], [])


def test_readme_and_status_explicitly_selected_without_memory_sweep(tmp_path):
    for tree in ('src', 'scripts', 'tests', 'ros_ws/src'):
        (tmp_path/tree).mkdir(parents=True)
    (tmp_path/'docs').mkdir()
    (tmp_path/'README.md').write_text('readme')
    (tmp_path/'docs/STATUS.md').write_text('status')
    paths = MODULE.standard_paths(tmp_path)
    assert tmp_path/'README.md' in paths
    assert tmp_path/'docs/STATUS.md' in paths
    assert not any('memory' in path.parts for path in paths)


def test_differential_synthetic_refusal_exception_does_not_allow_protected_evidence(tmp_path):
    path = tmp_path/'reports/physical_nonprotected_differential_20260911_v1.json'
    path.parent.mkdir()
    refusal = dict(baseline='PermissionError', current='PermissionError',
                   both_refuse_before_asset_access=True, map_id='r3geo_base_r015',
                   synthetic_partition='held_out')
    value = dict(schema_version='research3-nonprotected-catalog-differential/v1',
                 protected_data_used=False, deployment_eligible=False, equivalence_approved=False,
                 synthetic_default_refusals=[refusal])
    path.write_text(json.dumps(value))
    assert MODULE.engineering_evidence_paths(tmp_path, [path], [])[0] == [path]
    for update in ({'current': 'success'}, {'path': 'data/protected.json'},
                   {'both_refuse_before_asset_access': False}):
        path.write_text(json.dumps(value | {'synthetic_default_refusals': [refusal | update]}))
        with pytest.raises(ValueError, match='synthetic'):
            MODULE.engineering_evidence_paths(tmp_path, [path], [])
    path.write_text(json.dumps(value | {'rows': [{'map_id': 'r3geo_base_r015'}]}))
    with pytest.raises(ValueError, match='protected'):
        MODULE.engineering_evidence_paths(tmp_path, [path], [])


def test_journal_retains_failure_requires_explicit_run(tmp_path):
    run = make_run(tmp_path)
    _, records = MODULE.run_paths(tmp_path, [run])
    journal = tmp_path/'reports/physical_engineering_smoke_batch_v9/attempts.jsonl'
    journal.parent.mkdir()
    row = dict(run_id='explicit-run', status='halted_resource_infrastructure_or_unknown',
               error='synthetic setup failure')
    journal.write_text(json.dumps(row)+'\n')
    paths, references = MODULE.engineering_evidence_paths(tmp_path, [journal], records)
    assert paths == [journal]
    assert references[0]['journal_scope'] == 'explicit_nonprotected_runs'
    with pytest.raises(ValueError, match='explicit nonprotected'):
        MODULE.engineering_evidence_paths(tmp_path, [journal], [])
    journal.write_text((json.dumps(row)+'\n')*2)
    with pytest.raises(ValueError, match='unique'):
        MODULE.engineering_evidence_paths(tmp_path, [journal], records)


def camera_settings_fixture(tmp_path):
    directory=tmp_path/'reports/new_settings'
    (directory/'profiles').mkdir(parents=True)
    profiles={}
    for i in range(1,15):
        path=directory/'profiles'/f'base-r{i:03d}.yaml'
        path.write_text('synthetic: true\n')
        profiles[f'r3geo_base_r{i:03d}']=MODULE.digest(path.read_bytes())
    (directory/'camera_settings_freeze.json').write_text(json.dumps(dict(
        schema_version='research3-engineering-camera-freeze/v2',protected_data_used=False,
        human_labels_generated=False,confidence_calibration_frozen=False,profiles=profiles)))
    (directory/'validation_commands.json').write_text(json.dumps(dict(
        schema_version='research3-frozen-camera-validation-commands/v1',protected_content_used=False,
        commands=[dict(base_instruction_id='base-r011')])))
    return directory


def test_explicit_camera_settings_no_extra_sweep(tmp_path,monkeypatch):
    directory=camera_settings_fixture(tmp_path)
    (directory/'human_progress.jsonl').write_text('excluded')
    paths=MODULE.capture_settings_paths(tmp_path,directory)
    assert len(paths)==16
    assert all(path.name!='human_progress.jsonl' for path in paths)
    monkeypatch.setattr(MODULE,'standard_paths',lambda root:[])
    files,manifest=MODULE.collect(tmp_path,capture_settings=[directory])
    assert len(files)==16
    assert manifest['explicit_capture_inputs'][0]['kind']=='camera_settings'


def test_explicit_camera_settings_tamper_and_protection(tmp_path):
    directory=camera_settings_fixture(tmp_path)
    (directory/'profiles/base-r001.yaml').write_text('changed')
    with pytest.raises(ValueError,match='checksum'):
        MODULE.capture_settings_paths(tmp_path,directory)
    freeze=json.loads((directory/'camera_settings_freeze.json').read_text())
    freeze['protected_data_used']=True
    (directory/'camera_settings_freeze.json').write_text(json.dumps(freeze))
    with pytest.raises(ValueError,match='nonprotected'):
        MODULE.capture_settings_paths(tmp_path,directory)


def test_current_capture_plan_has_exact_profiles_and_no_extra_sweep(tmp_path):
    directory=tmp_path/'reports/fresh_plan';(directory/'profiles').mkdir(parents=True)
    snapshot=directory/'current_source_snapshot.json'
    snapshot.write_text(json.dumps({'schema_version':'research3-capture-source-snapshot/v1'}))
    names={f'profiles/base-r{i:03d}.yaml' for i in range(1,15)}|{'profiles/stress-dev10.yaml'}
    profiles={}
    for name in names:
        (directory/name).write_text('synthetic: true\n')
        profiles[name]=MODULE.digest((directory/name).read_bytes())
    rows=[dict(base_instruction_id=f'base-r{i:03d}',phase='development' if i<=10 else 'validation')
          for i in range(1,15) for _ in range(3)]
    rows.extend(dict(base_instruction_id='base-r010',phase='stress') for _ in range(4))
    plan=dict(schema_version='research3-current-source-recapture-plan/v1',protected_content_read=False,
              human_labels_generated=False,profile_files=profiles,views=rows,
              snapshot_sha256=MODULE.digest(snapshot.read_bytes()))
    (directory/'plan.json').write_text(json.dumps(plan))
    (directory/'human_progress.jsonl').write_text('excluded')
    paths=MODULE.current_capture_plan_paths(tmp_path,directory)
    assert len(paths)==17 and all(path.name!='human_progress.jsonl' for path in paths)
    plan['views'][0]['base_instruction_id']='base-r015'
    (directory/'plan.json').write_text(json.dumps(plan))
    with pytest.raises(ValueError,match='nonprotected'):
        MODULE.current_capture_plan_paths(tmp_path,directory)


def original_qa_packet(tmp_path):
    directory=packet_fixture(tmp_path)
    qa_path=tmp_path/'reports/explicit_qa.jsonl';qa_path.parent.mkdir()
    binding={key:'a'*64 for key in ('task_sha256','frame_sha256','request_sha256','provider_tasks_sha256')}
    row=dict(binding,schema_version='research3-machine-visual-qa/v1',run_id='run',observation_id='obs',
             attested_by='synthetic-only',correct=None,human_labels_generated=False)
    qa_path.write_text(json.dumps(row)+'\n')
    item=dict(binding,run_id='run',observation_id='obs',map_id='r3geo_base_r010',partition='development',
              correct=None,human_reviewer_id='')
    (directory/'inventory.json').write_text(json.dumps({'protected_data_used':False,'items':[item]}))
    (directory/'combined_visual_qa.jsonl').write_bytes(qa_path.read_bytes())
    manifest=json.loads((directory/'packet_manifest.json').read_text())
    for name in manifest['files']:manifest['files'][name]=MODULE.digest((directory/name).read_bytes())
    manifest['qa_inputs']=[{'path':str(qa_path),'sha256':MODULE.digest(qa_path.read_bytes()),'rows':1}]
    (directory/'packet_manifest.json').write_text(json.dumps(manifest))
    return directory,qa_path,row,manifest


def test_raw_individually_bound_qa_inputs_are_retained(tmp_path):
    directory,path,_,_=original_qa_packet(tmp_path)
    (path.parent/'unreferenced_qa.jsonl').write_text('not included')
    paths,record=MODULE.review_packet_paths(tmp_path,directory)
    assert len(paths)==5 and path in paths
    assert record['original_qa_inputs'][0]['sha256']==MODULE.digest(path.read_bytes())


@pytest.mark.parametrize('change',['tamper','label','binding','schema','duplicate'])
def test_original_qa_validation_fails_closed(tmp_path,change):
    directory,path,row,manifest=original_qa_packet(tmp_path)
    if change=='duplicate':manifest['qa_inputs']*=2
    else:
        if change=='label':row['correct']=False
        elif change=='binding':row['frame_sha256']='b'*64
        elif change=='schema':row['schema_version']='human-review/v1'
        else:row['inspection_note']='changed bytes'
        path.write_text(json.dumps(row)+'\n')
        if change!='tamper':manifest['qa_inputs'][0]['sha256']=MODULE.digest(path.read_bytes())
    (directory/'packet_manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError):MODULE.review_packet_paths(tmp_path,directory)


def test_capture_source_audit_scope_comes_from_explicit_runs(tmp_path):
    run=make_run(tmp_path);_,records=MODULE.run_paths(tmp_path,[run])
    audit=tmp_path/'reports/current_capture_source_audit_20260911_v1.json'
    report=dict(schema_version='research3-current-capture-source-audit/v1',human_labels_generated=False,
                qa_attestations_generated=False,rows=[dict(run_id='explicit-run',status='blocked',
                gaps=['synthetic_missing_checkpoint'],request_sha256=records[0]['request_sha256'])])
    audit.write_text(json.dumps(report))
    assert MODULE.engineering_evidence_paths(tmp_path,[audit],records)[0]==[audit]
    with pytest.raises(ValueError,match='explicit nonprotected'):
        MODULE.engineering_evidence_paths(tmp_path,[audit],[])
    report['rows'][0]['request_sha256']='0'*64;audit.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='binding'):
        MODULE.engineering_evidence_paths(tmp_path,[audit],records)


def test_draft_joint_policy_is_retained_without_approval_inference(tmp_path,monkeypatch):
    path=tmp_path/'policy.json'
    path.write_text(json.dumps(dict(schema_version='research3-joint-review-policy/v1',
        status='draft',protected_data_used=False,pose_rule=None)))
    monkeypatch.setattr(MODULE,'standard_paths',lambda root:[])
    files,manifest=MODULE.collect(tmp_path,review_policy=path)
    assert set(files)=={'policy.json'}
    assert manifest['joint_review']['policy']['declared_status']=='draft'
    assert not manifest['joint_review']['policy']['approval_inferred_by_packager']
    path.write_text(json.dumps(dict(schema_version='research3-joint-review-policy/v1',
        status='draft',protected_data_used=False,dimension_verdicts={})))
    with pytest.raises(ValueError,match='unlabelled'):
        MODULE.collect(tmp_path,review_policy=path)


def test_joint_reference_evidence_is_bound_and_retains_gaps(tmp_path):
    directory=packet_fixture(tmp_path)
    inventory={'protected_data_used':False,'runs':[],'items':[dict(status='ready_for_human_review',
        run_id='synthetic-run',observation_id='synthetic-obs',frame_sha256='f'*64,task_sha256='a'*64)]}
    (directory/'inventory.json').write_text(json.dumps(inventory))
    ref={'directory':str(directory.relative_to(tmp_path))}
    path=tmp_path/'evidence.json'
    item=dict(run_id='synthetic-run',observation_id='synthetic-obs',frame_sha256='f'*64,
              task_sha256='a'*64,evidence_complete=False,gaps=['synthetic_missing_reference'])
    evidence=dict(schema_version='research3-joint-review-evidence/v1',protected_data_used=False,
        human_labels_generated=False,inventory_sha256=MODULE.digest((directory/'inventory.json').read_bytes()),items=[item])
    path.write_text(json.dumps(evidence))
    paths,refs=MODULE.joint_review_paths(tmp_path,evidence=path,packet_reference=ref)
    assert paths==[path] and refs['evidence']['sha256']==MODULE.digest(path.read_bytes())
    item['correct']=False;path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError,match='label'):
        MODULE.joint_review_paths(tmp_path,evidence=path,packet_reference=ref)
    evidence['inventory_sha256']='0'*64;path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError,match='binding'):
        MODULE.joint_review_paths(tmp_path,evidence=path,packet_reference=ref)
