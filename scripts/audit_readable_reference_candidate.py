"""Recompute every text localization and reference conversion from pinned RGB-D."""
import json
from pathlib import Path
import numpy as np
import yaml
from integrate_object_depth_candidate import ROOT,sha,write,decode_depth
from candidate_depth_support import estimate
from readable_sign_reference_candidate import reference_from_text
from candidate_instance_association import associate
from expansion_camera_model import rendering_camera


def main():
    root=ROOT/'reports/readable_reference_candidate_20260924_v1'
    plan=json.loads((root/'plan.json').read_bytes());result=json.loads((root/'results.json').read_bytes())
    for p,d in plan['input_sha256'].items():
        if sha(p)!=d:raise ValueError('input changed')
    if sha(root/'plan.json')!=result['plan_sha256']:raise ValueError('plan binding')
    distances=[];n=0
    for slot,row in zip(plan['slots'],result['rows'],strict=True):
        if slot['source_index']!=row['source_index']:raise ValueError('order')
        if slot['status']!='ready':continue
        frame=ROOT/slot['frame'];meta=json.loads(frame.read_bytes());req=json.loads((frame.parent.parent/'request.json').read_bytes())
        depth=decode_depth((frame.parent/meta['depth']['file']).read_bytes(),meta['depth'])
        centre,rotation=rendering_camera(req['capture_pose']);t=np.eye(4);t[:3,:3]=rotation;t[:3,3]=centre
        scene=yaml.safe_load((frame.parent.parent/'runtime_scene.yaml').read_bytes())
        refs=[dict(entity_id=e['entity_id'],category=e['category'],x=e['pose']['x'],y=e['pose']['y']) for e in scene['entities']]
        for obs in row['observations']:
            quad=np.asarray(obs['text']['quad']);box=[*quad.min(axis=0),*quad.max(axis=0)]
            surface=estimate(depth,box,np.asarray(meta['camera_info']['k']).reshape(3,3),t)
            if surface!=obs['surface']:raise ValueError('surface replay')
            if obs.get('converted'):
                converted=reference_from_text(surface['map_pose'],[req['capture_pose']['x'],req['capture_pose']['y']],template=plan['template'])
                if converted!=obs['converted']:raise ValueError('reference replay')
                association=associate(dict(object_localized=True,visual_category=obs['visual_category'],map_pose=converted['map_pose'],entity_id=None),refs)
                if association!=obs['association']:raise ValueError('association replay')
                distances.extend(c['reference_distance_m'] for c in association['candidates'])
            n+=1
    write(root/'audit.json',dict(all_inputs_unchanged=True,all_localizations_reconstruct=True,
        observations=n,minimum_reference_distance_m=min(distances),maximum_reference_distance_m=max(distances),
        plan_sha256=sha(root/'plan.json'),results_sha256=sha(root/'results.json'),audit_source_sha256=sha(__file__),
        uses_authored_reference_prior=True,identity_or_calibration_certified=False))
    print(n,min(distances),max(distances))


if __name__=='__main__':main()
