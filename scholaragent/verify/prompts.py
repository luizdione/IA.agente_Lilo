"""
verify/prompts.py — Prompts de extração de claims e de NLI adversarial (juiz local).
"""
from __future__ import annotations


def claim_extraction_prompt(text: str) -> str:
    return f"""Você é um verificador científico. Quebre o TEXTO abaixo em afirmações
atômicas e verificáveis (uma ideia por afirmação). Para cada uma, classifique o tipo:
- "numeric": contém número (n amostras, p-valor, %, ano, dose);
- "citation": atribui algo a uma referência [n];
- "factual": afirmação factual sem número;
- "opinion": interpretação ou recomendação (não factual).
Liste os marcadores [n] citados e os números presentes.
Responda APENAS em JSON: lista de objetos {{"text","type","cited_refs","numbers"}}.

TEXTO:
{text}

JSON:"""


def nli_prompt(claim: str, evidence: str) -> str:
    return f"""Você é um juiz de verificação factual rigoroso e CÉTICO.
Decida se a EVIDÊNCIA sustenta a AFIRMAÇÃO. Regras:
- "supported": a evidência afirma claramente o que a afirmação diz;
- "contradicted": a evidência diz o oposto;
- "not_enough_info": a evidência não é suficiente — USE ESTE por padrão na dúvida.
Não use conhecimento externo; baseie-se SÓ na evidência. Números devem bater exatamente.
Responda APENAS em JSON: {{"verdict","confidence","rationale"}} (rationale <= 25 palavras).

AFIRMAÇÃO: {claim}

EVIDÊNCIA: {evidence}

JSON:"""
