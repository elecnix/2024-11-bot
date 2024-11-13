import sys
import os
import subprocess
from flask import Flask, request, jsonify

port = int(sys.argv[1])
servers = {}
self_schema = {
    "openapi": "3.1.0",
    "info": {
        "title": "list_tool_versions",
        "description": "List the versions of a tool.",
        "version": "0.0.1",
        "port": port,
        "url": f"http://127.0.0.1:{port}"
    },
    "servers": [
        {
            "url": f"http://127.0.0.1:{port}",
            "description": "List the versions of a tool.",
            "x-tool": "list_tool_versions"
        }
    ],
    "paths": {
        "/versions": {
            "post": {
                "requestBody": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["tool_name"],
                            "properties": {
                                "tool_name": {
                                    "type": "string",
                                    "description": "Name of the tool to list versions for."
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
app = Flask('list_tool_versions')
servers["list_tool_versions"] = self_schema


@app.route('/openapi.json', methods=['GET'])
def identify():
    return jsonify(self_schema)


@app.route('/versions', methods=['POST'])
def list_tool_versions():
    data = request.json
    tool_name = data['tool_name']
    tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
    tool_main_py = os.path.join(tools_dir, tool_name, 'main.py')
    if not os.path.exists(tool_main_py):
        return jsonify({'error': f'Tool {tool_name} does not exist'}), 404
    result = subprocess.run(
        ['git', 'log', '--oneline', tool_main_py],
        stdout=subprocess.PIPE,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    )
    if result.returncode != 0:
        return jsonify({'error': 'Failed to get git log'}), 500
    versions = result.stdout.decode('utf-8').splitlines()
    return jsonify({'tool_name': tool_name, 'versions': versions})


if __name__ == '__main__':
    app.run(port=port)
