# Relatório — Tarefa agendada `ia_lilo`
**Data:** 2026-06-02 · **Execução:** autônoma (usuário ausente) · **Perfil de teste:** `desktop_dev` (teto de iterações = 3)

Escopo do ciclo: protocolo de teste semântico multi-domínio do LILO/Villa-Lobos; verificar erros em scripts e corrigir; analisar qualidade, bugs e tempo em 1/2/3 iterações; comparar com a corrida anterior; solucionar problemas de roteamento/prompts/timeouts; gerar versão mais potente do LILO; registrar achados na memória (`project_ia_lilo`) e em `docs/`.

> **Ambiente:** a sandbox roda em **modo degradado (backend `mock`)** — sem Ollama/Anthropic nem rede LLM. É o melhor cenário para medir *travamento* e *autocorreção* (quando circuit breaker e fallbacks precisam atuar), mas **não** mede a qualidade real do conteúdo gerado (isso exige Ollama quente no FS nativo).

---

## 1. Bench semântico multi-domínio (V10.3 → V10.4)

Harness: `scripts/bench_semantic_domains.py --iters 1,2,3`, perfil `desktop_dev`, 9 domínios × 3 iterações = **27 corridas**. JSON: `docs/relatorios/bench_semantic_2026-06-02.json`.

| Métrica | 2026-05-31 | 2026-06-02 | Δ |
|---|---|---|---|
| Corridas | 27 | 27 | = |
| Travou | 0 | 0 | = |
| Bugs reais (exceção Python) | 0 | 0 | = |
| Degradado (stage sem LLM) | 21 | 21 | = |
| Qualidade média (mock) | 9,8 | 9,8 | = |
| Tempo médio 1 / 2 / 3 iters (s) | 0,063 / 0,049 / 0,056 | 0,070 / 0,062 / 0,066 | ~igual |

**Leitura:** estado **estável, sem regressões**. Em modo mock o circuito abre e não há trabalho real, por isso os tempos são uniformes (~0,06 s) e a "qualidade" é um piso heurístico — esses números só ganham sentido com Ollama quente.

### 1.1 Achado principal — inconsistência de roteamento (corrigida)

Analisando o **caminho** (`path`) por domínio, duas perguntas de nível pesquisador eram tratadas de forma divergente das demais:

| Domínio | Query | Path (antes) | Qualidade |
|---|---|---|---|
| história | "**Explique** as principais causas econômicas e sociais da Revolução Francesa." | `delegacao → gateway` | 25 |
| física | "**Explique** o princípio da incerteza de Heisenberg e suas implicações físicas." | `delegacao → gateway` | 28 |
| química, biologia, matemática, agropecuária, veterinária, conhec. gerais, geografia | (mesma profundidade) | `pipeline` completo | — |

**Causa-raiz:** `_detect_domain()` casava a keyword genérica `"explique"` do domínio `gateway`. Como história e física começam com "Explique", eram **delegadas ao chat raso do gateway** (curto-circuitando o pipeline em `run()`, linha 256), enquanto perguntas igualmente profundas que **não** usam "explique" (química "Detalhe…", biologia "Como funciona…", matemática "Enuncie e demonstre…") seguiam o pipeline completo. Mesma profundidade → roteamento divergente → resposta rasa para 2 dos 9 domínios.

---

## 2. Correção aplicada — LILO V10.4

**Arquivo:** `agents/villa_lobos/agent.py`, função `_detect_domain()`.

1. **Rebaixamento do gateway para queries não triviais.** Se o melhor domínio é `gateway` e a query é longa (≥ 60 chars) **ou** contém marcador de profundidade (`_GATEWAY_DEEP_MARKERS`: `principa`, `implicac`, `mecanismo`, `causas`, `etapas`, `fatores`, `diagnostic`, `manejo`, `economic`, `sociais`, `enuncie`, `aprofund`, …), o gateway perde para o melhor especialista **não-gateway**; se nenhum casa, retorna `None` → **Villa roda o pipeline completo** (resposta técnica) em vez do chat raso. Consistente com a filosofia "trivialidade endurecida" da V10.3 já presente em `_orchestrate_decision`.

