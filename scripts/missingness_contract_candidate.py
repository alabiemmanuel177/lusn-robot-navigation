"""Offline D2-compatible accounting candidate. Does not open any execution gate.

Inputs are synthetic or already independently audited nonprotected records.
Boolean verification fields are an interface contract, not cryptographic proof;
the eventual caller must derive them by independent audit, not trust a return.
"""
from collections import defaultdict
import re

ENDPOINTS=('instruction_completion','collision','timeout','navigation_success','terminal_identity_correct')


def bound(value):
    if value is None:return (0.,1.)
    if type(value) is not bool:raise ValueError('endpoint must be bool or explicit null')
    return (float(value),float(value))


def account(schedule,records):
    if not schedule:raise ValueError('nonempty fixed paired schedule required')
    planned={};pairs=defaultdict(dict)
    for row in schedule:
        identity=row['episode_id']
        if not isinstance(identity,str) or not identity or identity in planned:raise ValueError('unique scheduled identity')
        if row['system_id'] not in ('B5','B6'):raise ValueError('primary contrast only')
        if type(row['simulation_seed']) is not int or row['simulation_seed']<1:raise ValueError('seed')
        if not all(isinstance(row[k],str) and row[k] for k in ('map_id','condition_id')):raise ValueError('world/condition')
        key=(row['map_id'],row['condition_id'],row['simulation_seed'])
        if row['system_id'] in pairs[key]:raise ValueError('duplicate paired arm')
        pairs[key][row['system_id']]=identity;planned[identity]=row
    if any(set(p)!= {'B5','B6'} for p in pairs.values()):raise ValueError('schedule lacks paired arm')
    actual={};blockers=[];ledger=[];outcomes={}
    for row in records:
        identity=row['episode_id']
        if identity not in planned or identity in actual:raise ValueError('unknown/duplicate result')
        actual[identity]=row
    for identity,slot in planned.items():
        result=actual.get(identity)
        if result is None:
            blockers.append(dict(episode_id=identity,reason='missing_assignment_evidence'))
            values={k:None for k in ENDPOINTS};status='missing_assignment'
        else:
            if result.get('integrity_verified') is not True:raise ValueError('unverified/tampered evidence is not benign missingness')
            if any(result.get(k)!=slot[k] for k in ('map_id','condition_id','simulation_seed','system_id')):raise ValueError('result identity differs')
            status=result.get('status')
            if status not in ('measured','infrastructure_failure'):raise ValueError('explicit result status')
            if status=='infrastructure_failure':
                if result.get('failure_evidence_verified') is not True or re.fullmatch(r'[0-9a-f]{64}',str(result.get('failure_record_sha256',''))) is None:
                    raise ValueError('verified failure record required')
            values=result.get('outcomes',{})
            if set(values)!=set(ENDPOINTS):raise ValueError('all endpoints must be explicit')
            reasons=result.get('unknown_reasons',{})
            for name,value in values.items():
                bound(value)
                if value is None and (not isinstance(reasons.get(name),str) or not reasons[name].strip()):raise ValueError('unknown reason required')
                if value is not None and result.get('measurement_recomputed') is not True:raise ValueError('known outcome requires recomputed measurement')
        outcomes[identity]=values
        ledger.append(dict(episode_id=identity,status=status,outcomes=values,
            unknown_endpoints=[k for k,v in values.items() if v is None]))
    groups=defaultdict(list)
    for (world,condition,seed),arms in pairs.items():
        b5=bound(outcomes[arms['B5']]['instruction_completion']);b6=bound(outcomes[arms['B6']]['instruction_completion'])
        groups[world,condition].append((b6[0]-b5[1],b6[1]-b5[0]))
    worlds=defaultdict(list)
    for (world,condition),values in groups.items():
        worlds[world].append(tuple(sum(v[i] for v in values)/len(values) for i in (0,1)))
    per_world={world:tuple(sum(v[i] for v in values)/len(values) for i in (0,1)) for world,values in worlds.items()}
    overall=tuple(sum(v[i] for v in per_world.values())/len(per_world) for i in (0,1))
    return dict(schema_version='research3-missingness-contract-candidate/v1',candidate_only=True,
        scheduled_count=len(planned),accounted_slots=len(ledger),missing_evidence=blockers,
        evidence_accounting_complete=not blockers,endpoint_complete=all(not r['unknown_endpoints'] for r in ledger),
        primary_contrast='B6_minus_B5_ordered_instruction_completion',
        lower_bound=overall[0],upper_bound=overall[1],world_bounds=per_world,
        weighting='equal_world_then_equal_scheduled_condition_then_equal_seed_pair',
        bounds_are_confidence_intervals=False,unknowns_imputed=False,complete_case_deletion=False,
        active_gate_modified=False,protected_access_authorized=False,scientific_release_complete=False,ledger=ledger)
