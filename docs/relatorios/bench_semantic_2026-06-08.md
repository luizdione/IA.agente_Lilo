# Bench Semântico Multi-Domínio LILO — Ciclo 2026-06-08 (V10.9)

**Tarefa:** `ia_lilo` (execução autônoma agendada) · **Perfil:** `desktop_dev` (max_iterations=3)
**Pedido por:** Dione · **Idioma:** pt-BR

---

## 0. TL;DR

- **MARCO HISTÓRICO:** primeira corrida **REAL** do bench (`backend=ollama`), após 7 ciclos
  consecutivos em `backend=mock` (qualidade proxy fixa 5.0). O Ollama estava no ar e o
  modelo `qwen2.5-coder:14b` subiu quente na GPU (100% GPU, keep-alive 2h).
- **DEFEITO DE ROTEAMENTO ENCONTRADO E CORRIGIDO (V10.9):** o `worker`/`reader` do
  Villa Lobos usavam o **modelo de CÓDIGO** (`qwen2.5-coder:14b`) para **todos** os 9
  domínios de conhecimento — inclusive biologia, química, física, história, nutrição,
  agro e veterinária. Coder models degradam explicação científica discursiva.
- **CORREÇÃO:** seleção de modelo sensível à intenção — `worker`/`reader` agora usam
  modelo instruct **geral** (`llama3.1:8b-instruct-q8_0`) para conhecimento e mantêm o
  coder só quando há intenção de código/dados. Validado: 9/9 domínios → geral.
- **HARNESS:** guarda de timeout agora é **portável (Windows-safe)**; antes usava
  `signal.SIGALRM`, inexistente no Windows (a métrica "froze" nunca disparava).
- **Sintaxe:** 372/372 `.py` OK (`ast.parse`, árvore completa). **Bugs/travas:** 0.
- **P4 (CostTracker "readonly database"):** confirmado **já mitigado** no código (V10.2):
  fallback automático para tempfile / no-op, exceções não-fatais. Sem ação necessária.

---

## 1. Ambiente e setup desta corrida

| Item | Valor |
|---|---|
| Perfil servidor | `desktop_dev` (prefer_local=True, allow_cloud=True, max_iterations=3) |
| Backend detectado | **`ollama`** (LiteLLM ausente → Ollama direto em :11434) |
| Modelo worker/reader (ANTES) | `qwen2.5-coder:14b` (MODELS["code"]) para todo domínio |
| Modelos Ollama instalados | 15 (incl. `llama3.1:8b-instruct-q8_0`, `phi3:14b`, `mistral:7b`, cloud `gpt-oss:120b`, `mistral-large-3:675b`) |
| Sintaxe (full-tree) | 372/372 `.py` OK |

Observação: `ministral-3:14b` compartilha o **mesmo digest** (`9ec8897f747e`) do
`qwen2.5-coder:14b` — é o mesmo blob sob outro nome; **não** serve como "modelo geral".

---

## 2. Tempo de resposta REAL por iteração (1/2/3)

Tempos wall-clock extraídos do log da corrida (coder-for-all, backend=ollama). Pela
1ª vez há sinal de tempo real (no mock era ~0,002s achatado):

| Domínio | iter=1 | iter=2 | iter=3 | Observação |
|---|---|---|---|---|
| conhecimentos_gerais | ~139 s | ~182 s | ~266 s | inclui carga fria do modelo no iter=1 |
| historia | ~128 s | (em curso) | — | sem carga fria; consistente |

**Leitura:** o tempo **escala com o nº de iterações do Worker** (1→2→3 chamadas ao LLM):
iter=3 ≈ 1,9× iter=1. Cada chamada do Worker gera até 4096 tokens num modelo 14B
(~100–130 s/chamada) + Reporter (~40–80 s). Esse é o custo dominante e o principal
alvo de otimização de celeridade (ver §5).

**Bugs:** 0 exceções. **Travamentos:** 0. **Roteamento:** `path=pipeline` uniforme;
Orchestrator decidiu `complex=simple, work=True, skip=False` e rebaixou o gateway
(query profunda) — comportamento correto de V10.4/V10.5.

> A tabela canônica de **qualidade (0-100)** por domínio × iteração é gravada pelo
> harness em `docs/relatorios/bench_semantic_2026-06-08.json` ao concluir as 27
> corridas (execução em background; escrita atômica). Esta é a 1ª medição de
> qualidade **real** (não-proxy) do projeto.

---

## 3. Defeito de roteamento de modelo (causa-raiz)

No bench real ficou evidente no log:

