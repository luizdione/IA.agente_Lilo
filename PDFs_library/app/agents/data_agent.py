# app/agents/data_agent.py

from app.llm.ollama_client import ask

def analyze(data):
    return ask("qwen2.5-coder:14b",
               f"Analise os dados:\n{data}")