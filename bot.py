import argparse
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

self_name = 'tool_registry'
self_description = "Registry that can start a tool."

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(filename=f'logs/bot.log', level=logging.INFO)

# Registry of subprocess tools
processes = {}

# OpenAPI Object for each tool
openapi_objects: Dict[str, Dict] = {}

app = Flask(self_name)

retry_strategy = Retry(connect=10, backoff_factor=1)

adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("http://", adapter)


### Interactive functions

def interactive(port: int):
    subprocess_server(port)
    while True:
        try:
            user_input = read_user_input()
            tool = get_tool(user_input['tool'])
            response = tool['post'](user_input['input'], resource=user_input['resource'])
            print(response['content'])
        except KeyboardInterrupt:
            app.logger.warning("Keyboard Interrupt")
            shutdown()
        except Exception as e:
            app.logger.exception("Exception in interactive mode")
            shutdown()
            return


def subprocess_server(port: int):
    app.logger.info(f"Starting server process on port {port}")
    with open(f"logs/bot-server.log", "w") as log_file:
        process = subprocess.Popen(
            ['python', __file__, '--server', '-p', str(port)],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True  # Detach process from the parent
        )
    app.logger.info(f"Started server: pid {process.pid}, port {port}")
    # Interactive mode: this is the only tool we'll register
    return register_tool_process(port, process, self_name)


def read_user_input():
    content = input("input: ")
    try:
        user_input = json.loads(content)
    except json.JSONDecodeError:
        user_input = {"tool": "chat", "resource": "/chat", "input": {"message": content}}
    return user_input


def get_tool(tool_name):
    if tool_name in processes.keys():
        return processes[tool_name]
    return delegate_start_tool(tool_name)


def delegate_start_tool(tool_name):
    """Delegate the task of starting a tool to the server."""
    openapi = processes[self_name]['post']({"name": tool_name}, '/start')
    return get_tool_handle(openapi["servers"][0]["url"], tool_name)


### Server functions

def start_tool(tool_name, port: int = None):
    port = port if port else find_free_port()
    app.logger.info(f"Starting '{tool_name}' on port {port}")
    process = subprocess.Popen(
        ['python', 'main.py', str(port)],
        cwd=os.path.join('tools', tool_name),
        stdin=subprocess.PIPE
    )
    servers = [srv for openapi in openapi_objects.values() for srv in openapi["servers"]]
    process.stdin.write(json.dumps({'servers': servers}).encode('utf-8'))
    process.stdin.close()
    sleep(1)
    return register_tool_process(port, process, tool_name)


def register_tool_process(port, process, tool_name):
    url = f'http://localhost:{port}'
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
    port = s.getsockname()[1]
    s.close()
    return port


@app.route('/openapi.json', methods=['GET'])
def identify():
    """Self-report tool identification."""
    host = request.host
    port = host.split(':')[1] if ':' in host else '80'
    return jsonify(self_identification(host, port))


def self_identification(host, port):
    response = {
        "openapi": "3.1.0",
        "info": {
            "title": "tool_registry",
            "description": self_description,
            "version": "0.0.1",
            "port": port,
            "url": f"http://{host}:{port}"
        },
        "servers": [{"url": f"http://127.0.0.1:{args.port}", "description": self_description, "x-tool": self_name}],
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
                    "summary": "List the currently running tools.",
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
    return jsonify(openapi_objects)


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
    parser = argparse.ArgumentParser(prog='bot')
    parser.add_argument("-s", "--server", action="store_true")
    parser.add_argument('-p', '--port', default=8080, type=int)
    args = parser.parse_args(sys.argv[1:])
    signal.signal(signal.SIGTERM, lambda signum, frame: shutdown())
    signal.signal(signal.SIGINT, lambda signum, frame: shutdown())

    if args.server:
        openapi_objects[self_name] = self_identification('localhost', args.port)
        app.run(port=args.port)
    else:
        interactive(port=args.port)
