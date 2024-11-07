# bot.py
import json
import os
import socket
import subprocess
import sys
import time


def main():
    user_input = read_user_input()
    tool_name = user_input['tool']
    coins = user_input.get('coins', 100)
    search_tool_port = start_tool('search_tool', {}, coins, {})
    time.sleep(1)
    accessible_tools = {
        'search_tool': {
            'description': "Search for tools",
            'port': search_tool_port,
        },
    }
    start_tool(tool_name, user_input, coins, accessible_tools)


def read_user_input():
    if len(sys.argv) < 2:
        content = input("prompt> ")
    else:
        user_input_file = sys.argv[1]
        with open(user_input_file, 'r') as f:
            content = f.read()
    try:
        user_input = json.loads(content)
    except json.JSONDecodeError:
        user_input = {"tool": "chat", "inputs": {"text_input": content}}
    return user_input


def start_tool(tool_name, tool_input, coins, accessible_tools):
    tool_dir = os.path.join('tools', tool_name)
    tool_script = os.path.join(tool_dir, 'main.py')
    port = find_free_port()
    process = subprocess.Popen(
        ['python', tool_script, str(port)],
        stdin=subprocess.PIPE
    )
    input_data = {
        'input': tool_input,
        'coins': coins,
        'tools': accessible_tools
    }
    process.stdin.write(json.dumps(input_data).encode('utf-8'))
    process.stdin.close()
    return port


def find_free_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


if __name__ == '__main__':
    main()
