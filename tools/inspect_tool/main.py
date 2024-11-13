import sys
import os
from flask import Flask, request, jsonify

port = int(sys.argv[1])
servers = {}
self_schema = {
    "openapi": "3.1.0",
    "info": {
        "title": "inspect_tool",
        "description": "Inspect the code of a tool.",
        "version": "0.0.1",
        "port": port,
        "url": f"http://127.0.0.1:{port}"
    },
    "servers": [
        {
            "url": f"http://127.0.0.1:{port}",
            "description": "Inspect the code of a tool.",
            "x-tool": "inspect_tool"
        }
    ],
    "paths": {
        "/inspect": {
            "post": {
                "requestBody": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["tool_name"],
                            "properties": {
                                "tool_name": {
                                    "type": "string",
                                    "description": "Name of the tool to inspect."
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
app = Flask('inspect_tool')
servers["inspect_tool"] = self_schema


@app.route('/openapi.json', methods=['GET'])
def identify():
    return jsonify(self_schema)


@app.route('/inspect', methods=['POST'])
def inspect_tool():
    data = request.json
    tool_name = data['tool_name']
    tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
    tool_main_py = os.path.join(tools_dir, tool_name, 'main.py')
    if not os.path.exists(tool_main_py):
        return jsonify({'error': f'Tool {tool_name} does not exist'}), 404
    with open(tool_main_py, 'r') as f:
        tool_code = f.read()
    return jsonify({'tool_name': tool_name, 'tool_code': tool_code})


if __name__ == '__main__':
    app.run(port=port)