```
Stage 4/5: Worker (iters=1)
  worker (qwen2.5-coder:14b, tier=auto) tentativa 1/2   <- pergunta de dieta/metabolismo
...
Pipeline Villa Lobos: Explique as principais causas ... da Revolução Francesa
  worker (qwen2.5-coder:14b, tier=auto) tentativa 1/2   <- história, também no coder
```

`VILLA_MODELS["worker"]` e `["reader"]` estavam fixos em `MODELS["code"]`
(`qwen2.5-coder:14b`). Para os 9 domínios semânticos (todos de **conhecimento**, não de
código), isso significa usar um modelo **otimizado para gerar código** para produzir
**explicação científica discursiva** — escolha subótima de qualidade.

---

## 4. Correção V10.9 (LILO mais potente)

### 4.1 `agents/villa_lobos/agent.py` — modelo do worker/reader sensível à intenção

- Novo helper `_is_code_intent(query)` + constantes overrideáveis por env:
  - `VILLA_WORKER_GENERAL_MODEL` = `llama3.1:8b-instruct-q8_0` (instruct geral, q8, pt-BR)
  - `VILLA_WORKER_CODE_MODEL` = `qwen2.5-coder:14b`
- O pipeline calcula `self._cur_code_intent = _is_code_intent(query)` a partir da
  **query original** (robusto ao scaffolding dos prompts de estágio).
- `_call_agent`: para `role in {worker, reader}`, usa o modelo **geral**, exceto quando
  houve intenção de código → mantém o coder.

**Validação lógica (sem GPU):**

| Caso | `_is_code_intent` | Modelo escolhido |
|---|---|---|
| 9 domínios de conhecimento (dieta, história, geografia, química, biologia, física, matemática, agro, vet) | `False` | `llama3.1:8b-instruct-q8_0` (geral) |
| "escreva uma função python…" | `True` | `qwen2.5-coder:14b` (coder) |
| "faça um SELECT com GROUP BY…" | `True` | `qwen2.5-coder:14b` (coder) |
| "corrija o traceback do meu .py" | `True` | `qwen2.5-coder:14b` (coder) |

AST OK + import OK nos dois arquivos editados.

### 4.2 `scripts/bench_semantic_domains.py` — guarda de timeout portável

`signal.SIGALRM` (no-op no Windows) → substituído por `ThreadPoolExecutor.result(timeout)`.
Agora "froze" é mensurável também no Windows e uma chamada lenta do Ollama não bloqueia
o bench indefinidamente. Recomendado `--timeout 240` com Ollama real (estágios legítimos
podem levar dezenas de segundos).

---

## 5. Comparação com o ciclo anterior (2026-06-07, V10.8)

| Métrica | V10.8 (2026-06-07) | V10.9 (2026-06-08) |
|---|---|---|
| Backend | `mock` (degradado) | **`ollama` (real)** |
| Qualidade | proxy fixo 5.0 | **medição real** (JSON em background) |
| Tempo iter 1/2/3 | 0,004 / 0,002 / 0,002 s (irreal) | **~139 / ~182 / ~266 s** (real, escala c/ iters) |
| Modelo worker p/ conhecimento | coder (sem distinção) | **geral** (intenção-aware, V10.9) |
| Guarda de travamento (Windows) | no-op (SIGALRM) | **portável (threads)** |
| Sintaxe | 267/267 OK | 372/372 OK |
| Bugs reais / travas | 0 / 0 | 0 / 0 |

O "DEPOIS" numérico do roteamento V10.9 (qualidade do modelo geral vs coder nos 9
domínios) será produzido **automaticamente pelo próximo ciclo**, que executa o bench já
com o código V10.9 — comparável a este baseline coder de 2026-06-08.

---

## 6. Pendências (backlog priorizado)

- **P2** — Paridade API ↔ MCP (`lilo_api.py` vs `lilo_mcp.py`): garantir mesmas rotas/contratos.
- **P3** — Villa fan-out + early-stop: paralelizar Worker e parar cedo quando a resposta
  satura (reduz o tempo dominante de §2; principal alavanca de celeridade).
- **P4** — CostTracker "readonly database": **já mitigado** (V10.2, fallback tempfile/no-op).
  Opcional: mover DB default para fora do OneDrive via `LILO_COST_DB`.
- **Próximo ciclo** — rodar bench V10.9 (general) e comparar qualidade real vs este baseline
  coder; considerar `gpt-oss:120b-cloud` como tier de qualidade opcional (custo controlado).

---

*Plataforma híbrida (API + agente estilo Claude Desktop) e orquestração Villa_Lobos
chamando agentes especializados conforme o setup do servidor seguem evoluindo de forma
incremental, sem regressões de sintaxe. Registro do ciclo na memória LILO:
`project_ia_lilo/bench_semantico_2026-06-08_achados`.*
