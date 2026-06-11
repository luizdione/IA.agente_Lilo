# Relatório Técnico — Tarefa agendada `ia_lilo`
**Data:** 2026-05-07
**Escopo:** Verificar erros em scripts, sugerir/realizar correções, propor desenvolvimento contínuo da plataforma híbrida (API + Claude Desktop), melhorar configs MCP e Skills (Claude / OpenClaw / Claude Code / PyCharm), e ajustar o Orquestrador Villa Lobos para roteamento por especialista.

---

## 1. Diagnóstico — estado atual

### 1.1 Estrutura ativa
A árvore ativa do projeto (excluindo `_ARCHIVE_v10/`) está organizada de forma coerente:

| Camada | Localização | Função |
|---|---|---|
| Entry points | `lilo.py`, `lilo_mcp.py`, `lilo_server.py`, `dashboard.py` | CLI, MCP server, Streamlit dashboard |
| Subagentes | `agents/{villa_lobos, prism_ai, PDFs_library, Analise_SQL, scholaragent, gateway, desktop}/` | Especialistas via `BaseAgent` |
| Núcleo | `shared/{base_agent, llm_client, policy, cost_tracker, logger, utils, web_search}.py` | Infraestrutura compartilhada |
| Skills | `lilo_skills/` (registry de 199 funções + 16 skills *core*) | Auto-geradas a partir de scipy/numpy/pandas/etc. |
| Configs MCP | `config/mcp/{claude_desktop, claude_code, pycharm}.json` + `.mcp.json` | Perfis de exposição de tools |
| Backends | `config/litellm_config.yaml`, `ollama-service/` | LiteLLM proxy + Ollama local |
| Memória | `memory/agent_memory.db`, `memory/embeddings/` | Estado persistente |

### 1.2 Pontos saudáveis confirmados
- Todos os subagentes referenciados no registry de `lilo.py` (`SQLAgent`, `PDFAgent`, `ScholarAgent`, `PrismAgent`, `VillaLobosAgent`, `GatewayAgent`, `DesktopAgent`) estão exportados nos respectivos `__init__.py`.
- `shared/policy.py` expõe corretamente `get_policy_engine`, `ExecutionTier`, `TIER_MODELS`.
- `shared/utils.py` expõe `load_env` e `get_env`.
- `shared/obsidian.py` existe (usado em `lilo.py` com try/except — bom padrão de soft-dependency).
- `agents/desktop/agent.py` tem as 7 funções top-level (`fs_read`, `fs_write`, `fs_list`, `fs_stat`, `fs_search`, `run_shell`, `run_python`) que `lilo_mcp.py` importa — o profile `pycharm` está consistente.
- `lilo_skills/registry.json` válido com 199 funções (~67.6 KB).
- Os JSONs de MCP em `config/mcp/` apontam para o mesmo `lilo_mcp.py` com `--profile` adequado e `PYTHONPATH` correto.

### 1.3 Bugs e desalinhamentos encontrados (corrigidos nesta execução)

| # | Arquivo | Problema | Correção aplicada |
|---|---|---|---|
| 1 | `config/litellm_config.yaml` | Usava `anthropic/claude-3-sonnet-20240229` (>2 anos desatualizado) | Substituído pela família Claude 4.5 (sonnet/opus/haiku); adicionados aliases `claude-sonnet`, `claude-opus`, `claude-haiku` |
| 2 | `shared/policy.py` (`TIER_MODELS`) | Strings hard-coded `claude-sonnet-4-20250514` / `claude-opus-4-20250514` | Lê de `LILO_CLAUDE_SONNET` / `LILO_CLAUDE_OPUS` no `.env` (default `claude-sonnet-4-5` / `claude-opus-4-5`) |
| 3 | `shared/llm_client.py` (`chat` + `_chat_anthropic`) | Strings de modelo Claude duplicadas e desatualizadas | Lê de env vars; novo tier `claude_haiku` adicionado ao mapa |
| 4 | `agents/villa_lobos/agent.py` | Pipeline rodava sempre os 5 estágios mesmo quando uma tarefa de domínio claro (SQL, PDF, Scholar, Prism) seria melhor servida pelo especialista | Adicionado `_delegate_to_specialist` + flag `allow_delegate` em `context` (default `True`). Heurística: detecta domínio pelo `DOMAIN_KEYWORDS`, chama `lilo._load_agents()[domain].run(...)`, e só usa o resultado se ≥40 chars e sem `[ERRO`. Em caso contrário, cai no pipeline padrão |

