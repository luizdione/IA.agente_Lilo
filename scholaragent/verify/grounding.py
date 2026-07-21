"""
verify/grounding.py — Ancora cada claim em evidência e julga entailment (NLI).

Tudo local e injetável:
  - judge:    callable (claim_text, evidence_text) -> (verdict_str, confidence, rationale).
              Tipicamente o LLM-judge local (ver verify/ollama_judge). Injetável p/ testes.
  - reranker: objeto com .score(claim_text, chunk_text) -> float (cross-encoder local).
              Se None, usa sobreposição de tokens (Jaccard) como fallback determinístico.
  - store/embedder: opcionais; se fornecidos, re-busca evidência adicional pelo claim.
"""
from __future__ import annotations
import re

from .contracts import Claim, Evidence, ClaimResult, ClaimType, Verdict

RERANK_HI = 0.75      # acima: provável suporte (resolve sem LLM, p/ claims de baixo risco)
RERANK_LO = 0.30      # abaixo: provável não-suporte

_VERDICT_MAP = {
    "supported": Verdict.SUPPORTED,
    "contradicted": Verdict.CONTRADICTED,
    "partial": Verdict.PARTIAL,
    "not_enough_info": Verdict.UNSUPPORTED,
}


class Grounder:
    def __init__(self, judge, reranker=None, store=None, embedder=None):
        self.judge = judge
        self.reranker = reranker
        self.store = store
        self.embedder = embedder

    def ground(self, claim: Claim, used_chunks: list[Evidence]) -> ClaimResult:
        candidates = list(used_chunks) + self._research(claim)
        if not candidates:
            return ClaimResult(claim, Verdict.UNSUPPORTED, 1.0, [],
                               "Nenhuma evidência candidata.")

        scored = sorted(
            ((c, self._score(claim.text, c.text)) for c in candidates),
            key=lambda x: x[1], reverse=True,
        )
        top_ev, top_score = scored[0]
        top_ev.score = top_score

        # Claims de baixo risco (sem número/citação) podem resolver só pela triagem.
        hard = claim.claim_type in (ClaimType.NUMERIC, ClaimType.CITATION)
        if not hard:
            if top_score >= RERANK_HI:
                return ClaimResult(claim, Verdict.SUPPORTED, top_score, [top_ev],
                                   "Suporte forte (reranker).")
            if top_score <= RERANK_LO:
                return ClaimResult(claim, Verdict.UNSUPPORTED, 1 - top_score, [],
                                   "Sem trecho de suporte (reranker).")

        # Alto risco ou ambíguo → juiz NLI local decide.
        verdict_str, conf, rationale = self.judge(claim.text, top_ev.text)
        verdict = _VERDICT_MAP.get(verdict_str, Verdict.UNSUPPORTED)  # default conservador
        keep = verdict in (Verdict.SUPPORTED, Verdict.PARTIAL, Verdict.CONTRADICTED)
        return ClaimResult(claim, verdict, conf, [top_ev] if keep else [], rationale)

    def _score(self, claim_text: str, chunk_text: str) -> float:
        if self.reranker is not None:
            return float(self.reranker.score(claim_text, chunk_text))
        return _token_overlap(claim_text, chunk_text)

    def _research(self, claim: Claim) -> list[Evidence]:
        """Re-busca evidência adicional na biblioteca (opcional)."""
        if self.store is None or self.embedder is None:
            return []
        try:
            q = self.embedder.embed_query(claim.text)
            res = self.store.query(q, n_results=5)
            out = []
            for d, m in zip(res["documents"][0], res["metadatas"][0]):
                out.append(Evidence(
                    chunk_id=f'{m.get("paper_md5", "")}_?',
                    paper_md5=m.get("paper_md5", ""),
                    section=m.get("section", ""),
                    text=d,
                ))
            return out
        except Exception:
            return []


def _token_overlap(a: str, b: str) -> float:
    """Fallback determinístico: Jaccard de tokens (quando não há reranker)."""
    ta, tb = set(_tok(a)), set(_tok(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _tok(s: str) -> list[str]:
    return re.findall(r"\w+", s.lower())
