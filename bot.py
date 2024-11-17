import argparse
import json
import logging
import os
import signal
import socket
import subprocess
import sys
from time import sleep

import requests
from flask import Flask, request, jsonify
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

self_name = 'start_tool'

logging.basicConfig(filename=f'bot.log', level=logging.INFO)

# Registry of subprocess tools
processes = {}

# OpenAPI Server Objects tools
servers = {}

app = Flask(self_name)

retry_strategy = Retry(connect=10, backoff_factor=1)

adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("http://", adapter)


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
    with open(f"bot-server.log", "w") as log_file:
        process = subprocess.Popen(
            ['python', __file__, '--server', '-p', str(port)],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True  # Detach process from the parent
        )
    app.logger.info(f"Started server: pid {process.pid}, port {port}")
    return register_tool(port, process, self_name)


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
    return start_tool(tool_name)


def start_tool(tool_name, port: int = None):
    port = port if port else find_free_port()
    app.logger.info(f"Starting '{tool_name}' on port {port}")
    process = subprocess.Popen(
        ['python', os.path.join('tools', tool_name, 'main.py'), str(port)],
        stdin=subprocess.PIPE
    )
    process.stdin.write(json.dumps({'servers': servers}).encode('utf-8'))
    process.stdin.close()
    return register_tool(port, process, tool_name)


def register_tool(port, process, tool_name):
    url = f'http://localhost:{port}'
    app.logger.info(f"Registering '{tool_name}' at {url}")

    def post(data, resource='/'):
        endpoint = f'{url}{resource}'
        app.logger.info(f"{tool_name} POST {endpoint} \n{data}")
        return session.post(endpoint, json=data).json()

    def get(resource='/'):
        endpoint = f'{url}{resource}'
        app.logger.info(f"{tool_name} GET {endpoint}")
        return session.get(endpoint).json()

    sleep(1)
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
            list(servers.values())
        ],
        "paths": {
            "/start": {
                "post": {
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
            os.kill(tool_process.pid, signal.SIGTERM)
            tool_process.wait()
    return {"status": "shutting down"}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='bot')
    parser.add_argument("-s", "--server", action="store_true")
    parser.add_argument('-p', '--port', default=8080, type=int)
    args = parser.parse_args(sys.argv[1:])

    # Prepare for reentrant call to /openapi.json which returns a list of servers
    servers[self_name] = {"url": f"http://127.0.0.1:{args.port}", "description": self_name, "x-tool": self_name}

    if args.server:
        app.run(port=args.port)
    else:
        interactive(port=args.port)
