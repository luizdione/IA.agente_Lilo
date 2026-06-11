# app/indexing/vector_store.py

import faiss
import numpy as np

class VectorStore:
    def __init__(self, dim):
        self.index = faiss.IndexFlatL2(dim)
        self.texts = []

    def add(self, vector, text):
        self.index.add(np.array([vector]).astype("float32"))
        self.texts.append(text)

    def search(self, query_vector, k=5):
        D, I = self.index.search(np.array([query_vector]).astype("float32"), k)
        return [self.texts[i] for i in I[0]]