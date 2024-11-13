import argparse
import json
import os
import socket
import subprocess
import sys

import requests
from flask import Flask, request, jsonify

# Registry of subprocess tools
processes = {}

# OpenAPI Server Objects tools
servers = {}

self_name = 'start_tool'
app = Flask(self_name)


def interactive(port: int):
    subprocess_server(port)
    while True:
        try:
            user_input = read_user_input()
            tool = get_tool(user_input['tool'])
            response = tool.post(user_input['input'], resource=user_input['resource'])
            print(response)
        except KeyboardInterrupt:
            print("Keyboard Interrupt")
            shutdown()
        except Exception as e:
            print(e)


def subprocess_server(port: int):
    process = subprocess.Popen(
        ['python', __file__, '--interactive', 'false', '-p', str(port)],
        stdin=subprocess.PIPE
    )
    process.stdin.close()
    return register_tool(port, process, self_name)


def read_user_input():
    content = input("input: ")
    try:
        user_input = json.loads(content)
    except json.JSONDecodeError:
        user_input = {"tool": "chat", "resource": "chat", "input": {"message": content}}
    return user_input


def get_tool(tool_name):
    if tool_name in processes:
        return processes[tool_name]
    return start_tool(tool_name)


def start_tool(tool_name, port: int = None):
    port = port if port else find_free_port()
    print(f"Starting '{tool_name}' on port {port}")
    process = subprocess.Popen(
        ['python', os.path.join('tools', tool_name, 'main.py'), str(port)],
        stdin=subprocess.PIPE
    )
    process.stdin.write(json.dumps({'servers': servers}).encode('utf-8'))
    process.stdin.close()
    return register_tool(port, process, tool_name)


def register_tool(port, process, tool_name):
    url = f'http://localhost:{port}'
    print(f"Registering '{tool_name}' at {url}")

    def post(data, resource='/'):
        endpoint = f'{url}{resource}'
        print(f"{tool_name} POST {endpoint} \n{data}")
        return requests.post(endpoint, json=data).json()

    def get(resource='/'):
        endpoint = f'{url}{resource}'
        print(f"{tool_name} GET {endpoint}")
        return requests.get(endpoint).json()

    identification = get('/openapi.json')
    processes[tool_name] = {'process': process, 'get': get, 'post': post}
    servers[tool_name] = identification["servers"]
    return processes[tool_name]


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
    response = {
        "openapi": "3.1.0",
        "info": {
            "title": "start_tool",
            "description": "Start a tool to get its port number to invoke the tool.",
            "version": "0.0.1",
            "port": port,
            "url": f"http://{host}:{port}"
        },
        "servers": [
            servers.values()
        ],
        "paths": {
            "/start": {
                "post": {
                    "requestBody": {
                        "application/json": {
                            "schema": {
                                {
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
                        }
                    }
                }
            }
        }
    }
    return jsonify(response)


@app.route('/start', methods=['POST'])
def start_tool_route():
    """Endpoint to start a tool via HTTP POST request."""
    data = request.json
    tool_name = data['tool']
    accessible_tools = data.get('accessible_tools', {})
    result = start_tool(tool_name, accessible_tools)
    return jsonify(result)


@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Endpoint to shut down the server and terminate all tools this server has started."""
    for tool_info in processes.values():
        tool_process = tool_info.get('process')
        if tool_process:
            tool_process.terminate()
            tool_process.wait()
    return {"status": "shutting down"}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='bot')
    parser.add_argument("-i", "--interactive", action="store_true", default=True)
    parser.add_argument('-p', '--port', default=8080, type=int)
    args = parser.parse_args(sys.argv[1:])

    # Prepare for reentrant call to /openapi.json which returns a list of servers
    servers[self_name] = {"url": "http://127.0.0.1:" + args.port, "description": self_name, "x-tool": self_name}

    if args.interactive:
        interactive(port=args.port)
    else:
        app.run(port=args.port)
