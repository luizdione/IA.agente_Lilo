# LILO -- Relatório de Verificação e Desenvolvimento Contínuo

**Data:** 2026-05-12
**Tarefa agendada:** `ia_lilo` (continuidade do trabalho que parou por limite de créditos)
**Executor:** Cowork (Claude Sonnet 4.6)
**Escopo:** verificação de erros em scripts, correções, evolução contínua da plataforma híbrida (Desktop API + MCP), configurações MCP/Skills para Claude Desktop, OpenClaw, Claude Code, PyCharm, e do orquestrador Villa-Lobos.

---

## 1. Verificações executadas

Foram rodados dois pacotes de verificação na sandbox Linux que monta o workspace OneDrive:

`scripts/smoke_test_v11.py` (8 testes) -- sintaxe AST, KVMemory, CostTracker, heurística `_detect_domain`, imports de `lilo.py`, `VillaLobosAgent`, `lilo_mcp.py` (com tools v10.2) e `lilo_api.py` (opcional).

`scripts/lilo_diag.py` (5 etapas) -- sintaxe, caches stale, importações de `lilo_skills`, importação de `lilo` com `list_all_tools`, e teste funcional do `kv_memory`.

Estado inicial: 2 falhas críticas (kv_memory + lilo_mcp). Estado final: **todos os 8 smoke tests e todas as 5 etapas do diag passam**.

---

## 2. Bugs encontrados e corrigidos

### 2.1 `shared/kv_memory.py` -- ordem de migração quebrava bancos legados

`KVMemory._init_db()` criava o índice `idx_kv_expires ON kv(expires_at)` ANTES de a migração incremental (`_ensure_column("expires_at", "TEXT")`) ter adicionado a coluna em bancos legados que ainda usavam o schema 1.0. Resultado: ao migrar `memory/kv_memory.db` (OneDrive) para `%LOCALAPPDATA%\LILO\memory\kv_memory.db`, o primeiro CREATE INDEX falhava com `sqlite3.OperationalError: no such column: expires_at` -- e o singleton `get_memory()` nunca inicializava.

Correção aplicada: reordenei `_init_db` em três etapas explícitas:

1. CREATE TABLE/meta + índice `idx_kv_ns` (apenas colunas garantidas).
2. `_ensure_column("expires_at", "TEXT")` e `_ensure_column("tags", "TEXT")`.
3. CREATE INDEX `idx_kv_expires` e `idx_kv_tags` (agora seguros).

Validado: criação fresh de DB, migração de legado, set/get/list/delete, stats -- todos OK.

### 2.2 `lilo_mcp.py` -- string literal quebrada por newline real

Em `_stderr_log` (linha 1069) o autor escreveu `sys.stderr.write(msg.rstrip() + "\n")`, mas o `\n` foi salvo como newline real dentro da string, gerando `SyntaxError: unterminated string literal`. A correção (auto-aplicada pelo linter durante a edição) trocou a sequência por `chr(10)`, evitando a ambiguidade. Validado: `ast.parse` OK, import OK, smoke test 07 passa.

### 2.3 Metadados desatualizados em configs MCP

Os arquivos `config/mcp/{openclaw,pycharm,bio,claude_desktop}.json` listavam apenas os perfis legados (`desktop`, `bio`, `pycharm`, `http`) -- faltavam `opus` e `claude_code`, que existem em `lilo_mcp.py` desde 2026-05-08 e 2026-05-12. Também usavam `command: "python"` (depende de PATH), inconsistente com `claude_code.json` que já apontava para `C:\Users\luizd\miniforge3\python.exe`.

Correção aplicada nos quatro configs:

- `_profiles_disponiveis` agora inclui `opus` e `claude_code`;
- `command` padronizado para o caminho absoluto da miniforge3 (evita falha quando o usuário inicia o cliente sem Conda ativo);
- adicionado `OLLAMA_HOST` e `LILO_KEEP_ALIVE` em todos os envs (alinha com o template do Claude Desktop).

---

## 3. Estado dos componentes

### 3.1 Orquestrador Villa-Lobos (`agents/villa_lobos/agent.py`)

