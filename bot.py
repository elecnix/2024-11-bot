import sys
import json
from tool_manager import ToolManager

def main():
    user_input_file = sys.argv[1]
    with open(user_input_file, 'r') as f:
        user_input = json.load(f)
    root_tool_name = user_input['root_tool']
    inputs = user_input['inputs']
    manager = ToolManager()
    root_tool = manager.load_tool(root_tool_name)
    output = root_tool.run(inputs)
    print(output)

if __name__ == "__main__":
    main()