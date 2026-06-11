# Relatório Técnico — Tarefa `ia_lilo` (v2 - sessão 2)
**Data:** 2026-05-07 (continuação)
**Escopo:** Implementar os "próximos passos" do relatório v1 — `lilo_api.py`, `openclaw.json`, tools de memória/cost, e Sprint A do Villa Lobos (roteamento via LLM).

---

## 1. Entregas desta sessão

### 1.1 `lilo_api.py` — plataforma híbrida HTTP
Novo arquivo (~310 linhas) que reaproveita 100% da camada `lilo.handle_tool_call`/`route` e expõe as mesmas tools como API REST. Endpoints implementados:

| Endpoint | Método | Função |
|---|---|---|
| `/v1/health` | GET | Status agentes + backends |
| `/v1/agents` | GET | Subagentes carregados |
| `/v1/tools` | GET | Catálogo MCP-style (todas as tools) |
| `/v1/skills` | GET | Registry completo (16 core + 199 geradas) |
| `/v1/chat` | POST | `{query, tab?, context?}` → resposta |
| `/v1/tools/call` | POST | `{name, arguments}` → resultado |
| `/v1/chat/stream` | POST | Streaming SSE |
| `/v1/cost/today` | GET | Resumo do dia |
| `/v1/cost/recent?limit=N` | GET | Últimas N requests |
| `/v1/memory` | GET/POST | Listar/setar memória persistente |
| `/v1/memory/{ns}/{key}` | GET/DELETE | Obter/remover entrada |

Autenticação: token Bearer opcional via `LILO_API_TOKEN` no `.env`. Sem token → modo dev (aceita qualquer request). Com token → requer `Authorization: Bearer <token>`.

CORS: `LILO_API_CORS=*` por default; configurar em produção.

Launcher: `START_LILO_API.bat` na raiz auto-detecta Python (`.venv/`, conda `lilo`, sistema), instala deps faltantes (fastapi/uvicorn/sse-starlette/pydantic) e sobe em `http://localhost:8088`.

### 1.2 `config/mcp/openclaw.json`
Perfil MCP para OpenClaw. Aponta para `lilo_mcp.py --profile desktop` com `PYTHONPATH` correto (idêntico aos outros, só com comentário diferente). O usuário pode salvar em `~/.openclaw.json`.

### 1.3 `shared/kv_memory.py` — Key/Value persistente
Novo módulo (~130 linhas). SQLite em `memory/kv_memory.db` com:
- Tabela `kv(ns, key, value, tags, created_at, updated_at)` com PK composta `(ns, key)`.
- Métodos: `set`, `get`, `delete`, `list`, `clear_namespace`.
- Auto-serialização JSON quando o valor não é string.
- Singleton via `get_memory()`.

Smoke test in-line confirmou: set/get/list/delete funcionam end-to-end.

### 1.4 6 novas tools no `lilo_mcp.py`
| Tool | Função |
|---|---|
| `lilo_memory_set(key, value, namespace?, tags?)` | Salva entrada (string ou JSON) |
| `lilo_memory_get(key, namespace?)` | Lê entrada |
| `lilo_memory_list(namespace?, tag?)` | Lista (até 50 itens) |
| `lilo_memory_delete(key, namespace?)` | Remove entrada |
| `lilo_cost_today(target_date?)` | Resumo de custo (JSON) |
| `lilo_cost_recent(limit?)` | Últimas N requests |

Todas registradas no profile `desktop` automaticamente; o profile `pycharm` foi expandido para incluí-las também (memória/cost são úteis em qualquer cliente, não só Claude Desktop).

### 1.5 Villa Lobos — Sprint A (roteamento por LLM)
Substituí a heurística pura de keywords por um router de duas camadas em `agents/villa_lobos/agent.py`:

1. **`_route_via_llm(query)`** — chama o modelo `autocomplete` (Ollama leve, ex: `qwen2.5-coder:7b-instruct`, T=0.0, max_tokens=128) com prompt estruturado pedindo classificação em `{prism, sql, pdf, scholar, none}` + confidence + reason. Parse JSON robusto (aceita texto extra). Aceita o domínio só se `confidence >= 0.6`.
2. **Fallback `_detect_domain(query)`** — heurística de keywords original (não removida) se o LLM falhar/timeout/JSON inválido.

