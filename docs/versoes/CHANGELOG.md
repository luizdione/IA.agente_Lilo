# LILO — Changelog

## v10.6 — 2026-06-11 (V12: orquestração unificada — porta única + delegação por etapa)

Villa Lobos vira a **porta única** de roteamento; os subagentes continuam
módulos independentes, mas agora um só orquestrador semântico decide quem
assume — e pode **dividir as etapas** entre especialistas.

1. **Roteador semântico como porta única.** `lilo.route()` em modo auto delega
   a decisão a `VillaLobosAgent.route_target()` (LLM router → heurística →
   capabilities) em vez do keyword-router raso (`_detect_tab`, agora fallback).
   Domínio claro → especialista; ambíguo/complexo → pipeline. Desligável via
   `LILO_SEMANTIC_ROUTER=0`. Validado (Ollama): capital→gateway, ANOVA→prism,
   pubmed→scholar, arquivos→desktop, SQL→sql, incerteza→villa.
2. **Modo IA → "Auto" (default) + override.** O seletor manual
   chat/code/bioinfo/sql vira "Auto" (o roteador decide); os modos antigos
   permanecem como override opcional (`sql` força o agente SQL; chat/code/
   bioinfo forçam o gateway no modo).
3. **Delegação por etapa.** O Orchestrator pode indicar `worker_agent` no JSON
   (validado contra [scholar, sql, prism, pdf, desktop]); a etapa Worker do
   pipeline é então executada por esse especialista e o Reporter sintetiza.
   Validado e2e (Ollama): "busque artigos no pubmed e resuma" → Worker via
   ScholarAgent. Desligável via `LILO_STAGE_DELEGATION=0`.
4. **Decomposição em CADEIA (V12.1).** `_decompose_chain()` quebra uma tarefa
   multi-ação em até 4 sub-tarefas SEQUENCIAIS, cada uma para um especialista,
   encadeando as saídas (contexto acumulado) no lugar do loop do Worker. Gatilho
   leve (`_looks_multi_step`: ≥2 verbos de ação + conjunção). Validado e2e
   (Ollama): "busque no pubmed … e depois analise" → cadeia `scholar → prism`
   → Reporter sintetiza. Desligável via `LILO_CHAIN_DELEGATION=0`.

5. **Busca na internet ampliada (V12.2).** `shared/research_sources.py` ganhou
   4 fontes gratuitas: **OpenAlex** (substituto do Google Scholar — sem API/
   anti-scraping), **Europe PMC**, **Google Books** (`GOOGLE_BOOKS_API_KEY`
   opcional — quota anônima satura), **Wikipedia** (`LILO_WIKI_LANG`). Total: 10
   fontes acadêmicas/conteúdo + web geral (DuckDuckGo). ScholarAgent: `source`
   aceita as novas; `source="all"` agrega as acadêmicas.

Testes: +14 (61 passam).

## v10.5 — 2026-06-11 (plataforma híbrida, dashboard Claude Desktop, Villa V11.2)

### Arquitetura híbrida (v10)
- Subprojetos antigos consolidados em `agents/`; legado movido para `_ARCHIVE_v10/`.
- **API HTTP** (`lilo_api.py`, FastAPI :8088) e **multiplexer** `lilo_serve.py`
  (`--transport stdio/http/sse`). `lilo_server.py` e `lilo_pycharm_mcp.py`
  **arquivados** (o MCP do PyCharm hoje é `lilo_mcp.py --profile pycharm`).
- Profiles MCP `claude_code` e `cowork` adicionados a `_PROFILE_TOOLS`.

### Dashboard
- Reformulação visual estilo **Claude Desktop** (marfim/coral, headings
  serifados, composer arredondado) — `dashboard.py` + `dashboard_cowork.py`.

### Villa Lobos — V11.2 (roteamento e robustez)
- **Guarda anti-fast-path unificada** (`_block_fast_path`): explicação/profundidade
  deixam de cair em fast-path raso (antes só demonstração/prova era protegida).
