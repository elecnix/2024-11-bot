import sys
import os
import subprocess
from flask import Flask, request, jsonify

port = int(sys.argv[1])
servers = {}
self_schema = {
    "openapi": "3.1.0",
    "info": {
        "title": "create_tool",
        "description": "Create a new tool.",
        "version": "0.0.1",
        "port": port,
        "url": f"http://127.0.0.1:{port}"
    },
    "servers": [
        {
            "url": f"http://127.0.0.1:{port}",
            "description": "Create a new tool.",
            "x-tool": "create_tool"
        }
    ],
    "paths": {
        "/create": {
            "post": {
                "requestBody": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["tool_name", "tool_code"],
                            "properties": {
                                "tool_name": {
                                    "type": "string",
                                    "description": "Name of the tool to create."
                                },
                                "tool_code": {
                                    "type": "string",
                                    "description": "Python code for the tool."
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
app = Flask('create_tool')
servers["create_tool"] = self_schema


@app.route('/openapi.json', methods=['GET'])
def identify():
    return jsonify(self_schema)


@app.route('/create', methods=['POST'])
def create_tool():
    data = request.json
    tool_name = data['tool_name']
    tool_code = data['tool_code']
    tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
    tool_dir = os.path.join(tools_dir, tool_name)
    os.makedirs(tool_dir, exist_ok=True)
    tool_main_py = os.path.join(tool_dir, 'main.py')
    with open(tool_main_py, 'w') as f:
        f.write(tool_code)
    subprocess.run(['git', 'add', tool_main_py], cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    subprocess.run(['git', 'commit', '-m', f"Add tool {tool_name}"], cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    return jsonify({'status': 'Tool created', 'tool_name': tool_name})


if __name__ == '__main__':
    app.run(port=port)
