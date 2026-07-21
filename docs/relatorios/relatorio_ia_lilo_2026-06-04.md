# Relatório — Tarefa agendada `ia_lilo`
**Data:** 2026-06-04 · **Execução:** autônoma (usuário ausente) · **Perfil de teste:** `desktop_dev` (teto de iterações = 3)

Escopo do ciclo: protocolo de teste semântico multi-domínio do LILO/Villa-Lobos; verificar erros em scripts e corrigir; analisar qualidade, bugs e tempo em 1/2/3 iterações; comparar com a corrida anterior; solucionar problemas de roteamento/prompts/timeouts; gerar versão mais potente do LILO; registrar achados na memória (`project_ia_lilo`) e em `docs/`.

> **Ambiente:** sandbox em **modo degradado (backend `mock`)** — sem Ollama/Anthropic nem rede LLM. Mede *travamento* e *autocorreção*, **não** a qualidade real do conteúdo (exige Ollama quente no FS nativo).

---

## 1. Achado crítico — `agent.py` truncado em disco (CORRIGIDO)

O arquivo **`agents/villa_lobos/agent.py` estava truncado em disco desde 2026-05-31 16:58** (escrita interrompida por limite de créditos): **971 linhas**, terminando no meio de uma string (`"De`) dentro da definição da ferramenta `villa_explain_routing`. **O módulo não compilava nem importava** (`SyntaxError: unterminated string literal`). Os benches de 06-02 e 06-03 só rodaram porque o mount serviu, em alguns momentos, uma cópia cacheada completa ao runtime — comportamento intermitente e não confiável.

**Correção:** o trecho íntegro até o ponto de truncamento é byte-idêntico ao *snapshot* `backups/source_snapshot_2026-05-23.tar.gz`. Reconstituí o *tail* a partir dele — resto de `get_tools()` + `health()` + `capability_registry()` + `_route_via_capabilities()` + `capabilities()` — restaurando o arquivo para **1055 linhas**. As correções de roteamento V10.3/V10.4/V10.5 estão **todas antes da linha 894** e ficaram intactas.

Validação (via Read tool autoritativo + cópia nativa `/tmp`): `py_compile` OK, `import` OK, `get_tools()` retorna as 3 ferramentas, e o roteamento V10.4/V10.5 responde correto:

| Query | `_detect_domain` | Esperado |
|---|---|---|
| "Explique as causas… da Revolução Francesa." | `None` → pipeline | ✔ |
| "Explique o princípio da incerteza…" | `None` → pipeline | ✔ |
| "o que e PCR?" / "o que é PCR?" | `gateway` (fold de acento) | ✔ |

**Segundo truncamento:** `tests/test_villa_routing.py` também estava cortado (linha 144, `test_decision_iterations_bounded` incompleto). Reparado com a chamada `_orchestrate_decision(q)` + `assert 1 <= iterations <= 3` faltantes.

---

## 2. Testes de regressão

Sem `pytest` instalável na sandbox (disco cheio: `No space left on device`), rodei as 10 funções via *shim* que respeita `@parametrize`/`fixture`: **19 casos · PASSED=19 · FAILED=0**. O log confirma o caminho V10.5 ativo: `query profunda -> pipeline (gateway rebaixado)`. `_route_check` mostra os 9 domínios uniformes (`moderate`/`skip=False`/`pipeline`) e o controle trivial em `skip=True` — **sem divergência de roteamento**.

---

## 3. Bench semântico multi-domínio (2026-06-04)

`scripts/bench_semantic_domains.py --iters 1,2,3`, perfil `desktop_dev`, 9 domínios × 3 = **27 corridas**. JSON: `docs/relatorios/bench_semantic_2026-06-04.json`.

| Data | Corridas | Travou | Bugs reais | Degradado | Qual. média (mock) | Tempo 1/2/3 (s) |
|---|---|---|---|---|---|---|
| 2026-05-31 | 27 | 0 | 0 | 21 | 9,8 | 0,063 / 0,049 / 0,056 |
| 2026-06-02 | 27 | 0 | 0 | 21 | 9,8 | 0,070 / 0,062 / 0,066 |
| 2026-06-03 | 27 | 0 | 0 | 27 | 5,0 | 0,021 / 0,019 / 0,023 |
| **2026-06-04** | **27** | **0** | **0** | **27** | **5,0** | **0,017 / 0,016 / 0,020** |

