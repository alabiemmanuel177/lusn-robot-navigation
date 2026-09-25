"""Development-only simulator consuming the exact retained source snapshot."""
import json
import os
from pathlib import Path
import hashlib
from launch import LaunchDescription
from launch.actions import ExecuteProcess, OpaqueFunction, SetEnvironmentVariable
from launch_ros.actions import Node


def setup(context):
    root=Path(os.environ['R3_POSE_BOUND_RUN'])
    plan=json.loads((root/'plan.json').read_bytes())
    if plan['partition']!='development':raise ValueError('development only')
    for path,digest in plan['input_sha256'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:raise ValueError('source changed')
    pose=plan['capture_pose'];tb3='/opt/ros/jazzy/share/nav2_minimal_tb3_sim'
    return [SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH',f'{tb3}/models:/opt/ros/jazzy/share:'+os.environ.get('GZ_SIM_RESOURCE_PATH','')),
        ExecuteProcess(cmd=['gz','sim','-r','-s','--headless-rendering','-v','1','--seed',str(plan['seed']),plan['world']],output='screen'),
        Node(package='ros_gz_sim',executable='create',arguments=['-name','turtlebot3_waffle','-file',str(root/'robot.sdf'),
            '-x',str(pose['x']),'-y',str(pose['y']),'-z','0.01','-Y',str(pose['yaw'])],output='screen'),
        Node(package='ros_gz_bridge',executable='parameter_bridge',parameters=[dict(config_file=str(root/'bridge.yaml'),expand_gz_topic_names=True,use_sim_time=True)],output='screen'),
        Node(package='robot_state_publisher',executable='robot_state_publisher',parameters=[dict(use_sim_time=True,robot_description=(root/'robot.urdf').read_text())],output='screen')]


def generate_launch_description():
    return LaunchDescription([OpaqueFunction(function=setup)])
