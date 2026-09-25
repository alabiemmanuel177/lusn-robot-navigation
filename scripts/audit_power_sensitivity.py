"""Independent adaptive-integration check of the fixed synthetic planning grid.

Checks numerical marginals and accounting, not empirical assumptions or power
feasibility of the actual research study. Does not execute new research trials.
"""
from functools import lru_cache
import json
import math
from scipy.integrate import quad
from run_stage1_feasibility import ROOT,sha,write


@lru_cache(maxsize=None)
def independent_moments(encoded):
    model=json.loads(encoded)
    def logistic(x):return 1/(1+math.exp(-x))
    def values(z):
        p5=logistic(model['alpha']+model['sigma']*z)
        p6=model['target'] if model['beta'] is None else logistic(model['beta']+model['sigma']*z)
        upper=min(p5+p6,2-p5-p6);lower=abs(p6-p5)
        return p5,p6,lower+model['mixture']*(upper-lower),(p5-model['baseline'])**2
    cut=[]
    if model['sigma'] and model['beta'] is not None:
        kink=-(model['alpha']+model['beta'])/(2*model['sigma'])
        if -12<kink<12:cut=[kink]
    integrals=[];errors=[]
    for index in range(4):
        value,error=quad(lambda z:values(z)[index]*math.exp(-z*z/2)/math.sqrt(2*math.pi),
            -12,12,points=cut,epsabs=1e-11,epsrel=1e-11)
        integrals.append(value);errors.append(error)
    return dict(baseline=integrals[0],target=integrals[1],discordance=integrals[2],
        baseline_binary_icc=integrals[3]/(model['baseline']*(1-model['baseline'])),
        estimated_integration_error=max(errors),normal_tail_truncation='|Z| > 12; negligible at 1e-8 audit tolerance')


def audit():
    folder=ROOT/'reports/marginal_power_sensitivity_20260922_v1'
    report=json.loads((folder/'report.json').read_bytes())
    protocol=json.loads((folder/'protocol.json').read_bytes())
    if report['protocol_sha256']!=sha(folder/'protocol.json'):raise ValueError('protocol hash mismatch')
    for name,digest in protocol['source_sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('generator source drift')
    rows=[];failures=[];realizations=0;infeasible=0
    if len(report['cells'])!=144 or [r['index'] for r in report['cells']]!=list(range(144)):
        raise ValueError('incomplete or reordered fixed grid')
    for cell in report['cells']:
        path=folder/f"cell-{cell['index']:03}.json"
        if json.loads(path.read_bytes())!=cell:raise ValueError('cell/report mismatch')
        for name,offset in [('null',0),('alternative',1)]:
            value=cell[name]
            if not value['simulated']:
                infeasible+=1;continue
            if (value['replications']!=100000 or value['random_seed']!=20260922+2*cell['index']+offset
                    or value['achieved_study_power'] is not False):raise ValueError('simulation provenance mismatch')
            rate=value['rejection_rate']
            if abs(value['monte_carlo_se']-math.sqrt(rate*(1-rate)/100000))>1e-15:
                raise ValueError('Monte Carlo uncertainty mismatch')
            realization=independent_moments(json.dumps(value['model'],sort_keys=True))
            expected=dict(baseline=cell['baseline'],target=cell['baseline']+(.1 if name=='alternative' else 0),
                          discordance=cell['discordance'],baseline_binary_icc=cell['baseline_binary_icc'])
            errors={k:abs(realization[k]-v) for k,v in expected.items()}
            row=dict(index=cell['index'],hypothesis=name,absolute_errors=errors,moments=realization)
            rows.append(row)
            if max(errors.values())>1e-8:failures.append(row)
            realizations+=value['replications']
    if realizations!=report['actual_replicates']:raise ValueError('replication accounting differs')
    return dict(schema_version='research3-power-numerical-audit/v1',passed=not failures,
        checked_hypotheses=len(rows),infeasible_hypotheses_retained=infeasible,actual_replicates=realizations,
        worst_absolute_moment_error=max(max(r['absolute_errors'].values()) for r in rows),
        tolerance=1e-8,rows=rows,failures=failures,source_sha256=sha(__file__),
        protocol_sha256=sha(folder/'protocol.json'),report_sha256=sha(folder/'report.json'),
        empirical_assumptions_validated=False,achieved_study_power=False,protected_data_read=False)


if __name__=='__main__':
    result=audit();write(ROOT/'reports/power_numerical_audit_20260922_v1.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','failures')}))
