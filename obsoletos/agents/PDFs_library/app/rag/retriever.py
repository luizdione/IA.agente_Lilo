# app/rag/retriever.py

def retrieve(query, embedder, store):
    q_vec = embedder.encode(query)
    return store.search(q_vec)