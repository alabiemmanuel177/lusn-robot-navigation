import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_stage1_four_workers as runner


def test_original_eighty_assignments_and_four_isolated_domains():
    rows=runner.commands()
    assert len(rows)==80 and len({r['candidate_id'] for r in rows})==80
    for offset in range(0,80,4):
        batch=rows[offset:offset+4]
        assert {r['argv'][r['argv'].index('--ros-domain-id')+1] for r in batch}=={'96','97','98','99'}
        for row in batch:
            assert '--allow-coexistence-trial' not in row['argv']
            assert '--calibration' not in row['argv']
            assert '--capture-only' in row['argv']


def test_four_trial_frame_integrity_and_no_automated_labels():
    for index in range(1,5):
        audit=runner.audit_capture(runner.ROOT/f'reports/physical_live_episodes/r3-parallel-engineering-20260922-w{index}')
        assert audit['status'] in {'emitted','nondetection'}
        assert audit['human_correctness_verified'] is False
