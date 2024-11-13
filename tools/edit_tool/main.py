import sys
import os
import subprocess
from flask import Flask, request, jsonify

port = int(sys.argv[1])
servers = {}
self_schema = {
    "openapi": "3.1.0",
    "info": {
        "title": "edit_tool",
        "description": "Edit an existing tool.",
        "version": "0.0.1",
        "port": port,
        "url": f"http://127.0.0.1:{port}"
    },
    "servers": [
        {
            "url": f"http://127.0.0.1:{port}",
            "description": "Edit an existing tool.",
            "x-tool": "edit_tool"
        }
    ],
    "paths": {
        "/edit": {
            "post": {
                "requestBody": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["tool_name", "new_code"],
                            "properties": {
                                "tool_name": {
                                    "type": "string",
                                    "description": "Name of the tool to edit."
                                },
                                "new_code": {
                                    "type": "string",
                                    "description": "New Python code for the tool."
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
app = Flask('edit_tool')
servers["edit_tool"] = self_schema


@app.route('/openapi.json', methods=['GET'])
def identify():
    return jsonify(self_schema)


@app.route('/edit', methods=['POST'])
def edit_tool():
    data = request.json
    tool_name = data['tool_name']
    new_code = data['new_code']
    tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
    tool_dir = os.path.join(tools_dir, tool_name)
    tool_main_py = os.path.join(tool_dir, 'main.py')
    if not os.path.exists(tool_main_py):
        return jsonify({'error': f'Tool {tool_name} does not exist'}), 404
    with open(tool_main_py, 'w') as f:
        f.write(new_code)
    subprocess.run(['git', 'add', tool_main_py], cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    subprocess.run(['git', 'commit', '-m', f"Update tool {tool_name}"], cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    return jsonify({'status': 'Tool updated', 'tool_name': tool_name})


if __name__ == '__main__':
    app.run(port=port)
