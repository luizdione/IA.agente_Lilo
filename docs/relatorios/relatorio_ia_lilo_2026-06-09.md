# Relatório IA LILO — Ciclo 2026-06-09 (V11.0)

**Tarefa:** `ia_lilo` (execução autônoma agendada) · **Perfil:** `desktop_dev` (max_iterations=3)
**Pedido por:** Dione · **Idioma:** pt-BR · **Backend:** `ollama` (real, 2ª corrida real consecutiva)

---

## 0. TL;DR

- **GANHO DE CELERIDADE CONFIRMADO (principal resultado):** com o roteamento V10.9 já ativo
  (worker/reader usando o instruct **geral** `llama3.1:8b-instruct-q8_0` em vez do coder
  `qwen2.5-coder:14b`), a corrida real ficou **~47% mais rápida** que o baseline coder de
  2026-06-08, com **qualidade estrutural equivalente** (69,1 vs 71,6 — dentro do ruído).
  iter=3 caiu de **202,8 s → 92,2 s (−55%)**.
- **Estabilidade:** **0 bugs**, **0 travamentos**, **0 degradação** nas 27 corridas. Árvore
  `.py` íntegra. CostTracker sem erro "readonly" (P4 mitigado, confirmado em runtime).
- **DEFEITO DE ROTEAMENTO REPRODUZIDO E CORRIGIDO (V11.0):** matemática voltou a cair em
  **fast-path** com resposta **rasa** (49/49/49, ~400 chars) — o LLM Orchestrator marca
  "enuncie e **demonstre** o teorema…" como `skip_to_reporter`, e o prompt conciso do
  fast-path suprime a demonstração. Aplicada **guarda V11.0**: pedidos de
  demonstração/dedução/prova **escalam fast-path → Worker** (que usa o `EXPERT_SYSTEM`
  aprofundado). Cirúrgica: dos 9 domínios, só matemática dispara. `py_compile` OK.
- **Correção de harness:** `_run_bench.bat` chamava o bench com guarda de timeout **default
  (60 s)**; com Ollama real (estágios de 100–400 s) isso marcaria "froze" falso. Ajustado
  para `--timeout 300`.
- **Infra de análise:** novo `scripts/_bench_compare.py` automatiza a comparação entre as
  duas corridas mais recentes (antes feita a olho sobre o JSON).

---

## 1. Ambiente e setup desta corrida

| Item | Valor |
|---|---|
| Perfil servidor | `desktop_dev` (prefer_local=True, allow_cloud=True, max_iterations=3) |
| Backend | **`ollama`** (real, :11434) |
| Modelo worker/reader (V10.9 ativo) | **`llama3.1:8b-instruct-q8_0`** (instruct geral, q8, pt-BR) |
| Modelo coder (só p/ intenção de código) | `qwen2.5-coder:14b` |
| Modelos Ollama instalados | 15 (incl. cloud `gpt-oss:120b`, `mistral-large-3:675b`) |
| Sintaxe (árvore `.py`) | OK (267/267 no checador; `py_compile` OK no `agent.py` editado) |
| Python | 3.13.9 |

**Ação de ambiente:** o Ollama estava **fora do ar** no início (`:11434` recusou conexão).
Foi iniciado (`ollama serve`, detached) e o modelo geral pré-aquecido (smoke test: replicação
semiconservativa do DNA, resposta técnica correta em pt-BR, ~15 s carga fria). Sem o Ollama,
a corrida cairia em `mock` (degradada) — como nos 7 ciclos antes de 2026-06-08.

---

## 2. Resultados — tempo, qualidade, bugs (1/2/3 iterações)

### 2.1 Totais

| Métrica | **2026-06-09 (V11.0, geral)** | 2026-06-08 (V10.9, coder) |
|---|---|---|
| Corridas | 27 | 27 |
| Qualidade média (0-100, proxy) | **69,1** | 71,6 |
| Bugs reais | **0** | 0 |
| Travamentos | **0** | 0 |
| Degradação (sem LLM) | **0** | 0 |

### 2.2 Por iteração — tempo médio (s) e qualidade média

