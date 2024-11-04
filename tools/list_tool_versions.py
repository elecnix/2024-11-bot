import subprocess

class Tool:
    INPUT_SCHEMA = {
        "tool_name": "string"
    }

    def __init__(self, manager):
        self.manager = manager

    def run(self, inputs):
        tool_name = inputs['tool_name']
        tool_path = self.manager.tools.get(tool_name)
        result = subprocess.run(['git', 'log', '--oneline', tool_path], stdout=subprocess.PIPE)
        return result.stdout.decode('utf-8')