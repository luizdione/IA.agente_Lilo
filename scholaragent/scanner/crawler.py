"""
scanner/crawler.py — Varre recursivamente pastas em busca de PDFs.
Retorna PaperFile com path, hash MD5, tamanho e data de modificação.
"""
from __future__ import annotations
import os
import hashlib
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

MIN_SIZE_BYTES = 10_000   # ignora PDFs minúsculos (capas, thumbnails)


@dataclass
class PaperFile:
    path: Path
    md5: str
    size_bytes: int
    modified_at: datetime


def scan_directories(roots: list[str], min_size: int = MIN_SIZE_BYTES) -> list[PaperFile]:
    """Varre os diretórios raiz recursivamente; filtra .pdf acima de min_size."""
    found: list[PaperFile] = []
    for root in roots:
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                if not fname.lower().endswith(".pdf"):
                    continue
                fpath = Path(dirpath) / fname
                try:
                    st = fpath.stat()
                except OSError:
                    continue
                if st.st_size < min_size:
                    continue
                found.append(PaperFile(
                    path=fpath,
                    md5=md5_of(fpath),
                    size_bytes=st.st_size,
                    modified_at=datetime.fromtimestamp(st.st_mtime),
                ))
    return found


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
