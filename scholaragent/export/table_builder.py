"""
export/table_builder.py -- Tabela de evidências a partir de chunks + metadados.

Sem LLM: organiza o que o RAG recuperou em linhas (autor, ano, periódico, DOI,
seção, trecho) e exporta em Markdown. Útil para montar uma tabela de revisão
de literatura sem custo de geração.
"""
from __future__ import annotations

_HEADERS = ["#", "Autor", "Ano", "Periodico", "DOI", "Secao", "Trecho"]
_KEYS = ["ref", "autor", "ano", "periodico", "doi", "secao", "trecho"]


def build_evidence_table(chunks: list[str], metas: list[dict],
                         snippet_chars: int = 200) -> list[dict]:
    """Uma linha por chunk recuperado, com metadados do paper e um trecho curto."""
    rows = []
    for i, (chunk, meta) in enumerate(zip(chunks, metas), 1):
        first_author = (meta.get("authors", "") or "").split(";")[0].strip()
        rows.append({
            "ref": i,
            "autor": first_author or "?",
            "ano": str(meta.get("year", "") or ""),
            "periodico": meta.get("journal", "") or "",
            "doi": meta.get("doi", "") or "",
            "secao": meta.get("section", "") or "",
            "trecho": " ".join((chunk or "").split())[:snippet_chars],
        })
    return rows


def to_markdown(rows: list[dict]) -> str:
    """Renderiza as linhas como tabela Markdown (escapa pipes)."""
    if not rows:
        return "_(nenhuma evidencia)_"
    lines = ["| " + " | ".join(_HEADERS) + " |",
             "| " + " | ".join("---" for _ in _HEADERS) + " |"]
    for r in rows:
        cells = [str(r.get(k, "")).replace("|", "\\|") for k in _KEYS]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