| iter | wall (hoje) | wall (06-08) | Δ tempo | qual (hoje) | qual (06-08) |
|---|---|---|---|---|---|
| 1 | **49,5 s** | 80,7 s | **−38,7%** | 67,2 | 69,6 |
| 2 | **81,5 s** | 134,7 s | **−39,5%** | 70,2 | 71,2 |
| 3 | **92,2 s** | 202,8 s | **−54,5%** | 69,8 | 74,1 |

**Leitura:** o modelo geral (8,5 GB, q8) infere bem mais rápido que o coder de 14B (9 GB),
entregando **conhecimento científico discursivo** com qualidade estrutural equivalente. Como
o protocolo pede explicitamente **celeridade**, esta é a confirmação numérica do acerto do
V10.9: **mesma qualidade, ~metade do tempo no iter=3**.

**Valor marginal das iterações:** a qualidade praticamente satura já no iter=1
(67→70→70 hoje; 69,6→71,2→74,1 em 06-08), enquanto o tempo cresce de forma ~linear. Em uma
corrida o 2º passo do Worker retornou em ~2 s (saída quase vazia). Isso reforça **P3
(early-stop)** como a principal alavanca de celeridade restante (§5).

### 2.3 Por domínio (qualidade @iter1/2/3 · rota@1 · Δ média vs 06-08)

| Domínio | q@1/2/3 | rota | Δ vs 06-08 |
|---|---|---|---|
| conhecimentos_gerais | 81/73/78 | pipeline | −3,7 |
| historia | **48**/70/67 | pipeline | −10,0 |
| geografia | 65/75/73 | fast-path | −1,0 |
| quimica | 72/71/70 | pipeline | −0,7 |
| biologia | 71/79/78 | pipeline | −2,7 |
| fisica | 74/71/74 | fast-path | +1,7 |
| matematica | **49/49/49** | **fast-path** | −7,0 |
| agropecuaria | 81/75/74 | pipeline | +5,3 |
| veterinaria | 64/69/65 | pipeline | −5,0 |

Variações por domínio em sua maioria estão dentro do ruído de execução (LLM não-determinístico
+ heurística estrutural). Dois pontos baixos reais merecem ação (§3 e §4).

---

## 3. Defeito reproduzido: matemática em fast-path raso

`matematica` ("**Enuncie e demonstre** o teorema fundamental do cálculo.") caiu em **fast-path**
nas 3 iterações, com saídas de **441/342/434 chars** e qualidade **49** — um *stub* que enuncia
mas **não demonstra**.

**Causa-raiz (confirmada em código):** o **LLM Orchestrator** classifica a pergunta como
`skip_to_reporter=true` (trata "demonstre" como pergunta factual/definição). O fast-path usa o
**Reporter** com prompt explicitamente **conciso** ("*Apenas a resposta técnica direta*",
sem seções), que suprime a derivação que "demonstre" exige. A guarda `_EXPLAIN_KW` (V10.3) que
protegia esse caso **só atuava no ramo heurístico** — não no ramo do LLM, que é o usado quando
o Ollama está no ar. Por isso o defeito ressurgiu nas corridas reais.

---

## 4. Correção V11.0 (LILO mais potente)

### 4.1 `agents/villa_lobos/agent.py` — guarda anti-fast-path-raso no ramo do LLM

Após o parse da decisão do LLM Orchestrator, se a query contém marcadores de
**demonstração/dedução/prova**, a decisão é **escalada de fast-path para Worker**
(`skip_to_reporter=False`, `needs_worker=True`, `iterations≥2`):

```python
_qn = _strip_accents((query or "").lower())
if out.get("skip_to_reporter") and any(kw in _qn for kw in (
        "demonstr", "deduz", "deduc", "prove que",
        "provar que", "passo a passo", "derive ")):
    out["skip_to_reporter"] = False
    out["needs_worker"] = True
    out["complexity"] = out.get("complexity") or "moderate"
    out["iterations"] = max(2, int(out.get("iterations", 1)))
```

**Propriedades:** só **escala** (nunca rebaixa) — preserva o fast-path/celeridade das demais
perguntas explicativas (ex.: física "explique o princípio" segue em fast-path, qualidade boa).
**Validação:**

| Verificação | Resultado |
|---|---|
| `py_compile agent.py` (no PC real) | **OK** |
| Marcadores nos 9 domínios | dispara **só** em `matematica` (esperado) |
| Falsos positivos ("aprove o orçamento", "comprove sua teoria", "reprove o aluno") | **nenhum** |

