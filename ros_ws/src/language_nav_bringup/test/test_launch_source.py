from pathlib import Path
import unittest


class LaunchSourceTest(unittest.TestCase):
    def test_bringup_launches_all_three_pipeline_nodes(self) -> None:
        source = (Path(__file__).parents[1] / "launch" / "graph_world.launch.py").read_text()
        self.assertIn('package="language_interface"', source)
        self.assertIn('package="semantic_belief_map"', source)
        self.assertIn('package="language_nav_planner"', source)

    def test_research1_landmark_launch_adds_versioned_bridge(self) -> None:
        source = (Path(__file__).parents[1] / "launch" / "research1_landmarks.launch.py").read_text()
        runner = (Path(__file__).parents[1] / "language_nav_bringup" / "landmark_bridge_runner.py").read_text()
        self.assertIn('executable="landmark_bridge_runner"', source)
        self.assertIn("LandmarkObservationNode", runner)
        self.assertIn("MultiThreadedExecutor", runner)
        self.assertIn('LaunchConfiguration("scene")', source)
        self.assertIn('LaunchConfiguration("calibration")', source)
        self.assertIn('LaunchConfiguration("review_log")', source)
        self.assertIn('LaunchConfiguration("color_tolerance")', source)
