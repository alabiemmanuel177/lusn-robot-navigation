import copy
import pytest
from missingness_contract_candidate import account,ENDPOINTS


def fixture():
    schedule=[dict(episode_id=s,map_id='synthetic-world',condition_id='synthetic-condition',simulation_seed=1,system_id=s) for s in ('B5','B6')]
    records=[dict(r,status='measured',integrity_verified=True,measurement_recomputed=True,
        outcomes={k:False for k in ENDPOINTS},unknown_reasons={}) for r in schedule]
    return schedule,records


def test_known_failure_survives_unknown_auxiliary():
    schedule,records=fixture()
    records[1]['outcomes']['terminal_identity_correct']=None
    records[1]['unknown_reasons']['terminal_identity_correct']='insufficient terminal evidence'
    report=account(schedule,records)
    assert report['evidence_accounting_complete'] and not report['endpoint_complete']
    assert report['lower_bound']==report['upper_bound']==0
    assert report['ledger'][1]['outcomes']['instruction_completion'] is False


def test_unknown_primary_retained_in_denominator():
    schedule,records=fixture();records[1]['outcomes']['instruction_completion']=None
    records[1]['unknown_reasons']['instruction_completion']='trajectory incomplete'
    report=account(schedule,records)
    assert (report['lower_bound'],report['upper_bound'])==(0,1)
    assert report['accounted_slots']==2 and not report['unknowns_imputed']


def test_missing_assignment_stays_blocked_but_bounded():
    schedule,records=fixture();report=account(schedule,records[:1])
    assert not report['evidence_accounting_complete'] and report['accounted_slots']==2
    assert (report['lower_bound'],report['upper_bound'])==(0,1)


def test_infrastructure_failure_requires_evidence():
    schedule,records=fixture();record=records[1]
    record.update(status='infrastructure_failure',outcomes={k:None for k in ENDPOINTS},unknown_reasons={k:'capture interrupted' for k in ENDPOINTS})
    with pytest.raises(ValueError):account(schedule,records)
    record.update(failure_evidence_verified=True,failure_record_sha256='a'*64)
    assert account(schedule,records)['evidence_accounting_complete']


@pytest.mark.parametrize('value',[0,1,'false',float('nan')])
def test_no_boolean_coercion(value):
    schedule,records=fixture();records[0]['outcomes']['collision']=value
    with pytest.raises(ValueError):account(schedule,records)


def test_bad_integrity_is_not_missingness():
    schedule,records=fixture();records[1]['integrity_verified']=False
    with pytest.raises(ValueError):account(schedule,records)


def test_condition_weighting_not_replication_weighting():
    schedule,records=fixture()
    # Two positive pairs in another condition must not outweigh the first condition.
    for seed in (1,2):
        for system in ('B5','B6'):
            row=dict(episode_id=f'other-{seed}-{system}',map_id='synthetic-world',condition_id='other',simulation_seed=seed,system_id=system)
            schedule.append(row);records.append(dict(row,status='measured',integrity_verified=True,measurement_recomputed=True,
                outcomes={k:system=='B6' for k in ENDPOINTS},unknown_reasons={}))
    report=account(schedule,records)
    assert report['lower_bound']==report['upper_bound']==.5
    assert not report['active_gate_modified'] and not report['protected_access_authorized']
