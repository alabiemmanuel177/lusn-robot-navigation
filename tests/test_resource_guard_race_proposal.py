import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_resource_guard_race import probe


def test_unapplied_candidate_fixes_race_without_weakening_guard():
    result=probe()
    assert result['original_race_reproduced']
    assert result['candidate_handles_vanished_process']
    assert result['permission_fail_closed']
    assert result['active_research2_detection_preserved']
    assert result['frozen_source_unchanged']
    assert not result['patch_applied']