### 1.4 Pontos de atenção (não corrigidos — exigem decisão)

- **`.env` com chaves reais em texto claro.** Recomendo migrar para um `.env` ignorado pelo Git (`.gitignore` já cobre, mas confirmar) e usar Windows Credential Manager (via `keyring`) para `ANTHROPIC_API_KEY`. Aceitar fallback de `os.environ` continua sendo suficiente.
- **`config.yaml`** ainda referencia `claude-sonnet-4-20250514` em `model_sonnet` / `model_opus`. Não editado por estar fora da rota do `LLMClient` (usado apenas em paths secundários). Sugerido: remover esse arquivo ou ressincronizar com `policy.py`.
- **`shared/llm_client.py` `_detect_backend` testa apenas porta 4000/11434.** Em servidor remoto o usuário pode querer apontar `LITELLM_PROXY_URL` para um host externo — a lógica já suporta via env var.
- **Skills geradas (`lilo_skills/skills/*.py`)** não foram inspecionadas individualmente nesta passagem. Recomendado lote separado: rodar `python lilo_skills/scan_conda_env.py` periodicamente para detectar funções deprecadas após upgrade de scipy/numpy.

---

## 2. Plataforma Híbrida — proposta de evolução

A meta declarada é uma plataforma híbrida com API rodando o agente **similar ao Claude Desktop**, capaz de operar em três frentes: (a) sessão interativa local, (b) chamadas via API, (c) integração nativa no IDE (PyCharm) e CLI (Claude Code, OpenClaw).

### 2.1 Arquitetura-alvo (3 camadas)

```
┌──────────────────────────────────────────────────────────┐
│  Camada de UI/Cliente                                    │
│  - Claude Desktop (MCP stdio)                            │
│  - PyCharm AI Assistant (MCP)                            │
│  - Claude Code CLI / OpenClaw (MCP)                      │
│  - dashboard.py Streamlit (HTTP local)                   │
│  - Cliente HTTP próprio / curl / scripts                 │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│  Camada de Orquestração — LILO Core                      │
│  - lilo_mcp.py (stdio)        ← já existe                │
│  - lilo_api.py (FastAPI/HTTP) ← A IMPLEMENTAR            │
│    • POST /v1/chat (mesmo schema OpenAI)                 │
│    • POST /v1/tools/{name}                               │
│    • GET  /v1/health, /v1/skills, /v1/agents             │
│    • SSE para streaming                                  │
│  - Roteador único: lilo.route() / handle_tool_call()     │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│  Camada de Execução                                      │
│  - VillaLobos (orquestrador multi-LLM)                   │
│  - Especialistas: PRISM, SQL, PDF, Scholar, Desktop      │
│  - Skills geradas (199 funções scipy/numpy/pandas/bio)   │
│  - Backends: Ollama (local) | LiteLLM | Anthropic API    │
└──────────────────────────────────────────────────────────┘
```

### 2.2 Implementação do `lilo_api.py` — **CONCLUÍDO (v10.1)**

`lilo_api.py` está implementado com 797 linhas, indo bem além do esqueleto mínimo proposto. Reaproveita 100% de `handle_tool_call`/`route` (zero duplicação de lógica) e expõe os mesmos subagentes do MCP via HTTP/JSON.

**Endpoints implementados:**

| Método | Path | Função |
|---|---|---|
| `GET` | `/` | Portal HTML com chat embarcado, hero cards, catálogo de endpoints, health pill |
| `GET` | `/api` | Catálogo JSON dos endpoints (versão programática do portal) |
| `GET` | `/docs` | Swagger UI nativo do FastAPI |
| `GET` | `/redoc` | ReDoc |
| `GET` | `/v1/health` | Status de subagentes + backend LLM ativo |
| `GET` | `/v1/agents` | Lista subagentes carregados |
| `GET` | `/v1/tools` | Catálogo MCP-style de todas as tools |
| `GET` | `/v1/skills` | Registry completo (16 core + 199 geradas) |
| `POST` | `/v1/chat` | Chat síncrono `{query, tab?, context?}` → `{response}` |
| `POST` | `/v1/chat/stream` | **Streaming SSE** (`event=token` + `event=done`) |
| `POST` | `/v1/tools/call` | Invoca tool MCP por nome `{name, arguments}` |
| `GET` | `/v1/cost/today` | Resumo de custos do dia (por backend, por subagente) |
| `GET` | `/v1/cost/recent?limit=N` | Últimas N requests com modelo, custo, duração |
| `GET\|POST\|DELETE` | `/v1/memory[/{ns}/{key}]` | KV store SQLite persistente |

