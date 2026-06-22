"""
verify/gate.py — Orquestrador do gate de verificação factual.
Roda o pipeline completo sobre um conteúdo gerado e produz um GateReport.

Pipeline: extrai claims -> ancora cada um em evidência (NLI) -> confere citações [n]
-> confere números (tolerância zero) -> aplica a política PASS/REVIEW/BLOCK.
"""
from __future__ import annotations

from .contracts import GateReport, Verdict, Evidence
from .claim_extractor import extract_claims
from .citation_checker import check_citation
from .numeric_checker import numbers_match
from .policy import decide
from .grounding import Grounder
from .audit import write_audit


class VerificationGate:
    def __init__(self, grounder: Grounder, claim_llm_fn=None, audit_dir: str = "./audit"):
        self.grounder = grounder
        self.claim_llm_fn = claim_llm_fn      # opcional: extração de claims via LLM
        self.audit_dir = audit_dir

    def verify(self, content_id: str, question: str, generated_text: str,
               used_chunks: list[Evidence],
               ref_to_evidence: dict[int, Evidence] | None = None,
               write_trail: bool = True) -> GateReport:
        ref_to_evidence = ref_to_evidence or {}
        claims = extract_claims(generated_text, self.claim_llm_fn)

        results = []
        for claim in claims:
            res = self.grounder.ground(claim, used_chunks)
            # checagens determinísticas independentes do veredicto do juiz
            if claim.numbers:
                res.numeric_ok = (
                    any(numbers_match(claim.numbers, e.text) for e in res.evidence)
                    if res.evidence else False
                )
            if claim.cited_refs:
                res.citation_ok = check_citation(
                    claim, ref_to_evidence, self.grounder.judge
                )
            results.append(res)

        decision = decide(results)
        report = GateReport(
            content_id=content_id,
            source_question=question,
            generated_text=generated_text,
            results=results,
            decision=decision,
            unsupported_count=sum(r.verdict == Verdict.UNSUPPORTED for r in results),
            contradicted_count=sum(r.verdict == Verdict.CONTRADICTED for r in results),
        )
        if write_trail:
            report.audit_path = write_audit(report, self.audit_dir)
        return report