- **Retry/fallback**: HTTP 400 (payload) agora é fail-fast; demais 4xx pulam
  retry mas permitem fallback de modelo; 5xx/timeout seguem com retry.
- **`keep_alive`** normalizado (corrige 400 do Ollama com `OLLAMA_KEEP_ALIVE=-1`).
- **De-viés de domínio** no `EXPERT_SYSTEM`/worker prompt (não impõe mais
  "mecanismos moleculares" a história/geografia/matemática).

### Avaliação de qualidade
- **`shared/quality_judge.py`**: juiz LLM por domínio (rubrica 4×0-25),
  modelo distinto do avaliado para mitigar auto-viés.
- `scripts/bench_semantic_domains.py`: flags `--judge` e `--repeat N`.

## v10.4 — 2026-05-08 (profile MCP `opus` + descriptions reescritas)

### Profile `opus` em `lilo_mcp.py`

**Problema resolvido:** Claude Opus 4.x no Claude Desktop carregava 35 tools
mas usava só 2 (`lilo_web_search`, `lilo_web_fetch`). Análise mostrou que 17
tools eram redundantes com o próprio Opus (lilo_chat, lilo_pdf, villa_*,
prism_audit, etc.) — Opus prefere responder direto a delegar para outro LLM.

**Mudanças:**

- **Novo profile `opus`** em `_PROFILE_TOOLS` com **18 tools curadas** que
  AGREGAM capacidade ao Opus: internet (`lilo_web_search`, `lilo_web_fetch`),
  filesystem (`fs_read/write/list/stat/search`), execução local (`run_python`,
  `run_shell`), memória persistente (`lilo_memory_set/get/list/search`),
  literatura (`lilo_scholar`), estatística (`prism_analyze`, `prism_classify`),
  Ollama (`lilo_list_local_models`, `lilo_pull_model`).
- **Descriptions reescritas** com template `USE WHEN ... DO NOT USE WHEN ...
  Exemplo:` em todas as 18 tools, dando ao Opus triggers inequívocos.
- **`config/mcp/claude_desktop.json`** agora aponta `--profile opus` por default.
- **17 tools "ocultas"** continuam acessíveis no dashboard via slash command
  (`/lilo_chat`, `/villa_pipeline`, `/lilo_pdf`, etc.).
- **`opus` adicionado ao argparse** de `lilo_mcp.py` e `scripts/test_mcp_stdio.py`.
- **Smoke test corrigido** — antes tentava chamar `lilo_health` (não existe no
  profile `opus`); agora escolhe a primeira tool disponível.

### Robustez do servidor MCP

- **`_install_excepthook()`** captura crashes silenciosos do servidor e escreve
  stack trace em stderr (visível em `%LOCALAPPDATA%\Claude\logs\mcp-server-lilo.log`).
- **`_ensure_lilo()` resiliente** — falhas de `load_env` não derrubam o servidor.
- **Logging com timestamp** em transições (`[LILO MCP HH:MM:SS] ...`).

### Documentação

- **`docs/uso/PROFILE_OPUS.md`** — guia completo de ativação/reversão.
- **README** atualizado com tabela de profiles + saída esperada do smoke test.

### Refactor da UI (dashboard.py)

- Sidebar direita simplificada — só Histórico (lista flat estilo Claude Desktop)
  + nova seção **Progresso** com checkboxes de tasks por projeto.
- "Projetos" movida para a aba Villa Lobos (área central) com explorador de
  arquivos CRUD (Ler / Escrever / Renomear / Remover).
- "Anexos" virou popover (+) na caixa de mensagem em todas as views.
- Botões **✋ Agir** / **⚠️ Perguntar** na caixa LILO (estilo Claude Desktop):
  controla `intent`, `allow_tools`, `system_hint` no contexto enviado ao agente.

### Schema (chat_memory)

