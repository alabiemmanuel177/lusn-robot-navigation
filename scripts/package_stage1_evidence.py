"""Create a bounded, verified engineering evidence ZIP; never a scientific release."""
import hashlib
import json
from pathlib import Path
import zipfile
from run_stage1_feasibility import ROOT,assignments,sha,write
from audit_stage1_evidence import audit

DESTINATION=ROOT/'reports/research3_stage1_evidence_20260922_v2.zip'


def build():
    audit_result=audit()
    if not audit_result['passed']:raise ValueError('evidence audit failed')
    files=set()
    def add(path):
        path=Path(path)
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise ValueError('unsafe or missing bundle input: '+str(path))
        files.add(path)
    for target in assignments():
        folder=ROOT/'reports/physical_live_episodes'/target['candidate_id']
        for path in folder.rglob('*'):
            if path.is_file() or path.is_symlink():add(path)
    names=[
        'docs/STAGE1_FEASIBILITY_RESULTS_20260922.md','docs/RESEARCH3_BLOCKER_LEDGER_20260922.md',
        'docs/STAGE1_EVIDENCE_PACKAGE_README_20260922.md','docs/COMPLETION_DESIGN_SENSITIVITY_20260922.md',
        'docs/RESEARCH3_COMPLETION_GATES_20260922.md','docs/STAGE1_BOUNDED_PREFLIGHT_20260921.md',
        'docs/RESOURCE_GUARD_REPAIR_APPROVAL_20260922.md','docs/STAGE1_RESUME_36_20260922.md',
        'docs/CALIBRATION_RECOVERY_PROPOSAL_20260921.md',
        'reports/stage1_view_feasibility_20260921_v3.json',
        'reports/stage1_feasibility_authorization_20260921_v1.json',
        'reports/resource_guard_repair_approval_20260922.json','reports/stage1_resume36_approval_20260922.json',
        'reports/stage1_evidence_audit_20260922_v1.json','reports/stage1_design_score_support_20260922_v1.json',
        'reports/expansion_instrumentation_snapshot_20260914_v7/snapshot.json',
        'reports/expansion_instrumentation_snapshot_20260922_v8/snapshot.json',
        'reports/human_method_decisions_20260912_v1/decision_record.json',
        'reports/human_wrapper_decision_20260912_v1/decision_record.json',
        'reports/human_decisions_20260912_v1/decision_record.json',
        'reports/feasibility_nuisance_20260914_v1.json',
        'reports/completion_design_candidate_20260922_v1/design.json',
        'reports/completion_design_candidate_20260922_v1/readiness.json',
        'scripts/summarize_stage1_four_workers.py','scripts/audit_stage1_evidence.py',
        'scripts/analyze_feasibility_score_support.py','scripts/prepare_completion_design_candidate.py',
        'scripts/package_stage1_evidence.py','scripts/run_stage1_feasibility.py',
        'scripts/verify_stage1_bundle.py','scripts/verify_physical_release.py','scripts/export_stage1_frame_previews.py',
        'scripts/run_stage1_four_workers.py','scripts/resume_stage1_four_workers.py',
        'scripts/resume_stage1_two_workers.py','scripts/inspect_simulator_workloads.py',
        'scripts/snapshot_expansion_instrumentation.py',
        'scripts/expansion_sampling.py','scripts/physical_expansion_capture_candidate.py']
    for name in names:add(ROOT/name)
    for path in (ROOT/'reports/stage1_frame_previews_20260922_v1').iterdir():add(path)
    for seeds in (1,2,4,8):add(ROOT/f'reports/world_paired_power_bound_20260914_seeds{seeds}.json')
    for directory in ('stage1_four_workers_20260922_v1','stage1_four_workers_20260922_v2','stage1_two_workers_20260922_v4'):
        for path in (ROOT/'reports'/directory).iterdir():
            if path.suffix in ('.json','.log'):add(path)
    snapshots=[json.loads((ROOT/name).read_bytes()) for name in names if name.endswith('/snapshot.json')]
    latest=snapshots[-1]
    for name,digest in latest['source_sha256'].items():
        path=ROOT/name
        if sha(path)!=digest:raise ValueError('source no longer matches v8: '+name)
        add(path)
    for number in range(1,11):
        folder=ROOT/f'data/physical_worlds_readable_v1/base-r{number:03}'
        for path in folder.rglob('*'):
            if path.is_file() or path.is_symlink():add(path)
    historical=(ROOT/'src/language_nav/live_resources.py').read_bytes().replace(
        b'except (FileNotFoundError, ProcessLookupError):',b'except FileNotFoundError:')
    expected=snapshots[0]['source_sha256']['src/language_nav/live_resources.py']
    if hashlib.sha256(historical).hexdigest()!=expected:raise ValueError('historical guard reconstruction failed')
    extra={'historical_source/v7/src/language_nav/live_resources.py':historical}
    records=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(files)]
    records += [dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)) for name,raw in extra.items()]
    manifest=dict(schema_version='research3-engineering-evidence-bundle/v1',files=records,
        scientific_release_complete=False,calibration_eligible=False,protected_data_included=False,
        human_labels_generated=False,scope='fixed 80-view development design-feasibility evidence, not a calibration review kit',
        historical_guard_note='v7 guard reconstructed from the single approved change and verified against its original SHA-256',
        external_dependencies_note='R1/R2/ROS runtime not bundled; provider source/build hashes are retained in source snapshots. Not a complete executable environment.',
        audit_counts={k:audit_result[k] for k in ('scheduled','status_counts','completed_capture_integrity_count')})
    with zipfile.ZipFile(DESTINATION,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as archive:
        for path in sorted(files):archive.write(path,str(path.relative_to(ROOT)))
        for name,raw in extra.items():archive.writestr(name,raw)
        archive.writestr('bundle_manifest.json',json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    with zipfile.ZipFile(DESTINATION) as archive:
        if len(archive.namelist())!=len(set(archive.namelist())):raise ValueError('duplicate archive member')
        if set(archive.namelist())!={r['path'] for r in records}|{'bundle_manifest.json'}:raise ValueError('archive inventory differs')
        for row in records:
            raw=archive.read(row['path'])
            if hashlib.sha256(raw).hexdigest()!=row['sha256'] or len(raw)!=row['bytes']:
                raise ValueError('archived member differs: '+row['path'])
    result=dict(archive=str(DESTINATION.relative_to(ROOT)),sha256=sha(DESTINATION),bytes=DESTINATION.stat().st_size,
        verified_members=len(records),integrity_passed=True,scientific_release_complete=False)
    write(ROOT/'reports/stage1_evidence_bundle_verification_20260922_v2.json',result)
    print(json.dumps(result))


if __name__=='__main__':build()
