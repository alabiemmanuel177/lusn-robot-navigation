import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_navigation_feasibility import scheduled_bounds
from run_feasibility_navigation import plan_rows


def rows():
    plan=plan_rows()
    records=[dict(r,status='measured',instruction_completion=r['system_id']=='B6') for r in plan]
    return plan,records


def test_all_measured():
    plan,records=rows();result=scheduled_bounds(plan,records)
    assert result['lower_contrast']==result['upper_contrast']==1
    assert result['complete_pairs']==80


def test_missing_arm_is_bounded_not_dropped():
    plan,records=rows();records.pop()
    result=scheduled_bounds(plan,records)
    assert result['lower_contrast']==pytest.approx(79/80)
    assert result['upper_contrast']==1
    assert result['complete_pairs']==79
    assert result['missing_attempt_records']==1


def test_infrastructure_endpoint_never_counts_as_measurement():
    plan,records=rows();records[0]['status']='infrastructure_failure'
    result=scheduled_bounds(plan,records)
    assert result['complete_pairs']==79 and result['incomplete_pairs']==1


@pytest.mark.parametrize('kind',['duplicate','protected','numeric'])
def test_invalid_input_rejected(kind):
    plan,records=rows()
    if kind=='duplicate':records.append(records[0])
    elif kind=='protected':plan[0]=dict(plan[0],base='base-r015')
    else:records[0]['instruction_completion']=1
    with pytest.raises(ValueError):scheduled_bounds(plan,records)
