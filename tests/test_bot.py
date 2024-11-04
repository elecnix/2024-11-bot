import unittest
import json
import os
import sys
import io
from bot import main

class TestBot(unittest.TestCase):
    def test_bot_execution(self):
        user_input = {
            "root_tool": "execute_tool",
            "inputs": {
                "tool_name": "search_tool",
                "tool_inputs": {
                    "query": "execute"
                }
            }
        }
        with open('user_input_test.json', 'w') as f:
            json.dump(user_input, f)
        sys.argv = ['bot.py', 'user_input_test.json']
        captured_output = io.StringIO()
        sys.stdout = captured_output
        main()
        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()
        os.remove('user_input_test.json')
        self.assertIn('execute_tool', output)

if __name__ == '__main__':
    unittest.main()