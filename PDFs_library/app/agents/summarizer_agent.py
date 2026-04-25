# app/agents/summarizer_agent.py

from app.llm.ollama_client import ask

def summarize(text):
    return ask("phi3:14b-medium-128k-instruct-q4_K_M",
               f"Resuma cientificamente:\n{text[:12000]}")