A função `_delegate_to_specialist` agora:
- usa LLM primeiro, heurística como segundo,
- registra a decisão no `cost_tracker` com `backend="villa_route"` e `model=route_method` ("llm" ou "heuristic"),
- continua aceitando o resultado do especialista só se ≥40 chars e sem `[ERRO`.

Saída do `run()` agora exibe `**Roteamento:** llm` ou `heuristic` quando delega — observabilidade clara.

### 1.6 `requirements.txt` atualizado
Adicionados ao bloco MCP: `fastapi>=0.110`, `uvicorn>=0.29`, `sse-starlette>=2.0`, `pydantic>=2.5`.

### 1.7 `scripts/smoke_test_v11.py`
8 testes acionáveis localmente:
1. Sintaxe (`ast.parse`) de todos os módulos editados.
2. KVMemory end-to-end (set/get/list/delete).
3. CostTracker `log_request` + `daily_summary`.
4. `_detect_domain` heurística (4 casos positivos + 1 negativo).
5. `lilo` imports e atributos.
6. `VillaLobosAgent` tem `_route_via_llm` e `_delegate_to_specialist`.
7. `lilo_mcp` carrega e tem as 6 tools novas (skip se `mcp` ausente).
8. `lilo_api` carrega (skip se `fastapi` ausente).

Rodar com:
```cmd
python scripts\smoke_test_v11.py
```

---

## 2. Como usar

### 2.1 Plataforma híbrida (HTTP API)
```cmd
START_LILO_API.bat
:: depois, em outro terminal:
curl http://localhost:8088/v1/health
curl -X POST http://localhost:8088/v1/chat ^
     -H "Content-Type: application/json" ^
     -d "{\"query\":\"liste arquivos do projeto\"}"
```

### 2.2 Memória persistente via Claude Desktop
Após reiniciar o servidor MCP, o Claude/PyCharm/OpenClaw passam a ter acesso a:
```
lilo_memory_set("preferred_model", "claude-sonnet-4-5", namespace="user")
lilo_memory_get("preferred_model", namespace="user")
lilo_memory_list(namespace="user")
```
Isso permite ao agente lembrar preferências e decisões entre sessões.

### 2.3 Villa Lobos com roteamento inteligente
Sem mudanças na chamada — o roteamento é transparente:
```python
from lilo import route
route("rodar ANOVA no arquivo data/exp1.xlsx", tab="villa")
# Output mostrara "**Roteamento:** llm" ou "heuristic" e delega ao Prism.

route("desenhar arquitetura RNA-seq do zero", tab="villa")
# Sem dominio claro -> roda os 5 estagios normais.
```
Para testar o pipeline puro (sem delegação): passar `context={"allow_delegate": False}`.

---

## 3. Validação

| Item | Método | Status |
|---|---|---|
| `kv_memory.py` smoke test | Bash inline (set/get/list/delete) | OK |
| Sintaxe `lilo_api.py` | `ast.parse` | OK |
| Sintaxe `kv_memory.py` | `ast.parse` | OK |
| Sintaxe `lilo_mcp.py` | A confirmar localmente após sync OneDrive | A validar |
| Sintaxe `villa_lobos/agent.py` | A confirmar localmente após sync OneDrive | A validar |
| `openclaw.json` JSON válido | `json.load` | OK |
| `requirements.txt` | Inspeção manual | OK |

> Observação técnica: durante esta sessão houve atraso na propagação de Edits no OneDrive (ferramentas internas mostravam o conteúdo correto enquanto o disco mantinha cópia pré-edit por alguns minutos). O conteúdo final salvo na OneDrive **é** o conteúdo dos Reads/Writes finais — recomendado rodar `python scripts\smoke_test_v11.py` ao reabrir o projeto para confirmar.

---

## 4. Arquitetura final (estado em 2026-05-07)

