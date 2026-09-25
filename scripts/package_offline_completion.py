"""Create an explicit nonprotected preparation supplement with byte verification."""
import importlib.metadata
import json
import platform
import zipfile
from run_stage1_feasibility import ROOT,sha,write
from verify_stage1_bundle import verify

DESTINATION=ROOT/'reports/research3_offline_completion_20260922_v1.zip'


def build():
    if DESTINATION.exists():raise FileExistsError(DESTINATION)
    paths=set()
    def add(path):
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise ValueError('regular contained source/evidence required')
        paths.add(path)
    # Bounded code trees only, never a recursive sweep through research reports.
    for directory in ('scripts','src/language_nav','tests'):
        for path in (ROOT/directory).rglob('*.py'):
            if '__pycache__' not in path.parts:add(path)
    for name in (
        'pyproject.toml',
        'docs/OFFLINE_COMPLETION_HANDOFF_20260922.md',
        'docs/STATUS.md',
        'docs/RESEARCH3_BLOCKER_LEDGER_20260922.md',
        'docs/RESEARCH3_COMPLETION_GATES_20260922.md',
        'docs/STAGE1_FEASIBILITY_RESULTS_20260922.md',
        'docs/CALIBRATION_RECOVERY_PROPOSAL_20260921.md',
        'docs/CALIBRATION_FEASIBILITY_INTERPRETATION_20260922.md',
        'docs/CLASSWISE_RUNTIME_INTEGRATION_CANDIDATE_20260922.md',
        'docs/COMPLETION_DESIGN_SENSITIVITY_20260922.md',
        'docs/CALIBRATION_METHOD_PROPOSAL_20260912.md',
        'docs/STATISTICAL_METHOD_PROPOSAL_20260912.md',
        'memory/2026-09-22-calibration-workflow-admission.md',
        'memory/2026-09-22-ordered-failure-preservation.md',
        'memory/2026-09-22-power-sensitivity-parameterization.md',
        'reports/offline_completion_verification_20260922_v1.json',
        'reports/navigation_feasibility_audit_20260922_v1.json',
        'reports/development_navigation_recomputation_20260922_v1.json',
        'reports/power_numerical_audit_20260922_v1.json',
        'reports/conditional_score_bounds_20260922_v1.json',
        'reports/world_effect_sign_sensitivity_20260922_v1.json',
        'reports/stage1_design_score_support_20260922_v1.json',
        'reports/stage1_evidence_audit_20260922_v1.json',
        'reports/stage1_evidence_bundle_verification_20260922_v2.json',
        'reports/feasibility_nuisance_20260914_v1.json',
        'reports/completion_design_candidate_20260922_v1/design.json',
        'reports/completion_design_candidate_20260922_v1/readiness.json'):
        add(ROOT/name)
    for path in (ROOT/'reports/marginal_power_sensitivity_20260922_v1').glob('*.json'):add(path)
    versions={name:importlib.metadata.version(name) for name in ('numpy','scipy','PyYAML','pytest','cryptography','Pillow')}
    environment=json.dumps(dict(python=platform.python_version(),packages=versions,
        scope='versions used for offline checks; not a complete environment lock or ROS runtime'),indent=2).encode()
    import hashlib
    records=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)]
    records.append(dict(path='offline_environment.json',sha256=hashlib.sha256(environment).hexdigest(),bytes=len(environment)))
    manifest=dict(schema_version='research3-engineering-evidence-bundle/v1',files=records,
        scientific_release_complete=False,calibration_eligible=False,protected_data_included=False,
        human_labels_generated=False,scope='offline preparation supplement; no runtime activation or approvals',
        required_large_evidence_archive_sha256='5bf0c2a4c76948441e0dffb8489ee64cff42d808f6e880fe68c793fa93147c70')
    with zipfile.ZipFile(DESTINATION,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(paths):archive.write(path,str(path.relative_to(ROOT)))
        archive.writestr('offline_environment.json',environment)
        archive.writestr('bundle_manifest.json',json.dumps(manifest,indent=2,sort_keys=True))
    result=verify(DESTINATION,sha(DESTINATION))
    result.update(archive=str(DESTINATION.relative_to(ROOT)),bytes=DESTINATION.stat().st_size)
    write(ROOT/'reports/offline_completion_bundle_verification_20260922_v1.json',result)
    print(json.dumps(result))


if __name__=='__main__':build()
