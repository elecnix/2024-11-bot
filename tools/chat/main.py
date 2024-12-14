import json
import logging
import os
import sys
import traceback
from json import JSONDecodeError

import requests
from flask import Flask, request, jsonify, make_response

OLLAMA_API_URL = "http://localhost:11434/api/chat"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
self_name = 'chat'
tool_blacklist = [self_name] # Don't allow self-calls, the LLM gets too confused.

logging.basicConfig(filename=f'{self_name}.log', level=logging.INFO)

app = Flask(self_name)

port = int(sys.argv[1])

# OpenAPI Object for each tool
openapi_objects = {}

self_schema = {
    "openapi": "3.1.0",
    "info": {
        "title": "chat",
        "description": "Tool that uses Ollama",
        "version": "0.0.1",
        "port": port,
        "url": f"http://127.0.0.1:{port}"
    },
    "servers": [
        {
            "url": f"http://127.0.0.1:{port}",
            "description": "Tool that uses Ollama",
            "x-tool": "chat"
        }
    ],
    "paths": {
        "/chat": {
            "post": {
                "summary": """Instruct a large language model on what to do. Be sure to describe the user's intend.""",
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
                                    "description": "Your instruction to the LLM."
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


def call_tool(tool_call, tool_depth=0):
    """Maps a tool call to an operation on an OpenAPI object."""
    invoked_name = tool_call["function"]["name"]
    try:
        for tool_name, openapi in openapi_objects.items():
            tool_schema = openapi_objects[tool_name]

            # Find the correct path and method matching the operationId
            matching_path = None
            matching_method = None
            for path, operations in tool_schema["paths"].items():
                for method, operation in operations.items():
                    if operation.get("operationId") == invoked_name:
                        matching_path = path
                        matching_method = method
                        break
                if matching_path:
                    break

            if not matching_path or not matching_method:
                continue  # Try the next tool

            # Construct the endpoint URL
            tool_url = tool_schema["servers"][0]["url"]  # Assuming the first server URL is valid
            endpoint = f"{tool_url}{matching_path}"

            # Extract parameters from the tool_call
            tool_parameters = tool_call["function"].get("arguments", {})

            headers = {"X-Tool-Depth": str(tool_depth + 1)}

            # Issue the appropriate HTTP request (currently supports POST)
            if matching_method.lower() == "post":
                app.logger.info(f"POST {endpoint} tool_depth={tool_depth}\n{json.dumps(tool_parameters, indent=4)}")
                response = requests.post(endpoint, json=tool_parameters, headers=headers)
            elif matching_method.lower() == "get":
                app.logger.info(f"GET {endpoint} with params {json.dumps(tool_parameters, indent=4)}")
                response = requests.get(endpoint, params=tool_parameters, headers=headers)
            else:
                return {"role": "tool", "content": f"Unsupported HTTP method: {matching_method}"}

            response.raise_for_status()
            result = response.json()

            return {"role": "tool", "content": json.dumps(result, indent=4)}
    except Exception:
        app.logger.error(f"Error invoking tool:\n{traceback.format_exc()}")
        return {"role": "tool", "content": f"Error invoking tool:\n{traceback.format_exc()}"}
    return {"role": "tool", "content": f"Error! No matching path or method for tool: {invoked_name}"}


def request_tool(tool_call):
    """A virtual tool that adds a tool to the LLM context."""
    tool_url = tool_call["function"]["arguments"]["url"]
    schema = get_schema(tool_url)
    tool_name = openapi_objects[schema["title"]]
    openapi_objects[tool_name] = schema
    app.logger.info(f"Received {tool_name}")
    return {"role": "tool", "content": "Tool {tool_name} has been added to the context."}


@app.route('/chat', methods=['POST'])
def chat_route():
    tool_input = request.json
    tool_depth = int(request.headers.get("X-Tool-Depth", 0))
    if tool_depth > 3:
        return jsonify({'content': "You have reached the maximum depth of chat calls!"})
    model = tool_input.get("model", "llama3.1:8b")
    message = tool_input['message']
    messages = [
        {"role": "system", "content": """\
You are a chat bot that responds directly to the human user.
In some cases, the user may make a request that requires the use of tools.
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
            invoked_name = tool_call["function"]["name"]
            # LLMs like to respond with a tool, so we give it one.
            if invoked_name == "request_tool":
                messages.append(request_tool(tool_call))
            else:
                messages.append(call_tool(tool_call, tool_depth))
        model_response = ollama(messages, model, temperature)

    response = make_response(jsonify({'content': model_response['message']['content']}))
    response.headers['X-Tool-Depth'] = tool_depth
    return response


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
                if tool_name in tool_blacklist:
                    continue
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

    # Add a virtual tool that registers a running tool into the LLM context.
    tools.append({
        "type": "function",
        "function": {
            "name": "request_tool",
            "description": "Request access to a tool, given its URL. The tool must be started (running) and serve `/openapi.json`. If successful, the tool name will become invocable by the LLM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string"
                    }
                },
                "required": ["url"],
            },
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
    url = OPENAI_URL
    #url = OLLAMA_API_URL
    app.logger.info(f"POST {url}\n{json.dumps(data, indent=4)}")
    key = os.getenv('OPENAI_API_KEY')
    headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
    }
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    app.logger.info(f"Model response:\n{json.dumps(response.json(), indent=4)}")
    return response.json()


def get_schema(url):
    openapi = f'{url}/openapi.json'
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
            openapi_objects[server['x-tool']] = get_schema(server["url"])
            app.logger.info(f"Received {server['x-tool']}")
    except JSONDecodeError as e:
        app.logger.error(f"Failed to parse boot JSON\n{traceback.format_exc()}")
    app.run(port=port)