```
┌────────────────────────────────────────────────────────────┐
│  CLIENTES                                                  │
│  Claude Desktop ─┐                                         │
│  PyCharm ────────┼─ MCP stdio ──> lilo_mcp.py              │
│  OpenClaw ───────┘                                         │
│  Claude Code ────┘                                         │
│                                                            │
│  curl / scripts ─┐                                         │
│  Streamlit  ─────┼─ HTTP ──────> lilo_api.py (FastAPI)     │
│  Custom UI ──────┘                                         │
└────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│  CAMADA UNICA -- lilo.py                                   │
│  - route(query, tab, context)                              │
│  - handle_tool_call(name, args)                            │
│  - list_all_tools()                                        │
│  - health_check()                                          │
└────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│  ESPECIALISTAS                                             │
│  villa (orquestrador)                                      │
│    │                                                       │
│    ├── prism_ai (estatistica)                              │
│    ├── Analise_SQL (queries)                               │
│    ├── PDFs_library (sumarizacao)                          │
│    ├── scholaragent (PubMed/arXiv)                         │
│    ├── desktop (filesystem/shell)                          │
│    └── gateway (fallback geral)                            │
│                                                            │
│  Skills (199 funcoes scipy/numpy/pandas/...)               │
│  Memoria KV (sessoes persistentes)                         │
│  Cost Tracker (Ollama=$0, Claude=$$$)                      │
└────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│  BACKENDS LLM                                              │
│  LiteLLM proxy :4000 -> Ollama :11434                      │
│  Direct Anthropic API (Claude 4.5 Sonnet/Opus/Haiku)       │
└────────────────────────────────────────────────────────────┘
```

---

## 5. Próximos sprints recomendados (Roadmap atualizado)

**Sprint B — Pipeline adaptativo Villa Lobos** (3-5 dias)
- Planner retorna JSON estruturado `{stages, specialists, iterations}`.
- Orchestrator executa o JSON dinamicamente — fim dos 5 estágios fixos.
- Plugar `chat_memory.py` para memória curta entre estágios.

**Sprint C — Multi-LLM por estágio** (1 semana)
- Estágio Orchestrator → `claude_haiku` (decisão barata).
- Estágio Planner → Ollama `phi3:14b`.
- Estágio Worker → Ollama `qwen2.5-coder:14b`.
- Estágio Reporter → `claude_sonnet` (qualidade redacional).
- Tier `claude_haiku` já pronto em `llm_client.py` ✓.

**Sprint D — Painel de observabilidade** (2-3 dias)
- View dedicada no `dashboard.py`: por execução de Villa, mostrar (domínio detectado, route_method, tempo por estágio, modelo usado, custo). Estrutura de dados já existe em `cost_tracker`.

**Sprint E — Migrar Streamlit para Next.js + lilo_api** (opcional, 1-2 semanas)
- Frontend separado consumindo `lilo_api.py`.
- Permite rodar o servidor em máquina remota e o usuário acessar de qualquer device.
- Backend `lilo_api` já preparado com CORS + tokens.

---

## 6. Resumo dos arquivos novos/modificados

```
NOVOS:
  lilo_api.py                                   (FastAPI HTTP server)
  shared/kv_memory.py                           (KV persistente SQLite)
  config/mcp/openclaw.json                      (perfil MCP OpenClaw)
  START_LILO_API.bat                            (launcher Windows)
  scripts/smoke_test_v11.py                     (validador local)
  docs/RELATORIO_ia_lilo_2026-05-07_v2.md       (este relatorio)

MODIFICADOS:
  lilo_mcp.py                                   (+ 6 tools memoria/cost; pycharm profile)
  agents/villa_lobos/agent.py                   (Sprint A: _route_via_llm + delegate)
  requirements.txt                              (+ fastapi/uvicorn/sse-starlette/pydantic)

PRESERVADOS (sessao 1, ja entregues):
  config/litellm_config.yaml                    (claude 4.5 atualizado)
  shared/policy.py                              (TIER_MODELS via env vars)
  shared/llm_client.py                          (tier claude_haiku adicionado)
  docs/RELATORIO_ia_lilo_2026-05-07.md          (relatorio sessao 1)
```