2. **Casamento insensível a acento (`_strip_accents`, NFD fold).** Corrige uma classe inteira de erro pt-BR: antes `"o que e"` (keyword) não casava `"o que é"` (query acentuada), e `química/física/replicação` acentuadas escapavam das keywords. Agora keyword e query são normalizadas antes do match.

**Validação (FS nativo `/tmp`, fora do mount):**

| Caso | Resultado | Esperado |
|---|---|---|
| história / física / geografia | `None` → pipeline | ✔ |
| "o que e PCR?" / "o que é PCR?" | `gateway` | ✔ |
| t-test/ANOVA → prism · pubmed → scholar · PDF/DOI → pdf | inalterado | ✔ |

Testes de regressão adicionados em `tests/test_villa_routing.py` (`test_detect_domain_deep_explanation_not_gateway`, `test_detect_domain_short_concept_stays_gateway` parametrizado com e sem acento).

**Limpeza:** removido `agents/villa_lobos/agent.py.new` (0 bytes, resíduo de escrita interrompida — pendência da sessão 2026-05-31).

---

## 3. Limitação de ambiente (importante)

O mount do OneDrive serve, ao **runtime do Python da sandbox**, uma versão **cacheada e por vezes truncada** dos arquivos editados: `import` e `py_compile` falham (nome ausente / *unterminated string*) **mesmo com `Edit`, `Read` e `grep` enxergando o conteúdo novo e completo** no arquivo autoritativo. Consequência: não foi possível executar `pytest`/bench já refletindo a V10.4 dentro da sandbox. A lógica foi validada **isoladamente em FS nativo** (`/tmp`). No FS nativo Windows do usuário (sem essa camada de cache) o import funciona normalmente.

---

## 4. Pendências para o próximo ciclo (Ollama quente, FS nativo)

1. Rodar `LILO_SERVER_PROFILE=desktop_dev python scripts/bench_semantic_domains.py --iters 1,2,3` com **Ollama quente** e confirmar que história e física passam a `path=pipeline` (não mais `delegacao`).
2. Medir a **qualidade real** do conteúdo e o **delta de tempo** 1 vs 2 vs 3 iterações (em mock o delta é ~0; em produção ≈ +1 chamada do Worker por iteração extra).
3. `pytest tests/test_villa_routing.py` — esperado ≥ 15 verdes (13 originais + novos).

## 5. Desenvolvimento contínuo (mantém prioridades da sessão anterior)

- **P1 — write-atômico** (`.tmp` + `os.replace`) nos pontos de persistência: elimina a classe de "arquivo meio-escrito" (vide `agent.py.new`, openclaw.json corrompido na sessão anterior).
- **P2 — plataforma híbrida (API ~ Claude Desktop):** `lilo_api.py` já tem SSE stage-a-stage; próximo passo é paridade de tool-calling com `lilo_mcp.py` e seleção de perfil por header/JWT reusando `get_profile_policy()`.
- **P3 — Villa como "LLM chamando agentes":** habilitar **fan-out** (delegar a >1 especialista + Reporter sintetiza) e *early-stop* quando Worker N ≈ N-1 (similaridade) para economizar a iteração extra.
- **P4 — telemetria resiliente:** o `CostTracker` logou `disk I/O error` em **toda** request na sandbox (SQLite em FS restrito) — non-fatal, mas perde métricas. Buffer em memória + flush retentável.

---

## 6. Resumo executivo

Bench multi-domínio estável vs. 2026-05-31 (27 corridas, 0 travamento, 0 bug). Identificada e corrigida uma **inconsistência real de roteamento** (V10.4): perguntas explicativas profundas (história, física) eram delegadas ao chat raso do gateway por casarem a keyword "explique", enquanto domínios de mesma profundidade seguiam o pipeline completo. A correção rebaixa o gateway em queries não triviais e adiciona casamento insensível a acento, com testes de regressão. Lógica validada em FS nativo; validação de runtime na sandbox bloqueada por cache do mount. Próximo ciclo deve re-rodar com Ollama quente para medir ganho real de qualidade/tempo.