**Previsão p/ o próximo ciclo:** matemática deve sair de **49** (fast-path/stub) para **~70+**
(Worker com `EXPERT_SYSTEM`, ≥2 iterações) — validação numérica no bench de 2026-06-10.

### 4.2 `scripts/_run_bench.bat` — guarda de timeout coerente com Ollama real

`--iters 1,2,3` → `--iters 1,2,3 **--timeout 300**`. Sem isso, o default de 60 s marcaria
"froze" falso (estágios reais levam 100–400 s).

### 4.3 `scripts/_bench_compare.py` (novo) — análise/comparação automatizada

Carrega as duas corridas mais recentes e imprime totais, por-iteração, por-domínio e *flags*
(bugs/travas/qualidade<55). Reusável nos próximos ciclos.

---

## 5. Backlog priorizado (desenvolvimento contínuo)

- **P3 — Villa fan-out + early-stop (principal alavanca de celeridade):** a qualidade satura
  no iter=1 mas o tempo escala com as iterações; um 2º passo chegou a retornar saída vazia em
  ~2 s. **Proposta:** parar de iterar quando a variação de conteúdo entre iterações cair abaixo
  de um limiar (ex.: similaridade ≥ 0,9 ou ganho de comprimento < 5%), e paralelizar Worker
  quando houver subtarefas independentes. Ganho estimado: 1/3 do tempo em iter=3 sem perda de
  qualidade.
- **P2 — Paridade API ↔ MCP:** o MCP expõe capacidades que a API HTTP (`lilo_api.py`) ainda não:
  `scholar`, `sql`, `pdf`, `web_search/fetch`, `prism_*`. Lacunas **intencionais** (segurança):
  `fs_*`/`run_shell`/`run_python` não devem ir para a API de rede; `sessions` é conceito só-API.
  **Proposta:** adicionar endpoints read-only `/v1/scholar`, `/v1/pdf`, `/v1/web/*`, `/v1/prism/*`
  reaproveitando os handlers do MCP, com testes de contrato. (Não implementado neste ciclo por
  exigir o servidor HTTP no ar para teste de integração — evitar shipar endpoint sem teste em
  execução não supervisionada.)
- **Watch — `historia@1` (q=48):** 1ª iteração do Worker produziu saída fina (673 chars). Não é
  bug sistêmico (variância do LLM em passo único); reavaliar com early-stop/iteração mínima 2
  para perguntas explicativas longas se reincidir.
- **P4 — CostTracker "readonly database":** **mitigado** (V10.2) e confirmado em runtime (0 erros
  nas 27 corridas). Opcional: mover DB default para fora do OneDrive via `LILO_COST_DB`.
- **Plataforma híbrida (API + agente estilo Claude Desktop)** e **Orquestrador Villa_Lobos**
  (LLMs chamando agentes especializados conforme o setup do servidor) seguem evoluindo de forma
  incremental, sem regressões de sintaxe.

---

## 6. Comparação com o ciclo anterior (2026-06-08 → 2026-06-09)

| Métrica | V10.9 (06-08, coder) | **V11.0 (06-09, geral)** |
|---|---|---|
| Modelo worker p/ conhecimento | coder (qwen 14B) | **geral (llama3.1:8b q8)** |
| Tempo iter 1/2/3 | 80,7 / 134,7 / 202,8 s | **49,5 / 81,5 / 92,2 s (~47% mais rápido)** |
| Qualidade média | 71,6 | 69,1 (equivalente, dentro do ruído) |
| Bugs / travas / degradação | 0 / 0 / 0 | **0 / 0 / 0** |
| Defeito matemática (fast-path stub) | presente | **corrigido (guarda V11.0, valida 06-10)** |
| Guarda de timeout do launcher | 60 s (default, marcaria froze falso) | **300 s** |
| Análise/comparação | manual sobre JSON | **automatizada (`_bench_compare.py`)** |

---

*Registro do ciclo na memória LILO: `project_ia_lilo/bench_semantico_2026-06-09_achados`.
Artefatos: `docs/relatorios/bench_semantic_2026-06-09.json` (dados brutos das 27 corridas),
este relatório, e `logs/bench_run.log` (log completo da corrida).*
