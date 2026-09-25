#!/usr/bin/env python3
"""Pin approved candidate instrumentation beside the intact historical freeze.

This does not assert runner integration or authorize live capture.
"""
import argparse
import hashlib
import json
from pathlib import Path
from language_nav.camera_configuration import capture_source_snapshot, capture_provider_snapshot

ROOT=Path(__file__).resolve().parents[1]
FILES=('scripts/expansion_sampling.py','scripts/physical_expansion_capture_candidate.py')
GUARD='src/language_nav/live_resources.py'
GUARD_BEFORE='fc0ad9a3e249c2aeffbe2e64424d67230e9604bd588e48b12b9e88a2c3df4a0c'
GUARD_AFTER='a484706b8133c95a8c4f2ae90677a5246513d6d9e77eb7d8e6117cf1347df9aa'


def guard_approval():
    raw=(ROOT/'reports/resource_guard_repair_approval_20260922.json').read_bytes()
    record=json.loads(raw)
    if (record.get('schema_version')!='research3-resource-guard-repair-approval/v1'
            or record.get('authorized') is not True or record.get('source_path')!=GUARD
            or record.get('before_sha256')!=GUARD_BEFORE or record.get('after_sha256')!=GUARD_AFTER
            or record.get('replace_failed_attempt') is not False
            or record.get('protected_access') is not False):
        raise ValueError('exact resource guard repair approval required')
    return hashlib.sha256(raw).hexdigest()


def validate(path):
    raw=Path(path).read_bytes();record=json.loads(raw)
    if (record.get('schema_version')!='research3-expansion-instrumentation-snapshot/v2'
            or record.get('scope')!='capture_instrumentation_only'
            or record.get('source_sha256')!=capture_source_snapshot()
            or record.get('provider_source_snapshot')!=capture_provider_snapshot()):
        raise ValueError('instrumentation source/provider snapshot mismatch')
    if set(record.get('instrumentation_sha256',{}))!=set(FILES):raise ValueError('exact instrumentation files required')
    for name,digest in record['instrumentation_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('instrumentation changed')
    approval=(ROOT/'reports/human_method_decisions_20260912_v1/decision_record.json').read_bytes()
    if hashlib.sha256(approval).hexdigest()!=record['human_scope_record_sha256']:
        raise ValueError('human scope binding changed')
    wrapper=(ROOT/'reports/human_wrapper_decision_20260912_v1/decision_record.json').read_bytes()
    if hashlib.sha256(wrapper).hexdigest()!=record.get('wrapper_scope_sha256'):
        raise ValueError('wrapper scope binding changed')
    if record['source_sha256'].get(GUARD)==GUARD_AFTER:
        if record.get('resource_guard_repair_approval_sha256')!=guard_approval():
            raise ValueError('resource guard repair approval binding changed')
    return hashlib.sha256(raw).hexdigest()


def snapshot(output, resource_guard_repair=False):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    approval_path=ROOT/'reports/human_method_decisions_20260912_v1/decision_record.json'
    approval_raw=approval_path.read_bytes();approval=json.loads(approval_raw)
    wrapper_raw=(ROOT/'reports/human_wrapper_decision_20260912_v1/decision_record.json').read_bytes()
    if json.loads(wrapper_raw).get('authorized') is not True:raise ValueError('wrapper approval required')
    if (approval['P4']['capture_instrumentation_source_revision_authorized'] is not True
            or approval['P4']['named_candidates']!=list(FILES)):
        raise ValueError('exact human-authorized instrumentation scope required')
    prior=ROOT/'reports/fresh_current_capture_20260911_v1/current_source_snapshot.json'
    old_raw=prior.read_bytes();old=json.loads(old_raw);old_hash=hashlib.sha256(old_raw).hexdigest()
    current=capture_source_snapshot();provider=capture_provider_snapshot()
    changed={name for name in set(current)|set(old['source_sha256'])
             if current.get(name)!=old['source_sha256'].get(name)}
    allowed={'scripts/run_physical_episode.py'}
    guard_binding=None
    if resource_guard_repair:
        guard_binding=guard_approval()
        if old['source_sha256'].get(GUARD)!=GUARD_BEFORE or current.get(GUARD)!=GUARD_AFTER:
            raise ValueError('resource guard revision differs from approved patch')
        allowed.add(GUARD)
    if changed-allowed:
        raise ValueError('revision exceeds capture runner orchestration scope')
    if provider!=old['provider_source_snapshot']:raise ValueError('provider invariant changed')
    payload={name:(ROOT/name).read_bytes() for name in FILES}
    for name,raw in payload.items():compile(raw,name,'exec')
    record={'schema_version':'research3-expansion-instrumentation-snapshot/v2',
            'status':'approved_scope_candidate_source_pinned_not_live_verified',
            'scope':'capture_instrumentation_only',
            'human_scope_record_sha256':hashlib.sha256(approval_raw).hexdigest(),
            'wrapper_scope_sha256':hashlib.sha256(wrapper_raw).hexdigest(),
            'historical_capture_snapshot_sha256':old_hash,
            'instrumentation_sha256':{name:hashlib.sha256(raw).hexdigest() for name,raw in payload.items()},
            'source_sha256':current,'provider_source_snapshot':provider,
            'changed_historical_files':sorted(changed),
            'historical_archive_preserved':True,'provider_unchanged':True,
            'runtime_integration_verified':False,'isolated_development_preflight_verified':False,
            'live_collection_authorized_by_this_snapshot':False,'human_labels_generated':False}
    if guard_binding:
        record['resource_guard_repair_approval_sha256']=guard_binding
    output.mkdir(parents=True,exist_ok=False)
    for name,raw in payload.items():
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
    with (output/'snapshot.json').open('x') as stream:json.dump(record,stream,indent=2,sort_keys=True)
    if (hashlib.sha256(prior.read_bytes()).hexdigest()!=old_hash or current!=capture_source_snapshot()
            or any((ROOT/name).read_bytes()!=raw for name,raw in payload.items())):
        raise ValueError('source changed while pinning')
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--resource-guard-repair',action='store_true')
    args=p.parse_args()
    print(json.dumps(snapshot(args.output,args.resource_guard_repair),indent=2))
