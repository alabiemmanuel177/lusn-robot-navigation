"""Prospectively bind and run a synthetic planning grid; no live/protected data."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
import os
from pathlib import Path
import time
import numpy as np
from run_stage1_feasibility import ROOT,sha,write
from language_nav.live_resources import coexistence_headroom
from marginal_power_sensitivity import simulate

OUTPUT=ROOT/'reports/marginal_power_sensitivity_20260922_v1'


def prepare():
    protocol=dict(schema_version='research3-marginal-power-grid-proposal/v1',
        worlds=6,conditions=8,simulator_repetitions_per_condition=[1,2,4,8],
        baselines=[.75,.85,.9],discordances=[.1,.14,.2,.3],baseline_binary_iccs=[0.,.05,.1],
        target_marginal_effect=.1,alpha=.05,monte_carlo_replications_per_hypothesis=100000,
        monte_carlo_seed=20260922,workers=4,
        assumptions=['independent worlds; common normal world effect on both system logits',
            'intercepts match marginal rates; variance matches B5 binary ICC',
            'conditional joint mixture matches requested marginal discordance if feasible',
            'conditions/seeds conditionally iid within world; no missing outcomes or infrastructure failures',
            'all grid cells retained; infeasible cells reported rather than clipped or dropped'],
        final_method_approved=False,achieved_study_power=False,protected_data_read=False,
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),ROOT/'scripts/marginal_power_sensitivity.py')},
        original_nuisance_estimates_sha256=sha(ROOT/'reports/feasibility_nuisance_20260914_v1.json'))
    OUTPUT.mkdir(exist_ok=False);write(OUTPUT/'protocol.json',protocol)
    print('Prepared fixed synthetic grid: 144 cells, null and alternative, 100000 replications each where feasible',flush=True)


def worker(task):
    os.nice(19)
    coexistence_headroom()
    index,seeds,baseline,discordance,icc,replications=task
    result=dict(index=index,seeds=seeds,baseline=baseline,discordance=discordance,baseline_binary_icc=icc)
    for hypothesis,effect,offset in [('null',0.,0),('alternative',.1,1)]:
        result[hypothesis]=simulate(baseline=baseline,effect=effect,icc=icc,discordance=discordance,
            seeds=seeds,replications=replications,random_seed=20260922+2*index+offset)
    coexistence_headroom()
    return result


def execute():
    protocol=json.loads((OUTPUT/'protocol.json').read_bytes())
    for name,digest in protocol['source_sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('prospectively bound source changed')
    if sha(ROOT/'reports/feasibility_nuisance_20260914_v1.json')!=protocol['original_nuisance_estimates_sha256']:
        raise ValueError('nuisance evidence changed')
    tasks=[(i,*values,protocol['monte_carlo_replications_per_hypothesis']) for i,values in enumerate(itertools.product(
        protocol['simulator_repetitions_per_condition'],protocol['baselines'],protocol['discordances'],protocol['baseline_binary_iccs']))]
    start=time.monotonic();rows=[]
    write(OUTPUT/'started.json',dict(headroom=coexistence_headroom(),protocol_sha256=sha(OUTPUT/'protocol.json')))
    with ProcessPoolExecutor(max_workers=4) as pool:
        for row in pool.map(worker,tasks):
            write(OUTPUT/f"cell-{row['index']:03}.json",row);rows.append(row)
            if len(rows)%12==0:print(f'Completed {len(rows)}/144 synthetic grid cells',flush=True)
    result=dict(schema_version='research3-marginal-power-sensitivity/v1',protocol_sha256=sha(OUTPUT/'protocol.json'),
        cells=rows,elapsed_seconds=time.monotonic()-start,complete=len(rows)==144,
        infeasible_alternative_cells=sum(not r['alternative']['simulated'] for r in rows),
        actual_replicates=sum(r[k].get('replications',0) for r in rows for k in ('null','alternative')),
        protected_data_read=False,achieved_study_power=False,final_method_approved=False)
    write(OUTPUT/'report.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='cells'}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true')
    if parser.parse_args().execute:execute()
    else:prepare()
