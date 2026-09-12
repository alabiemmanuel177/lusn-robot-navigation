import unittest


class RuntimeNodeImportTest(unittest.TestCase):
    def test_runtime_nodes_are_importable(self) -> None:
        from language_nav_runtime.monitor_bridge import Research2MonitorBridge
        from language_nav_runtime.nav2_adapter import Nav2RouteAdapter
        from language_nav_runtime.semantic_routes import SemanticRouteNode

        self.assertTrue(Research2MonitorBridge)
        self.assertTrue(Nav2RouteAdapter)
        self.assertTrue(SemanticRouteNode)
