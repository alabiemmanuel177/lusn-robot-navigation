"""Create-once, hash-bound engineering handoff; never grants scientific admission."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from integrate_object_depth_candidate import ROOT,sha,write
from snapshot_expansion_instrumentation import validate


def main():
    out=ROOT/'reports/four_class_perception_readiness_20260924_v1';pins={};panels={}
    for panel in ('readiness','broad','live','repeated'):
        root=ROOT/f'reports/four_class_{panel}_integration_20260924_v3'
        plan=json.loads((root/'plan.json').read_bytes());result=json.loads((root/'results.json').read_bytes());audit=json.loads((root/'audit.json').read_bytes())
        for p,d in plan['input_sha256'].items():
            if sha(p)!=d:raise ValueError('evidence source changed: '+p)
        for p,d in audit['input_sha256'].items():
            if sha(p)!=d:raise ValueError('audited evidence changed: '+p)
        if not audit['runtime_replay_passed'] or not audit['independent_association_arithmetic_passed']:raise ValueError('audit failed')
        for p in (root/'plan.json',root/'results.json',root/'audit.json'):pins[str(p.relative_to(ROOT))]=sha(p)
        panels[panel]=dict(status_counts=result['status_counts'],integrated_frames=audit['replayed_frames'],hypotheses=audit['hypotheses'],
            support=result['supporting_frames_by_map_class'],repeated=audit['same_frame_two_distinct_in_radius_instances'])
    if len(panels['broad']['support'])!=10 or any(v[c]<1 for v in panels['broad']['support'].values() for c in ('chair','doorway','laboratory_entrance','office_entrance')):
        raise ValueError('40 map/class geometry gates not met')
    if any(sum(v[c] for v in panels['live']['support'].values())<1 for c in ('chair','doorway','laboratory_entrance','office_entrance')):
        raise ValueError('fresh support missing')
    if any(panels['repeated']['repeated'].get(c,0)<1 for c in ('laboratory_entrance','office_entrance')):raise ValueError('repeated entrance check missing')
    capture=ROOT/'reports/four_class_deferred_capture_20260924_v1/view-00-chair'
    frames=sorted((capture/'episode/context_capture').glob('frame-*.json'))
    if len(frames)!=20:raise ValueError('deferred capture incomplete')
    for p in frames:
        meta=json.loads(p.read_bytes());tf=meta['camera_to_map']
        if not tf:raise ValueError('deferred TF missing')
        s=tf['header']['stamp'];s=s['sec']*10**9+s['nanosec']
        if s!=meta['rgb_stamp_ns'] or s!=meta['depth_stamp_ns']:raise ValueError('exact timestamp required')
        pins[str(p.relative_to(ROOT))]=sha(p)
    truth_audit=ROOT/'reports/four_class_deferred_capture_20260924_v1/independent_audit.json'
    ta=json.loads(truth_audit.read_bytes())
    if not ta['all_views_have_exact_rgbd_pose_support'] or not ta['all_measured_comparisons_pass']:raise ValueError('truth audit')
    for p,d in ta['input_sha256'].items():
        if sha(p)!=d:raise ValueError('truth source changed')
    freeze=validate(ROOT/'reports/expansion_instrumentation_snapshot_20260922_v8/snapshot.json')
    if freeze!='6b7bc9e5dd4f5289af88ee4524db3544d277eeeb6a0685177b12c128ef6fb49a':raise ValueError('frozen v8 changed')
    regression=ROOT/'reports/four_class_readiness_regression_20260924_v3.xml'
    suite=ET.parse(regression).getroot().find('testsuite').attrib
    if int(suite['failures']) or int(suite['errors']):raise ValueError('regression failure')
    sources=['four_class_candidate_runtime_v3.py','four_class_perception_candidate_v3.py','four_class_perception_candidate.py',
        'chair_foreground_band_candidate.py','candidate_depth_support.py','candidate_portal_depth.py','candidate_instance_association.py',
        'candidate_rendering_transform.py','entrance_context_candidate.py','readable_sign_reference_candidate.py',
        'deferred_physical_capture_candidate.py','fixed_frame_delay.py']
    for p in [ROOT/'scripts'/name for name in sources]+[Path(__file__),regression,truth_audit,
        ROOT/'reports/world_specific_method_approval_20260924.json',ROOT/'reports/four_class_world_template_audit_20260924_v1.json',
        ROOT/'docs/FOUR_CLASS_PERCEPTION_READINESS_20260924.md',ROOT/'docs/FOUR_CLASS_READINESS_PROTOCOL_20260924.md']:
        pins[str(p.resolve().relative_to(ROOT))]=sha(p)
    out.mkdir(exist_ok=False)
    write(out/'manifest.json',dict(schema_version='research3-four-class-engineering-readiness/v1',created_at=datetime.now(timezone.utc).isoformat(),
        engineering_readiness_passed=True,ready_for_next_reviewed_protocol_preparation=True,
        candidate_version='four-class-v3-supported-depth-band',panels=panels,
        deferred_capture_exact_tf_frames=20,frozen_v8_sha256=freeze,
        tests_passed=int(suite['tests'])-int(suite['skipped']),tests_skipped=int(suite['skipped']),input_sha256=pins,
        human_identity_accuracy_verified=False,repeated_chair_live_validation=False,repeated_doorway_live_pass=False,
        calibrated_runtime_admitted=False,calibration_coverage_certified=False,
        primary_collection_authorized_by_this_manifest=False,protected_access_authorized=False,
        validation_labels_accessed=False,external_publication_performed=False))
    print(out/'manifest.json')


if __name__=='__main__':main()
