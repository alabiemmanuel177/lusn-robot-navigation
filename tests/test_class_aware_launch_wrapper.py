from pathlib import Path
import subprocess


def test_launcher_is_valid_bash_and_preflights_before_execute():
    path = Path(__file__).resolve().parents[1] / 'scripts/launch_class_aware_pilot.sh'
    subprocess.run(['bash', '-n', str(path)], check=True)
    text = path.read_text()
    assert text.startswith('#!/usr/bin/env bash\n')
    assert 'set -e\n' in text
    assert 'lusn-robot-navigation/ros_ws/install/setup.bash' in text
    assert 'lusn-robot-navigation/install/setup.bash' not in text
    assert text.index('check_pins()') < text.index('exec python3')
    assert text.index('if not path.is_file():') < text.index('exec python3')
    assert 'physical_sim.launch.py' in text and 'nav2.launch.py' in text
