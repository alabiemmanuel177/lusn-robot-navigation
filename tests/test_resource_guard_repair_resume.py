import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import resume_stage1_four_workers as resume
import snapshot_expansion_instrumentation as snapshot
from probe_resource_guard_race import Entry,Proc
from language_nav import live_resources


def test_actual_guard_handles_exit_and_still_blocks_permission(monkeypatch):
    monkeypatch.setattr(live_resources,'Path',lambda value:value if isinstance(value,Proc) else Path(value))
    assert live_resources.research2_execution_pids(Proc(Entry(ProcessLookupError())))==[]
    with pytest.raises(RuntimeError,match='visibility denied'):
        live_resources.research2_execution_pids(Proc(Entry(PermissionError())))
    assert live_resources.research2_execution_pids(Proc(Entry(payload=b'/home/eao/failure-prediction/scripts/run_campaign_parallel.py\0')))==[123]


def test_resume_exact_unstarted_only():
    rows=resume.commands()
    assert len(rows)==56
    assert {r['candidate_id'] for r in rows}=={r['candidate_id'] for r in resume.base.assignments()[24:]}
    for row in rows:
        assert row['argv'][row['argv'].index('--expansion-instrumentation-snapshot')+1]==str(resume.SNAPSHOT)
    assert snapshot.validate(resume.SNAPSHOT)


def test_new_snapshot_requires_specific_approval_binding(tmp_path):
    record=json.loads(resume.SNAPSHOT.read_bytes())
    record['resource_guard_repair_approval_sha256']='0'*64
    changed=tmp_path/'snapshot.json'; changed.write_text(json.dumps(record))
    with pytest.raises(ValueError,match='approval binding changed'):
        snapshot.validate(changed)