Nova tabela `project_tasks` (id, project_id, title, done, created_at, updated_at)
com 6 métodos: `add_task`, `list_tasks`, `set_task_done`, `delete_task`,
`rename_task`, `task_progress`.

### Erros de sintaxe corrigidos

3 arquivos haviam sido truncados em sessão anterior por limite de créditos:
`lilo.py:672`, `lilo_mcp.py:594`, `lilo_skills/__init__.py:348`.

## v10.3 — 2026-05-07 (memória robusta + 4 tools novas)

### `shared/kv_memory.py` reescrito (394 linhas)

**Problema resolvido:** "disk I/O error" e locks em SQLite quando o
banco fica dentro do OneDrive (sync ativo causa contention).

**Mudanças:**

- **DB padrão fora do OneDrive.** Default Windows: `%LOCALAPPDATA%\LILO\memory\kv_memory.db`. Unix: `~/.local/share/lilo/memory/kv_memory.db`. Override via env `LILO_KV_MEMORY_DB`.
- **Migração automática** do `memory/kv_memory.db` legado (no OneDrive). Cópia única na primeira inicialização; o original permanece como backup.
- **TTL/expires_at** opcional em `set(key, value, ttl_seconds=N)`. `get()` retorna `default` se entrada expirou. `cleanup_expired()` faz housekeeping.
- **Busca textual** com `search(query, ns=, limit=)` — substring case-insensitive em key, value e tags.
- **WAL mode** (`PRAGMA journal_mode=WAL`) + `busy_timeout=5000` para mitigar locks em uso concorrente.
- **Schema migrável** via `_ensure_column()` — bancos antigos ganham `expires_at` automaticamente. Tabela `meta` registra `schema_version=2`.
- **Export/import JSON** (`export_json(ns=)`, `import_json(data, overwrite=)`) para backup.
- **Stats** (`stats()`) com total, contagem por namespace, expirados, tamanho do DB, schema_version.

### 4 novas tools MCP de memória (v10.3)

Centralizadas em `lilo.handle_tool_call` + thin wrappers em `lilo_mcp.py` (delegam) + entradas em `lilo_skills/__init__.py` (menu `/`).

| Tool | Args | Função |
|---|---|---|
| `lilo_memory_search` | `query`, `namespace=""`, `limit=50` | Busca textual em key/value/tags |
| `lilo_memory_stats` | — | JSON com total, by_namespace, expired, db_size, schema_version |
| `lilo_memory_export` | `namespace=""` | Backup JSON (filtra por ns opcional) |
| `lilo_memory_cleanup` | — | Remove entradas expiradas |

`lilo_memory_set` ganhou parâmetro opcional `ttl_seconds` (omita para nunca expirar).

### Total de tools v10.3

- **CORE_SKILLS**: 28 (era 24 → +4 memory_search/stats/export/cleanup)
- **list_all_tools**: 236 (era 232)
- **Menu `/` do dashboard**: 28 core + 199 geradas = **227 skills visíveis**

## v10.2.1 — 2026-05-07 (hotfix menu / no dashboard)

**Bug:** após v10.2, `/lilo_memory_set`, `/lilo_cost_today`, etc. **não
apareciam no menu `/` do dashboard 8100** apesar de estarem registradas
em `lilo.list_all_tools()`. Causa: o menu lê de `_CORE_SKILL_META` em
`lilo_skills/__init__.py`, que tinha apenas as 16 tools originais.

**Fix:**

1. `lilo_skills/__init__.py` — adicionadas as 8 tools v10.2 (`lilo_memory_*`, `lilo_cost_*`, `lilo_pull_model`, `lilo_list_local_models`) tanto em `CORE_SKILLS` (mapeamento de roteamento) quanto em `_CORE_SKILL_META` (metadados visíveis no menu). Total subiu de 16 para 24 skills core.
2. `dashboard.py` — parser de slash command refeito:
   - Antes: `/lilo_cost_today` (sem args) **listava** em vez de executar.
   - Agora: nome exato sem args **executa com `{}`** (útil para tools com defaults). Nome parcial continua listando como autocomplete.
   - Mensagens de listagem agora mencionam ambos os formatos: `/<nome>` ou `/<nome> arg=val`.

