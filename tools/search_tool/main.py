class Tool:
    INPUT_SCHEMA = {
        "query": "string"
    }

    def __init__(self, manager):
        self.manager = manager

    def run(self, inputs):
        query = inputs['query']
        matching_tools = []
        for tool_name in self.manager.tools.keys():
            if query in tool_name:
                matching_tools.append(tool_name)
        return matching_tools