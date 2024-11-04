class Tool:
    INPUT_SCHEMA = {
        "tool_name": "string",
        "tool_inputs": "dict"
    }

    def __init__(self, manager):
        self.manager = manager

    def run(self, inputs):
        tool_name = inputs['tool_name']
        tool_inputs = inputs['tool_inputs']
        tool = self.manager.load_tool(tool_name)
        return tool.run(tool_inputs)