**Para aplicar:** reiniciar o `dashboard.py` (Ctrl+C e re-rodar `START_LILO_WINDOWS.bat`). O cache `@st.cache_data(ttl=60)` da função `load_skills_list` invalida automaticamente em 60s, mas reiniciar é mais rápido.

## v10.2 — 2026-05-07 (sprint MCP tools + skills)

### 8 novas tools MCP centralizadas em `lilo.py`

Antes elas só existiam em `lilo_mcp.py` (acessíveis via Claude Desktop e
PyCharm). Agora estão em `handle_tool_call` e `list_all_tools`,
expondo-as automaticamente em **todos os clientes**: CLI, dashboard 8100,
API HTTP `/v1/tools/call`, MCP stdio. `lilo_mcp.py` agora apenas delega
(zero duplicação).

**Memória persistente (4 tools)** — KV store SQLite em `data/kv_memory.db`:

- `lilo_memory_set(key, value, namespace="default", tags="")`
- `lilo_memory_get(key, namespace="default")`
- `lilo_memory_list(namespace="", tag="")`
- `lilo_memory_delete(key, namespace="default")`

**Cost tracker (2 tools)** — observabilidade de gastos:

- `lilo_cost_today(target_date="")` — JSON do `daily_summary` (por backend e subagente)
- `lilo_cost_recent(limit=20)` — últimas N requests com modelo, custo, duração

**Ollama model manager (2 tools)** — útil ao trocar de máquina:

- `lilo_pull_model(name, timeout=600)` — `ollama pull <name>` via subprocess. Validação regex no nome para bloquear injection. Timeout configurável.
- `lilo_list_local_models()` — `ollama list`

### Skills — saneamento (`lilo_skills/`)

- **`registry.json` ganha `schema_version`** (v1.1) e `generator_version`. O `_load_registry()` em `lilo_skills/__init__.py` detecta divergência e emite warning sugerindo regenerar — útil ao trocar de máquina ou após `mamba update`.
- **Prefixo `skill_advanced_<nome>`** para skills com `complexity="high"` (em vez de `skill_<nome>`). Reduz poluição no menu `/` do dashboard. `load_skills_as_tools(include_advanced=False)` permite omitir totalmente. Hoje há 0 skills high (193 simple + 6 medium); o esquema é futuro-proof.
- `generate_skills.py` atualizado para emitir `schema_version=1.1` em regenerações. Contagem `by_complexity` agora inclui `high`.
- **`call_skill()`** trata os dois prefixos (`skill_` e `skill_advanced_`) corretamente ao remover.

### Documentação

- `docs/uso/COMANDOS.md` — 3 novas seções (Memória, Cost, Ollama manager) + seção de saneamento periódico das skills.
- `docs/historico/2026-05-07_relatorio_ia_lilo.md` — itens 3.2 e 3.3 marcados como concluídos.
- `docs/tecnico/arquitetura_v10.md` — bumpado para v10.2.

## v10.1 — 2026-05-07 (sprint curto-prazo)

### Aba Desktop no dashboard 8100 (`dashboard.py`)

- Novo botão **Desktop** na sidebar (`SUB-AGENTES`).
- Página com 6 sub-abas (`fs_read`, `fs_write`, `fs_list`, `fs_search`, `run_shell`, `run_python`) — formulário visual para cada tool, reutilizando `lilo.handle_tool_call` (zero duplicação de lógica).
- Mostra a allow-list ativa em um expander para o usuário saber onde pode operar antes de digitar paths.
- `DesktopAgent` carregado automaticamente em `load_agents()` ao lado dos demais.

### Smart routing no Villa-Lobos (`agents/villa_lobos/agent.py`)

