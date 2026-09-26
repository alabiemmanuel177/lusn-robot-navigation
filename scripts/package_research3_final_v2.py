"""Create-once corrected closure bundle, preserving historical v1 evidence."""
import json
from pathlib import Path
import zipfile
from prepare_joint_score_protocol import ROOT,sha
from joint_score_collection import write_once


def main():
    old=json.loads((ROOT/'reports/research3_final_closure_20260926_v1/manifest.json').read_text())
    paths={ROOT/r['path'] for r in old['files'] if 'research3_final_closure_20260926_v1/' not in r['path']}
    paths.update(ROOT/p for p in [
        'reports/research3_closure_interpretation_20260926.json',
        'reports/wave-s-review-return.json',
        'reports/joint_score_protocol_20260924_v1/review_decision_CONVERSATION_FINAL.json',
        'reports/joint_score_protocol_20260924_v1/schedule.json',
        'reports/joint_score_wave_s_primary_inference_20260924_v1/evidence.json',
        'reports/joint_score_wave_s_primary_inference_20260924_v1/detector/audit.json',
        'reports/joint_score_wave_s_primary_inference_20260924_v1/detector/report.json',
        'reports/joint_score_wave_s_primary_inference_20260924_v1/ocr/report.json',
        'reports/joint_score_wave_s_supervisor_20260924_v1/complete.json',
        'reports/joint_score_wave_s_gazebo_preflight_20260924_v2/capture_audit.json',
        'reports/joint_score_wave_s_assets_20260924_v3/static_clearance_audit.json',
        'reports/joint_score_wave_s_execution_20260924_v1/execution_manifest.json',
        'reports/joint_score_wave_s_execution_20260924_v1/execution_approval.json',
        'reports/research3_closure_regression_20260926.xml',
        'scripts/package_research3_final_v2.py'])
    for source in ['reports/hybrid_score_candidate_20260925_v1/candidate.json',
                   'reports/joint_score_wave_s_execution_20260924_v1/execution_manifest.json']:
        m=json.loads((ROOT/source).read_text())
        for p,h in m['input_sha256'].items():
            if sha(p)!=h:raise ValueError('source changed: '+p)
    root=ROOT/'reports/research3_final_closure_20260926_v2';root.mkdir(exist_ok=False)
    manifest=dict(schema_version='research3-descriptive-final-archive/v2',
        status='closed_descriptive_exploratory',runtime_calibration_validated=False,
        wave_c_v_cancelled=True,entrypoint='docs/RESEARCH3_RESULTS.md',
        scope='Final reports, human return, full Wave S evidence ledger, key audit and authority records. Raw binary captures/model dependencies remain in the original workspace, referenced by hashes; this is not a self-contained simulator distribution.',
        files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)])
    write_once(root/'manifest.json',manifest)
    archive=root.with_suffix('.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(paths):z.write(p,str(p.relative_to(ROOT)))
        z.writestr('manifest.json',json.dumps(manifest,indent=2))
    import hashlib
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for r in manifest['files']:assert hashlib.sha256(z.read(r['path'])).hexdigest()==r['sha256']
    receipt=dict(archive=str(archive.relative_to(ROOT)),sha256=sha(archive),files=len(paths),verified=True)
    write_once(root/'verification.json',receipt);print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
