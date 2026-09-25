"""Reconstruct context pairing and evaluate reference distances after inference."""
import json
from collections import Counter
import yaml
from integrate_object_depth_candidate import ROOT,sha,write
from entrance_context_candidate import contextual_candidates
from candidate_instance_association import associate


def main():
    root=ROOT/'reports/entrance_context_candidate_20260924_v1'
    plan=json.loads((root/'plan.json').read_bytes());report=json.loads((root/'report.json').read_bytes())
    for p,d in plan['input_sha256'].items():
        if sha(p)!=d:raise ValueError('pin changed')
    if report['journal_sha256']!=sha(root/'results.jsonl') or report['plan_sha256']!=sha(root/'plan.json'):raise ValueError('report binding')
    ground=ROOT/'reports/grounding_candidate_20260923_v3'
    predictions={r['source_index']:r for r in map(json.loads,(ground/'results.jsonl').read_text().splitlines())}
    portal=ROOT/'reports/portal_depth_candidate_20260923_v1'
    portal_plan=json.loads((portal/'plan.json').read_bytes())
    for p,d in portal_plan['input_sha256'].items():
        if sha(p)!=d:raise ValueError('portal input changed')
    surfaces={r['source_index']:r for r in json.loads((portal/'results.json').read_bytes())['rows']}
    rows=[json.loads(s) for s in (root/'results.jsonl').read_text().splitlines()]
    evaluated=[];counts=Counter();within=Counter();pins={}
    for slot,row in zip(plan['slots'],rows,strict=True):
        index=slot['source_index']
        if index!=row['source_index']:raise ValueError('order')
        if slot['status']!='ready':continue
        doors=[b for b in predictions[index]['boxes'] if b['visual_category']=='doorway']
        if contextual_candidates(doors,row['texts'])!=row['doorway_candidates']:raise ValueError('pairing does not reconstruct')
        frame=ROOT/slot['frame'];scene_path=frame.parent.parent/'runtime_scene.yaml';pins[str(scene_path)]=sha(scene_path)
        scene=yaml.safe_load(scene_path.read_bytes())
        refs=[dict(entity_id=e['entity_id'],category=e['category'],x=e['pose']['x'],y=e['pose']['y']) for e in scene['entities']]
        door_surfaces=[b for b in surfaces[index]['boxes'] if b['prediction']['visual_category']=='doorway']
        if len(door_surfaces)!=len(doors):raise ValueError('surface order')
        for c in row['doorway_candidates']:
            if c['status']!='context_candidate':counts[c['status']]+=1;continue
            surf=door_surfaces[c['doorway_index']]['surface'];category=c['context'][0]['visual_category']
            association=None
            if surf['map_pose'] is not None:
                association=associate(dict(object_localized=True,map_pose=surf['map_pose'],visual_category=category,entity_id=None),refs)
                if any(v['reference_distance_m']<=.35 for v in association['candidates']):within[category]+=1
            status=surf['status'] if association is None else association['status'];counts[status]+=1
            evaluated.append(dict(source_index=index,context=c,surface=surf,association=association,status=status,
                                  human_verdict=None,calibration_eligible=False))
    for p in (root/'plan.json',root/'results.jsonl',portal/'plan.json',portal/'results.json',ground/'results.jsonl',ROOT/'scripts/audit_entrance_context_candidate.py'):
        pins[str(p)]=sha(p)
    write(root/'audit.json',dict(pairing_reconstruction_passed=True,slots=len(rows),evaluated_contexts=evaluated,
        status_counts=counts,within_radius_candidate_counts=within,input_sha256=pins,
        human_labels_generated=False,calibration_eligible=False,
        transform_limit='historical commanded stationary rendering model; fresh live check does not certify historical frames'))
    print(json.dumps(dict(status_counts=counts,within_radius=within),indent=2))


if __name__=='__main__':main()