- `_orchestrate_decision()` — Orchestrator emite JSON estruturado com `{complexity, needs_planning, needs_reader, needs_worker, iterations, skip_to_reporter, reasoning}`.
- **Fast-path** `skip_to_reporter`: tarefas triviais (definições, conversões, perguntas factuais) pulam Planner+Reader+Worker e vão direto ao Reporter — economiza ~70% de latência (1 chamada Ollama vs 5).
- Cada stage agora é condicional via flags do JSON (`needs_planning`, `needs_reader`, `needs_worker`).
- Fallback duplo: se o LLM falhar/devolver JSON inválido, heurística regex (`_SIMPLE_PATTERNS` + comprimento<80) decide; se nem isso acionar, pipeline completo (default conservador).
- `context` continua aceitando override manual de qualquer flag (compat com chamadas antigas e testes).
- Saída inclui `**Stages:** orchestrator -> ... -> reporter` para rastreabilidade.

### Pre-commit hook AST (`scripts/`)

- `scripts/pre_commit_ast_check.py` — valida com `ast.parse()` todos os `.py` staged. Detecta também truncamento OneDrive via heurística (null bytes, brackets/strings não fechados) **antes** de chegar ao `ast.parse`, dando mensagens diagnósticas mais claras.
- `scripts/install_hooks.py` — instala o hook em `.git/hooks/pre-commit` (cross-platform, com `.bat` de diagnóstico ao lado para Windows nativo). Suporta `--uninstall`.
- Bypass de emergência: `git commit --no-verify` (registrar motivo no commit).
- Testado contra arquivo deliberadamente truncado: `FAIL  /tmp/truncated.py  (truncamento provavel -- brackets nao fechados: ))` — exit 1.

## v10.0 — 2026-05-07 (arch-v10)

### MCP integrado e funcionando

- **Bug crítico corrigido:** `_profile_tool` chamava `mcp.tool()` antes de `mcp = FastMCP(...)` ser definido — causava `NameError` no import e impedia o servidor de subir no Claude Desktop e PyCharm. Reordenado.
- **Smoke test stdio** (`scripts/test_mcp_stdio.py`) — simula handshake MCP do Claude Desktop. Validado com 23 tools detectadas e 7/7 subagentes OK.
- **MCPs unificados** com flag `--profile {desktop|pycharm|http}`. `lilo_pycharm_mcp.py` removido (era 95% duplicado).
- **Perfis MCP prontos** em `config/mcp/{claude_desktop,claude_code,pycharm}.json`.

### Desktop Commander integrado (subagente novo)

- `agents/desktop/agent.py` — 7 tools (`fs_read`, `fs_write`, `fs_list`, `fs_stat`, `fs_search`, `run_shell`, `run_python`).
- Allow-list de paths em `LILO_DESKTOP_ALLOW` (`.env`).
- Bloqueio de comandos perigosos (`rm -rf /`, `format c:`, `mkfs`, fork bomb).
- Acessível via Claude Desktop, PyCharm e dashboard 8100.

### Tools de memória e custo (lilo_mcp.py)

- `lilo_memory_set/get/list/delete` — persistência de variáveis entre sessões.
- `lilo_cost_today/recent` — visualização de gastos com Claude API.

### Refatoração arquitetural (arch-v10)

- **Subagentes não duplicados:** removidas cópias de `Analise_SQL/`, `scholaragent/`, `PDFs_library/` da raiz (eram 1 linha diferentes de `agents/`).
- **`llm-gateway/` desmontado:** `agent.py` virou `agents/gateway/agent.py`, `litellm_config.yaml` foi para `config/`. Restantes (orfãos `agents/lilo_agent.py` 328 linhas, `health_check.py` 68 linhas, dirs vazios) movidos para `_ARCHIVE_v10/to_delete/`.
- **`backend/` + `frontend/` arquivados** em `_ARCHIVE_v10/v6_fastapi/` (FastAPI v6 + React nunca foram iniciados pelo `START_LILO_WINDOWS.bat`).
- **Docker compose arquivado** (idem).

