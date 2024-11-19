import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Setup logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(filename=f'logs/bot.log', level=logging.INFO)
logger = logging.getLogger(__name__)

registry_process: Optional[subprocess.Popen[bytes]] = None


def interactive(port: int):
    url = f'http://localhost:{port}'
    retry_strategy = Retry(connect=10, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("http://", adapter)
    while True:
        try:
            user_input = read_user_input()
            tool_name = user_input["tool"]
            start_response = session.post(f'{url}/start', json={"name": tool_name})
            start_response.raise_for_status()
            tool_schema = start_response.json()
            tool_url = tool_schema["servers"][0]["url"]
            tool_resource = user_input["resource"]
            tool_response = session.post(f'{tool_url}/{tool_resource}', json=user_input['input'])
            tool_response.raise_for_status()
            response = tool_response.json()
            print(response['content'])
        except KeyboardInterrupt:
            logger.warning("Keyboard Interrupt")
            shutdown()
        except Exception as e:
            logger.exception("Exception in interactive mode")
            shutdown()
            return


def read_user_input():
    content = input("input: ")
    try:
        user_input = json.loads(content)
    except json.JSONDecodeError:
        user_input = {"tool": "chat", "resource": "/chat", "input": {"message": content}}
    return user_input


def subprocess_server(port: int):
    logger.info(f"Starting server process on port {port}")
    with open(f"logs/bot-server.log", "w") as log_file:
        process = subprocess.Popen(
            ['python', 'main.py', str(port)],
            cwd='tools/registry_tool',
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True  # Detach process from the parent
        )
    time.sleep(1)
    logger.info(f"Started server: pid {process.pid}, port {port}")
    return process


def shutdown():
    """Endpoint to shut down the bot and terminate all tools started."""
    if registry_process:
        os.kill(registry_process.pid, signal.SIGTERM)
        registry_process.wait()
    logging.info("Shutdown complete")
    exit(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='bot')
    parser.add_argument("-s", "--server", action="store_true")
    parser.add_argument('-p', '--port', default=8080, type=int)
    args = parser.parse_args(sys.argv[1:])
    signal.signal(signal.SIGTERM, lambda signum, frame: shutdown())
    signal.signal(signal.SIGINT, lambda signum, frame: shutdown())
    registry_process = subprocess_server(args.port)
    if args.server:
        registry_process.wait()
    else:
        interactive(port=args.port)
