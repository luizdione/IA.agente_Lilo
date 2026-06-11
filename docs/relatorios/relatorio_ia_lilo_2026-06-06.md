# Relatório — Tarefa agendada `ia_lilo`
**Data:** 2026-06-06 · **Execução:** autônoma (usuário ausente) · **Perfil de teste:** `desktop_dev` (teto de iterações = 3)

Escopo do ciclo: protocolo de teste semântico multi-domínio do LILO/Villa-Lobos; verificar erros em scripts e corrigir; analisar qualidade, bugs e tempo em 1/2/3 iterações; comparar com a corrida anterior; solucionar problemas de roteamento/prompts/circuit breaker/timeouts; gerar versão mais potente do LILO; registrar achados na memória (`project_ia_lilo`) e em `docs/`.

> **Ambiente:** sandbox em **modo degradado (backend `mock`)** — sem Ollama nem rede LLM (`http://localhost:11434` indisponível). Mede *roteamento*, *travamento*, *autocorreção* e *integridade de código*, **não** a qualidade real do conteúdo (exige Ollama quente no FS nativo).

---

## 1. Verificação de scripts — AST/compile

Checagem de sintaxe (`py_compile`) em **todos os 267 arquivos `.py`** do projeto (excluídos `_ARCHIVE_v10`, `obsoletos`, caches): **0 erros**. Base de código íntegra; nenhuma quebra de sintaxe herdada de ciclos anteriores.

---

## 2. Achado deste ciclo — reporte enganoso do circuit breaker (CORRIGIDO · V10.7)

Durante o bench, os logs do estágio Worker/Reporter exibiam:

```
worker (qwen2.5-coder:14b, tier=auto) tentativa 1/1
Agente worker falhou apos 2 tentativas: resposta vazia ou mock
```

Há **contradição**: o loop roda `tentativa 1/1` (uma só chamada), mas a mensagem final reporta `apos 2 tentativas`.

**Causa-raiz:** em `_call_agent` (`agents/villa_lobos/agent.py`), com o **circuit breaker aberto** (backend `mock`) define-se `effective_retries = 1` para não desperdiçar reintentos sem LLM. Porém o `log.error` final e a string de retorno de erro usavam a constante `MAX_RETRIES` (=2) em vez de `effective_retries`. Resultado: telemetria/logs enganosos — sugeria duas falhas onde houve apenas uma.

**Correção (V10.7):**

```python
log.error("  Agente %s falhou apos %d tentativa(s): %s",
          role, effective_retries, last_error)
return "[%s ERRO apos %d tentativas: %s]" % (role, effective_retries, last_error)
```

**Validação (FS nativo):** após o fix o log passou a reportar corretamente:

```
Agente planner falhou apos 1 tentativa(s): resposta vazia ou mock
```

Em produção (Ollama quente, circuito fechado) `effective_retries == MAX_RETRIES`, então o comportamento e a contagem permanecem idênticos ao anterior — a correção só conserta o caso degradado. Impacto funcional nulo no roteamento/qualidade/tempo; é uma correção de **honestidade de telemetria**, importante porque os relatórios de bug deste protocolo dependem de logs fiéis.

---

## 3. Bench semântico multi-domínio (2026-06-06)

`scripts/bench_semantic_domains.py --iters 1,2,3`, perfil `desktop_dev`, 9 domínios × 3 = **27 corridas**. JSON: `docs/relatorios/bench_semantic_2026-06-06.json`.

| Data | Corridas | Travou | Bugs reais | Degradado | Qual. média (mock) | Tempo 1/2/3 (s) | Roteamento |
|---|---|---|---|---|---|---|---|
| 2026-06-03 | 27 | 0 | 0 | 27 | 5,0 | 0,021 / 0,019 / 0,023 | pipeline |
| 2026-06-04 | 27 | 0 | 0 | 27 | 5,0 | 0,017 / 0,016 / 0,020 | pipeline |
| 2026-06-05 (pós-fix V10.6) | 27 | 0 | 0 | 27 | 5,0 | 0,014 / 0,015 / 0,018 | pipeline (uniforme) |
| **2026-06-06 (V10.7)** | **27** | **0** | **0** | **27** | **5,0** | **0,015 / 0,015 / 0,019** | **pipeline (uniforme nos 9)** |

