import sys
import os
from flask import Flask, request, jsonify

port = int(sys.argv[1])
servers = {}
self_schema = {
    "openapi": "3.1.0",
    "info": {
        "title": "search_tool",
        "description": "Search for tools by name.",
        "version": "0.0.1",
        "port": port,
        "url": f"http://127.0.0.1:{port}"
    },
    "servers": [
        {
            "url": f"http://127.0.0.1:{port}",
            "description": "Search for tools by name.",
            "x-tool": "search_tool"
        }
    ],
    "paths": {
        "/search": {
            "post": {
                "requestBody": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["query"],
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Query string to search for in tool names."
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
app = Flask('search_tool')
servers["search_tool"] = self_schema


@app.route('/openapi.json', methods=['GET'])
def identify():
    return jsonify(self_schema)


@app.route('/search', methods=['POST'])
def search_tool():
    data = request.json
    query = data['query']
    tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
    all_tools = [name for name in os.listdir(tools_dir) if os.path.isdir(os.path.join(tools_dir, name))]
    matching_tools = [name for name in all_tools if query in name]
    return jsonify({'query': query, 'matching_tools': matching_tools})


if __name__ == '__main__':
    app.run(port=port)
