import unittest
from tool_manager import ToolManager

class TestExecuteTool(unittest.TestCase):
    def test_execute_tool(self):
        manager = ToolManager()
        execute_tool = manager.load_tool('execute_tool')
        inputs = {
            "tool_name": "search_tool",
            "tool_inputs": {
                "query": "execute"
            }
        }
        output = execute_tool.run(inputs)
        self.assertIn('execute_tool', output)

if __name__ == '__main__':
    unittest.main()