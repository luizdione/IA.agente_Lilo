# Arquitetura LILO v10.3

**Última atualização:** 2026-05-07 (sprint memória robusta)
**Status:** Em produção, MCP validado via stdio handshake.

## Sumário das mudanças v10.3

- **`shared/kv_memory.py` reescrito** (394 linhas) — DB padrão fora do OneDrive (`%LOCALAPPDATA%\LILO\memory\kv_memory.db`), TTL/expires_at, busca textual, WAL mode, schema migrável, export/import JSON, stats. Migração automática do banco legado.
- **4 novas tools MCP de memória**: `lilo_memory_search`, `lilo_memory_stats`, `lilo_memory_export`, `lilo_memory_cleanup`. `lilo_memory_set` ganhou `ttl_seconds` opcional.
- **Total de tools subiu para 236** (28 core skills no menu `/` + 199 skills geradas + 9 outras).
- Doc dedicado em [`docs/tecnico/memoria.md`](memoria.md) com schema completo, exemplos, convenções de namespace e roadmap.

## Sumário das mudanças v10.2

- **8 novas tools MCP centralizadas em `lilo.py`** (memória persistente
  4 tools, cost tracker 2 tools, Ollama model manager 2 tools). Antes
  só existiam em `lilo_mcp.py`; agora estão em `handle_tool_call` e
  `list_all_tools`, expondo-as automaticamente em CLI, dashboard, API
  HTTP e MCP. `lilo_mcp.py` apenas delega — zero duplicação.
- **Skills com `schema_version`** em `registry.json` (v1.1). Cache é
  invalidado automaticamente ao detectar versão antiga.
- **Prefixo `skill_advanced_*`** para skills com `complexity=high`,
  separando-as no menu do dashboard.

## Sumário das mudanças v10.1

- **Aba Desktop no dashboard 8100** — formulário visual para
  `fs_read/write/list/search` e `run_shell/run_python` (reusa
  `lilo.handle_tool_call`, zero duplicação).
- **Smart routing no Villa-Lobos** — Orchestrator emite JSON declarando
  quais stages executar; tarefas triviais entram em fast-path
  (skip-to-reporter, ~70% menos latência).
- **Pre-commit hook AST** — `scripts/pre_commit_ast_check.py` valida
  todos os `.py` staged contra `SyntaxError` e detecta truncamento
  OneDrive antes do commit. Instalável via `scripts/install_hooks.py`.
  Bypass: `git commit --no-verify`.

---

## Visão geral

```
┌─────────────────────────────────────────────────────────────┐
│  CLIENTES                                                    │
│  ┌───────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │ Claude Desktop│  │   PyCharm   │  │ CLI / Streamlit  │   │
│  │ (stdio MCP)   │  │ (stdio MCP) │  │ (8100, 8101)     │   │
│  └───────┬───────┘  └──────┬──────┘  └────────┬─────────┘   │
│          │ profile=desktop │ profile=pycharm  │             │
│          └─────────────────┴──────────────────┘             │
│                            │                                 │
│                            ▼                                 │
│           ┌─────────────────────────────────────┐           │
│           │      lilo_mcp.py (UNIFICADO)        │           │
│           │   --profile {desktop|pycharm|http}  │           │
│           └─────────────────┬───────────────────┘           │
│                             │                                │
│              ┌──────────────▼──────────────┐                 │
│              │   lilo.route()              │                 │
│              │  1. detect_tab(query)       │                 │
│              │  2. policy.decide()         │                 │
│              │  3. dispatch                │                 │
│              └──────┬──────────────────┬───┘                 │
│        TAREFA SIMPLES               TAREFA COMPLEXA          │
│              │                          │                    │
│   ┌──────────┼──────────┐               │                    │
│   ▼          ▼          ▼               ▼                    │
│ ┌────┐   ┌─────┐    ┌────────┐    ┌───────────────┐          │
│ │SQL │   │ PDF │    │Scholar │    │ Villa-Lobos   │          │
│ │    │   │     │    │        │    │  (pipeline)   │          │
│ └────┘   └─────┘    └────────┘    └───────┬───────┘          │
│                                           │                  │
│ ┌─────────┐ ┌────────────┐ ┌────────────┐ │                  │
│ │ Prism   │ │  Gateway   │ │  Desktop   │ │                  │
│ │  AI     │ │ (fallback) │ │ Commander  │ ▼                  │
│ └─────────┘ └────────────┘ └────────────┘ ┌─────────────┐    │
│                                            │ lilo_skills │    │
│                                            │ (199)       │    │
│                                            └─────────────┘    │
└─────────────────────────────────────────────────────────────┘

           Backends LLM (transparente para o resto)
   ┌─────────────────────────────────────────────────────┐
   │  shared/llm_client.py                                │
   │   1. LiteLLM proxy (config/litellm_config.yaml) :4000│
   │   2. Ollama direto :11434                            │
   │   3. Anthropic API (com budget control)              │
   └─────────────────────────────────────────────────────┘
```

---