**Leitura:** roteamento **uniforme** — `path = pipeline` e `route_domain = geral` para todos os 27 (9 domínios × 3 iters). O fix V10.6 (química desviando para `desktop` via substring `cat`→`catálise`) **se mantém estável**, sem regressão. Em modo mock a escala 1→2→3 iterações permanece praticamente plana (circuito sem LLM real), com **0 travamento e 0 bug** em todas as corridas. A qualidade 5,0 é o piso heurístico do modo mock (não reflete conteúdo real).

---

## 4. Limitação de ambiente (recorrente, contornada)

O mount do OneDrive serviu **leituras truncadas** de `agents/villa_lobos/agent.py` ao runtime do sandbox: o bash via o arquivo cortado na **linha 1061** (real = **1067**, confirmado pelo Read tool), quebrando `py_compile` num literal de string aberto na linha 1062. As ferramentas **Read/Edit** (autoritativas) acessam o arquivo íntegro — a correção V10.7 foi gravada e **confirmada por leitura** no arquivo do usuário. A validação de execução foi feita reconstruindo a cauda truncada numa cópia em **FS nativo `/tmp/lilo_run`** (598 itens, 597/597 `.py` compilando; o único truncado foi `agent.py`, reconstituído a partir do conteúdo autoritativo). Esta é a 3ª ocorrência do problema (ver relatórios 06-04/06-05) e reforça a pendência **P1 — write-atômico abrangente**.

---

## 5. Segurança — observação

O `.env` contém `ANTHROPIC_API_KEY` em **texto claro**. Verificado que `.env` está **no `.gitignore` e não rastreado** pelo git (`git check-ignore` e `git ls-files` confirmam) — portanto **não vaza pelo repositório**. Recomendação: se este `.env` já foi copiado/compartilhado fora da máquina, **rotacionar a chave** por precaução.

---

## 6. Desenvolvimento contínuo — fila priorizada

1. **Ollama quente, FS nativo:** rodar o bench medindo **qualidade real** do conteúdo e o **delta de tempo** 1 vs 2 vs 3 iterações (em produção ≈ +1 chamada do Worker por iteração extra). Único passo capaz de validar o objetivo central do protocolo.
2. **P1 — write-atômico abrangente:** estender `tmp + os.replace` a `shared/kv_memory.py`, `fs_write` e persistência de código/configs — erradicar o truncamento na origem (já confirmado 3× neste mês).
3. **P2 — plataforma híbrida (API ~ Claude Desktop):** paridade de tool-calling entre `lilo_api.py` (SSE stage-a-stage) e `lilo_mcp.py`; seleção de perfil por header/JWT reusando `get_profile_policy()`.
4. **P3 — Villa como "LLM chamando agentes":** fan-out (delegar a >1 especialista + Reporter sintetiza) e *early-stop* quando Worker N ≈ N-1 (similaridade).
5. **P4 — telemetria resiliente:** `CostTracker` com buffer em memória + flush retentável (SQLite em FS restrito loga `disk I/O error`).
6. **Follow-up V10.7:** adicionar teste de regressão travando o formato da mensagem de erro em modo degradado (`[role ERRO apos 1 tentativas: ...]`) assim que `pytest` rodar no FS nativo.

---

## 7. Resumo executivo

Base íntegra (**267/267 `.py` compilam**). Identificado e corrigido um bug de **honestidade de telemetria (V10.7)**: com o circuit breaker aberto (modo mock), `_call_agent` reportava `falhou apos 2 tentativas` (constante `MAX_RETRIES`) apesar de só ter feito **1 chamada** (`effective_retries=1`); trocado para `effective_retries`, validado no FS nativo. Bench semântico **27/27 em pipeline, roteamento uniforme nos 9 domínios, 0 travamento, 0 bug real** — o fix V10.6 (química) permanece estável, sem regressão. Tempos planos em mock (0,015/0,015/0,019 s para 1/2/3 iters). Recorreu novamente o truncamento intermitente do mount OneDrive (`agent.py` cortado na linha 1061), contornado via Read autoritativo + cópia em FS nativo. `.env` confirmado fora do git. Achados gravados na memória `project_ia_lilo` (`bench_semantico_2026-06-06_achados`). **Próximo ciclo:** Ollama quente para medir ganho real de conteúdo e atacar o P1 (write-atômico na persistência central).
