import sys
import json
from flask import Flask, request, jsonify
import requests

OLLAMA_API_URL = "http://localhost:11434/api/chat"

tools = {}
app = Flask('chat')


@app.route('/chat', methods=['POST'])
def chat():
    tool_input = request.json
    data = {
        "model": tool_input.get("model", "llama3:8b"),
        "messages": [
            {"role": "system", "content": "You are a chat bot."},
            {"role": "system", "content": f"{tool_input['message']}"},
        ],
        "stream": False,
        "options": {
            "temperature": tool_input.get("temperature", 0),
        }
    }
    print(f"POST {OLLAMA_API_URL}{data}")
    response = requests.post(OLLAMA_API_URL, json=data)
    response.raise_for_status()
    return jsonify({'response': response.json()['message']['content']})


def main():
    global tools
    config = json.load(sys.stdin)
    tools = config['tools']
    app.run(port=(int(sys.argv[1])))


if __name__ == '__main__':
    main()
