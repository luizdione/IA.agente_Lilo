"""
verify/ — Gate de verificação factual do ScholarAgent.

Impede que afirmações, números ou citações sejam publicados sem estar ancorados
em um chunk-fonte verificável da biblioteca, com revisão humana antes de toda
saída externa. Tudo local; o juiz LLM e o reranker são injetáveis.
"""
from .contracts import (
    Claim, ClaimType, Evidence, ClaimResult, Verdict, Decision, GateReport,
)
from .grounding import Grounder
from .gate import VerificationGate
from .policy import decide
from .ollama_judge import make_ollama_judge
from .factory import build_grounder
from .bridge import evidence_from_rag
from .reranker import BgeReranker

__all__ = [
    "Claim", "ClaimType", "Evidence", "ClaimResult", "Verdict", "Decision",
    "GateReport", "Grounder", "VerificationGate", "decide", "make_ollama_judge",
    "build_grounder", "evidence_from_rag", "BgeReranker",
]
