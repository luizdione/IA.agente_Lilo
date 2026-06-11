# app/indexing/embedder.py

from sentence_transformers import SentenceTransformer

class Embedder:
    def __init__(self, model_name):
        self.model = SentenceTransformer(model_name)

    def encode(self, text):
        return self.model.encode(text)