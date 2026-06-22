"""
chat/prompts.py — Prompts científicos do ScholarAgent (RAG, gaps, rascunho de introdução).
"""
from __future__ import annotations


def build_prompt(question: str, chunks: list[str], metas: list[dict]) -> str:
    blocks = []
    for i, (chunk, meta) in enumerate(zip(chunks, metas)):
        ref = f"[{i+1}] {meta.get('authors','').split(';')[0]} et al. ({meta.get('year','')})"
        blocks.append(f"{ref}:\n{chunk}")
    context = "\n\n---\n\n".join(blocks)
    n = len(chunks)
    return f"""Você é um assistente científico especializado em Biologia Molecular, Genômica e Bioinformática.
Responda APENAS com base nos trechos fornecidos. Se a informação não estiver nos trechos, diga explicitamente.
Cite SOMENTE pelos números dos trechos acima, de [1] a [{n}]. NUNCA invente outros números de
citação nem copie números que apareçam DENTRO do texto dos trechos (ex.: listas de referências).
Responda em português brasileiro. Seja preciso e técnico.

TRECHOS DA BIBLIOTECA:
{context}

PERGUNTA: {question}

RESPOSTA:"""


def gap_detection_prompt(theme: str, papers_summary: str) -> str:
    return f"""Analise os papers abaixo sobre o tema "{theme}".
Identifique lacunas na literatura: o que ainda não foi estudado, contradições entre estudos,
populações não cobertas, métodos ausentes ou perguntas em aberto. Cite os papers relevantes.

PAPERS:
{papers_summary}

LACUNAS IDENTIFICADAS:"""


def intro_draft_prompt(topic: str, chunks: list[str], metas: list[dict]) -> str:
    context = "\n\n".join(f"[{i+1}] {c}" for i, c in enumerate(chunks))
    refs = "\n".join(
        f"[{i+1}] {m.get('authors','').split(';')[0]} et al., {m.get('year','')}. {m.get('title','')}"
        for i, m in enumerate(metas)
    )
    return f"""Escreva um parágrafo de introdução científica sobre: "{topic}".
Use APENAS as referências fornecidas. Cite pelo número [1], [2], etc.
Estilo: científico formal, terceira pessoa.

CONTEXTO:
{context}

REFERÊNCIAS DISPONÍVEIS:
{refs}

INTRODUÇÃO:"""