## Fluxo de uma query

1. **Cliente** (Claude Desktop, PyCharm, CLI ou dashboard) envia query.
2. **lilo_mcp.py** recebe via stdio JSON-RPC. Filtra tools pelo `--profile`.
3. **lilo.route()** detecta o subagente por keywords (ou usa o explícito).
4. **Policy Engine** classifica complexidade e escolhe tier:
   - `NO_LLM` (resposta direta)
   - `OLLAMA_FAST` (qwen2.5-coder:7b)
   - `OLLAMA` (llama3.1:8b)
   - `OLLAMA_HEAVY` (qwen2.5-coder:14b)
   - `CLAUDE_SONNET` (com budget)
   - `CLAUDE_OPUS` (com budget)
5. **Subagente** é invocado com a query + contexto.
6. **shared/llm_client.py** faz a chamada ao backend (LiteLLM → Ollama → Anthropic).
7. **CostTracker** registra a request e duração.
8. **Obsidian** (opcional) salva a nota com query + resposta.
9. Resultado retorna pelo mesmo caminho.

---

## Subagentes

### SQL (`agents/Analise_SQL/agent.py`)

- Executa queries SQLite e detecta tipo (SELECT/COUNT/aggregate).
- Aplica testes estatísticos automáticos: ANOVA, t-test, regressão, correlação.
- Mode NO_LLM quando query SQL é direta.

### PDF (`agents/PDFs_library/agent.py`)

- PyMuPDF para extração rápida.
- Modos `simple`, `introduction`, `methods`, `results` filtram seções do paper.
- Banco `workaholics.db` indexa por DOI e ISSN.
- Interface secundária em `localhost:8101` (cards estilo /referencias).

### Scholar (`agents/scholaragent/agent.py`)

- Busca PubMed (E-utilities) e arXiv.
- Síntese opcional via LLM (modo "Scholar+síntese" → Ollama heavy).
- Salva resultados como notas Obsidian.

### Prism AI (`agents/prism_ai/`)

- 6 sub-agentes internos: ingestion, classification, stats, visualization, writing, export.
- Aceita `.xlsx` e `.csv`.
- Saída: gráficos publication-grade (matplotlib + seaborn) + texto de Resultados em pt/en.
- Audita testes: detecta uso indevido (ex.: t-test em dados não-normais).

### Villa-Lobos (`agents/villa_lobos/agent.py`)

Pipeline 5-stage:

| Stage | Modelo default | Função |
|---|---|---|
| Orchestrator | llama3.1:8b-instruct-q8_0 | Analisa complexidade e dominio |
| Planner | phi3:14b-medium-128k | Cria plano detalhado |
| Reader | qwen2.5-coder:14b | Lê arquivos e contexto (opcional) |
| Worker | qwen2.5-coder:14b | Executa o plano (1-5 iterações) |
| Reporter | llama3.1:8b-instruct-q8_0 | Sintetiza relatório final |

### Gateway (`agents/gateway/agent.py`)

Fallback genérico. Modos:
- `chat` → llama3.1:8b
- `code` → qwen2.5-coder:14b
- `bioinfo` → phi3:14b
- `sql` → qwen2.5-coder:7b

### Desktop Commander (`agents/desktop/agent.py`) — novo em v10

- 7 tools de filesystem + shell.
- Allow-list em `LILO_DESKTOP_ALLOW`.
- Bloqueio de comandos perigosos (`DANGEROUS_PATTERNS`).
- `run_python` em subprocess isolado (não no proc do MCP).

---

## MCP server (`lilo_mcp.py`)

### Profile flag

| Profile | Tools expostas | Cliente alvo |
|---|---|---|
| `desktop` | 29 (todas) | Claude Desktop |
| `pycharm` | 23 (sem web search/skills/lilo_models) | PyCharm AI Assistant |
| `http` | 29 (igual desktop) | Reservado para futuro `lilo_api.py` |

### Bug histórico (corrigido em v10)

A versão anterior do `lilo_mcp.py` definia `_profile_tool` **antes** de `mcp = FastMCP(...)`. Como Python avalia decorators no momento do parse, todas as 16+ tools davam `NameError: name 'mcp' is not defined` — o servidor crashava no import e o Claude Desktop nunca conseguia se conectar (silenciosamente, sem mensagem de erro útil).

**Fix:** mover `mcp = FastMCP("lilo")` **antes** da definição de `_profile_tool`.

---

## Policy Engine (`shared/policy.py`)

### Indicadores de complexidade

`COMPLEX_INDICATORS` — termos que aumentam o score:
- Estatística: `anova`, `regressao`, `clustering`, `pca`, `t-test`, `chi-quadrado`
- Bioinformática: `blast`, `docking`, `molecular dynamics`, `phylogen`, `genom`
- DM (adicionado em 2026-05-06): `openmm`, `nvt`, `npt`, `equilibration`, `rmsd`, `mmgbsa`, `metadynamics`, `gromacs`, `amber`, `force field`, `trajectory`, `umbrella sampling`, `metadynamics`, `pmf`, `well-tempered`
- Análise: `analise critica`, `revisao sistematica`, `pipeline completo`

