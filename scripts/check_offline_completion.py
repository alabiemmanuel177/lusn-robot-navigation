"""Record fresh regression/integrity evidence without claiming scientific closure."""
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys

from run_stage1_feasibility import ROOT,sha,write
from snapshot_expansion_instrumentation import validate
from fit_expansion_calibration import development_model_ready
from check_physical_design_readiness import check
from verify_stage1_bundle import verify


def main():
    output=ROOT/'reports/offline_completion_verification_20260922_v1.json'
    if output.exists():raise FileExistsError(output)
    snapshot=ROOT/'reports/expansion_instrumentation_snapshot_20260922_v8/snapshot.json'
    validate(snapshot)
    model_path=ROOT/'reports/expansion_development_calibration_candidate_20260914_v1/development_calibration_candidate.json'
    model=json.loads(model_path.read_bytes())
    design_path=ROOT/'reports/completion_design_candidate_20260922_v1/design.json'
    design=json.loads(design_path.read_bytes())
    environment=dict(os.environ,PYTHONPATH='src:scripts',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    command=[sys.executable,'-m','pytest','tests','-o','addopts=','-q']
    process=subprocess.run(command,cwd=ROOT,env=environment,capture_output=True,text=True,timeout=300)
    diff=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True,timeout=30)
    sources={str(p.relative_to(ROOT)):sha(p) for base in ('src','scripts','tests','ros_ws/src')
             for p in (ROOT/base).rglob('*.py') if '__pycache__' not in p.parts and not p.is_symlink()}
    artifact_paths=[
        'reports/stage1_evidence_audit_20260922_v1.json',
        'reports/stage1_design_score_support_20260922_v1.json',
        'reports/navigation_feasibility_audit_20260922_v1.json',
        'reports/development_navigation_recomputation_20260922_v1.json',
        'reports/power_numerical_audit_20260922_v1.json',
        'reports/conditional_score_bounds_20260922_v1.json']
    result=dict(schema_version='research3-offline-completion-verification/v1',
        written_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        tests=dict(command=command,returncode=process.returncode,stdout=process.stdout,stderr=process.stderr),
        git_diff_check=dict(returncode=diff.returncode,stdout=diff.stdout,stderr=diff.stderr),
        capture_snapshot_unchanged=True,capture_snapshot_sha256=sha(snapshot),
        archive_verification=verify(ROOT/'reports/research3_stage1_evidence_20260922_v2.zip',
            '5bf0c2a4c76948441e0dffb8489ee64cff42d808f6e880fe68c793fa93147c70'),
        development_model_sha256=sha(model_path),development_model_numerically_eligible=development_model_ready(model),
        development_coverage=model['coverage'],design_sha256=sha(design_path),design_readiness=check(design),
        artifact_sha256={name:sha(ROOT/name) for name in artifact_paths},source_sha256=sources,
        scientific_research_complete=False,protected_outcomes_read=False,human_approvals_generated=False,
        live_execution_performed=False,
        scope='fresh offline regression, fixed artifact integrity and current failed prerequisite evidence; not exhaustive scientific completion')
    write(output,result)
    print(process.stdout)
    print(json.dumps({k:result[k] for k in ('capture_snapshot_unchanged','development_model_numerically_eligible','scientific_research_complete')}))
    if process.returncode or diff.returncode:raise SystemExit(1)


if __name__=='__main__':main()
