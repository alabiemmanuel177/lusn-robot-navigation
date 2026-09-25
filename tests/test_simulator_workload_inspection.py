import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from inspect_simulator_workloads import simulator_command


def test_normal_and_rewritten_gazebo_titles():
    assert simulator_command(['/usr/bin/ruby','/usr/bin/gz','sim','world.sdf'])
    assert simulator_command(['gz sim -r -s --headless-rendering -v 1 /other/shifted_world.sdf','',''])
    assert simulator_command(['/usr/bin/ign sim world.sdf',''])


def test_shell_text_and_nonsimulator_do_not_match():
    assert not simulator_command(['zsh','-c','gz sim world.sdf'])
    assert not simulator_command(['python3','script.py','some gz sim text'])
    assert not simulator_command(['gz','topic','-l'])
