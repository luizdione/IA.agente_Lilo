"""
tests/test_integration.py — Testes de integração (reranker real + juiz Ollama local).

Ficam FORA da rodada padrão (addopts = -m 'not integration'). Para rodar:
    python -m pytest -m integration

Cada teste pula com graça se a dependência/serviço não estiver disponível.
"""
import pytest

pytestmark = pytest.mark.integration


def test_bge_reranker_scores_in_unit_range():
    """O reranker real devolve score 0..1 e prefere o trecho relevante."""
    pytest.importorskip("FlagEmbedding")
    from scholaragent.verify.reranker import BgeReranker

    rr = BgeReranker()
    claim = "O Nelore é adaptado ao estresse térmico."
    bom = rr.score(claim, "O Nelore apresenta adaptação ao estresse térmico em clima tropical.")
    ruim = rr.score(claim, "A reação de PCR foi otimizada com primers específicos.")
    assert 0.0 <= ruim <= 1.0 and 0.0 <= bom <= 1.0
    assert bom > ruim


def test_ollama_judge_reachable():
    """O juiz NLI local responde com um veredicto válido (exige Lilo 3.0 na :11435)."""
    httpx = pytest.importorskip("httpx")
    from scholaragent.verify.ollama_judge import make_ollama_judge, OLLAMA_URL, _VALID

    try:
        httpx.get(OLLAMA_URL.replace("/api/generate", "/api/tags"), timeout=2)
    except Exception:
        pytest.skip("Ollama/Lilo 3.0 não acessível na porta 11435")

    judge = make_ollama_judge()
    verdict, conf, _ = judge(
        "O céu é azul.", "Observou-se que o céu apresenta coloração azul durante o dia."
    )
    assert verdict in _VALID
    assert 0.0 <= conf <= 1.0
