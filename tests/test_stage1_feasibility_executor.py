import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_stage1_feasibility as runner


def test_exact_approved_eighty_and_no_campaign_flags():
    rows=runner.assignments()
    assert len(rows)==80
    for row in rows:
        args=runner.argv(row)
        assert '--capture-only' in args
        assert '--calibration' not in args and '--allow-coexistence-trial' not in args
        assert args[args.index('--capture-frame-budget')+1]=='1'
        assert args[args.index('--capture-entity-id')+1]==row['entity_id']
        assert 'validation' not in row['world_directory']


def test_other_simulators_detected_without_matching_shell_text(tmp_path):
    commands={11:['/usr/bin/ruby','/usr/bin/gz','sim','/other/project/world.sdf'],
              12:['zsh','-c','echo gz sim'],
              13:['/usr/bin/ruby','/usr/bin/gz','sim',str(runner.ROOT/'data/world.sdf')]}
    for pid,args in commands.items():
        folder=tmp_path/str(pid);folder.mkdir();(folder/'cmdline').write_bytes(('\0'.join(args)+'\0').encode())
    assert runner.other_simulators(tmp_path)==[11]


def test_changed_manifest_refused(tmp_path,monkeypatch):
    path=tmp_path/'manifest.json';path.write_text('{}');monkeypatch.setattr(runner,'MANIFEST',path)
    with pytest.raises(ValueError,match='manifest changed'):runner.assignments()


def test_create_once_record(tmp_path):
    path=tmp_path/'record.json';runner.write(path,{'state':'started'})
    with pytest.raises(FileExistsError):runner.write(path,{'state':'replaced'})
    assert json.loads(path.read_text())=={'state':'started'}
