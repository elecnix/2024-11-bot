import requests

OLLAMA_API_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.1:8b"
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
        "text_input": "string"
    }

    def __init__(self, manager):
        self.manager = manager

    def run(self, inputs):
        text_input = inputs['text_input']
        available_tools = list(self.manager.tools.keys())
        
        messages = [
            {"role": "system", "content": "You are a task assistant that chooses tools to solve tasks based on available tools and user input."},
            {"role": "user", "content": f"User input: {text_input}\nAvailable tools: {available_tools}\nChoose the best tool and provide necessary inputs to solve the task."}
        ]
        
        response = ollama_chat(messages)
        tool_decision = response['message']['content']
        
        # Process the LLM's response to determine the selected tool and input parameters
        tool_name, tool_inputs = self.parse_tool_decision(tool_decision)
        
        if tool_name in available_tools:
            tool = self.manager.load_tool(tool_name)
            return tool.run(tool_inputs)
        else:
            return "No appropriate tool found based on the LLM's response."

    def parse_tool_decision(self, tool_decision):
        # Basic parsing of the LLM response to get tool name and inputs
        print(tool_decision)
        lines = tool_decision.splitlines()
        tool_name = lines[0].strip()
        tool_inputs = {}
        
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                tool_inputs[key.strip()] = value.strip()
        
        return tool_name, tool_inputs
