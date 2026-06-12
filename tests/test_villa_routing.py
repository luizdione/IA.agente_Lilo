"""
tests/test_villa_routing.py -- Cobertura da logica de roteamento do Villa_Lobos.

Criado em 2026-05-26 (tarefa agendada ia_lilo) para fechar a lacuna de testes:
ate entao apenas shared/kv_memory.py tinha cobertura. Estes testes exercitam,
de forma DETERMINISTICA e OFFLINE (sem Ollama/nuvem), a maquinaria de
roteamento que e o coracao do orquestrador:

  * _detect_domain (heuristica por keywords)
  * _orchestrate_decision (fallback heuristico + cache LRU)
  * explain_routing (debug sem executar pipeline)
  * cap de iteracoes por perfil de servidor (server_profile)
  * normalizacao de query p/ chave de cache

Para isolar o backend, injetamos um client falso cujo .chat() devolve sempre
"[MOCK]" -- assim _orchestrate_decision/_route_via_llm caem no caminho
heuristico de forma previsivel, independentemente do ambiente.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class _FakeClient:
    """Client LLM falso: forca o caminho heuristico (resposta '[MOCK]')."""
    backend = "mock"

    def chat(self, *a, **k):
        return "[MOCK] resposta simulada para teste"

    def health(self):
        return {"backend": "mock"}


@pytest.fixture()
def villa():
    from agents.villa_lobos.agent import VillaLobosAgent
    v = VillaLobosAgent()
    v.client = _FakeClient()
    return v


# --------------------------------------------------------------------------
# _detect_domain
# --------------------------------------------------------------------------
@pytest.mark.parametrize("query,expected", [
    ("rode um t-test e compare grupos com ANOVA", "prism"),
    ("escreva uma query SELECT com JOIN no banco sqlite", "sql"),
    ("resuma a introducao deste artigo PDF (DOI 10.x)", "pdf"),
    ("busque papers no pubmed sobre apoptose", "scholar"),
])
def test_detect_domain(query, expected):
    from agents.villa_lobos.agent import _detect_domain
    assert _detect_domain(query) == expected


def test_detect_domain_none_for_generic():
    from agents.villa_lobos.agent import _detect_domain
    # frase sem keyword de dominio -> None (vai p/ pipeline completo)
    assert _detect_domain("zzz qqq xyz abc") is None


@pytest.mark.parametrize("query", [
    # V10.4: pedidos de EXPLICACAO PROFUNDA nao podem cair no gateway raso.
    "Explique o principio da incerteza de Heisenberg e suas implicacoes fisicas.",
    "Explique as principais causas economicas e sociais da Revolucao Francesa.",
])
def test_detect_domain_deep_explanation_not_gateway(query):
    from agents.villa_lobos.agent import _detect_domain
    # gateway rebaixado -> None (Villa roda pipeline completo, resposta tecnica)
    assert _detect_domain(query) != "gateway"


@pytest.mark.parametrize("query", [
    "o que e PCR?",
    "o que é PCR?",   # V10.4: acento nao deve quebrar o casamento (fold)
])
def test_detect_domain_short_concept_stays_gateway(query):
    from agents.villa_lobos.agent import _detect_domain
    # pergunta curta e conceitual continua valida para o gateway (chat rapido)
    assert _detect_domain(query) == "gateway"


@pytest.mark.parametrize("query", [
    # V10.5: a delegacao COMPLETA (llm+heuristic+capabilities) nao pode mandar
    # query profunda ao gateway raso. Regressao: _detect_domain ja rebaixava
    # gateway->None, mas _route_via_capabilities reinjetava 'gateway' p/
    # historia/fisica -> delegacao rasa (qualidade 25/28). Agora -> pipeline.
    "Explique o principio da incerteza de Heisenberg e suas implicacoes fisicas.",
    "Explique as principais causas economicas e sociais da Revolucao Francesa.",
    "Descreva a formacao e a importancia das bacias hidrograficas do Brasil.",
])
def test_delegate_deep_query_falls_to_pipeline(villa, query):
    # None => Villa nao delega e roda o pipeline completo (resposta tecnica).
    assert villa._delegate_to_specialist(query, {}) is None


@pytest.mark.parametrize("query,expected", [
    ("o que e PCR?", False),
    ("Explique as principais causas economicas e sociais", True),
    ("causas economicas e sociais da revolucao", True),  # fold de acento
])
def test_is_deep_query(query, expected):
    from agents.villa_lobos.agent import _is_deep_query
    assert _is_deep_query(query) is expected


# --------------------------------------------------------------------------
# V11.2 (2026-06-11): guarda anti-fast-path UNIFICADA (ramo LLM + heuristico).
# Bench 2026-06-11: fisica ("Explique ... e suas implicacoes fisicas") caiu em
# fast-path (q=64) porque a guarda do ramo do LLM-orchestrator so cobria
# demonstracao/prova, deixando explicacao/profundidade escapar.
# --------------------------------------------------------------------------
@pytest.mark.parametrize("query,expected", [
    ("Enuncie e demonstre o teorema fundamental do calculo.", "proof"),
    ("prove que a soma de dois pares e par", "proof"),
    ("Explique o principio da incerteza e suas implicacoes fisicas.", "explain"),
    ("Detalhe o mecanismo da esterificacao de Fischer.", "explain"),
    ("Descreva a formacao das bacias hidrograficas.", "explain"),
    # factual curto/longo SEM marcador -> fast-path permitido (celeridade)
    ("o que e PCR?", None),
    ("Qual a capital da Franca e a sua populacao aproximada hoje?", None),
])
def test_block_fast_path_classification(query, expected):
    from agents.villa_lobos.agent import _block_fast_path
    assert _block_fast_path(query) == expected


class _FakeClientFastSkip:
    """LLM falso que SEMPRE manda pular para o reporter (skip_to_reporter=true).

    Simula o classificador LLM marcando fast-path indevidamente; a guarda
    V11.2 deve reescalar queries explicativas/prova para o Worker.
    """
    backend = "ollama"

    def chat(self, *a, **k):
        return ('{"complexity":"simple","needs_planning":false,'
                '"needs_reader":false,"needs_worker":false,"iterations":1,'
                '"skip_to_reporter":true,"reasoning":"factual"}')

    def health(self):
        return {"backend": "ollama"}


@pytest.mark.parametrize("query,min_iters", [
    ("Explique o principio da incerteza de Heisenberg e suas implicacoes fisicas.", 1),
    ("Detalhe o mecanismo da esterificacao de Fischer, incluindo catalise.", 1),
    ("Enuncie e demonstre o teorema fundamental do calculo.", 2),  # prova -> >=2
])
def test_llm_fast_path_escalated_to_worker(query, min_iters):
    from agents.villa_lobos.agent import VillaLobosAgent
    v = VillaLobosAgent()
    v.client = _FakeClientFastSkip()
    d = v._orchestrate_decision(query, use_cache=False)
    # Mesmo o LLM mandando pular, a guarda V11.2 garante o Worker.
    assert d["skip_to_reporter"] is False
    assert d["needs_worker"] is True
    assert d["iterations"] >= min_iters


def test_llm_fast_path_preserved_for_trivial():
    # Query factual curta sem marcador: fast-path do LLM e RESPEITADO.
    from agents.villa_lobos.agent import VillaLobosAgent
    v = VillaLobosAgent()
    v.client = _FakeClientFastSkip()
    d = v._orchestrate_decision("o que e PCR?", use_cache=False)
    assert d["skip_to_reporter"] is True
    assert d["needs_worker"] is False


# --------------------------------------------------------------------------
# V12 (2026-06-11): porta única de roteamento semântico (route_target).
# Com o client mock, _route_via_llm devolve None -> cai na heurística
# (_detect_domain), exercitando o roteamento de forma offline/determinística.
# --------------------------------------------------------------------------
@pytest.mark.parametrize("query,expected", [
    ("rode um t-test e compare grupos com ANOVA", "prism"),
    ("busque papers no pubmed sobre apoptose", "scholar"),
    ("escreva uma query SELECT com JOIN no banco sqlite", "sql"),
])
def test_route_target_specialist(villa, query, expected):
    avail = {"sql", "pdf", "scholar", "prism", "villa", "gateway", "desktop"}
    target, method = villa.route_target(query, avail)
    assert target == expected
    assert method in ("llm", "heuristic", "capabilities")


def test_route_target_ambiguous_goes_to_pipeline(villa):
    # Sem keyword de domínio e sem LLM (mock) -> pipeline multi-agente, nunca
    # gateway raso. (zzz... não casa nenhuma heurística nem capabilities.)
    target, method = villa.route_target("zzz qqq xyz", {"villa", "gateway"})
    assert target == "villa"


def test_route_target_unavailable_domain_falls_to_villa(villa):
    # Domínio detectado (prism) mas NÃO disponível -> cai em villa.
    target, method = villa.route_target(
        "rode ANOVA e compare grupos", {"villa", "gateway"})
    assert target == "villa"


# --------------------------------------------------------------------------
# V12: delegação por etapa -- worker_agent no JSON do Orchestrator, validado.
# --------------------------------------------------------------------------
class _FakeClientWorkerAgent:
    backend = "ollama"

    def __init__(self, wa):
        self._wa = wa

    def chat(self, *a, **k):
        return ('{"complexity":"moderate","needs_planning":true,'
                '"needs_reader":false,"needs_worker":true,"iterations":1,'
                '"skip_to_reporter":false,"worker_agent":"%s",'
                '"reasoning":"x"}' % self._wa)

    def health(self):
        return {"backend": "ollama"}


@pytest.mark.parametrize("wa,expected", [
    ("scholar", "scholar"),     # especialista valido -> preservado
    ("prism", "prism"),
    ("banana", None),           # alucinacao -> rejeitada
    ("villa", None),            # nao e stage-agent (evita recursao)
    ("gateway", None),          # chat raso nao executa etapa
])
def test_worker_agent_validation(wa, expected):
    from agents.villa_lobos.agent import VillaLobosAgent
    v = VillaLobosAgent()
    v.client = _FakeClientWorkerAgent(wa)
    d = v._orchestrate_decision("analise os dados do experimento", use_cache=False)
    assert d.get("worker_agent") == expected


# --------------------------------------------------------------------------
# _orchestrate_decision (heuristica, pois client e mock)
# --------------------------------------------------------------------------
def test_decision_simple_query_skips_to_reporter(villa):
    d = villa._orchestrate_decision("o que e PCR?")
    assert d["skip_to_reporter"] is True
    assert d["needs_worker"] is False
    assert d["_source"] in ("heuristic", "llm")


def test_decision_complex_query_runs_full_pipeline(villa):
    q = ("Analise e compare o efeito de inibidores competitivos e implemente "
         "o calculo de Ki para a cinetica de Michaelis-Menten neste experimento.")
    d = villa._orchestrate_decision(q)
    assert d["skip_to_reporter"] is False
    assert d["needs_worker"] is True
    assert 1 <= d["iterations"] <= 3


def test_decision_cache_hit(villa):
    q = "explique a via de sinalizacao MAPK em detalhe tecnico aprofundado"
    villa._orchestrate_decision(q)               # miss
    before = villa.cache_stats()["hits"]
    villa._orchestrate_decision(q)               # hit
    after = villa.cache_stats()["hits"]
    assert after == before + 1


def test_decision_iterations_bounded(villa):
    # iterations sempre no intervalo [1,3] mesmo via heuristica
    for q in ["o que e DNA", "implemente um pipeline completo e compare resultados",
              "rode analise estatistica e plote graficos"]:
        d = villa._orchestrate_decision(q)
        assert 1 <= d["iterations"] <= 3
        d = villa._orchestrate_decision(q)
        assert 1 <= d["iterations"] <= 3


# --------------------------------------------------------------------------
# normalizacao de cache
# --------------------------------------------------------------------------
def test_cache_key_normalization_is_stable():
    from agents.villa_lobos.agent import VillaLobosAgent
    k1 = VillaLobosAgent._normalize_query_for_cache("  Olá   Mundo  ")
    k2 = VillaLobosAgent._normalize_query_for_cache("olá mundo")
    assert k1 == k2  # case + espacos normalizados


# --------------------------------------------------------------------------
# explain_routing
# --------------------------------------------------------------------------
def test_explain_routing_structure(villa):
    info = villa.explain_routing("compare dois grupos com t-test")
    for key in ("query", "domain_heuristic", "decision",
                "stages_planned", "stage_tiers", "server_profile"):
        assert key in info
    assert info["stages_planned"][0] == "orchestrator"
    assert info["stages_planned"][-1] == "reporter"


# --------------------------------------------------------------------------
# cap de iteracoes por perfil de servidor
# --------------------------------------------------------------------------
def test_profile_iteration_cap():
    from shared.server_profile import get_profile_policy
    # cowork/bio/pycharm => teto 2; desktop_dev/claude_desktop => 3
    assert get_profile_policy("cowork")["max_iterations"] == 2
    assert get_profile_policy("bio")["max_iterations"] == 2
    assert get_profile_policy("desktop_dev")["max_iterations"] == 3
    # perfil desconhecido -> politica conservadora (local, sem nuvem, teto 2)
    unknown = get_profile_policy("perfil_inexistente_xyz")
    assert unknown["known"] is False
    assert unknown["allow_cloud"] is False
    assert unknown["max_iterations"] == 2


def test_health_reports_smart_routing(villa):
    h = villa.health()
    assert h["smart_routing"] is True
    assert h["delegation_enabled"] is True
    assert "decision_cache" in h


# --------------------------------------------------------------------------
# V10.6 (2026-06-05): regressao do match por substring em _route_via_capabilities
# O keyword 'cat' do agente desktop casava dentro de "CATalise" (quimica) e
# sequestrava a query profunda para um `fs_list`. O match agora e por
# fronteira de palavra (\b...\b).
# --------------------------------------------------------------------------
def test_capabilities_route_word_boundary_no_false_positive(villa):
    # "catalise" NAO pode casar o keyword 'cat' do agente desktop
    assert villa._route_via_capabilities(
        "detalhe o mecanismo da esterificacao de fischer, incluindo "
        "catalise acida e equilibrio") != "desktop"
    # outras palavras que contem keywords curtos como substring
    assert villa._route_via_capabilities(
        "categoria e classificacao dos lipidios") != "desktop"


def test_capabilities_route_legitimate_desktop_still_matches(villa):
    # comandos reais de filesystem/shell continuam casando o agente desktop
    assert villa._route_via_capabilities(
        "liste os arquivos do diretorio atual") == "desktop"
    assert villa._route_via_capabilities(
        "faca cat no arquivo de log") == "desktop"
