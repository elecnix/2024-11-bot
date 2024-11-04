import requests

OLLAMA_API_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "your_model_name"
headers = {}

def ollama_chat(messages):
    data = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
    }
    response = requests.post(OLLAMA_API_URL, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

class Tool:
    INPUT_SCHEMA = {
        "tool_name": "string",
        "purpose": "string"
    }

    def __init__(self, manager):
        self.manager = manager

    def run(self, inputs):
        tool_name = inputs['tool_name']
        purpose = inputs['purpose']
        tool_code = self.manager.get_tool_code(tool_name)
        messages = [
            {"role": "system", "content": "You are an AI assistant that evaluates Python code for fitness for a given purpose."},
            {"role": "user", "content": f"Evaluate the following code for the purpose: '{purpose}'\n\nCode:\n{tool_code}"}
        ]
        response = ollama_chat(messages)
        return response['message']['content']