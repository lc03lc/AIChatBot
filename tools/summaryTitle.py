import json

import requests


def create_message(role, content):
    return {"role": role, "content": content}


def request_model(messages):
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "llamafamily/llama3-chinese-8b-instruct:latest",
        "messages": messages,
        "stream": False
    }
    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to get response: ", response.status_code)
        print("Response Content:", response.content)

