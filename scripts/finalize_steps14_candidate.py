"""Audit bounded diagnostics and emit an explicitly non-executable gate record."""
import json
import xml.etree.ElementTree as ET
import numpy as np
from research3_steps14_feasibility import OUT, checked_plan
from integrate_object_depth_candidate import ROOT, sha, write
from candidate_rendering_transform import correction, described_mounts, rigid
from expansion_camera_model import rendering_camera
from audit_object_localization_candidate import reconstruct


def quaternion_rotation(q):
    x,y,z,w=[float(q[k]) for k in ('x','y','z','w')]
    if abs(x*x+y*y+z*z+w*w-1)>1e-6: raise ValueError('unit quaternion required')
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def main():
    plan=checked_plan()
    urdf=__import__('pathlib').Path('/opt/ros/jazzy/share/nav2_minimal_tb3_sim/urdf/turtlebot3_waffle.urdf')
    root=ET.parse(urdf).getroot()
    expected={'base_joint':([0,0,.01],[0,0,0]),'camera_joint':([.064,-.065,.094],[0,0,0]),
              'camera_depth_joint':([.005,.028,.013],[-1.57,0,-1.57])}
    for name,(xyz,rpy) in expected.items():
        origin=root.find(f"joint[@name='{name}']/origin")
        if origin is None or not np.allclose([float(v) for v in origin.get('xyz').split()],xyz) or not np.allclose([float(v) for v in origin.get('rpy','0 0 0').split()],rpy):
            raise ValueError('inspected mount description changed')
    nominal,rendered=described_mounts(); transform_rows=[]; box_count=0
    rows=[json.loads(s) for s in (OUT/'short_prompt_results.jsonl').read_text().splitlines()]
    names=list(plan['prompts'])
    for slot,row in zip(plan['slots'],rows,strict=True):
        if slot['source_index']!=row['source_index']:raise ValueError('source ordering')
        if slot['status']!='ready':
            if row != dict(slot,boxes=[]):raise ValueError('failure retained')
            continue
        frame=ROOT/slot['frame'];meta=json.loads(frame.read_bytes())
        t=meta['camera_to_map']['transform']
        actual=correction(rigid(quaternion_rotation(t['rotation']),[t['translation'][k] for k in 'xyz']),nominal,rendered)
        req=json.loads((frame.parent.parent/'request.json').read_bytes())
        centre,rotation=rendering_camera(req['capture_pose'])
        transform_rows.append(dict(source_index=slot['source_index'],corrected_transform=actual.tolist(),
            command_translation_difference_m=float(np.linalg.norm(actual[:3,3]-centre)),
            command_rotation_matrix_max_difference=float(np.max(np.abs(actual[:3,:3]-rotation)))))
        path=OUT/row['raw_arrays']
        if sha(path)!=row['sha256']:raise ValueError('raw checksum')
        with np.load(path,allow_pickle=False) as raw:
            labels,scores,boxes=reconstruct(raw['logits'],raw['pred_boxes'],meta['rgb']['width'],meta['rgb']['height'],.1)
        for label,score,box,saved in zip(labels,scores,boxes,row['boxes'],strict=True):
            if names[int(label)]!=saved['query'] or abs(score-saved['score'])>1e-6 or not np.allclose(box,saved['xyxy'],atol=1e-3,rtol=0):
                raise ValueError('box reconstruction')
        box_count+=len(labels)
    write(OUT/'transform_candidate_audit.json',dict(rows=transform_rows,
        current_urdf_path=str(urdf),current_urdf_sha256=sha(urdf),
        historical_urdf_bytes_bound_at_capture=False,
        source_sha256={str(p):sha(p) for p in (ROOT/'scripts/candidate_rendering_transform.py',ROOT/'scripts/expansion_camera_model.py',__import__('pathlib').Path(__file__))},
        static_correction_implemented=True,actual_pose_ground_truth_validated=False,
        max_command_translation_difference_m=max(r['command_translation_difference_m'] for r in transform_rows),
        max_command_rotation_matrix_difference=max(r['command_rotation_matrix_max_difference'] for r in transform_rows)))
    write(OUT/'independent_audit.json',dict(all_short_prompt_boxes_reconstructed=True,box_count=box_count,
        fixed_slots_retained=len(rows),source_sha256=sha(__file__),plan_sha256=sha(OUT/'plan.json'),
        journal_sha256=sha(OUT/'short_prompt_results.jsonl'),validation_data_used=False))
    write(OUT/'primary_protocol_gate.json',dict(schema_version='research3-primary-redesign-readiness/v1',
        execution_allowed=False,scientific_freeze=False,primary_attempts_authorized=0,
        blockers=['independent_transform_and_reference_point_accuracy_not_established',
                  'four_class_joint_detector_feasibility_not_established',
                  'joint_confidence_contract_and_calibration_compatibility_not_established',
                  'exact_revised_primary_distribution_and_schedule_not_approved'],
        coverage_floors_unchanged=True,validation_release_allowed=False,
        evidence_sha256={name:sha(OUT/name) for name in ('plan.json','camera.json','detector_score_audit.json','transform_candidate_audit.json','independent_audit.json')},
        protocol_document_sha256=sha(ROOT/'docs/REVISED_PRIMARY_PROTOCOL_DRAFT_20260923.md')))
    print(json.dumps(dict(audit_passed=True,boxes=box_count,scientific_freeze=False)))


if __name__=='__main__':main()
