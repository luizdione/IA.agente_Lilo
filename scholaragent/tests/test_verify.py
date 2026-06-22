"""
tests/test_verify.py — Critérios de aceite do gate de verificação factual.
Usa fakes injetáveis para o juiz LLM e o reranker — não exige Ollama/ChromaDB.
"""
import pytest

from scholaragent.verify.contracts import Evidence, Decision
from scholaragent.verify.grounding import Grounder
from scholaragent.verify.gate import VerificationGate
from scholaragent.export.guard import can_export, assert_exportable, ExportBlocked


# --------------------------- fakes injetáveis ----------------------------- #
def judge_supported(claim, evidence):
    return "supported", 0.9, "ok"


def judge_not_enough(claim, evidence):
    return "not_enough_info", 0.2, "sem suporte na evidência"


class HighReranker:
    def score(self, a, b):
        return 0.95


class LowReranker:
    def score(self, a, b):
        return 0.05


def make_gate(judge, reranker):
    return VerificationGate(Grounder(judge=judge, reranker=reranker))


def ev(text, md5="m1", sec="results"):
    return Evidence(chunk_id=f"{md5}_0", paper_md5=md5, section=sec, text=text)


# ------------------------------- 1. órfã ---------------------------------- #
def test_orphan_citation_blocks():
    gate = make_gate(judge_supported, HighReranker())
    text = "O eQTL regula a expressão muscular [3]."
    chunks = [ev("O eQTL regula a expressão muscular no Nelore.")]
    report = gate.verify("t1", "q", text, chunks, ref_to_evidence={}, write_trail=False)
    assert report.decision == Decision.BLOCK
    assert any(not r.citation_ok for r in report.results)


# --------------------------- 2. número inventado -------------------------- #
def test_invented_number_blocks():
    gate = make_gate(judge_supported, HighReranker())
    text = "O estudo incluiu 240 animais."
    chunks = [ev("O estudo incluiu 180 animais Nelore.")]
    report = gate.verify("t2", "q", text, chunks, write_trail=False)
    assert report.decision == Decision.BLOCK
    assert any(not r.numeric_ok for r in report.results)


# ------------------------- 3. fonte mal atribuída ------------------------- #
def test_misattributed_citation_blocks():
    gate = make_gate(judge_not_enough, HighReranker())   # juiz: evidência não sustenta
    text = "A naftoquinona inibe a cruzaína [1]."
    src = ev("Texto sobre reprodução bovina e IATF, sem relação com cruzaína.")
    report = gate.verify("t3", "q", text, [src], ref_to_evidence={1: src}, write_trail=False)
    assert report.decision == Decision.BLOCK
    assert any(not r.citation_ok for r in report.results)


# --------------- 4. afirmação factual não suportada -> REVIEW ------------- #
def test_unsupported_factual_reviews():
    gate = make_gate(judge_not_enough, LowReranker())
    text = "O gene candidato é responsável pela termotolerância."
    chunks = [ev("Conteúdo irrelevante sobre metagenômica de rúmen.")]
    report = gate.verify("t4", "q", text, chunks, write_trail=False)
    assert report.decision == Decision.REVIEW


# ------------- 5. tudo ancorado -> PASS, mas sem aprovação humana --------- #
def test_all_grounded_passes_but_not_approved():
    gate = make_gate(judge_supported, HighReranker())
    text = "O Nelore apresenta adaptação ao estresse térmico."
    chunks = [ev("O Nelore apresenta marcada adaptação ao estresse térmico em clima tropical.")]
    report = gate.verify("t5", "q", text, chunks, write_trail=False)
    assert report.decision == Decision.PASS
    assert report.human_approved is False
    assert can_export(report) is False        # PASS não basta: precisa de revisão humana


# ---------------- 6. export bloqueado sem PASS + aprovação ---------------- #
def test_export_guard():
    gate = make_gate(judge_supported, HighReranker())
    text = "O Nelore apresenta adaptação ao estresse térmico."
    chunks = [ev("O Nelore apresenta marcada adaptação ao estresse térmico em clima tropical.")]
    report = gate.verify("t6", "q", text, chunks, write_trail=False)
    assert report.decision == Decision.PASS
    with pytest.raises(ExportBlocked):
        assert_exportable(report)             # ainda não aprovado
    report.human_approved = True
    report.reviewer = "Luiz Dione (IFRJ)"
    assert can_export(report) is True
    assert_exportable(report)                 # agora libera (não levanta)


# ---- 7. resposta degenerada/vazia -> REVIEW (nao PASS vacuo) ------------- #
def test_degenerate_answer_reviews():
    # "[3] [5]" (so marcadores) nao gera nenhum claim verificavel -> nao pode dar PASS
    gate = make_gate(judge_supported, HighReranker())
    report = gate.verify("t7", "q", "[3] [5]", [ev("texto de contexto qualquer")],
                         write_trail=False)
    assert report.results == []
    assert report.decision == Decision.REVIEW
