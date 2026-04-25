# app/agents/orchestrator.py

from app.llm.ollama_client import ask

def route(query):
    prompt = f"""
    Classifique:
    - busca_artigos
    - analise_dados
    - gerar_artigo

    Query: {query}
    """

    return ask("llama3.1:8b-instruct-q8_0", prompt).lower()