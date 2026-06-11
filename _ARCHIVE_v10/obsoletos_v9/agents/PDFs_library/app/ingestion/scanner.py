# app/ingestion/scanner.py

from pathlib import Path

def scan_pdfs(base_path):
    return list(Path(base_path).rglob("*.pdf"))