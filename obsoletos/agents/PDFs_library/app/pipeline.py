# app/pipeline.py

from app.agents.orchestrator import route_query
from app.agents.retrieval_agent import retrieve_articles
from app.agents.summarizer_agent import summarize

def run(query):
    intent = route_query(query)

    if "busca" in intent:
        articles = retrieve_articles(query)

        summaries = [summarize(a) for a in articles]

        return summaries