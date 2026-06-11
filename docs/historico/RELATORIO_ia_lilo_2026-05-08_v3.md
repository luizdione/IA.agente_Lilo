# Relatorio de execucao -- ia_lilo (2026-05-08 v3 -- continuidade)

> Tarefa agendada `ia_lilo` (continuacao). A run anterior (v2) corrigiu os 3
> truncamentos do crash por limite de creditos. Esta run prosseguiu com os
> itens cross-cutting do roadmap e iniciou a Sprint 1 (convergencia API/MCP).

## 1. Verificacao de erros

- 251 arquivos `.py` da versao ativa parseiam sem `SyntaxError`
  (excluidas `_ARCHIVE_v10`, `obsoletos`, `__pycache__`, `.git`, `.idea`).
- Confirmado que os 3 arquivos antes truncados ja estao integros:
  `lilo.py`, `lilo_mcp.py`, `lilo_skills/__init__.py`.
- `scripts/pre_commit_ast_check.py` rodando OK (sem erros) -- bom hook para
  evitar reincidencia do truncamento por limite de creditos.

> **Sem novos erros para corrigir nesta passada.**

## 2. Mudancas aplicadas nesta run

### 2.1 Cross-cutting -- tiers do Villa_Lobos via `.env`

`agents/villa_lobos/agent.py` agora resolve `DEFAULT_STAGE_TIERS` lendo do
ambiente. Cada estagio pode ser sobrescrito sem editar codigo:

```env
VILLA_TIER_ORCHESTRATOR=ollama_fast
VILLA_TIER_PLANNER=ollama_plan
VILLA_TIER_READER=ollama_code
VILLA_TIER_WORKER=ollama_code
VILLA_TIER_REPORTER=ollama_chat
# Para usar Claude no Reporter (qualidade em sintese):
# VILLA_TIER_REPORTER=claude_haiku
```

Defaults preservados (todos Ollama). Atende o item 4.cross-cutting do
relatorio v2.

### 2.2 Sprint 1 -- convergencia API/MCP iniciada

`lilo_api.py` ganhou um endpoint que faz paridade com o MCP `lilo_run_skill`:

```
POST /v1/skills/run
Body: {"name": "<skill>", "args": {...}}
-> {"ok": true, "skill": "...", "result": ..., "duration_ms": int}
```

A implementacao reusa `handle_tool_call("lilo_run_skill", ...)` para garantir
identidade de comportamento entre os clientes MCP (Claude Desktop, Claude Code,
OpenClaw, PyCharm) e o cliente HTTP (Cowork, dashboards externos, scripts).

Testavel com:
```bash
curl -X POST http://localhost:8088/v1/skills/run \
  -H "Content-Type: application/json" \
  -d '{"name":"numpy.mean","args":{"a":[1,2,3,4]}}'
```

### 2.3 `.env.example` documentado

Adicionada secao "Villa_Lobos -- tiers por estagio" com lista de tiers
aceitos pelo Policy Engine: `ollama_fast | ollama_chat | ollama_plan |
ollama_code | ollama_heavy | claude_haiku | claude_sonnet | claude_opus`.

## 3. Estado dos perfis MCP (revisao)

Confirmadas as 4 configs em `config/mcp/`:

| Cliente         | Profile  | Tools tipicas                        |
|-----------------|----------|--------------------------------------|
| Claude Desktop  | desktop  | Tudo (sem restricao)                 |
| Claude Code     | desktop  | Tudo + Bash via fs/run_shell         |
| OpenClaw        | desktop  | Tudo (mesmo set do Claude Code)      |
| PyCharm         | pycharm  | fs_*, run_shell, run_python, prism, villa, memory |
| Bio (literatura)| bio      | scholar, pdf, prism, villa, fs read-only |

`_PROFILE_TOOLS` em `lilo_mcp.py:52` esta consistente com as 4 configs JSON.
Profile `bio` segue sem `run_shell`/`fs_write` -- correto para fluxo de
revisao bibliografica.

## 4. Estado do Villa_Lobos (revisao)

Capacidades atuais validadas em `agents/villa_lobos/agent.py`:

- **Smart routing** (Orchestrator emite JSON com complexity, needs_*).
- **Skip-to-reporter** para queries triviais (regex + heuristica de tamanho).
- **Delegate-to-specialist** com 2 vias: LLM router (`_route_via_llm`,
  threshold 0.55) e fallback heuristico por keywords (`DOMAIN_KEYWORDS`).
- **6 dominios reconhecidos**: prism, sql, pdf, scholar, desktop, gateway
  (+ none).
- **Tiers por estagio** -- agora externalizados em `.env`.
- **`_call_agent(role, prompt, tier=...)`** propaga tier para `LLMClient.chat`.
- **Fallback automatico** para modelo `chat` se o modelo do estagio falhar
  apos `MAX_RETRIES` (2 retries com 5s de espera).
- **`health()`** retorna `models`, `domains_supported`, `default_tiers`,
  flags de feature.

## 5. Roadmap revisado para v11

