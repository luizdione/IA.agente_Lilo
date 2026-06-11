# app/memory/vector_memory.py

import faiss
import numpy as np
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer

class Memory:
    def __init__(self):
        self.model = SentenceTransformer("mxbai-embed-large")
        self.index = faiss.IndexFlatL2(1024)
        self.data = []
        self.path = Path("data/memory/memory.json")

        if self.path.exists():
            self.data = json.loads(self.path.read_text())

    def store(self, query, response):
        text = query + " " + str(response)
        vec = self.model.encode(text)

        self.index.add(np.array([vec]).astype("float32"))
        self.data.append({"q": query, "r": response})

        self.path.write_text(json.dumps(self.data))

    def search(self, query):
        vec = self.model.encode(query)
        D, I = self.index.search(np.array([vec]).astype("float32"), 3)

        return [self.data[i] for i in I[0] if i < len(self.data)]