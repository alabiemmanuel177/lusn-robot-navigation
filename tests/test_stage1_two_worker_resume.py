import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import resume_stage1_two_workers as resume


def test_exact_remaining_36_and_two_domains():
    rows=resume.commands()
    assert len(rows)==36
    assert {r['candidate_id'] for r in rows}=={r['candidate_id'] for r in resume.base.assignments()[44:]}
    for offset in range(0,36,2):
        assert {r['argv'][r['argv'].index('--ros-domain-id')+1] for r in rows[offset:offset+2]}=={'100','101'}
    assert not any('r006-chair' in r['candidate_id'] or 'r006-doorway' in r['candidate_id'] for r in rows)


def test_external_workload_adapter_detects_campaign_between_simulations(monkeypatch):
    monkeypatch.setattr(resume,'inspect_external_workloads',lambda:[dict(pid=123,campaign_driver=True)])
    assert resume.external_workload_pids()==[123]