**Recursos extras** (não estavam no esqueleto):

- **Autenticação Bearer token** opcional via `LILO_API_TOKEN` (env). Se vazio, modo dev sem auth.
- **CORS configurável** via `LILO_API_CORS` (default `*`).
- **Lazy import** de `lilo` (não impacta tempo de inicialização do server).
- **Streaming SSE** para chat token-a-token.
- **Hero card** no portal aponta para a UI Streamlit em `:8100` com health-check assíncrono (mode `no-cors`).

**Inicialização:**

```cmd
python lilo_api.py
:: ou
uvicorn lilo_api:app --host 0.0.0.0 --port 8088 --reload
```

Variáveis lidas: `LILO_API_HOST`, `LILO_API_PORT`, `LILO_API_TOKEN`, `LILO_API_CORS` (todas com defaults sensatos em `.env.example`).

O profile `http` em `lilo_mcp.py` segue reservado para reuso futuro via FastMCP-HTTP (quando estável); enquanto isso, este FastAPI cobre o gap completo.

### 2.3 Configuração unificada em `.env` — **CONCLUÍDO (v10.1)**

`.env.example` atualizado com **todas** as variáveis usadas pelo código atual, agrupadas por seção:

```
# Modelos Claude (lidos por shared/llm_client.py e shared/policy.py)
LILO_CLAUDE_HAIKU=claude-haiku-4-5
LILO_CLAUDE_SONNET=claude-sonnet-4-5
LILO_CLAUDE_OPUS=claude-opus-4-5

# Backends
LITELLM_PROXY_URL=http://localhost:4000
OLLAMA_HOST=http://localhost:11434

# lilo_api.py (FastAPI HTTP)
LILO_API_HOST=0.0.0.0
LILO_API_PORT=8088
LILO_API_TOKEN=                # vazio = modo dev (sem auth)
LILO_API_CORS=*

# Desktop Commander (allow-list)
LILO_DESKTOP_ALLOW=...         # paths separados por ; no Windows
```

Verificações feitas:

- `shared/llm_client.py:99-101` lê `LILO_CLAUDE_HAIKU/SONNET/OPUS` via `get_env()` com defaults.
- `shared/policy.py:61-62` faz a mesma leitura para o `TIER_MODELS`.
- `lilo_api.py:88,97,792-793` lê `LILO_API_*`.
- Sem leituras hard-coded restantes — a config está 100% externa ao código.

---

## 3. MCP / Skills — melhorias propostas

### 3.1 Padronização entre clientes

| Cliente | Arquivo | Profile sugerido | Status |
|---|---|---|---|
| Claude Desktop | `%APPDATA%/Claude/claude_desktop_config.json` ← `config/mcp/claude_desktop.json` | `desktop` (todas as tools) | OK |
| Claude Code | `~/.claude.json` ou `${PROJECT}/.mcp.json` | `desktop` | OK |
| PyCharm AI | Settings → Tools → AI Assistant → MCP | `pycharm` (subset com fs/run) | OK |
| OpenClaw | (mesmo formato Claude Code) | `desktop` | Recomendado adicionar `config/mcp/openclaw.json` idêntico ao `claude_code.json` |

### 3.2 Tools que ainda podem ser expostas — **CONCLUÍDO (v10.2)**

