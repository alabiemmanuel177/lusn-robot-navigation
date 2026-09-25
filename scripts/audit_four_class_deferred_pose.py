"""Independent replay of every retained context frame, including unavailable truth."""
import json
from pathlib import Path
from collections import Counter
import numpy as np
from integrate_object_depth_candidate import ROOT,sha,write
from bound_pose_observer import matrix
from candidate_rendering_transform import correction
from candidate_pose_validation import compare_transforms


def stamp(header):
    return header['stamp']['sec']*10**9+header['stamp']['nanosec']


def main():
    root=ROOT/'reports/four_class_deferred_capture_20260924_v1'
    schedule=json.loads((root/'schedule.json').read_bytes());summaries=[];pins={str(root/'schedule.json'):sha(root/'schedule.json')}
    for i,view in enumerate(schedule['views']):
        run=root/f"view-{i:02}-{view['category']}";plan=json.loads((run/'plan.json').read_bytes())
        for p,d in plan['input_sha256'].items():
            if sha(p)!=d:raise ValueError('launch source changed: '+p)
        pins[str(run/'plan.json')]=sha(run/'plan.json')
        if not (run/'execution.json').exists():raise ValueError('execution not complete')
        truth={}
        for raw in (run/'truth.jsonl').read_text().splitlines():
            msg=json.loads(raw)
            if msg['header']['frame_id']!='default':raise ValueError('unexpected world frame')
            s=stamp(msg['header'])
            if s in truth and truth[s]!=msg:raise ValueError('conflicting simulator truth')
            truth[s]=msg
        pins[str(run/'truth.jsonl')]=sha(run/'truth.jsonl');rows=[];counts=Counter()
        frames=sorted((run/'episode/context_capture').glob('frame-*.json'))
        for frame in frames:
            pins[str(frame)]=sha(frame);meta=json.loads(frame.read_bytes());s=meta['rgb_stamp_ns']
            for kind in ('rgb','depth'):
                media=frame.parent/meta[kind]['file']
                if media.resolve().parent!=frame.parent.resolve() or sha(media)!=meta[kind]['sha256']:raise ValueError('media integrity')
                pins[str(media)]=sha(media)
            row=dict(frame=str(frame),stamp_ns=s,status='missing_exact_truth')
            if meta['depth_stamp_ns']!=s:row['status']='rgb_depth_not_exact'
            elif not meta['camera_to_map']:row['status']='missing_localization_tf'
            elif s in truth:
                tf=meta['camera_to_map']
                if stamp(tf['header'])!=s or tf['header']['frame_id']!='map' or tf['child_frame_id']!=meta['rgb']['frame_id']:
                    raise ValueError('transform timestamp/frame mismatch')
                t=tf['transform']['translation'];q=tf['transform']['rotation']
                nominal=matrix([t[k] for k in ('x','y','z')],[q[k] for k in ('x','y','z','w')])
                corrected=correction(nominal,plan['nominal_mount'],plan['rendered_mount'])
                gt=truth[s]['pose'];p=gt['position'];q=gt['orientation']
                actual=matrix([p[k] for k in ('x','y','z')],[q[k] for k in ('x','y','z','w')])@np.asarray(plan['rendered_mount'])
                row.update(status='compared',comparison=compare_transforms(corrected,actual,estimate_stamp_ns=s,truth_stamp_ns=s,
                    truth_source='simulator_world_pose',descriptions_bound=True))
            counts[row['status']]+=1;rows.append(row)
        comparisons=[r['comparison'] for r in rows if r['status']=='compared']
        summaries.append(dict(view=view['category'],retained_frames=len(frames),status_counts=counts,rows=rows,
            passes=sum(c['engineering_screen_pass'] for c in comparisons),
            maximum_translation_error_m=max((c['translation_error_m'] for c in comparisons),default=None),
            maximum_rotation_error_rad=max((c['rotation_error_rad'] for c in comparisons),default=None)))
    pins[str(Path(__file__).resolve())]=sha(__file__)
    write(root/'independent_audit.json',dict(views=summaries,input_sha256=pins,
        all_views_have_exact_rgbd_pose_support=all(v['status_counts'].get('compared',0)>0 for v in summaries),
        all_measured_comparisons_pass=all(v['passes']==v['status_counts'].get('compared',0) for v in summaries),
        scope='stationary development views only; not historical or dynamic pose certification',
        calibration_eligible=False,human_labels_generated=False))
    print(json.dumps([{k:v for k,v in s.items() if k!='rows'} for s in summaries],indent=2))


if __name__=='__main__':main()
