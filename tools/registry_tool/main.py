import json
import logging
import os
import signal
import socket
import subprocess
import sys
from pathlib import Path
from time import sleep
from typing import Dict

import requests
from flask import Flask, request, jsonify
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

self_name = 'registry_tool'
self_description = "Registry that can start tools."

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(filename=f'registry_tool.log', level=logging.INFO)

# Registry of subprocess tools
processes = {}

# OpenAPI Object for each tool
openapi_objects: Dict[str, Dict] = {}

app = Flask(self_name)
port = int(sys.argv[1])

retry_strategy = Retry(connect=10, backoff_factor=1)

adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("http://", adapter)


def start_tool(tool_name):
    tool_port = find_free_port()
    app.logger.info(f"Starting '{tool_name}' on port {tool_port}")
    process = subprocess.Popen(
        ['python', 'main.py', str(tool_port)],
        cwd=os.path.join('..', tool_name),
        stdin=subprocess.PIPE
    )
    servers = [srv for openapi in openapi_objects.values() for srv in openapi["servers"]]
    process.stdin.write(json.dumps({'servers': servers}).encode('utf-8'))
    process.stdin.close()
    sleep(1)
    return register_tool_process(tool_port, process, tool_name)


def register_tool_process(tool_port, process, tool_name):
    url = f'http://localhost:{tool_port}'
    app.logger.info(f"Registering '{tool_name}' at {url}")
    tool = get_tool_handle(url, tool_name)
    tool.update({'process': process})
    processes[tool_name] = tool
    openapi_objects[tool_name] = tool['get']('/openapi.json')
    return openapi_objects[tool_name]


def get_tool_handle(url, tool_name):
    def post(data, resource='/'):
        endpoint = f'{url}{resource}'
        app.logger.info(f"{tool_name} POST {endpoint} \n{data}")
        return session.post(endpoint, json=data).json()

    def get(resource='/'):
        endpoint = f'{url}{resource}'
        app.logger.info(f"{tool_name} GET {endpoint}")
        return session.get(endpoint).json()

    return {'get': get, 'post': post}


def find_free_port():
    s = socket.socket()
    s.bind(('', 0))
    free_port = s.getsockname()[1]
    s.close()
    return free_port


@app.route('/openapi.json', methods=['GET'])
def schema_route():
    """Self-report tool identification."""
    return jsonify(self_schema(request.host))


def self_schema(host):
    response = {
        "openapi": "3.1.0",
        "info": {
            "title": "registry_tool",
            "description": self_description,
            "version": "0.0.1",
            "port": port,
            "url": f"http://{host}:{port}"
        },
        "servers": [{"url": f"http://127.0.0.1:{port}", "description": self_description, "x-tool": self_name}],
        "paths": {
            "/start": {
                "post": {
                    "summary": "Start a tool, adding it to the registry.",
                    "operationId": "start_tool",
                    "requestBody": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": [
                                    "name"
                                ],
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "The name of the tool to start, which corresponds to the name of the directory containing a main.py file."
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Tool has been started.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "https://json-schema.org/draft/2020-12/schema"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/list": {
                "get": {
                    "operationId": "list_tools",
                    "summary": "List the available tools.",
                    "description": "Once a tool has been started, it should be listed in the response."
                }
            }
        }
    }
    return response


@app.route('/start', methods=['POST'])
def start_tool_route():
    """Endpoint to start a tool via HTTP POST request, returning its OpenAPI schema."""
    tool_name = request.json['name']
    if tool_name not in processes.keys():
        start_tool(tool_name)
    return openapi_objects[tool_name]


@app.route('/list', methods=['GET'])
def list_tools_route():
    """List the currently running tools."""
    tool_names = sorted(os.listdir('..'))
    tools = {}
    for tool_name in tool_names:
        if '__pycache__' in tool_name:
            continue
        status = "Stopped"
        info = None
        if tool_name in openapi_objects.keys():
            status = "Started"
            info = openapi_objects[tool_name]['info']
        tools[tool_name] = {
            "status": status,
            "info": info
        }

    return jsonify(tools)


@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Endpoint to shut down the server and terminate all tools this server has started."""
    for tool_info in processes.values():
        tool_process = tool_info.get('process')
        if tool_process:
            os.kill(tool_process.pid, signal.SIGTERM)
            tool_process.wait()
    logging.info("Shutdown complete")
    exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda signum, frame: shutdown())
    signal.signal(signal.SIGINT, lambda signum, frame: shutdown())
    openapi_objects[self_name] = self_schema('localhost')
    app.run(port=port)
