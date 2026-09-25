"""Independent fail-closed audit of the completed fixed feasibility panel."""
import json
from pathlib import Path
from collections import Counter
import run_stage1_four_workers as original
from summarize_stage1_four_workers import summarize,RESULT_DIRECTORIES


def require(condition,message):
    if not condition:raise ValueError(message)


def check_request(request,target):
    require(request['run_id']==target['candidate_id'],'run identity')
    require(request['partition']=='development' and request['protected_test_routes_used'] is False,'nonprotected scope')
    require(request['capture_only'] is True and request['capture_frame_budget']==1,'stationary single frame')
    require(request['simulation_seed']==1 and request['camera_horizontal_fov']==2.0,'seed/FOV drift')
    require(request['capture_pose']==target['pose'],'pose drift')
    require(request['capture_target_entity_id']==target['entity_id'],'target identity drift')
    require(request['capture_target_categories']==[target['category']],'category drift')
    require(request['allow_coexistence_trial'] is False and request['calibration_sha256'] is None,'scope bypass')
    require(request['world_directory']==str(original.ROOT/target['world_directory']),'world drift')
    require(request['camera_profile_sha256']==original.base.sha(original.ROOT/target['camera_profile']),'profile drift')


def audit():
    summary=summarize()
    require(summary['complete'],'schedule incomplete')
    rows=[]
    for target in original.base.assignments():
        folder=original.ROOT/'reports/physical_live_episodes'/target['candidate_id']
        request=json.loads((folder/'request.json').read_bytes())
        check_request(request,target)
        records=[p/(target['candidate_id']+'.result.json') for p in RESULT_DIRECTORIES
                 if (p/(target['candidate_id']+'.result.json')).exists()]
        require(len(records)==1,'one retained result per assignment')
        result=json.loads(records[0].read_bytes())
        snapshot=Path(request['expansion_instrumentation_snapshot'])
        require(snapshot.is_relative_to(original.ROOT/'reports'),'snapshot path outside report scope')
        require(original.base.sha(snapshot)==request['expansion_instrumentation_sha256'],'snapshot binding')
        pinned=json.loads(snapshot.read_bytes())
        require(request['source_sha256']==pinned['source_sha256'],'request source differs from historical source binding')
        completed=result['status']!='infrastructure_failure'
        if completed:
            original.audit_capture(folder)
            frame_path=folder/'perception_capture/frame-000.json'
            frame=json.loads(frame_path.read_bytes()); completion=json.loads((folder/'provider_frame_completion.json').read_bytes())
            require(completion['status']=='completed','provider incomplete')
            require(original.base.sha(frame_path)==completion['frame_sha256'],'frame digest')
            require(frame['rgb_stamp_ns']==frame['depth_stamp_ns']==completion['frame_stamp_ns'],'frame stamps')
            for kind in ('rgb','depth'):
                payload=frame_path.parent/frame[kind]['file']
                require(payload.resolve().is_relative_to(frame_path.parent.resolve()),'frame payload escapes folder')
                require(original.base.sha(payload)==frame[kind]['sha256'] and payload.stat().st_size==frame[kind]['bytes'],'payload integrity')
        rows.append(dict(candidate_id=target['candidate_id'],status=result['status'],
                    request_sha256=original.base.sha(folder/'request.json'),result_sha256=original.base.sha(records[0]),
                    snapshot_sha256=request['expansion_instrumentation_sha256'],completed_capture_integrity=completed))
    return dict(schema_version='research3-fixed-feasibility-evidence-audit/v1',passed=True,
        scheduled=80,unique_assignments=len({r['candidate_id'] for r in rows}),status_counts=dict(Counter(r['status'] for r in rows)),
        completed_capture_integrity_count=sum(r['completed_capture_integrity'] for r in rows),
        scientific_correctness_verified=False,calibration_certified=False,protected_data_read=False,rows=rows)


if __name__=='__main__':
    result=audit()
    original.base.write(original.ROOT/'reports/stage1_evidence_audit_20260922_v1.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
