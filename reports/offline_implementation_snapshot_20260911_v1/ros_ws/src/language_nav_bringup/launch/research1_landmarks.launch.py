"""Bring up the Research 3 pipeline with the opt-in Research 1 landmark producer."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("scene"),
        DeclareLaunchArgument("calibration", default_value=""),
        DeclareLaunchArgument("review_log", default_value=""),
        DeclareLaunchArgument("color_tolerance", default_value="38.0"),
        Node(
            package="language_nav_bringup",
            executable="landmark_bridge_runner",
            name="research3_landmark_bridge",
            parameters=[{
                "use_sim_time": True,
                "scene": LaunchConfiguration("scene"),
                "calibration": LaunchConfiguration("calibration"),
                "review_log": LaunchConfiguration("review_log"),
                "color_tolerance": LaunchConfiguration("color_tolerance"),
            }],
        ),
        Node(
            package="language_interface",
            executable="instruction_node",
            name="language_interface",
            parameters=[{"use_sim_time": True}],
        ),
        Node(
            package="semantic_belief_map",
            executable="belief_node",
            name="semantic_belief_map",
            parameters=[{"use_sim_time": True}],
        ),
        Node(
            package="language_nav_planner",
            executable="planner_node",
            name="language_nav_planner",
            parameters=[{"use_sim_time": True}],
        ),
    ])
