import unittest


class PlannerNodeImportTest(unittest.TestCase):
    def test_planner_node_is_importable(self) -> None:
        from language_nav_planner.node import PlannerNode

        self.assertIsNotNone(PlannerNode)
