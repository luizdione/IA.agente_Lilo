"""
verify/numeric_checker.py — Números do claim têm que existir na evidência (tolerância zero).
"""
from __future__ import annotations
import re

NUM = re.compile(r"\d+(?:[.,]\d+)?")


def extract_numbers(text: str) -> list[str]:
    """Extrai tokens numéricos do texto (inteiros e decimais)."""
    return NUM.findall(text)


def numbers_match(claim_numbers: list[str], evidence_text: str) -> bool:
    """True se TODO número do claim aparece (normalizado) na evidência."""
    if not claim_numbers:
        return True
    ev_nums = {_norm(n) for n in NUM.findall(evidence_text)}
    return all(_norm(n) in ev_nums for n in claim_numbers)


def _norm(n: str) -> str:
    """Normaliza vírgula decimal e zeros à direita ('240' == '240,0')."""
    s = n.replace(",", ".")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s
