import unittest


class BeliefNodeImportTest(unittest.TestCase):
    def test_belief_node_is_importable(self) -> None:
        from semantic_belief_map.node import BeliefMapNode

        self.assertIsNotNone(BeliefMapNode)
