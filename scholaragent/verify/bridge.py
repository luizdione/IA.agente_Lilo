"""
verify/bridge.py — Converte a saída do RAG (chunks + metadados) nas entradas do gate.

O retriever devolve documentos e metadados paralelos; o gate precisa de uma lista de
Evidence (used_chunks) e de um mapa {n: Evidence} para conferir as citações [n].
A ordem dos chunks define a numeração das referências (1-indexada).
"""
from __future__ import annotations

from .contracts import Evidence


def evidence_from_rag(chunks: list[str], metas: list[dict]) -> tuple[list[Evidence], dict[int, Evidence]]:
    evidences: list[Evidence] = []
    for i, (text, meta) in enumerate(zip(chunks, metas)):
        evidences.append(Evidence(
            chunk_id=f'{meta.get("paper_md5", "")}_{meta.get("chunk_index", i)}',
            paper_md5=meta.get("paper_md5", ""),
            section=meta.get("section", ""),
            text=text,
        ))
    ref_to_evidence = {i + 1: ev for i, ev in enumerate(evidences)}   # [1] -> 1º chunk
    return evidences, ref_to_evidence
