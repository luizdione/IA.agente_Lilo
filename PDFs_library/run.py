# run.py

from app.ingestion.scanner import scan_pdfs
from app.ingestion.pdf_parser import extract_text
from app.ingestion.doi_detector import find_doi
from app.ingestion.classifier import is_scientific

pdfs = scan_pdfs(BASE_DIR)

for pdf in pdfs:
    text = extract_text(pdf)

    if not text:
        continue

    doi = find_doi(text)

    if doi and is_scientific(text):
        print(f"[OK] {pdf} | DOI: {doi}")