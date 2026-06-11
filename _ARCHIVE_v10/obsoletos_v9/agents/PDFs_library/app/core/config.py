# app/core/config.py

from pathlib import Path

BASE_DIR = Path(r"C:\Users\SEU_USER\OneDrive\Documentos\Workaholics")

DATA_DIR = Path("data")
VECTOR_DB_PATH = DATA_DIR / "vectors"
MODEL_NAME = "all-MiniLM-L6-v2"

MAX_SUMMARY_WORDS = 400