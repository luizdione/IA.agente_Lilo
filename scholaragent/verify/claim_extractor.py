"""
verify/claim_extractor.py — Quebra o texto gerado em afirmações atômicas verificáveis.

Dois modos:
  - rule-based (default): split por sentenças + classificação por regex. Determinístico,
    sem dependência externa — usado em testes e como fallback.
  - LLM (opcional): injeta-se uma função llm_fn(prompt) -> str(JSON) para extração mais
    fina (ver verify/prompts.claim_extraction_prompt).
"""
from __future__ import annotations
import json
import re

from .contracts import Claim, ClaimType
from .numeric_checker import extract_numbers

REF = re.compile(r"\[(\d+)\]")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
OPINION_HINTS = (
    "recomenda", "sugere", "deve-se", "é promissor", "acreditamos",
    "provavelmente", "pode ser", "talvez",
)


def extract_claims(text: str, llm_fn=None) -> list[Claim]:
    """Extrai claims. Se llm_fn for fornecida, usa-a; senão, rule-based."""
    if llm_fn is not None:
        return _extract_with_llm(text, llm_fn)
    return _extract_rule_based(text)


def _classify(sentence: str, refs: list[int], numbers: list[str]) -> ClaimType:
    low = sentence.lower()
    if refs:
        return ClaimType.CITATION
    if numbers:
        return ClaimType.NUMERIC
    if any(h in low for h in OPINION_HINTS):
        return ClaimType.OPINION
    return ClaimType.FACTUAL


def _extract_rule_based(text: str) -> list[Claim]:
    claims: list[Claim] = []
    idx = 0
    cursor = 0
    for sent in SENT_SPLIT.split(text):
        s = sent.strip()
        start = text.find(s, cursor) if s else -1
        if start >= 0:
            cursor = start + len(s)
        if len(s) < 8:
            continue
        span = (start if start >= 0 else 0, (start + len(s)) if start >= 0 else len(s))
        refs = [int(n) for n in REF.findall(s)]
        numbers = extract_numbers(REF.sub("", s))   # ignora os [n] ao contar números
        claims.append(Claim(
            id=f"c{idx}",
            text=s,
            claim_type=_classify(s, refs, numbers),
            span=span,
            cited_refs=refs,
            numbers=numbers,
        ))
        idx += 1
    return claims


def _extract_with_llm(text: str, llm_fn) -> list[Claim]:
    from .prompts import claim_extraction_prompt
    try:
        items = json.loads(llm_fn(claim_extraction_prompt(text)))
    except Exception:
        return _extract_rule_based(text)   # fallback se o LLM não devolver JSON válido
    claims: list[Claim] = []
    for i, it in enumerate(items):
        t = (it.get("text") or "").strip()
        if not t:
            continue
        start = text.find(t)
        try:
            ctype = ClaimType(it.get("type", "factual"))
        except ValueError:
            ctype = ClaimType.FACTUAL
        claims.append(Claim(
            id=f"c{i}",
            text=t,
            claim_type=ctype,
            span=(start if start >= 0 else 0, (start + len(t)) if start >= 0 else len(t)),
            cited_refs=[int(x) for x in it.get("cited_refs", []) if str(x).isdigit()],
            numbers=[str(x) for x in it.get("numbers", [])],
        ))
    return claims or _extract_rule_based(text)
