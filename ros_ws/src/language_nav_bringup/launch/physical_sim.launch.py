"""Research 3-owned seeded server; provider resources are read-only inputs."""
import math
import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET


def configure_camera_fov(expanded, value):
    if value == '':
        return expanded
    fov = float(value)
    if not math.isfinite(fov) or not .5 <= fov <= 2.0:
        raise ValueError('camera horizontal FOV must be within [0.5, 2.0] radians')
    root = ET.fromstring(expanded)
    cameras = root.findall('.//sensor/camera/horizontal_fov')
    if len(cameras) != 2:
        raise ValueError('expected exactly two matched RGB/depth camera FOV fields')
    for camera in cameras:
        camera.text = str(fov)
    return ET.tostring(root, encoding='unicode')

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess, OpaqueFunction,
                            RegisterEventHandler, SetEnvironmentVariable)
from launch.event_handlers import OnShutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def seed_value(value):
    # Same explicit unsigned-nonzero contract as physical_seed_preflight.py.
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
        raise ValueError('simulation_seed must be an explicit unsigned integer')
    seed = int(value)
    if not 1 <= seed <= 2**32 - 1:
        raise ValueError('simulation_seed must be between 1 and 4294967295')
    return seed


def launch_setup(context, *_args, **_kwargs):
    def arg(name):
        return LaunchConfiguration(name).perform(context)

    seed = seed_value(arg('simulation_seed'))
    world = Path(arg('world_path'))
    if not world.is_absolute() or world.suffix != '.sdf' or not world.is_file():
        raise ValueError('world_path must be an existing absolute SDF file')
    provider = Path(arg('research1_root'))
    tb3 = Path(arg('tb3_root'))
    positions = {name: arg(name) for name in ('x_pose', 'y_pose', 'yaw')}
    if any(not math.isfinite(float(value)) for value in positions.values()):
        raise ValueError('start pose must be finite')
    robot = provider / 'src/robot_description/urdf/rcn_waffle.sdf.xacro'
    bridge = provider / 'src/simulation_worlds/config/bridge.yaml'
    urdf = tb3 / 'urdf/turtlebot3_waffle.urdf'
    for resource in (robot, bridge, urdf):
        if not resource.is_file():
            raise FileNotFoundError(resource)
    expanded = subprocess.run(['xacro', str(robot), 'namespace:='],
                              capture_output=True, text=True, check=True).stdout
    expanded = configure_camera_fov(expanded, arg('camera_horizontal_fov'))
    fd, temporary = tempfile.mkstemp(prefix='research3_seeded_robot_', suffix='.sdf')
    with os.fdopen(fd, 'w') as stream:
        stream.write(expanded)

    def cleanup(_context, *_a, **_kw):
        Path(temporary).unlink(missing_ok=True)
        return []

    return [
        RegisterEventHandler(OnShutdown(on_shutdown=[OpaqueFunction(function=cleanup)])),
        SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH',
            f'{tb3}/models:{tb3.parent}:' + os.environ.get('GZ_SIM_RESOURCE_PATH', '')),
        ExecuteProcess(cmd=['gz', 'sim', '-r', '-s', '--headless-rendering', '-v', '1',
                            '--seed', str(seed), str(world)],
                       output='screen', sigterm_timeout='15'),
        Node(package='ros_gz_sim', executable='create', output='screen',
             arguments=['-name', 'turtlebot3_waffle', '-file', temporary,
                        '-x', positions['x_pose'], '-y', positions['y_pose'],
                        '-z', '0.01', '-Y', positions['yaw']]),
        Node(package='ros_gz_bridge', executable='parameter_bridge', output='screen',
             parameters=[{'config_file': str(bridge), 'expand_gz_topic_names': True,
                          'use_sim_time': True}]),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             output='screen', parameters=[{'use_sim_time': True,
                                          'robot_description': urdf.read_text()}]),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('world_path', description='Explicit physical world SDF'),
        DeclareLaunchArgument('simulation_seed', description='Explicit nonzero uint32 seed'),
        DeclareLaunchArgument('camera_horizontal_fov', default_value='',
                             description='Optional matched RGB/depth FOV in radians, engineering capture only'),
        DeclareLaunchArgument('x_pose', default_value='0.6'),
        DeclareLaunchArgument('y_pose', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        DeclareLaunchArgument('research1_root', default_value='/home/eao/risk-calibrated-nav'),
        DeclareLaunchArgument('tb3_root', default_value='/opt/ros/jazzy/share/nav2_minimal_tb3_sim'),
        OpaqueFunction(function=launch_setup),
    ])
