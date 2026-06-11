# app/llm/ollama_client.py

import requests

def ask(model, prompt):
    r = requests.post("http://localhost:11434/api/generate", json={
        "model": model,
        "prompt": prompt,
        "stream": False
    })
    return r.json()["response"]