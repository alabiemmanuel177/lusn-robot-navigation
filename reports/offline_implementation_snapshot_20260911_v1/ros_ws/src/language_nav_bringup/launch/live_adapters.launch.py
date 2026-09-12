"""Research 3 live overlay for an already-running Research 1 Gazebo/Nav2 stack."""
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    common = {"use_sim_time": True}
    research2_root = os.environ.get("RESEARCH2_ROOT", "/home/eao/failure-prediction")
    monitor_python = PathJoinSubstitution([LaunchConfiguration("research2_root"), ".venv", "bin", "python"])
    return LaunchDescription([
        DeclareLaunchArgument("scene"),
        DeclareLaunchArgument("semantic_catalog", default_value=""),
        DeclareLaunchArgument("physical_catalog", default_value=""),
        DeclareLaunchArgument("partition", default_value="development"),
        DeclareLaunchArgument("research1_root", default_value="/home/eao/risk-calibrated-nav"),
        DeclareLaunchArgument("research2_root", default_value=research2_root),
        DeclareLaunchArgument("calibration", default_value=""),
        DeclareLaunchArgument("review_log", default_value=""),
        DeclareLaunchArgument("color_tolerance", default_value="38.0"),
        DeclareLaunchArgument("run_id"),
        DeclareLaunchArgument("system_id", default_value="B6"),
        DeclareLaunchArgument("research2_output_dir", default_value=""),
        DeclareLaunchArgument("research3_output_dir", default_value=""),
        Node(
            package="failure_monitor",
            executable="failure_monitor",
            name="research2_failure_monitor",
            prefix=monitor_python,
            parameters=[{
                **common,
                "research2_root": LaunchConfiguration("research2_root"),
                "run_id": LaunchConfiguration("run_id"),
                "recovery_policy": "R2",
                "output_root": LaunchConfiguration("research2_output_dir"),
            }],
        ),
        Node(
            package="language_nav_runtime",
            executable="monitor_bridge",
            name="research2_monitor_bridge",
            parameters=[common],
        ),
        Node(
            package="language_nav_bringup",
            executable="landmark_bridge_runner",
            name="research3_landmark_bridge",
            parameters=[{
                **common,
                "scene": LaunchConfiguration("scene"),
                "calibration": LaunchConfiguration("calibration"),
                "review_log": LaunchConfiguration("review_log"),
                "color_tolerance": ParameterValue(LaunchConfiguration("color_tolerance"), value_type=float),
            }],
        ),
        Node(
            package="language_interface",
            executable="instruction_node",
            name="language_interface",
            parameters=[common],
        ),
        Node(
            package="semantic_belief_map",
            executable="belief_node",
            name="semantic_belief_map",
            parameters=[common],
        ),
        Node(
            package="language_nav_runtime",
            executable="semantic_route_node",
            name="semantic_route_provider",
            parameters=[{
                **common,
                "catalog": LaunchConfiguration("semantic_catalog"),
                "physical_catalog": LaunchConfiguration("physical_catalog"),
                "research1_repository": LaunchConfiguration("research1_root"),
            }],
        ),
        Node(
            package="language_nav_runtime",
            executable="nav2_route_adapter",
            name="nav2_route_adapter",
            parameters=[{
                **common,
                "partition": LaunchConfiguration("partition"),
                "physical_catalog": LaunchConfiguration("physical_catalog"),
                "research1_repository": LaunchConfiguration("research1_root"),
                "run_id": LaunchConfiguration("run_id"),
                "output_dir": LaunchConfiguration("research3_output_dir"),
            }],
        ),
        Node(
            package="language_nav_planner",
            executable="planner_node",
            name="language_nav_planner",
            parameters=[{
                **common,
                "require_failure_monitor": True,
                "physical_catalog": LaunchConfiguration("physical_catalog"),
                "system_id": LaunchConfiguration("system_id"),
                "failure_monitor_timeout_s": 3.0,
                "failure_monitor_ready_timeout_s": 120.0,
            }],
        ),
    ])
