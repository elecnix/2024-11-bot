import os
import subprocess

class Tool:
    INPUT_SCHEMA = {
        "tool_name": "string",
        "new_code": "string"
    }

    def __init__(self, manager):
        self.manager = manager

    def run(self, inputs):
        tool_name = inputs['tool_name']
        new_code = inputs['new_code']
        tool_path = self.manager.tools.get(tool_name)
        with open(tool_path, 'w') as f:
            f.write(new_code)
        subprocess.run(['git', 'add', tool_path])
        subprocess.run(['git', 'commit', '-m', f"Update tool {tool_name}"])