# app/agents/synthesis_agent.py

def generate_article(context):
    prompt = f"""
    Gere um texto científico baseado nos artigos:

    {context}
    """

    return ask_llm("llama3:8b-instruct-q4_K_M", prompt)