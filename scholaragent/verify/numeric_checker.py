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
    """Normaliza um token numérico para comparação.
    Trata separador de milhar (1,000 / 1.000 -> 1000) e decimal (0,75 -> 0.75),
    evitando o colapso lossy '1,000' -> '1' (que causava bloqueio falso E match
    espúrio com qualquer '1' na fonte)."""
    s = n.strip()
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", s):   # milhar agrupado -> inteiro
        return s.replace(".", "").replace(",", "")
    s = s.replace(",", ".")                          # vírgula decimal -> ponto
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s