`SIMPLE_INDICATORS` — diminuem score:
- `traduzir`, `listar`, `formatar`, `o que e`, `defina`

### Override explícito

`\lilo opus <query>` força tier Opus. Outras flags: `sonnet`, `heavy`, `local`, `fast`.

### Budget control

- `LILO_DAILY_BUDGET=1.0` (USD/dia).
- Se a query estimada extrapolar, faz downgrade para Sonnet ou tier local.

---

## Backends LLM (`shared/llm_client.py`)

### Ordem de detecção

1. **LiteLLM proxy** em `localhost:4000` (config/litellm_config.yaml) — unifica multi-modelo.
2. **Ollama direto** em `localhost:11434`.
3. **Anthropic API** (se `ANTHROPIC_API_KEY` definida).
4. **Mock** (último recurso, retorna placeholder).

### keep_alive

`OLLAMA_KEEP_ALIVE=2h` no `.env` — modelo não descarrega da VRAM após 5 min como no default Ollama.

### CoT (Chain-of-Thought)

Enriquece o system prompt com:
> "Think step-by-step. First reason inside `<thinking>...</thinking>`, then provide your final answer. Local tokens are free — be thorough."

Filtra o `<thinking>` da resposta final apresentada ao usuário.

---

## Decisões de design

### Por que stdio (MCP) e não HTTP?

- Claude Desktop só fala stdio.
- PyCharm AI Assistant só fala stdio.
- HTTP fica para o futuro `lilo_api.py` (FastAPI + SSE) com autenticação.

### Por que múltiplos profiles num único arquivo?

- Era 2 arquivos quase idênticos (`lilo_mcp.py` e `lilo_pycharm_mcp.py`).
- Manutenção dupla, bugs em só um, divergência rápida.
- Profile flag = decorator condicional, sem custo em runtime.

### Por que subagente Desktop Commander e não MCP separado?

- Permite reaproveitar via dashboard 8100 (UI), CLI, e Streamlit do PDFs library.
- Allow-list é configurada uma vez e respeitada por todos os pontos de entrada.
- Tools aparecem com prefixo unificado (`fs_*`, `run_*`) no Claude Desktop.

---

## Roadmap

### Curto prazo (próxima sprint)

1. **Aba "Desktop" no dashboard 8100** — formulário visual para `fs_read/write/list/search` e `run_shell`/`run_python`.
2. **Smart routing no Villa-Lobos** — Orchestrator emite JSON e Router decide quais stages executar (skip-to-reporter para tarefas simples).
3. **Pre-commit hook** — `python -c "import ast; ast.parse(...)"` para todos os .py modificados, evita os truncamentos do OneDrive.

### Médio prazo (4-8 semanas)

4. **`lilo_api.py`** (FastAPI + SSE + `X-LILO-Token`) — abre o LILO como serviço HTTP autenticado, base para apps mobile/desktop futuros.
5. **Skills bio adicionais:** `mdanalysis_rmsd_rmsf`, `rdkit_compound_2d3d`, `biopython_pdb_clean`, `chimera_x_publication_image`.
6. **Cliente desktop Tauri/Electron** — UI nativa sobre o `lilo_api.py`.

### Longo prazo (3+ meses)

7. **Streaming token-by-token** em todos os subagentes (atualmente só responde quando completa).
8. **Multi-usuário** — separação de contexto por user_id, ACLs no Desktop Commander.
9. **Telemetria opt-in** — análise post-hoc das decisões do Policy Engine.

---

## Como contribuir / debugar

### Regenerar registry de skills

```cmd
python lilo_skills/generate_skills.py
```

### Smoke test do MCP

```cmd
python scripts\test_mcp_stdio.py --profile desktop
python scripts\test_mcp_stdio.py --profile pycharm
```

### Logs

- `logs/lilo.log` — todas as decisões do Policy Engine + chamadas dos subagentes.
- `logs/cost_tracking.db` — SQLite com cada request e custo estimado.

### Adicionar nova tool MCP

1. Crie a função em `lilo_mcp.py` decorada com `@_profile_tool` e docstring + Args.
2. Inclua o nome na lista `pycharm` em `_PROFILE_TOOLS` se quiser expor no PyCharm também.
3. Validar com `python scripts\test_mcp_stdio.py --profile desktop`.
4. Reiniciar Claude Desktop pela bandeja.

### Adicionar novo subagente

1. Crie `agents/<nome>/agent.py` com classe `XxxAgent(BaseAgent)`.
2. Implemente `run()`, `get_tools()`, `health()`.
3. Adicione na `_AGENT_REGISTRY` do `lilo.py`.
4. Adicione keywords em `_KEYWORD_MAP` do `lilo.py` (opcional, p/ auto-detect).
5. Crie tools wrapping em `lilo_mcp.py` (com `@_profile_tool`).
6. Documente em `docs/agentes/<nome>.md`.
