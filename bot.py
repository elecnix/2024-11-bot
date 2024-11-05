# bot.py
import sys
import json
from tool_manager import ToolManager

def load_user_input(user_input_file):
    with open(user_input_file, 'r') as f:
        content = f.read()
        try:
            user_input = json.loads(content)
        except json.JSONDecodeError:
            user_input = {"root_tool": "default_tool", "inputs": {"text_input": content}}
    return user_input

def main():
    user_input_file = sys.argv[1]
    user_input = load_user_input(user_input_file)
    root_tool_name = user_input['root_tool']
    inputs = user_input['inputs']
    manager = ToolManager()
    root_tool = manager.load_tool(root_tool_name)
    output = root_tool.run(inputs)
    print(output)

if __name__ == "__main__":
    main()
