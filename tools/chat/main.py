import json
import logging
import sys
import traceback
from json import JSONDecodeError

import requests
from flask import Flask, request, jsonify

OLLAMA_API_URL = "http://localhost:11434/api/chat"
self_name = 'chat'

logging.basicConfig(filename=f'{self_name}.log', level=logging.INFO)

app = Flask(self_name)

port = int(sys.argv[1])

# OpenAPI Object for each tool
openapi_objects = {}

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
                "summary": """\
Humans can send a message to a chat bot with this API.
If you are a chat bot, then this is yourself, the chat bot! You can respond directly to the user, or you can invoke this tool to branch out your thinking process recursively.
Be sure to include context on what the user said, and why you are invoking yourself before answering to the user.""",
                "operationId": "chat",
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
                                    "description": "Your message to the chat bot."
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

openapi_objects["chat"] = self_schema


@app.route('/openapi.json', methods=['GET'])
def identify():
    return jsonify(self_schema)

@app.route('/tools/schemas', methods=['GET'])
def get_tools_schemas_route():
    return openapi_objects


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
        {"role": "system", "content": """\
You are a chat bot.
You respond directly to the user.
You have access to a strict list of tools.
Tool outputs are not visible to the user, so you should read their output to answer the user's prompt.
When invoking a tool, you must pick one from the provided list."""},
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

@app.route('/tools', methods=['GET'])
def get_tools_route():
    return get_tools()


def get_tools():
    """Convert OpenAPI Objects to Ollama tools."""
    tools = []
    for name, openapi in openapi_objects.items():
        paths = openapi.get("paths", {})
        for path, operations in paths.items():
            for method, operation in operations.items():
                tool_name = operation.get("operationId", f"{method}_{path.strip('/').replace('/', '_')}")
                app.logger.info(f"Defining tool {tool_name}")
                description = operation.get("summary", f"{method.upper()} {path}")
                parameters = operation.get("parameters", [])
                request_schema = operation.get("requestBody", {}).get("application/json", {}).get("schema", {})
                param_schema = {
                    "type": "object",
                    "properties": {},
                    "required": [],
                }

                # Handle Parameter Objects
                for param in parameters:
                    param_name = param["name"]
                    schema = param.get("schema", {})
                    param_schema["properties"][param_name] = {
                        "type": schema.get("type", "string"),
                        "description": param.get("description", f"parameter {param_name}"),
                    }
                    if param.get("required", False):
                        param_schema["required"].append(param_name)

                # Add body schema if present
                if request_schema:
                    param_schema["properties"].update(request_schema.get("properties", {}))
                    param_schema["required"].extend(request_schema.get("required", []))

                # Remove duplicates in the "required" list
                param_schema["required"] = list(set(param_schema["required"]))

                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": description,
                        "parameters": param_schema,
                    },
                })

    return tools


def ollama(messages, model, temperature):
    data = {
        "model": model,
        "messages": messages,
        "tools": get_tools(),
        "stream": False,
        "options": {
            "temperature": temperature,
        }
    }

    app.logger.info(f"POST {OLLAMA_API_URL}\n{json.dumps(data, indent=4)}")
    response = requests.post(OLLAMA_API_URL, json=data)
    response.raise_for_status()
    app.logger.info(f"Model response:\n{json.dumps(response.json(), indent=4)}")
    return response.json()


def get_schema(server_endpoint):
    openapi = f'{server_endpoint["url"]}/openapi.json'
    app.logger.info(f"GET {openapi}")
    return requests.get(openapi).json()


if __name__ == '__main__':
    try:
        # Read list of OpenAPI Server objects;
        # sys.stdin.read() returns a single line in PyCharm, so we loop
        input_data = [line for line in iter(sys.stdin.readline, '')]
        boot = json.loads(''.join(input_data))
        app.logger.info(json.dumps(boot, indent=4))
        for server in boot["servers"]:
            openapi_objects[server['x-tool']] = get_schema(server)
            app.logger.info(f"Received {server['x-tool']}")
    except JSONDecodeError as e:
        app.logger.error(f"Failed to parse boot JSON\n{traceback.format_exc()}")
    app.run(port=port)