### Portas trocadas (conflitos com outras APIs do usuário)

- Dashboard Streamlit: **8506 → 8100** (travado em `.streamlit/config.toml`).
- PDFs Library: **8503 → 8101**.

### Correções de bugs encontrados na auditoria

- `shared/llm_client.py`: arquivo estava **truncado em produção** (`_client_instance` sem corpo). Restaurado o singleton `get_client()`.
- `shared/policy.py`: `get_status()` também truncado, restaurado.
- `shared/llm_client.py`: ordem de detecção de backend invertida (Ollama era detectado antes do LiteLLM, contrariando o docstring). Corrigido para LiteLLM-first.
- `shared/policy.py`: query OpenMM/DM era classificada como "tarefa simples" e ia pra Ollama leve. Adicionados 26 tokens (`openmm`, `nvt`, `npt`, `equilibration`, `gromacs`, `amber`, `rmsd`, `mmgbsa`, etc.) → agora vai pra Claude Sonnet/Opus quando aplicável.
- `requirements.txt`: declarado `duckduckgo-search`, `beautifulsoup4`, `lxml` (eram opcionais e silenciavam falhas).
- `BUILD_E_ABRIR.bat` e `dashboard.py`: paths antigos de `PDFs_library/` (raiz) atualizados para `agents/PDFs_library/`.

### Skills adicionadas

- `lilo_skills/skills/bio/openmm_nvt_equilibration_safe.py` — gera script OpenMM anti-NaN com minimização + ramp + HMR + checkpoints. Resolve o erro reportado em 2026-05-06.

### Dashboard reformado

- **CSS reescrito do zero** — sidebar verde com texto branco legível, header sem corte, painel direito mais estreito.
- **Aba Ajuda nova** com 6 sub-tabs renderizando dinamicamente os .md de `docs/`.
- **Aba Docs eliminada** (redundante com Ajuda).
- **Card 3D Villa-Lobos** mostrando os LLMs de cada estágio (Orchestrator/Planner/Reader/Worker/Reporter), posicionado no rodapé da página.
- **Botão "Aquecer GPU"** na aba Saúde — força o modelo para a VRAM com `keep_alive=2h`.
- **Diagnóstico GPU diferenciado**: distingue "GPU (driver)" via `nvidia-smi` de "Ollama VRAM" (modelos carregados agora). "Idle" não é mais erro.
- **Default de iterações Villa-Lobos = 2** (era 1) — sweet spot para research-grade.
- **Tooltips** em `iterations`, `use_reader`, `base_path`.

### Configuração

- `OLLAMA_KEEP_ALIVE=2h` adicionado ao `.env` — modelos não descarregam mais da VRAM após 5 min.
- `LILO_DESKTOP_ALLOW` no `.env` — controla pastas acessíveis ao Desktop Commander.

### Documentação

- Todos os .md migrados para `docs/{uso,tecnico,versoes,historico,agentes}/`. Apenas `README.md` restou na raiz.
- Aba Ajuda do dashboard renderiza tudo dinamicamente.
- `_ARCHIVE_v10/README.md` documenta o que foi removido.

---

## v9.0 — 2026-04-25 (não documentada formalmente; reconstituída)

- Adicionado subagente `prism_ai` com 6 sub-agentes internos.
- Adicionado pipeline Villa-Lobos (5 stages).
- Auto-síntese de diretório anexado.
- Notas de projeto auto-mantidas em `notes.md`.
- Slash commands no chat (`/skill_name`).

## v8.0 — 2026-04 (não documentada)

- ChatMemory com SQLite + busca textual.
- CostTracker com SQLite.
- Skills auto-geradas (199) do ambiente Conda.

## v7.0 — 2026-03 (não documentada)

- Primeira versão funcional do MCP server.
- Health check.
- Dashboard Streamlit inicial.

---

Para ver as auditorias e investigações detalhadas, veja `docs/historico/`.
