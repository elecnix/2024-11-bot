import os
import importlib.util

class ToolManager:
    def __init__(self, tools_directory='tools'):
        self.tools_directory = tools_directory
        self.tools = self.discover_tools()

    def discover_tools(self):
        tools = {}
        for filename in os.listdir(self.tools_directory):
            if filename.endswith('.py'):
                tool_name = filename[:-3]
                tools[tool_name] = os.path.join(self.tools_directory, filename)
        return tools

    def load_tool(self, tool_name):
        tool_path = self.tools.get(tool_name)
        spec = importlib.util.spec_from_file_location(tool_name, tool_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.Tool(self)

    def get_tool_code(self, tool_name):
        tool_path = self.tools.get(tool_name)
        with open(tool_path, 'r') as f:
            code = f.read()
        return code