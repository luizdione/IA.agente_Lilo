"""tests/shared/test_policy_budget.py — V18 QW3: limites de custo do Policy.

Offline (sem rede/LLM). Cobre os dois gates que eram letra morta ate a V18
(ver docs/tecnico/analise_open_agent_studio.md, secao 4):
  1. LILO_MAX_SINGLE_COST — teto POR CHAMADA aplicado em _budget_allows
  2. LILO_ALLOW_CLOUD — flag do .env volta a ser lida (E chave presente)
"""
from __future__ import annotations

from shared.policy import ExecutionTier, PolicyConfig, PolicyEngine


def _engine(monkeypatch, *, budget=10.0, ceiling=0.50, today=0.0,
            allow_cloud=None):
    cfg = PolicyConfig(daily_budget_usd=budget, max_single_cost_usd=ceiling)
    if allow_cloud is not None:
        cfg.allow_cloud = allow_cloud
    eng = PolicyEngine(cfg)
    monkeypatch.setattr(eng, "_today_cost", lambda: today)
    return eng


def test_max_single_cost_barra_chamada_cara(monkeypatch):
    # Opus: $0.045/1K estimado; input de 8000 chars -> ~2000 tokens -> ~$0.09.
    eng = _engine(monkeypatch, ceiling=0.01)
    assert eng._budget_allows(ExecutionTier.CLAUDE_OPUS, 8000) is False


def test_max_single_cost_libera_abaixo_do_teto(monkeypatch):
    eng = _engine(monkeypatch, ceiling=0.50)
    assert eng._budget_allows(ExecutionTier.CLAUDE_OPUS, 8000) is True


def test_budget_diario_continua_valendo(monkeypatch):
    # Teto por chamada folgado, mas budget do dia quase esgotado -> barra.
    eng = _engine(monkeypatch, budget=0.05, ceiling=0.50, today=0.049)
    assert eng._budget_allows(ExecutionTier.CLAUDE_OPUS, 8000) is False


def test_decide_degrada_tier_quando_teto_barra(monkeypatch):
    # Query complexa (indicador + input longo) com teto minusculo: em vez de
    # CLAUDE_*, a decisao degrada para o modelo local pesado.
    eng = _engine(monkeypatch, ceiling=0.0001, allow_cloud=True)
    query = "arquitetura do pipeline completo " * 200  # >5000 chars + indicadores
    decision = eng.decide(query)
    assert decision.tier == ExecutionTier.OLLAMA_HEAVY


def test_allow_cloud_exige_flag_e_chave(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("LILO_ALLOW_CLOUD", "0")
    assert PolicyConfig().allow_cloud is False

    monkeypatch.setenv("LILO_ALLOW_CLOUD", "true")
    assert PolicyConfig().allow_cloud is True

    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert PolicyConfig().allow_cloud is False


def test_allow_cloud_default_ligada_com_chave(monkeypatch):
    # Sem a flag no ambiente, o default e "true" -> comportamento pre-V18
    # (chave presente = nuvem permitida) preservado.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("LILO_ALLOW_CLOUD", raising=False)
    assert PolicyConfig().allow_cloud is True
