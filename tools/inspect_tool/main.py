class Tool:
    INPUT_SCHEMA = {
        "tool_name": "string"
    }

    def __init__(self, manager):
        self.manager = manager

    def run(self, inputs):
        tool_name = inputs['tool_name']
        tool_code = self.manager.get_tool_code(tool_name)
        return tool_code