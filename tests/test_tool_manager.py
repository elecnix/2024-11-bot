import unittest
from tool_manager import ToolManager

class TestToolManager(unittest.TestCase):
    def test_discover_tools(self):
        manager = ToolManager()
        self.assertIn('execute_tool', manager.tools)
        self.assertIn('search_tool', manager.tools)

    def test_load_tool(self):
        manager = ToolManager()
        tool = manager.load_tool('execute_tool')
        self.assertTrue(hasattr(tool, 'run'))

if __name__ == '__main__':
    unittest.main()