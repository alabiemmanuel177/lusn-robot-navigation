"""Package completed R3-only prototype sources/results, without large external weights."""
import json
import zipfile
from run_stage1_feasibility import ROOT,sha,write
from verify_stage1_bundle import verify


def main():
    directories=['catalogue_blind_candidate_20260923_v1','object_localization_candidate_20260923_v1']
    paths=set()
    for name in directories:
        folder=ROOT/'reports'/name
        if not json.loads((folder/'audit.json').read_bytes())['integrity_passed']:raise ValueError('complete independent audits required')
        paths.update(p for p in folder.rglob('*') if p.is_file())
    paths.add(ROOT/'reports/owlv2_candidate_assets_20260923_v1.json')
    paths.update(ROOT/'reports/method_decision_20260923_v1'/n for n in ('followup_authorization.json','upload_receipt.json'))
    paths.update(ROOT/'scripts'/n for n in ('catalogue_blind_regions.py','run_catalogue_blind_probe.py','audit_catalogue_blind_probe.py',
        'candidate_instance_association.py','candidate_depth_support.py','prepare_owlv2_candidate.py','run_object_localization_candidate.py',
        'audit_object_localization_candidate.py','package_redesign_candidates_20260923.py'))
    paths.update(ROOT/'tests'/n for n in ('test_catalogue_blind_regions.py','test_candidate_instance_association.py',
        'test_candidate_depth_support.py','test_object_candidate_audit.py'))
    paths.update(ROOT/'docs'/n for n in ('CATALOGUE_BLIND_CANDIDATE_20260923.md','OBJECT_LOCALIZATION_CANDIDATE_20260923.md',
        'CANDIDATE_DEPTH_ASSOCIATION_CONTRACT_20260923.md','REDESIGN_ENGINEERING_RESULTS_20260923.md'))
    manifest=dict(schema_version='research3-engineering-evidence-bundle/v1',
        files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)],
        scientific_release_complete=False,calibration_eligible=False,protected_data_included=False,human_labels_generated=False,
        scope='R3-only offline redesign candidates; not admitted models or calibration data',
        entrypoint='docs/REDESIGN_ENGINEERING_RESULTS_20260923.md',
        runtime_note='Source/results bundle; original Stage A RGB-D and exact pretrained weights are referenced by hash, not duplicated')
    destination=ROOT/'reports/research3_redesign_candidates_20260923_v1.zip'
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(paths):z.write(path,str(path.relative_to(ROOT)))
        z.writestr('bundle_manifest.json',json.dumps(manifest,indent=2,sort_keys=True))
    result=verify(destination,sha(destination));result['archive']=str(destination.relative_to(ROOT))
    write(ROOT/'reports/redesign_candidates_bundle_verification_20260923_v1.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
