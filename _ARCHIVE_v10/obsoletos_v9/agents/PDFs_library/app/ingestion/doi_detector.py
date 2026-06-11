# app/ingestion/doi_detector.py

import re

doi_pattern = re.compile(r'10.\d{4,9}/[-._;()/:A-Z0-9]+', re.I)

def find_doi(text):
    match = doi_pattern.search(text)
    return match.group(0) if match else None