Já implementa exatamente o pattern pedido pela tarefa -- "LLMs chamando diferentes agentes capacitados para tarefas específicas, de acordo com o setup do servidor":

- `_route_via_llm`: classifica a query em `prism|sql|pdf|scholar|desktop|gateway|none` via Ollama (modelo `MODELS["autocomplete"]`).
- `_detect_domain`: heurística por keywords como fallback (config/villa/domains.yaml com hot-reload).
- `_delegate_to_specialist`: instancia o subagente alvo via `lilo._load_agents()` e roda `agents[domain].run(query, ctx)` -- registrando no `cost_tracker` o roteamento como `villa_route`.
- `_orchestrate_decision`: Orchestrator emite JSON com `complexity`, `needs_planning|reader|worker`, `iterations`, `skip_to_reporter`, `reasoning`. Cache LRU bounded por SHA1 da query normalizada (256 entradas).
- Pipeline padrão: Orchestrator → Planner → Reader → Worker (1-3 iterações) → Reporter. Fast path quando o Orchestrator declara `skip_to_reporter`.
- Telemetria stage-level via `cost_tracker.log_request` em `_call_agent`.
- `explain_routing(query)` permite tracing sem executar o pipeline.
- Métodos de saúde retornam `domains_supported`, `domains_source` (yaml/defaults), `default_tiers`, `decision_cache`.

Não é necessária reescrita; o componente atende ao requisito. Propostas de evolução listadas em §4.

### 3.2 Plataforma híbrida (Desktop-like + API)

`lilo_mcp.py` (stdio MCP, 6 profiles: `desktop|opus|bio|pycharm|http|claude_code`) e `lilo_api.py` (FastAPI + portal HTML + Swagger) compartilham 100% da camada `lilo.handle_tool_call/route` -- a mesma lógica de routing, fallback, policy engine e cost tracking atende CLI, MCP e API.

Verificado:

- `lilo_api.py` expõe `/v1/chat`, `/v1/tools/call`, `/v1/skills/run`, `/v1/memory`, `/v1/cost/*`, `/v1/health`, `/v1/chat/stream` (SSE), portal HTML em `/`, Swagger em `/docs`.
- Auth opcional via `LILO_API_TOKEN` (Bearer header ou query `?token=`).
- CORS configurável via `LILO_API_CORS`.
- Profile `http` reservado para uso futuro -- atualmente expõe tudo (None = sem filtro).

### 3.3 Skills (`lilo_skills/`)

- Registry 1.1: 28 CORE_SKILLS + 199 skills auto-geradas a partir de `scan_conda_env.py` + `generate_skills.py`.
- Schemas por skill em `lilo_skills/schemas/<name>.json`.
- Filtragem por tags/packages/complexity (`include_advanced`).
- Meta-skills: `lilo_list_skills`, `lilo_run_skill`, `lilo_skill_info`.
- Prefixos: `skill_<name>` (normal) e `skill_advanced_<name>` (complexity=high).
- Caching e schema-version check (warn quando registry < MIN_REGISTRY_VERSION).

Sem ajustes necessários no curto prazo. Propostas de evolução em §4.

### 3.4 Configurações MCP por cliente (estado final)

| Cliente              | Arquivo                          | Profile        | Tools efetivas |
|----------------------|----------------------------------|----------------|----------------|
| Claude Desktop (Opus)| `config/mcp/claude_desktop.json` | `opus`         | 18 curadas     |
| Claude Code (Sonnet) | `config/mcp/claude_code.json`    | `claude_code`  | ~17 complementares ao CLI nativo |
| OpenClaw             | `config/mcp/openclaw.json`       | `desktop`      | 35 (todas)     |
| PyCharm AI Assistant | `config/mcp/pycharm.json`        | `pycharm`      | ~30 (foco refactor) |
| Setup biomolecular   | `config/mcp/bio.json`            | `bio`          | 27 (sem run_shell) |

Todos apontando para `C:\Users\luizd\miniforge3\python.exe`, com `PYTHONPATH`, `OLLAMA_HOST` e `LILO_KEEP_ALIVE` consistentes.

---

## 4. Roadmap de desenvolvimento contínuo (propostas)