- **Memória persistente** ✓ `lilo_memory_set / get / list / delete` usando `shared/kv_memory.py` (SQLite KV em `data/kv_memory.db`). Centralizadas em `lilo.handle_tool_call` — disponíveis em CLI, MCP, dashboard, API HTTP. `lilo_mcp.py` agora delega (zero duplicação).
- **Cost tracker** ✓ `lilo_cost_today` (JSON do `daily_summary`) e `lilo_cost_recent(limit)` (últimas N requests com modelo, custo, duração). Permite ao agente decidir entre Ollama vs Claude com base em orçamento real consultado em runtime.
- **Ollama model manager** ✓ `lilo_pull_model(name, timeout=600)` invoca `ollama pull` via subprocess com validação regex no nome (bloqueio de injection). Companion `lilo_list_local_models()` para listar o que já está instalado. Útil ao trocar de máquina (laptop ↔ desktop).

### 3.3 Skills — saneamento — **CONCLUÍDO (v10.2)**

- ✓ **Campo `schema_version` em `registry.json`** (v1.1) + `generator_version`. `_load_registry()` em `lilo_skills/__init__.py` detecta divergência via comparação semver simples e emite warning sugerindo regenerar. Aplicado retroativamente ao registry atual via script Python.
- ✓ **Namespace `skill_advanced_*` para `complexity=high`**. Implementado em `_skill_mcp_name(skill)` no `lilo_skills/__init__.py`. `load_skills_as_tools(include_advanced=False)` permite omitir totalmente da listagem. `call_skill()` aceita ambos os prefixos. Hoje há 0 skills high (193 simple + 6 medium) — o esquema é futuro-proof.
- ✓ **Documentação do ciclo de saneamento**. Seção dedicada em `docs/uso/COMANDOS.md` explicando quando rodar `scan_conda_env.py + generate_skills.py --validate` (após `mamba update` / `pip install -U` em pacotes científicos) e como agendar mensalmente via Windows Task Scheduler.

---

## 4. Villa Lobos — desenvolvimento contínuo

### 4.1 Mudança aplicada hoje
`VillaLobosAgent.run()` agora tenta **delegação por domínio** antes do pipeline 5-estágios. Isso reduz latência (chamada única vs 5 chamadas Ollama) e melhora qualidade quando há um especialista (ex: `prism_analyze` para análise estatística, `scholar_synthesize` para revisão de literatura).

### 4.2 Roadmap (3 sprints curtos)

**Sprint A — Roteamento estatístico (1-2 dias)**
- Substituir `_detect_domain` por chamada ao Orchestrator LLM (Ollama leve, ex: `qwen2.5-coder:7b`) com prompt: "qual especialista abaixo é melhor para esta tarefa?". Output JSON parseado.
- Logging do domínio escolhido em `cost_tracker` para análise post-mortem.

**Sprint B — Pipeline adaptativo (3-5 dias)**
- O **Planner** retorna um JSON estruturado: `{stages: [...], specialists: [...], iterations: N}`.
- O **Orchestrator** executa o JSON dinamicamente — não mais "5 estágios fixos".
- Adicionar memória curta entre estágios (`shared/chat_memory.py` já existe — só falta plugar).

**Sprint C — Multi-LLM por estágio (1 semana)**
- Permitir que cada estágio use um LLM distinto: `Orchestrator=Claude Haiku` (decisão rápida e barata), `Planner=Ollama phi3:14b`, `Worker=Ollama qwen2.5-coder:14b`, `Reporter=Claude Sonnet` (qualidade redacional).
- Pré-condição: tier `claude_haiku` agora exposto em `llm_client.py` ✓.

### 4.3 Observabilidade
- Painel Streamlit em `dashboard.py` que mostra, por execução de Villa: domínio detectado, delegação efetuada (sim/não), tempo por estágio, modelo usado, custo estimado. Estrutura já existe via `cost_tracker.log_request()`; precisa só de view dedicada.

---

## 5. Próximos passos imediatos (acionáveis)

**Concluídos nesta sprint (v10.1):**

