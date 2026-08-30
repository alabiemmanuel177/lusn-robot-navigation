from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(package="language_interface", executable="instruction_node", name="language_interface"),
            Node(package="semantic_belief_map", executable="belief_node", name="semantic_belief_map"),
            Node(package="language_nav_planner", executable="planner_node", name="language_nav_planner"),
        ]
    )

