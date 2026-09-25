"""Independent completed-panel checks; never correctness labels or certification."""
from collections import Counter
import json
from pathlib import Path
from run_stage1_feasibility import ROOT,sha,write
from run_redesign_stage_a import assignments,validate_pins,validate_row,OUTPUT,SNAPSHOT,EXPECTED
from resume_stage1_two_workers import audit_capture


def require(value,message):
    if not value:raise ValueError(message)


def check_request(request,row):
    require(request['run_id']==row['candidate_id'],'identity')
    require(request['partition']=='development' and request['protected_test_routes_used'] is False,'scope')
    require(request['capture_only'] and request['capture_frame_budget']==1,'stationary single frame')
    require(request['simulation_seed']==7 and request['camera_horizontal_fov']==2.,'seed/FOV')
    require(request['capture_pose']==row['capture_pose'],'pose')
    require(request['capture_target_entity_id']==row['entity_id'],'target')
    require(request['capture_target_categories']==[row['category']],'category')
    require(request['calibration_sha256'] is None,'uncalibrated')
    require(request['camera_profile_sha256']==sha(ROOT/row['camera_profile']),'camera')
    require(request['expansion_instrumentation_sha256']==sha(SNAPSHOT),'core snapshot')
    require(request['source_sha256']==json.loads(SNAPSHOT.read_bytes())['source_sha256'],'core source')
    require(request['lighting_redesign']['plan_sha256']==EXPECTED,'lighting plan')
    require(request['lighting_redesign']['world_sha256']==sha(ROOT/row['derivative_world_path']),'world hash')
    require('world_path:='+str(ROOT/row['derivative_world_path']) in request['simulation_launch_argv'],'actual world argument')


def audit():
    validate_pins();records=[];bins={c:[0,0,0] for c in ('chair','doorway','laboratory_entrance','office_entrance')}
    for row in assignments():
        name=row['candidate_id'];validate_row(row)
        result_path=OUTPUT/(name+'.result.json')
        require(result_path.exists(),'fixed panel incomplete')
        folder=ROOT/'reports/physical_live_episodes'/name
        result=json.loads(result_path.read_bytes())
        require(result['run_id']==name,'result identity')
        request_path=folder/'request.json'
        require(request_path.exists(),'missing dispatched request')
        request=json.loads(request_path.read_bytes());check_request(request,row)
        score=None
        if result['status']!='infrastructure_failure':
            captured=audit_capture(folder)
            require(captured['status']==result['status'],'status mismatch')
            require(captured['selected_observation']==result.get('selected_observation'),'selected evidence mismatch')
            observation=captured['selected_observation']
            if observation:
                require(observation['entity_id']==row['entity_id'] and observation['category']==row['category'],'exact target')
                score=observation['confidence'];require(0<=score<=1,'probability domain')
                bins[row['category']][0 if score<.5 else 1 if score<.8 else 2]+=1
        records.append(dict(candidate_id=name,category=row['category'],lighting_scale=row['lighting_scale'],
            status=result['status'],confidence=score,human_verdict=None,result_sha256=sha(result_path),
            request_sha256=sha(request_path),completed_capture_integrity=result['status']!='infrastructure_failure'))
    return dict(schema_version='research3-redesign-stage-a-audit/v1',passed=True,scheduled=144,
        status_counts=dict(Counter(r['status'] for r in records)),raw_confidence_bins=bins,
        confidence_bin_intervals=['[0,0.5)','[0.5,0.8)','[0.8,1]'],
        automatic_feasibility_passed=all(n>=2 for b in bins.values() for n in b),
        human_review_requested=False,calibration_certified=False,primary_collection_authorized=False,
        validation_or_protected_data_read=False,rows=records)


if __name__=='__main__':
    result=audit();write(OUTPUT/'independent_audit.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
