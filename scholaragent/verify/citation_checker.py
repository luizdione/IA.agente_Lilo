"""
verify/citation_checker.py — Cada [n] no texto deve sustentar a afirmação adjacente.
Detecta citação órfã (sem fonte) e fonte mal atribuída (existe mas não sustenta).
"""
from __future__ import annotations
from .contracts import Claim, Evidence


def check_citation(claim: Claim, ref_to_evidence: dict[int, Evidence], judge) -> bool:
    """
    judge(claim_text, evidence_text) -> (verdict_str, confidence, rationale)
    verdict_str in {"supported","contradicted","not_enough_info","partial"}.
    Retorna False se qualquer [n] for órfã ou não sustentar a afirmação.
    """
    for n in claim.cited_refs:
        ev = ref_to_evidence.get(n)
        if ev is None:
            return False                       # citação órfã: [n] sem chunk correspondente
        verdict, _, _ = judge(claim.text, ev.text)
        if verdict != "supported":
            return False                       # fonte existe, mas não sustenta a afirmação
    return True
