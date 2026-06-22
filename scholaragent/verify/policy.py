"""
verify/policy.py — Política conservadora de decisão do gate.

Em contexto científico, um falso "está ok" é pior que pedir revisão extra:
  - citação/número não sustentado ou contradição → BLOCK
  - afirmação factual sem suporte, ou ambígua (PARTIAL) → REVIEW
  - tudo sustentado → PASS (ainda exige aval humano para saída externa)
"""
from __future__ import annotations
from .contracts import ClaimResult, ClaimType, Verdict, Decision


def decide(results: list[ClaimResult]) -> Decision:
    block = False
    review = False
    for r in results:
        hard = r.claim.claim_type in (ClaimType.NUMERIC, ClaimType.CITATION)
        if r.verdict == Verdict.CONTRADICTED:
            # OPINION (não factual) não bloqueia — no máximo revisão (contrato em contracts.py)
            if r.claim.claim_type == ClaimType.OPINION:
                review = True
            else:
                block = True
        elif r.verdict == Verdict.UNSUPPORTED:
            if hard:
                block = True
            elif r.claim.claim_type == ClaimType.FACTUAL:
                review = True
        elif r.verdict == Verdict.PARTIAL:
            review = True
        # checagens determinísticas reforçam o bloqueio
        if not r.numeric_ok or not r.citation_ok:
            block = True
    if block:
        return Decision.BLOCK
    return Decision.REVIEW if review else Decision.PASS
