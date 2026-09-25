#!/usr/bin/env bash
# Wrapper only: fail before dispatch if ROS environment is incomplete or stale.
set -e
source /opt/ros/jazzy/setup.bash
source /home/eao/risk-calibrated-nav/install/setup.bash
source /home/eao/lusn-robot-navigation/ros_ws/install/setup.bash
export PYTHONPATH=/home/eao/risk-calibrated-nav:/home/eao/lusn-robot-navigation/src:/home/eao/lusn-robot-navigation/scripts:${PYTHONPATH:-}
cd /home/eao/lusn-robot-navigation
python3 - <<'PY'
from ament_index_python.packages import get_package_share_directory as share
from pathlib import Path
import run_live_episode
from class_aware_acquisition_pilot import check_pins
check_pins()
for package, launch in [('language_nav_bringup', 'physical_sim.launch.py'), ('simulation_worlds', 'nav2.launch.py')]:
    path = Path(share(package)) / 'launch' / launch
    if not path.is_file():
        raise RuntimeError(f'Missing launch asset: {path}')
print('Live environment and source preflight passed', flush=True)
PY
exec python3 scripts/class_aware_acquisition_pilot.py execute
