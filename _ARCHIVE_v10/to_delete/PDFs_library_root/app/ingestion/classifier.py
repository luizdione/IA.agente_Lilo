# app/ingestion/classifier.py

def is_scientific(text):
    sections = ["abstract", "introduction", "methods", "results"]
    score = sum(1 for s in sections if s in text.lower())
    return score >= 2