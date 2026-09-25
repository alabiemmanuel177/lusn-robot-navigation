"""Recompute existing nonprotected telemetry; no live or protected execution."""
import copy
import json
from pathlib import Path

from audit_navigation_feasibility import audit
from analyze_physical_campaign import analyze
from run_physical_episode import evaluate
from run_stage1_feasibility import ROOT,sha,write

EVALUATORS=('scripts/run_physical_episode.py','src/language_nav/live.py',
            'src/language_nav/evaluation/ordered.py')
KEYS=('collision','timeout','instruction_completion','navigation_success',
      'terminal_identity_correct','goal_error_m','distance_travelled_m',
      'ordered_instruction_score','trajectory_quality')


def require_development_request(request,row):
    expected=ROOT/row['world_directory']
    if (request.get('partition')!='development'
            or request.get('protected_test_routes_used') is not False
            or request.get('map_id')!='r3geo_'+row['base'].replace('-','_')
            or request.get('run_id')!=row['run_id']
            or request.get('system_id')!=row['system_id']
            or request.get('variant_id')!=row['variant_id']
            or Path(request.get('world_directory','')).resolve()!=expected.resolve()):
        raise ValueError('exact nonprotected development request required')
    allowed={ROOT/'data'/family/row['base'] for family in
             ('physical_worlds_readable_v1','physical_absence_worlds_v1')}
    if expected not in allowed or not row['base'] in {f'base-r{i:03}' for i in range(1,11)}:
        raise ValueError('world outside fixed development scope')
    if any(Path(name).name!=name for name in request['asset_sha256']):
        raise ValueError('unsafe asset member')
    for name in EVALUATORS:
        if request['source_sha256'].get(name)!=sha(ROOT/name):
            raise ValueError('evaluator source differs from retained run')


def recompute():
    integrity=audit()
    if not integrity['integrity_passed']:raise ValueError('retained evidence integrity audit failed')
    directory=ROOT/'reports/feasibility_navigation_20260912_v1'
    plan=json.loads((directory/'planned.json').read_bytes())
    report=json.loads((directory/'report.json').read_bytes())
    by_id={r['run_id']:r for r in report['attempts']}
    comparisons=[];failures=[];scheduled=[];outcomes=[]
    for row in plan['rows']:
        recorded=by_id[row['run_id']]
        identity=dict(episode_id=row['run_id'],variant_id=row['variant_id'],system_id=row['system_id'],
            partition='development',base_instruction_id=row['base'],condition=row['condition'],
            paired_block_index=row['paired_block_index'])
        scheduled.append(identity)
        measured=recorded['status']=='measured'
        outcomes.append(dict(identity,schema_version='research3-physical-campaign-outcome/v1',
            attempted=True,dispatched=measured,infrastructure_failure=not measured,
            evaluation_mode='physical_live',**{k:recorded.get(k) if measured else None for k in KEYS[:5]}))
        if not measured:continue
        run=ROOT/'reports/physical_live_episodes'/row['run_id']
        try:
            request=json.loads((run/'request.json').read_bytes())
            require_development_request(request,row)
            evidence=json.loads((run/'measurements.json').read_bytes())
            original=copy.deepcopy(evidence)
            summary=json.loads((run/'summary.json').read_bytes())
            regenerated=evaluate(request,evidence)
            differences=[k for k in KEYS if regenerated.get(k)!=summary.get(k)]
            if differences:raise ValueError('recomputed fields differ: '+', '.join(differences))
            comparisons.append(dict(run_id=row['run_id'],matched_fields=list(KEYS),
                retained_annotations_match_recomputed=evidence==original,
                summary_sha256=sha(run/'summary.json'),measurements_sha256=sha(run/'measurements.json')))
        except (ValueError,OSError,KeyError) as exc:failures.append(dict(run_id=row['run_id'],error=str(exc)))
    analysis=analyze(dict(schema_version='research3-physical-comparison-plan/v1',episodes=scheduled),outcomes,'B5')
    return dict(schema_version='research3-development-navigation-recomputation/v1',
        passed=not failures,matched=len(comparisons),comparisons=comparisons,failures=failures,
        infrastructure_attempts_retained=160-len(comparisons)-len(failures),
        evaluator_sha256={name:sha(ROOT/name) for name in EVALUATORS},
        source_sha256=sha(__file__),input_sha256=integrity['input_sha256'],
        normalized_analysis=analysis,protected_outcomes_read=False,live_execution_performed=False,
        original_files_modified=False,confirmatory_inference=False,
        limitation='Re-execution of the pinned evaluator on retained telemetry, not an independent sensor or new navigation trial.')


if __name__=='__main__':
    result=recompute()
    write(ROOT/'reports/development_navigation_recomputation_20260922_v1.json',result)
    print(json.dumps({k:result[k] for k in ('passed','matched','failures','infrastructure_attempts_retained')}))
    print(json.dumps(result['normalized_analysis']['world_equal_weight_sensitivity_bounds']))
