# Villa-Lobos — Pipeline Multi-Estágio

**Path:** `agents/villa_lobos/agent.py`
**Tools MCP:** `villa_pipeline`, `villa_quick_ask`
**Smart routing:** v10.1 (2026-05-07)

---

## Pipeline 5-stage com smart routing

```
Orchestrator → Planner → Reader → Worker → Reporter
   (decisão)   (plano)  (contexto)(execução) (síntese)
        │         │        │         │
        └─ pode pular qualquer stage abaixo, ou ir direto ao Reporter
```

A partir da v10.1, o **Orchestrator emite JSON estruturado** declarando
quais stages são realmente necessários. Tarefas triviais (definições,
conversões, perguntas factuais) entram no **fast-path** e pulam direto
ao Reporter — 1 chamada Ollama em vez de 5 (~70% menos latência).

| Stage | Modelo default | Função |
|---|---|---|
| **Orchestrator** | llama3.1:8b-instruct-q8_0 | Analisa complexidade e dominio |
| **Planner** | phi3:14b-medium-128k-instruct-q4_K_M | Cria plano detalhado |
| **Reader** | qwen2.5-coder:14b | Lê arquivos do diretório `base_path` (opcional) |
| **Worker** | qwen2.5-coder:14b | Executa o plano (1-5 iterações) |
| **Reporter** | llama3.1:8b-instruct-q8_0 | Sintetiza relatório final |

Modelos configuráveis em `VILLA_MODELS` (no agent.py) ou via `.env` (`OLLAMA_MODEL_*`).

---

## Smart routing — JSON do Orchestrator

O método `_orchestrate_decision(query)` retorna:

```json
{
  "complexity": "trivial | simple | moderate | complex",
  "needs_planning": true,
  "needs_reader": true,
  "needs_worker": true,
  "iterations": 1,
  "skip_to_reporter": false,
  "reasoning": "frase curta justificando a decisão"
}
```

**Como cada flag controla o pipeline:**

| Flag | Efeito |
|---|---|
| `skip_to_reporter=true` | **Fast-path**: pula Planner+Reader+Worker, executa só o Reporter com prompt direto. Para definições, factos, conversões. |
| `needs_planning=false` | Pula stage 2 (Planner). Útil em tarefas diretas (tradução, paráfrase, resumo). |
| `needs_reader=false` | Pula stage 3 (Reader). Quando a query não referencia arquivos/dados externos. |
| `needs_worker=false` | Pula stage 4 (Worker). Reporter responde direto com base em Plano + Reader. |
| `iterations` | 1-3, limitado pelo Orchestrator (3 só em tarefas multi-fase complexas). |

**Fallback triplo (do mais ao menos confiável):**

1. **LLM estruturado** (modelo `autocomplete`/`chat` leve, temperature=0, JSON).
2. **Heurística regex** — `_SIMPLE_PATTERNS` (ex: "o que é...", "defina...", "converter ...") + queries < 80 chars sem verbos imperativos viram `skip_to_reporter`.
3. **Default conservador** — pipeline completo (todos `needs_*=true`).

**Override manual via `context`** (compat com chamadas antigas e testes):

```python
agent.run(query, context={
    "needs_planning": False,
    "needs_reader": False,
    "iterations": 1,
})
```

A saída do pipeline mostra qual roteamento foi usado:

```
## Villa Lobos -- Pipeline (smart routing)
**Stages:** orchestrator -> reporter
**Roteamento:** heuristica: query curta/factual
```

---

## Parâmetros (dashboard / villa_pipeline tool)

| Param | Default | Descrição |
|---|---|---|
| `query` | (obrigatório) | Tarefa a executar |
| `iterations` | 2 | Quantas vezes Worker re-executa, refinando |
| `use_reader` | True | Ativa stage 3 (lê contexto do diretório) |
| `base_path` | "." | Diretório que o Reader inspeciona |

### Tempo aproximado (RTX 3060 12GB)

| Roteamento | Tempo |
|---|---|
| **Fast-path** (skip-to-reporter) | ~10-30s |
| iterations=1, sem Reader | ~30-60s |
| iterations=1 (pipeline completo) | ~1-2 min |
| iterations=2 (era o default antigo) | ~3-5 min |
| iterations=3-5 | ~5-15 min |

A v10.1 reduz drasticamente a latência média porque queries triviais
nunca mais passam pelos 5 stages — fluxo típico de chat conversacional
agora responde em segundos.

---

## Quick Ask

`villa_quick_ask` permite consultar **um agente específico** sem rodar o pipeline completo. Útil para:

- Pedir ao Planner um plano sem executá-lo.
- Pedir ao Reporter para reformatar uma resposta anterior.
- Validar uma resposta com o Worker.

---

## Resilência

- **Retry:** cada agente tenta 2 vezes com 5s de delay.
- **Fallback:** se o modelo do agente falha, cai para llama3.1:8b.
- **Timeout cooperativo:** planejado para próxima sprint (atualmente confia no timeout do LiteLLM).

---

## Quando usar Villa-Lobos vs Gateway?

| Situação | Use |
|---|---|
| Pergunta direta, factual | Gateway (`lilo_chat`) ou Villa-Lobos fast-path |
| Tarefa de código simples | Gateway (`lilo_chat mode=code`) |
| Análise estatística completa | Prism AI |
| Busca em literatura | Scholar |
| Multi-step com leitura de arquivos | **Villa-Lobos** |
| Research-grade (DM, simulação, paper draft) | **Villa-Lobos** com iterations=2-3 |

---

## Card 3D no dashboard

A aba **Villa Lobos** do dashboard 8100 mostra um card 3D no rodapé com os modelos default de cada stage, lendo diretamente de `VILLA_MODELS`. Hover faz o card subir e ganhar profundidade.