### 4.1 Plataforma híbrida (curto prazo)

1. Expor `villa_explain_routing` também via `/v1/villa/explain` em `lilo_api.py` -- útil para depurar decisões do orquestrador sem rodar o pipeline.
2. Adicionar autenticação por API key persistente em `kv_memory` (namespace `api_tokens`), com rotação e log de uso por token.
3. Implementar profile `http` em `lilo_mcp.py` como um subset HTTP-friendly (sem tools que dependam de `mcp.server.stdio`).
4. Endpoint `/v1/stream` por subagente (não só por `chat`), permitindo streaming de Worker/Planner em Villa-Lobos.

### 4.2 Villa-Lobos (médio prazo)

1. Suporte a múltiplos especialistas em paralelo: quando o Orchestrator declarar `needs_multi_domain`, despachar para 2-3 subagentes simultaneamente e fundir resultados no Reporter.
2. Persistir o decision_cache em `kv_memory` (namespace `villa_decisions`) com TTL configurável -- hoje o cache é só in-memory e reseta a cada reinício do servidor MCP.
3. Adicionar tier `claude_sonnet` ao `DEFAULT_STAGE_TIERS` para queries cujo Orchestrator marcar como `complexity=complex` -- promove uso de Claude API só onde realmente compensa.
4. Métrica de "delegate success rate" em `cache_stats()` para validar a qualidade do LLM router.

### 4.3 MCP/Skills (médio prazo)

1. Gerar índice `lilo_skills/manifest.json` versionado, contendo apenas nome+descrição+tags (sem schemas inline) -- reduz I/O quando carregamos só o menu.
2. Adicionar `lilo_skill_diff` MCP tool: compara registry.json atual com o último commit em git, listando skills adicionadas/removidas/alteradas.
3. Migrar `scan_conda_env.py` para usar `inspect.signature` + `typing.get_type_hints` (em vez de regex em docstrings) -- mais robusto a pacotes que mudaram convenção.
4. Profile `claude_code` poderia receber dinamicamente skills auto-geradas filtradas por tags (`statistics`, `bioinformatics`) sem expor todas as 199.

### 4.4 Observabilidade e CI

1. Habilitar `scripts/pre_commit_ast_check.py` como hook git para evitar regressões do tipo "string com newline real" como o bug de §2.2.
2. Adicionar `scripts/smoke_test_v11.py` ao `START_LILO_WINDOWS.bat` como pré-flight check.
3. Dashboard: aba "diag" rodando `lilo_diag.py` em background e mostrando os resultados (sem precisar abrir terminal).
4. Cost tracker: alerta automatic
o quando custo diário Claude API ultrapassar threshold configurável (ex: $5/dia) -- integrar com `kv_memory` para persistir o threshold.

---

## 5. Caveats e notas de execução

- O ambiente bash (Linux mount sobre OneDrive) apresentou em determinado momento truncamento intermitente de visualização de arquivos grandes (`lilo.py`, `lilo_mcp.py`, `agents/villa_lobos/agent.py`) -- nas mesmas chamadas, a leitura via path Windows direto retornava o arquivo íntegro. As correções aplicadas usaram o path Windows para não depender da sincronia do mount Linux.
- Cache `.pyc` do CPython usa mtime da fonte para validar staleness; uma fonte editada no OneDrive pode ficar com mtime antigo enquanto o `.pyc` está mais novo, fazendo o Python servir o pyc antigo. Workaround: `touch` na fonte após editar, ou apagar `__pycache__/` (alguns `.pyc` ficaram com permissão "Operation not permitted" no sandbox -- relação direta com lock do OneDrive). Recomendação: incluir um `find . -name __pycache__ -exec rm -rf {} +` no `START_LILO_WINDOWS.bat`.

---

## 6. Próxima ação sugerida

Atualizar `requirements.txt` para garantir `fastapi`, `uvicorn`, `sse-starlette` e `mcp>=1.0.0` -- hoje o smoke test 08 só passa porque o teste detecta a ausência de `fastapi` e pula. Em produção isso significaria que `lilo_api.py` não inicia até alguém rodar `pip install` manualmente.
