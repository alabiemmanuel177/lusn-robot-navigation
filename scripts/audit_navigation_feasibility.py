"""Read-only development navigation audit and scheduled-cohort bounds.

Preserves the independently recorded ordered-completion endpoint, including
measured failures with no terminal identity. Does not refit, run simulations,
read validation labels, approve inference, or change historical outcomes.
"""
import itertools
import json
from pathlib import Path

from run_feasibility_navigation import CONDITIONS, WORLDS, SYSTEMS
from run_stage1_feasibility import ROOT, sha, write


def scheduled_bounds(plan, records):
    expected={(w,c,s) for w,c,s in itertools.product(WORLDS,CONDITIONS,SYSTEMS)}
    planned={}
    for row in plan:
        key=(row['base'],row['condition'],row['system_id'])
        if key in planned or row['simulation_seed']!=1:
            raise ValueError('duplicate slot or unexpected seed')
        planned[key]=row['run_id']
    if set(planned)!=expected or len(set(planned.values()))!=len(planned):
        raise ValueError('exact development schedule required')
    values={}
    for row in records:
        key=(row['base'],row['condition'],row['system_id'])
        if key not in planned or key in values or row['run_id']!=planned[key]:
            raise ValueError('unscheduled, duplicate or mismatched observation')
        value=row.get('instruction_completion')
        if value is not None and type(value) is not bool:
            raise ValueError('endpoint must be boolean or null')
        if row['status'] not in ('measured','infrastructure_failure'):
            raise ValueError('unknown lifecycle status')
        values[key]=value if row['status']=='measured' else None
    worlds=[]
    complete=[]
    for world in WORLDS:
        slots=[]
        for condition in CONDITIONS:
            a,b=(values.get((world,condition,s)) for s in SYSTEMS)
            possibilities=[(int(y)-int(x),int(x!=y)) for x in ([False,True] if a is None else [a])
                           for y in ([False,True] if b is None else [b])]
            if a is not None and b is not None:complete.append((int(a),int(b)))
            slots.append(dict(condition=condition,b5=a,b6=b,
                lower_contrast=min(v[0] for v in possibilities),upper_contrast=max(v[0] for v in possibilities),
                lower_discordance=min(v[1] for v in possibilities),upper_discordance=max(v[1] for v in possibilities)))
        worlds.append(dict(world=world,slots=slots,**{
            name:sum(s[name] for s in slots)/len(slots)
            for name in ('lower_contrast','upper_contrast','lower_discordance','upper_discordance')}))
    arms={s:dict(scheduled=80,known=sum(values.get((w,c,s)) is not None for w,c in itertools.product(WORLDS,CONDITIONS)),
        correct=sum(values.get((w,c,s)) is True for w,c in itertools.product(WORLDS,CONDITIONS))) for s in SYSTEMS}
    for record in arms.values():
        record['unknown']=record['scheduled']-record['known']
        record['lower_completion']=record['correct']/record['scheduled']
        record['upper_completion']=(record['correct']+record['unknown'])/record['scheduled']
    return dict(scheduled_pairs=80,complete_pairs=len(complete),incomplete_pairs=80-len(complete),
        arms=arms,worlds=worlds,**{name:sum(w[name] for w in worlds)/len(worlds)
            for name in ('lower_contrast','upper_contrast','lower_discordance','upper_discordance')},
        complete_pair_mean_difference=sum(b-a for a,b in complete)/len(complete) if complete else None,
        missing_attempt_records=160-len(values),confidence_interval=False,
        weighting='equal worlds, equal eight conditions within worlds, one fixed seed',
        scope='identification bounds for fixed recorded engineering outcomes, not population inference')


def audit():
    directory=ROOT/'reports/feasibility_navigation_20260912_v1'
    plan=json.loads((directory/'planned.json').read_bytes())
    report=json.loads((directory/'report.json').read_bytes())
    bounds=scheduled_bounds(plan['rows'],report['attempts'])
    failures=[];verified=[];false_without_identity=[]
    for row in report['attempts']:
        run=ROOT/'reports/physical_live_episodes'/row['run_id']
        record=dict(run_id=row['run_id'])
        try:
            if sha(run/'request.json')!=row['request_sha256']:raise ValueError('request digest mismatch')
            if row['summary_sha256'] is not None:
                if sha(run/'summary.json')!=row['summary_sha256']:raise ValueError('summary digest mismatch')
                summary=json.loads((run/'summary.json').read_bytes())
                if summary.get('partition')!='development' or summary.get('protected_test_routes_used') is not False:
                    raise ValueError('summary not nonprotected development')
                for field in ('instruction_completion','navigation_success','collision','timeout','terminal_identity_correct'):
                    if summary.get(field)!=row.get(field):raise ValueError('recorded endpoint mismatch: '+field)
                if summary.get('measurements_sha256'):
                    if sha(run/'measurements.json')!=summary['measurements_sha256']:
                        raise ValueError('measurements digest mismatch')
                if row['instruction_completion'] is False and row['terminal_identity_correct'] is None:
                    false_without_identity.append(row['run_id'])
                record['summary_verified']=True
            else:
                if row['status']!='infrastructure_failure':raise ValueError('missing measured summary')
                record['summary_verified']=False
            verified.append(record)
        except (OSError,ValueError) as exc:failures.append(dict(record,error=str(exc)))
    return dict(schema_version='research3-navigation-feasibility-audit/v1',integrity_passed=not failures,
        input_sha256={name:sha(directory/name) for name in ('planned.json','report.json')},
        source_sha256=sha(__file__),verified=verified,failures=failures,bounds=bounds,
        measured_false_with_unknown_terminal_identity=false_without_identity,
        endpoint_policy='Use raw independently recorded ordered completion for existing nuisance evidence; do not reinterpret a measured failure as success or impute unknowns.',
        calibration_used=False,protected_outcomes_read=False,confirmatory_inference=False,
        raw_trajectory_semantics_recomputed=False)


if __name__=='__main__':
    result=audit()
    write(ROOT/'reports/navigation_feasibility_audit_20260922_v1.json',result)
    print(json.dumps({k:result[k] for k in ('integrity_passed','failures')}))
    print(json.dumps({k:v for k,v in result['bounds'].items() if k!='worlds'}))
