import os
import subprocess

class Tool:
    INPUT_SCHEMA = {
        "tool_name": "string",
        "tool_code": "string"
    }

    def __init__(self, manager):
        self.manager = manager

    def run(self, inputs):
        tool_name = inputs['tool_name']
        tool_code = inputs['tool_code']
        tool_path = os.path.join(self.manager.tools_directory, f"{tool_name}.py")
        with open(tool_path, 'w') as f:
            f.write(tool_code)
        subprocess.run(['git', 'add', tool_path])
        subprocess.run(['git', 'commit', '-m', f"Add tool {tool_name}"])
        self.manager.tools[tool_name] = tool_path