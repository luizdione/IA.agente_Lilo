# app/pipeline/executor.py

from app.agents.orchestrator import route
from app.agents.planner import plan
from app.agents.retrieval_agent import retrieve
from app.agents.summarizer_agent import summarize
from app.memory.vector_memory import Memory

memory = Memory()

def run(query):
    intent = route(query)
    steps = plan(query)

    context = []

    for step in steps:
        if "buscar" in step:
            docs = retrieve(query)
            context.extend(docs)

        elif "resumir" in step:
            context = [summarize(c) for c in context]

    memory.store(query, context)

    return context