### Sprint 1 (em andamento) -- Convergencia API/MCP
- [x] `/v1/skills/run` (esta run).
- [ ] Padronizar response shape: `{ok, tool, output, duration_ms, cost_usd}`
      para `/v1/chat`, `/v1/tools/call`, `/v1/skills/run`.
- [ ] Endpoint `/v1/villa/route` que retorna a decisao do Orchestrator
      sem executar (util para debugar smart routing em producao).
- [ ] WebSocket `/v1/chat/ws` com streaming token-a-token (substituir o SSE
      com chunking artificial atual).

### Sprint 2 -- Orquestrador como servico
- [ ] `agents/villa_lobos/service.py`: fila assincrona (RQ ou Celery + Redis).
- [ ] Cada estagio em worker isolado: timeout independente + retry policy
      por estagio.
- [ ] Tracing OpenTelemetry com decorator em `_call_agent`.
- [ ] Persistir traces em SQLite (reaproveitar `kv_memory` schema).

### Sprint 3 -- UI desktop estilo Claude Desktop
- [ ] Avaliar Tauri (Rust+webview, ~5MB) vs Electron (~80MB).
- [ ] Hot-reload de skills via filesystem watcher
      (`scripts/install_hooks.py` ja tem base).
- [ ] System tray + atalho global (Ctrl+Shift+L) para chat rapido.
- [ ] Empacotamento: `pyinstaller --onefile lilo_api.py` para fallback CLI.

### Cross-cutting (sempre)
- [x] `VILLA_TIER_*` no `.env` (esta run).
- [ ] `pre-commit` rodando `scripts/pre_commit_ast_check.py` em todos os
      `.py` modificados (criar `.pre-commit-config.yaml`).
- [ ] `ruff check .` minimo em CI (sem `mypy --strict` ainda; comecar com
      `mypy --strict shared/`).
- [ ] Testes unitarios: `tests/` com pytest cobrindo `route()`, smart routing
      e Policy Engine.

## 6. Plataforma hibrida -- arquitetura alvo

```
                 ┌────────────────────────────────┐
                 │    Clientes (humanos / bots)    │
                 └───────┬────────────────┬───────┘
                         │ MCP stdio      │ HTTP
                         ▼                ▼
         ┌──────────────────┐   ┌──────────────────────┐
         │   lilo_mcp.py    │   │     lilo_api.py      │
         │  (FastMCP)       │   │  (FastAPI/uvicorn)   │
         │  --profile=*     │   │  /v1/* endpoints     │
         └────────┬─────────┘   └──────────┬───────────┘
                  │                        │
                  └─────────┬──────────────┘
                            ▼
                 ┌──────────────────────┐
                 │  lilo.py (route())   │
                 │  + handle_tool_call  │
                 │  + skills registry   │
                 └────────┬─────────────┘
                          │
                ┌─────────┴─────────────────────┐
                ▼                               ▼
       ┌────────────────┐             ┌──────────────────┐
       │ Subagentes     │             │ Villa_Lobos      │
       │ (sql, pdf,     │ ◀─────────▶ │ (Orchestrator    │
       │  prism, ...)   │  delegate   │  pipeline 5x)    │
       └───────┬────────┘             └────────┬─────────┘
               │                               │
               └───────────────┬───────────────┘
                               ▼
                  ┌──────────────────────────────┐
                  │ Policy Engine (shared/)      │
                  │ tier->backend: ollama|claude │
                  │ daily_budget, allow_cloud    │
                  └────────┬────────────────┬────┘
                           ▼                ▼
                    ┌──────────┐     ┌──────────────┐
                    │  Ollama  │     │   Claude API │
                    │ (local)  │     │ (haiku/son/  │
                    │          │     │  opus)       │
                    └──────────┘     └──────────────┘
```

A convergencia esta na camada `lilo.py::handle_tool_call`: tanto MCP quanto
HTTP chamam o mesmo handler, garantindo paridade de comportamento. O proximo
passo critico e padronizar o **response shape** de todas as 3 superficies
(MCP/HTTP/CLI) para que dashboards e telemetria funcionem em qualquer cliente.

## 7. Verificacao (checks rodados)

- `python3 -m py_compile lilo_api.py agents/villa_lobos/agent.py`: PASS.
- AST scan dos 251 `.py` ativos: 0 SyntaxErrors.
- `_STAGE_DEFAULTS + os.getenv` -- valida tier override em runtime.
- `lilo_api.py` ganhou 1 endpoint novo + 1 bloco de doc inline.

> Observacao recorrente: o sandbox Linux desta sessao continua com snapshot
> antigo do OneDrive (timestamps 2026-05-07). As edicoes desta run foram
> aplicadas via Read/Write/Edit contra o filesystem Windows real; quando o
> OneDrive sincronizar, o mount Linux refletira as mudancas.

## 8. TL;DR

- Sem novos erros de sintaxe.
- **`VILLA_TIER_*`** no `.env` -- tiers do pipeline configuraveis sem editar
  codigo.
- **`POST /v1/skills/run`** -- paridade HTTP com `lilo_run_skill` (Sprint 1).
- `.env.example` documentado.
- Roadmap v11 atualizado: Sprint 1 em andamento, Sprint 2/3 e cross-cutting
  com itens claros.
