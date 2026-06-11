# app/api/main.py

from fastapi import FastAPI
from app.rag.retriever import retrieve

app = FastAPI()

@app.get("/search")
def search(q: str):
    results = retrieve(q)
    return {"results": results}