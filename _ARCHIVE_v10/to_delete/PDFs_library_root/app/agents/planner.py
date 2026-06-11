# app/agents/# app/agents/planner.py
#
# from app.llm.ollama_client import ask
#
# def plan(query):
#     prompt = f"""
#     Quebre em etapas:
#
#     Query: {query}
#
#     Responda como lista:
#     1.
#     2.
#     3.
#     """
#
#     steps = ask("llama3.1:8b-instruct-q8_0", prompt)
#     return steps.split("\n").py

from app.llm.ollama_client import ask

def plan(query):
    prompt = f"""
    Quebre em etapas:

    Query: {query}

    Responda como lista:
    1.
    2.
    3.
    """

    steps = ask("llama3.1:8b-instruct-q8_0", prompt)
    return steps.split("\n")