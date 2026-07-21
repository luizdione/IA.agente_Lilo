"""
verify/contracts.py — Estruturas de dados do gate de verificação factual.
Tipadas para garantir que cada etapa consome o que a anterior produz.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class ClaimType(str, Enum):
    FACTUAL = "factual"      # afirmação verificável sem número
    NUMERIC = "numeric"      # contém número (n amostras, p-valor, %, ano, dose)
    CITATION = "citation"    # apoia/atribui algo a uma referência [n]
    OPINION = "opinion"      # interpretação/recomendação (não factual — não bloqueia)


class Verdict(str, Enum):
    SUPPORTED = "supported"        # evidência sustenta o claim
    PARTIAL = "partial"            # sustenta em parte / ambíguo
    UNSUPPORTED = "unsupported"    # nenhuma evidência sustenta
    CONTRADICTED = "contradicted"  # evidência contradiz o claim


class Decision(str, Enum):
    PASS = "pass"        # todos os claims sustentados (ainda exige aval humano p/ externo)
    REVIEW = "review"    # há claims PARTIAL / factual UNSUPPORTED → revisar
    BLOCK = "block"      # há claim numérico/citação UNSUPPORTED ou CONTRADICTED


@dataclass
class Claim:
    id: str
    text: str                       # a afirmação atômica
    claim_type: ClaimType
    span: tuple[int, int]           # posição (início, fim) no texto gerado
    cited_refs: list[int] = field(default_factory=list)   # marcadores [n] presentes
    numbers: list[str] = field(default_factory=list)       # números extraídos do claim


@dataclass
class Evidence:
    chunk_id: str                   # id no ChromaDB (paper_md5 + chunk_index)
    paper_md5: str
    section: str
    text: str
    score: float = 0.0              # relevância recuperada (reranker/embedding)


@dataclass
class ClaimResult:
    claim: Claim
    verdict: Verdict
    confidence: float               # 0..1
    evidence: list[Evidence] = field(default_factory=list)
    rationale: str = ""
    numeric_ok: bool = True         # números batem com a fonte?
    citation_ok: bool = True        # [n] realmente sustenta a afirmação?


@dataclass
class GateReport:
    content_id: str
    source_question: str
    generated_text: str
    results: list[ClaimResult]
    decision: Decision
    unsupported_count: int = 0
    contradicted_count: int = 0
    human_approved: bool = False    # só vira True após revisão no dashboard
    reviewer: str = ""
    audit_path: str = ""            # JSON da trilha de auditoria
