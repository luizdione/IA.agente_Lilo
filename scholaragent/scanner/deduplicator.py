"""
scanner/deduplicator.py — Deduplica papers por hash MD5 (conteúdo idêntico).
Mantém o arquivo modificado mais recentemente. DOI duplicado é tratado depois,
na etapa de metadados.
"""
from __future__ import annotations
from .crawler import PaperFile


def deduplicate(papers: list[PaperFile]) -> list[PaperFile]:
    by_hash: dict[str, PaperFile] = {}
    for p in papers:
        cur = by_hash.get(p.md5)
        if cur is None or p.modified_at > cur.modified_at:
            by_hash[p.md5] = p
    return list(by_hash.values())
