import unittest


class InstructionNodeImportTest(unittest.TestCase):
    def test_instruction_node_is_importable(self) -> None:
        from language_interface.node import InstructionNode

        self.assertIsNotNone(InstructionNode)