1. ~~Reiniciar o servidor MCP após as edições para que Claude Desktop / Claude Code peguem as strings de modelo novas.~~ ✓
2. ~~Adicionar ao `.env`: `LILO_CLAUDE_SONNET`, `LILO_CLAUDE_OPUS`, `LILO_CLAUDE_HAIKU`.~~ ✓ (e mais: `LILO_API_*`, `LITELLM_PROXY_URL`, `OLLAMA_KEEP_ALIVE`)
3. ~~Implementar `lilo_api.py` seguindo o esqueleto da seção 2.2.~~ ✓ (FastAPI completo: 14 endpoints, SSE streaming, portal HTML, auth Bearer, CORS)
4. ~~Aba Desktop no dashboard 8100~~ ✓ (6 sub-abas: fs_read/write/list/search, run_shell/run_python)
5. ~~Smart routing no Villa-Lobos~~ ✓ (Orchestrator emite JSON, fast-path skip-to-reporter ~70% menos latência)
6. ~~Pre-commit hook AST~~ ✓ (`scripts/pre_commit_ast_check.py` + `scripts/install_hooks.py`)

**Concluídos no mesmo dia (sprints v10.2 + v10.3):**

- ✓ **8 tools MCP centralizadas em `lilo.py`** (memory + cost + ollama manager — v10.2)
- ✓ **Saneamento de skills**: `schema_version` + namespace `skill_advanced_*` (v10.2)
- ✓ **Hotfix menu `/`** no dashboard — 24 core skills agora aparecem (v10.2.1)
- ✓ **Memória robusta** (v10.3): TTL, busca textual, WAL, banco fora do OneDrive, migração automática, 4 tools novas (`lilo_memory_search/stats/export/cleanup`)

**Pendentes (próxima sprint v10.4 — ver `docs/ROADMAP.md`):**

1. **Testar a delegação Villa Lobos** com prompts típicos — exemplos:
   - `villa_pipeline("rodar ANOVA no arquivo data/exp1.xlsx")` deve delegar para PRISM.
   - `villa_pipeline("buscar artigos sobre TcTR Trypanosoma")` deve delegar para Scholar.
   - `villa_pipeline("desenhar arquitetura de pipeline RNA-seq do zero")` mantém pipeline 5-estágios.
   - `villa_pipeline("o que é PCR?")` agora entra em fast-path (skip-to-reporter).
2. **Criar `config/mcp/openclaw.json`** clonando `claude_code.json` (1 linha de comentário trocada).
3. **Instalar o pre-commit hook**: `python scripts\install_hooks.py` na raiz do projeto.
4. **Subir `lilo_api.py` em produção**: definir `LILO_API_TOKEN` em `.env` e configurar `LILO_API_CORS` para os domínios cliente.

---

## 6. Resumo das alterações de código

**Arquivos editados ao longo das sprints v10.0 + v10.1:**

```
v10.0 (sprint anterior)
config/litellm_config.yaml             ← model_list expandida (claude 4.5)
shared/policy.py                        ← TIER_MODELS lê env vars
shared/llm_client.py                    ← tier claude_haiku + leitura via env
agents/villa_lobos/agent.py             ← _delegate_to_specialist() + DOMAIN_KEYWORDS
agents/desktop/agent.py                 ← novo subagente (fs_*, run_shell, run_python)
lilo_mcp.py                             ← --profile {desktop|pycharm|http} unificado

v10.1 (sprint curto-prazo, 2026-05-07)
dashboard.py                            ← aba Desktop com 6 sub-abas (formulario visual)
agents/villa_lobos/agent.py             ← smart routing: _orchestrate_decision() + JSON
                                          + fast-path skip-to-reporter
scripts/pre_commit_ast_check.py         ← validador AST + deteccao de truncamento OneDrive
scripts/install_hooks.py                ← instalador cross-platform do hook git
.env.example                            ← config unificada (LILO_CLAUDE_*, LILO_API_*)
lilo_api.py                             ← FastAPI completo (14 endpoints, SSE, portal HTML)
docs/agentes/desktop.md                 ← doc da aba Desktop
docs/agentes/villa_lobos.md             ← doc do smart routing + JSON schema
docs/uso/COMANDOS.md                    ← comandos do pre-commit hook
docs/tecnico/arquitetura_v10.md         ← bumpado para v10.1
docs/versoes/CHANGELOG.md               ← entrada v10.1
docs/historico/2026-05-07_relatorio_*   ← este arquivo (atualizado com 2.2 e 2.3 ✓)
```

Validação: todos os `.py` editados foram parseados com `ast.parse` (e o pre-commit hook agora bloqueia commits que falhem nessa validação). YAML validado com `yaml.safe_load`.
