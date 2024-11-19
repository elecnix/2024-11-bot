import logging
import re
import subprocess
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
        "/inspect/{tool_name}": {
            "get": {
                "summary": "Get the source code of a tool.",
                "operationId": "inspect_tool",
                "description": "Retrieve information about a specified tool, including its file structure and contents.",
                "parameters": [
                    {
                        "name": "tool_name",
                        "in": "path",
                        "description": "The name of the tool to inspect.",
                        "required": True,
                        "schema": {
                            "type": "string"
                        }
                    }
                ],
            }
        }
    }
}
app = Flask('inspect_tool')
servers["inspect_tool"] = self_schema


@app.route('/openapi.json', methods=['GET'])
def identify():
    return jsonify(self_schema)


@app.route('/inspect/<tool_name>', methods=['GET'])
def inspect_tool(tool_name: str):
    tool_name = re.sub(r'[^a-zA-Z_]', '', tool_name)
    tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
    tool_dir = os.path.join(tools_dir, tool_name)
    if not os.path.exists(tool_dir):
        return jsonify({'error': f'Tool {tool_name} does not exist'}), 404
    return jsonify({'tool_name': tool_name, 'code': generate_tree_dict(tool_dir)})


def get_git_tracked_files(path):
    """Get a list of all files tracked by Git within the specified directory."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=path,
            text=True,
            capture_output=True,
            check=True
        )
        tracked_files = result.stdout.splitlines()
        return set(tracked_files)
    except subprocess.CalledProcessError:
        logging.warning(f"Error: The specified directory '{path}' not a Git repository.")
        return set()


def build_tree_dict(path, tracked_files, base_path):
    """Build a dictionary representing the directory tree, including file contents."""
    tree = {}
    items = sorted(os.listdir(path))

    for item in items:
        item_path = os.path.join(path, item)
        relative_item_path = os.path.relpath(item_path, base_path)

        if os.path.isdir(item_path):
            # Check if any tracked file exists in this directory or its subdirectories
            if any(f.startswith(relative_item_path + os.sep) for f in tracked_files):
                tree[item] = build_tree_dict(item_path, tracked_files, base_path)
        elif os.path.isfile(item_path) and relative_item_path in tracked_files:
            # Read file content
            try:
                with open(item_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                tree[item] = {'content': content}
            except Exception as e:
                tree[item] = f"Error reading file: {e}"

    return tree


def generate_tree_dict(path="."):
    """Generate a dictionary representation of the directory tree with Git-tracked files and their contents."""
    tracked_files = get_git_tracked_files(path)
    if not tracked_files:
        return {}

    tree_dict = build_tree_dict(path, tracked_files, path)
    return tree_dict


if __name__ == '__main__':
    app.run(port=port)
