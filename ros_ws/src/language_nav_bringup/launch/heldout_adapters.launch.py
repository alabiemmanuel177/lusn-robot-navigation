"""Separately authorized held-out overlay. Ordinary launch stays unchanged."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from language_nav.physical_heldout_authorization import authorize, pinned, validate_runtime_isolation


def launch_setup(context):
    def arg(name):
        return LaunchConfiguration(name).perform(context)
    authorization = authorize(arg('heldout_authorization'), arg('heldout_authorization_sha256'),
                              arg('heldout_episode_id'))
    validate_runtime_isolation(authorization)
    row = authorization.episode
    world = authorization.root / row['world_directory']
    if (arg('partition') != 'test' or arg('run_id') != row['run_id']
            or arg('system_id') != row['system_id']
            or float(arg('color_tolerance')) != row['camera_color_tolerance']):
        raise PermissionError('held-out launch options differ from authorized episode')
    from pathlib import Path
    report = authorization.root / 'reports/physical_live_episodes' / row['run_id']
    if any(Path(arg('research' + number + '_output_dir')).resolve() != (report / ('research' + number)).resolve()
           for number in ('2', '3')):
        raise PermissionError('held-out outputs must stay inside the authorized R3 episode directory')
    if (Path(arg('scene')).resolve() != (world / 'landmark_scene.yaml').resolve()
            or Path(arg('physical_catalog')).resolve() != (world / 'execution_catalog.json').resolve()
            or Path(arg('calibration')).resolve() != pinned(authorization.root, authorization.approval['calibration']).resolve()):
        raise PermissionError('held-out launch assets differ from authorized episode')
    common = {'use_sim_time': True}
    auth = {key: arg(key) for key in ('heldout_authorization', 'heldout_authorization_sha256', 'heldout_episode_id')}
    physical = {**common, **auth, 'physical_catalog': arg('physical_catalog')}
    return [
        Node(package='failure_monitor', executable='failure_monitor', name='research2_failure_monitor',
             prefix='/home/eao/failure-prediction/.venv/bin/python', parameters=[{**common,
                 'research2_root': '/home/eao/failure-prediction', 'run_id': row['run_id'],
                 'recovery_policy': 'R2', 'output_root': arg('research2_output_dir')}]),
        Node(package='language_nav_runtime', executable='monitor_bridge', name='research2_monitor_bridge', parameters=[common]),
        Node(package='language_nav_bringup', executable='heldout_landmark_bridge', name='research3_landmark_bridge',
             parameters=[{**common, **auth, 'scene': arg('scene'), 'calibration': arg('calibration'),
                          'color_tolerance': row['camera_color_tolerance']}]),
        Node(package='language_interface', executable='instruction_node', name='language_interface', parameters=[common]),
        Node(package='semantic_belief_map', executable='belief_node', name='semantic_belief_map', parameters=[common]),
        Node(package='language_nav_runtime', executable='semantic_route_node', name='semantic_route_provider', parameters=[physical]),
        Node(package='language_nav_runtime', executable='nav2_route_adapter', name='nav2_route_adapter',
             parameters=[{**physical, 'partition': 'test', 'run_id': row['run_id'], 'output_dir': arg('research3_output_dir')}]),
        Node(package='language_nav_planner', executable='planner_node', name='language_nav_planner',
             parameters=[{**physical, 'require_failure_monitor': True, 'system_id': row['system_id'],
                          'failure_monitor_timeout_s': 3., 'failure_monitor_ready_timeout_s': 120.}]),
    ]


def generate_launch_description():
    names = ('heldout_authorization', 'heldout_authorization_sha256', 'heldout_episode_id',
             'scene', 'physical_catalog', 'calibration', 'partition', 'run_id', 'system_id',
             'color_tolerance', 'research2_output_dir', 'research3_output_dir')
    return LaunchDescription([*(DeclareLaunchArgument(name) for name in names),
                              OpaqueFunction(function=launch_setup)])
