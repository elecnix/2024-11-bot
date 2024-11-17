import sys

import requests
from flask import Flask, request, jsonify

OLLAMA_API_URL = "http://localhost:11434/api/chat"

tools = {}
app = Flask('chat')

port = int(sys.argv[1])

# OpenAPI Server Objects tools
servers = {}

self_schema = {
    "openapi": "3.1.0",
    "info": {
        "title": "chat",
        "description": "Chat with a bot!",
        "version": "0.0.1",
        "port": port,
        "url": f"http://127.0.0.1:{port}"
    },
    "servers": [
        {
            "url": f"http://127.0.0.1:{port}",
            "description": "Chat with a bot!",
            "x-tool": "chat"
        }
    ],
    "paths": {
        "/chat": {
            "post": {
                "requestBody": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": [
                                "message"
                            ],
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "The user message to send to the chat bot."
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

servers["chat"] = self_schema


@app.route('/openapi.json', methods=['GET'])
def identify():
    return jsonify(self_schema)


@app.route('/chat', methods=['POST'])
def chat():
    tool_input = request.json
    data = {
        "model": tool_input.get("model", "llama3:8b"),
        "messages": [
            {"role": "system", "content": "You are a chat bot."},
            {"role": "user", "content": f"{tool_input['message']}"},
        ],
        "stream": False,
        "options": {
            "temperature": tool_input.get("temperature", 0),
        }
    }
    print(f"POST {OLLAMA_API_URL}{data}")
    response = requests.post(OLLAMA_API_URL, json=data)
    response.raise_for_status()
    return jsonify({'content': response.json()['message']['content']})


if __name__ == '__main__':
    app.run(port=port)