**Leitura — a queda 9,8 → 5,0 NÃO é regressão.** É o efeito esperado do fix V10.4/V10.5: toda query profunda agora vai ao **pipeline completo** em vez do **gateway raso**. Em modo mock o pipeline não tem LLM → degrada uniformemente (piso heurístico 5,0). O 9,8 anterior era **inflado** por respostas rasas do gateway (história/física pontuavam 25/28). O 06-04 confirma o estado pós-fix do 06-03 — e é a **primeira corrida em que o arquivo em disco realmente importa**. Escala de iterações 1→2→3 plana em mock (circuito aberto, sem trabalho real), como esperado; 0 travamento e 0 bug em todas as corridas.

---

## 4. Correção de desenvolvimento contínuo aplicada (P1)

Implementei **escrita atômica** (`tmp` + `os.replace`) na gravação do JSON do bench (`bench_semantic_domains.py`) — exatamente a classe de "arquivo meio-escrito/truncado" que corrompeu `agent.py` e o test file. Re-rodado: sem resíduo `.tmp`, JSON íntegro. Próximo passo é estender o padrão aos demais pontos de persistência (item P1 abaixo).

---

## 5. Limitação de ambiente (recorrente)

O mount do OneDrive serve **leituras truncadas intermitentes** ao runtime da sandbox (`cp`, `python`) mesmo quando `Read`/`Edit` enxergam o conteúdo autoritativo completo. Por isso todos os reparos foram validados pelo **Read tool** (autoritativo) e por cópia em **FS nativo `/tmp`**. No FS nativo Windows do usuário (sem essa camada de cache) os arquivos reparados importam normalmente.

---

## 6. Pendências para o próximo ciclo

1. **Ollama quente, FS nativo:** rodar o bench e medir **qualidade real** do conteúdo e o **delta de tempo** 1 vs 2 vs 3 iterações (em produção ≈ +1 chamada do Worker por iteração extra).
2. **P1 — write-atômico abrangente:** aplicar `tmp + os.replace` em `shared/kv_memory.py`, `fs_write` e na persistência de código/configs — **erradicar o truncamento na origem** (causa-raiz dos dois bugs deste ciclo).
3. **P2 — plataforma híbrida (API ~ Claude Desktop):** paridade de tool-calling entre `lilo_api.py` (SSE stage-a-stage) e `lilo_mcp.py`; seleção de perfil por header/JWT reusando `get_profile_policy()`.
4. **P3 — Villa como "LLM chamando agentes":** fan-out (delegar a >1 especialista + Reporter sintetiza) e *early-stop* quando Worker N ≈ N-1 (similaridade) para economizar a iteração extra.
5. **P4 — telemetria resiliente:** `CostTracker` loga `disk I/O error` (SQLite em FS restrito) — buffer em memória + flush retentável.

---

## 7. Resumo executivo

Identificado e corrigido um **bug crítico**: `agents/villa_lobos/agent.py` estava **truncado em disco** (971 linhas, sem importar) desde 2026-05-31 — restaurado para 1055 linhas a partir do snapshot, com as correções de roteamento V10.3/V10.4/V10.5 preservadas. O test file, também truncado, foi reparado. **19/19 testes verdes**; roteamento consistente nos 9 domínios. Bench 06-04: 27 corridas, **0 travamento, 0 bug**. A aparente queda de qualidade 9,8→5,0 é o **efeito correto do fix** (queries profundas vão ao pipeline, não ao gateway raso), não regressão. Aplicada escrita atômica no harness para conter a classe de truncamento. Achados gravados na memória `project_ia_lilo` (`bench_semantico_2026-06-04_achados`). Próximo ciclo: re-rodar com Ollama quente para medir ganho real e estender o write-atômico à persistência central.
