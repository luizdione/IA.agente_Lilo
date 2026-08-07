# Auditoria LILO — 2026-08-06 (arch-v11)

Auditoria por fan-out (3 dimensões: bugs, código morto/redundância, docs/deps/segurança),
verificada com `arquivo:linha` + AST/pyflakes. Diagnóstico completo nos transcricts; abaixo
o que foi **aplicado e testado** e o que **precisa de decisão/teste**.

## Aplicado e testado (2026-08-06)

| # | arquivo | correção | teste |
|---|---|---|---|
| Bug CRÍTICO | `agents/villa_lobos/agent.py:1366` | Removida a mutação `self.client._backend="mock"` — envenenava o singleton do processo inteiro (todos os agentes viravam MOCK até restart) a partir de um `ModuleNotFoundError` local. O circuito local `_circuit_open` já protegia. | py_compile |
| Gap Parte B | `shared/llm_client.py:_route_by_cost` | Passa a respeitar o **Portão B** (`server_profile.allow_cloud`): perfis `bio`/`cowork` (local-only) não vazam mais para Claude via cost-routing. | testado: query crítica em perfil local-only → rebaixa `claude_opus`→`ollama` |
| Bug médio | `lilo_api.py` (3 endpoints) | `get_chat_memory` (inexistente) → `get_memory`. Os 3 endpoints `/v1/sessions*` sempre caíam no `except` silencioso e reconstruíam `ChatMemory()` a cada request. | import OK |
| Bug baixo | `shared/cost_tracker.py:_init_db` | `PRAGMA journal_mode=WAL` + `busy_timeout` — evita perder telemetria de custo por "database is locked" sob concorrência. | py_compile |
| Doc | `lilo_skills/skills/lilo_models/SKILL.md` | Instruía editar `MODELS` em `llm_client.py` (no-op silencioso). Corrigido para a fonte única `shared/models.py` / `.env`. | — |
| Doc | `CLAUDE.md:49` | Afirmava que `run_shell` respeita a allow-list de caminhos; na verdade só valida `cwd`. Corrigido (blocklist + exec_mode). | — |

## Precisa de decisão/teste (NÃO aplicado)

### CRÍTICO — 1 linha, mas muda o roteamento core
- **`agents/villa_lobos/agent.py:1353`** — usa `tier=tier` (cru, sempre `None`) em vez do
  `effective_tier` calculado na linha 1283. Quando Ollama/LiteLLM caem e há
  `ANTHROPIC_API_KEY`, **todo stage do Villa passa a usar Claude pago silenciosamente**,
  contornando o duplo-gate `LILO_ALLOW_CLOUD_FALLBACK` + `policy.allow_cloud`.
  **Correção:** `tier=tier` → `tier=effective_tier`. **Risco:** médio — força Ollama nos
  stages; exige re-testar o circuito fallback local→cloud com o pipeline Villa (Ollama
  up/down). Por isso não apliquei sem você poder rodar o pipeline.

### ALTO — decisão de design
- **`lilo.py:145-287`** — a Policy Engine é **decorativa**: grava `ctx["_tier"]`/`_model`
  que nenhum agente lê (0 ocorrências no repo). Custo estimado (`decision.estimated_cost`)
  fica desconectado do gasto real → dashboard de custo não confiável. Decisão: (a) fazer
  os `run()` dos agentes honrarem `ctx.get("_tier")`, ou (b) remover a policy do caminho e
  depender só do `_route_by_cost` opt-in (preservando o retry-em-exceção da linha 264-275).
- **Taxonomia de keywords divergente** — `_detect_domain` (`agent.py:235-255` +
  `config/villa/domains.yaml`) roda em paralelo a `capabilities().keywords` e **já
  divergem** (`postgres`/`duckdb` só num lado; `query sql` só no outro). Muda qual agente
  atende a query. Decisão: unificar a fonte.

### Remoções seguras (baixo risco — aguardando seu OK para aplicar)
- **`villa_route`** (`lilo_mcp.py:1226-1246`) — redundante com `villa_explain_routing`
  (mesmo `explain_routing()`); não exposto em nenhum perfil, não coberto por teste.
- **`config.yaml.example`** — arquivo órfão inteiro (nenhum código carrega; caminhos
  obsoletos). Remover ou marcar como legado.
- **Env vars vestigiais** no `.env.example`: `OPENAI_API_KEY`, `LILO_VERSION`, `DEBUG` (0 usos).
- **3 `requirements.txt` órfãos**: `agents/scholaragent/` (flask/werkzeug),
  `agents/PDFs_library/` (faiss-cpu), `agents/Analise_SQL/` (customtkinter/mysql/…).

### Latente / baixo
- **`agents/desktop/composed.py:152-186`** (`process_run_and_wait`) executa shell sem os
  gates de `run_shell` (`_is_git_write` + `exec_mode`). Hoje **não exposto** em nenhum
  perfil MCP (código morto), mas é armadilha se religado.
- **Singletons `get_*` sem lock** — race benigna de dupla-construção sob threadpool.
- **`run_shell` exec_mode=`auto` default** — sem confirmação; considerar `ask` no perfil
  `claude_desktop`/`opus` que expõe `run_shell` a um LLM.

## Sem achado (verificado)
Segredos versionados: nenhum (`.env` protegido, nunca no git). `_AGENT_REGISTRY`: 10/10
íntegro. Módulos órfãos em `shared/`/`agents/`: nenhum.

## Nota — Parte A (toolbox) revertida
A auditoria de código morto encontrou o registry de skills 12/12/12 íntegro, mas ao
cruzar com a **memória do projeto** descobriu-se que a Parte A (import das skills do
Claude) reintroduziu **IP de artigo purgado** (`build_paper`/`auditoria_paper`/etc.). Foi
**revertida** — ver `docs/PLANO_toolbox_roteamento_custo_2026-08-06.md`. Achado colateral,
**decisão do autor**: os wrappers/schemas de `bibref`, `check_integrity`, `git_check_clean`,
`git_sync`, `montar_raw_data` **já estavam trackeados antes** desta sessão (a purga removeu
as pastas de código-fonte, não os wrappers flat). Se a intenção é IP 100% fora do git,
esses resíduos pré-existentes também precisam sair do tracking + entrar no `.gitignore`.
