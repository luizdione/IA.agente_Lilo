# app/rag/summarizer.py

def summarize(text, llm):
    prompt = f"""
    Resuma este artigo científico em até 400 palavras:

    {text[:8000]}
    """
    return llm(prompt)