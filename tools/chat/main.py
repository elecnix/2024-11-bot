import sys
import traceback

import requests
from flask import Flask, request, jsonify
import json

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


def call_tool(tool_call):
    name = tool_call["function"]["name"]
    try:
        return {"role": "tool", "content": f"Error! No such tool: {name}"}
    except Exception as e:
        return {"role": "tool", "content": f"Error invoking tool:\n{traceback.format_exc()}"}


@app.route('/chat', methods=['POST'])
def chat():
    tool_input = request.json
    model = tool_input.get("model", "llama3.1:8b")
    message = tool_input['message']
    messages = [
        {"role": "system", "content": "You are a chat bot."},
        {"role": "user", "content": f"{message}"},
    ]
    temperature = tool_input.get("temperature", 0)
    model_response = ollama(messages, model, temperature)
    while 'tool_calls' in model_response['message']:
        messages.append(model_response['message'])
        for tool_call in model_response['message']['tool_calls']:
            messages.append(call_tool(tool_call))
        model_response = ollama(messages, model, temperature)

    return jsonify({'content': model_response['message']['content']})


def ollama(messages, model, temperature):
    data = {
        "model": model,
        "messages": messages,
        "tools": [
            {
                'type': 'function',
                'function': {
                    'name': 'get_current_weather',
                    'description': 'Get the current weather for a city',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'city': {
                                'type': 'string',
                                'description': 'The name of the city',
                            },
                        },
                        'required': ['city'],
                    },
                },
            }
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
        }
    }

    print(f"POST {OLLAMA_API_URL}\n{json.dumps(data, indent=4)}")
    response = requests.post(OLLAMA_API_URL, json=data)
    response.raise_for_status()
    print(f"Model response:\n{json.dumps(response.json(), indent=4)}")
    return response.json()


if __name__ == '__main__':
    app.run(port=port)
