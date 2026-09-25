import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import audit_stage1_evidence as audit


def test_complete_panel_accounting():
    result=audit.audit()
    assert result['unique_assignments']==80
    assert result['completed_capture_integrity_count']==75
    assert result['status_counts']==dict(emitted=49,nondetection=26,infrastructure_failure=5)


@pytest.mark.parametrize('field,value',[('partition','validation'),('capture_frame_budget',2),('simulation_seed',2),('calibration_sha256','fake')])
def test_request_drift_rejected(field,value):
    target=audit.original.base.assignments()[0]
    request=json.loads((audit.original.ROOT/'reports/physical_live_episodes'/target['candidate_id']/'request.json').read_bytes())
    request[field]=value
    with pytest.raises(ValueError):audit.check_request(request,target)
