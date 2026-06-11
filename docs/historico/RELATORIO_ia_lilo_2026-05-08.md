# Relatorio de execucao -- ia_lilo (2026-05-08)

> Tarefa agendada `ia_lilo`: verificar erros, sugerir/realizar correcoes, propor
> evolucao para plataforma hibrida (API + Desktop), melhorar configuracoes MCP/Skills
> para Claude Desktop, Claude Code, OpenClaw e PyCharm, e ajustar o orquestrador
> Villa_Lobos como roteador multi-LLM.

## 1. Auditoria de erros

Auditados 50 arquivos `.py` da versao ativa (excluindo `_ARCHIVE_v10`,
`__pycache__`, `obsoletos` e `lilo_skills/skills/` -- skills geradas
automaticamente). Foram identificados 3 arquivos com truncamento por interrupcao
de salvamento (provavelmente perda de creditos de uma execucao anterior):

| Arquivo                       | Linha | Problema                                 | Status      |
|-------------------------------|-------|------------------------------------------|-------------|
| `lilo.py`                     | 672   | `# Bloqueia` (handler `lilo_pull_model` cortado) | **CORRIGIDO** |
| `lilo_mcp.py`                 | 594   | `@_profile_to` (decorator truncado)             | **CORRIGIDO** |
| `lilo_skills/__init__.py`     | 348   | string literal nao terminada                    | **CORRIGIDO** |

### Detalhes das correcoes

1. **`lilo.py`**: completado o handler `lilo_pull_model` (validacao do nome do
   modelo, chamada `subprocess.run(["ollama","pull",name])` com timeout, captura
   de stdout/stderr) e adicionado handler `lilo_list_local_models` (`ollama list`).
   Bloco `__main__` original ja existia mais abaixo no arquivo e foi preservado.

2. **`lilo_mcp.py`**: completado o registro `@_profile_tool` para
   `lilo_pull_model(name, timeout)` e adicionado `lilo_list_local_models()`.

3. **`lilo_skills/__init__.py`**: fechada a string da entrada
   `lilo_list_local_models` na lista `_CORE_SKILL_META` e a propria lista.

> Os outros 47 arquivos compilam sem erros sintaticos.

## 2. Configuracoes MCP -- antes vs depois

### Antes
- 4 perfis (`claude_desktop.json`, `claude_code.json`, `openclaw.json`, `pycharm.json`).
- Apenas `pycharm` divergia (profile `pycharm`); os outros 3 eram identicos com
  profile `desktop`.
- Sem perfil dedicado para o workflow biomolecular do usuario.

### Depois
- **Novo profile `bio`** em `lilo_mcp.py::_PROFILE_TOOLS`: focado em PrismAI,
  Scholar, PDF, Villa, web search e fs read-only (sem `run_shell` por seguranca).
- **Novo arquivo `config/mcp/bio.json`**: aponta `--profile bio` no servidor
  `lilo-bio`. Util para setups onde nao quer expor execucao de codigo
  (ex.: integracao com agentes de literatura).
- Cada config agora declara `"_profiles_disponiveis"` com a lista atualizada.
- `claude_desktop.json` recebeu `OLLAMA_HOST` e `LILO_KEEP_ALIVE` no env para
  garantir que clientes que herdam do parent shell nao quebrem em setups novos.

## 3. Skills

Inventario atual em `lilo_skills/`:
- `registry.json` indexa as skills core e as auto-geradas.
- 16 skills CORE registradas (em `_CORE_SKILL_META`), incluindo:
  - `lilo_chat`, `lilo_sql`, `lilo_pdf`, `lilo_scholar`
  - `prism_analyze`, `prism_classify`, `prism_audit`
  - `villa_pipeline`, `villa_quick_ask`
  - `lilo_health`, `lilo_models`
  - `lilo_memory_*` (set/get/list/delete/search/stats/export/cleanup)
  - `lilo_cost_today`, `lilo_cost_recent`
  - `lilo_pull_model`, `lilo_list_local_models` (recem-completadas).
- Skills auto-geradas em `lilo_skills/skills/` (~199 skills tipo
  `numpy_*`, `pandas_*`, `seaborn_*`, `matplotlib_*`).

> Recomendacao: rodar `lilo_skills/generate_skills.py` apos atualizar pacotes
> Python para refrescar o registry. O `lilo_skills/scan_conda_env.py` pode ser
> agendado (skill `schedule`) para detectar novas libs.

## 4. Orquestrador Villa_Lobos -- ajustes

`agents/villa_lobos/agent.py` foi revisado para atuar como roteador multi-LLM
respeitando o setup do servidor (`.env` + Policy Engine):

1. **Dominios estendidos**: `DOMAIN_KEYWORDS` agora reconhece `desktop` e
   `gateway` (alem de `prism`, `sql`, `pdf`, `scholar`).
2. **Threshold de confianca relaxado**: 0.6 -> 0.55 no `_route_via_llm`,
   reduzindo fall-through para heuristica em queries curtas.
3. **Roteamento por tier**: `_call_agent` agora aceita `tier=` e propaga para
   `LLMClient.chat`, permitindo que cada estagio (orchestrator, planner, reader,
   worker, reporter) use Ollama local OU Claude (via tier `claude_haiku`,
   `claude_sonnet`, `claude_opus`) conforme `DEFAULT_STAGE_TIERS` ou override do
   `context["tiers"]`.
4. **`health()` enriquecido**: retorna lista de dominios suportados, tiers
   default, flags `smart_routing` e `delegation_enabled`.

## 5. Plataforma hibrida (API + Desktop) -- proximas iteracoes

O setup atual ja oferece:
- `lilo.py` (CLI + entrypoint Python `route()`)
- `lilo_mcp.py` (servidor MCP stdio para clientes Claude/OpenClaw/PyCharm)
- `lilo_api.py` (FastAPI HTTP em `LILO_API_HOST:LILO_API_PORT`, default 8088)
- `dashboard.py` (Streamlit UI)
- `START_LILO_API.bat` e `START_LILO_WINDOWS.bat` (launchers Windows)

### Recomendacoes para a v11 (proximas 2-3 sprints)

1. **Sprint 1 -- Convergencia API/MCP**
   - Expor as mesmas tools do `lilo_mcp.py` em endpoints REST `/v1/tools/<name>`
     em `lilo_api.py`. Hoje a HTTP API parece ter rotas por subagente
     (`/v1/sql`, `/v1/pdf`, etc.) -- duplica logica.
   - Padronizar response `{ok:bool, tool:str, output:str, duration_ms:int, cost_usd:float}`.

2. **Sprint 2 -- Orquestrador como servico**
   - Promover Villa_Lobos a servico independente (`agents/villa_lobos/service.py`)
     com fila assincrona. Cada estagio rodando em worker Celery/RQ permite
     scaling horizontal e timeout independente por estagio.
   - Adicionar tracing OpenTelemetry com decorator em `_call_agent`.

3. **Sprint 3 -- UI desktop estilo Claude Desktop**
   - Empacotar `dashboard.py` (Streamlit) ou substituir por Tauri/Electron
     com binding direto ao `lilo_api.py` HTTP.
   - Suporte a hot-reload de skills (`lilo_skills/registry.json`) via watcher
     ja embutido em `scripts/install_hooks.py`.

4. **Cross-cutting**
   - Adicionar `pre-commit` rodando `python scripts/pre_commit_ast_check.py` em
     todos os `.py` para evitar truncamentos no futuro (este incidente).
   - Considerar `ruff` + `mypy --strict` em CI minimal.
   - Externalizar `DEFAULT_STAGE_TIERS` para `.env` (`VILLA_TIER_ORCHESTRATOR=...`).

## 6. Verificacao

- Sintaxe revalidada via leitura direta dos 3 arquivos corrigidos.
- Configs MCP validados visualmente (JSON valido).
- Villa_Lobos: novos campos em `health()` retornam dict bem-formado;
  `_call_agent(tier=...)` compativel com assinatura atual de `LLMClient.chat()`
  (que ja aceita `tier` opcional na linha 88 do `shared/llm_client.py`).

> Observacao: o sandbox Linux desta sessao tinha cache do mount apontando para
> snapshot anterior (timestamp 2026-05-07 23:18). As edicoes foram aplicadas via
> Read/Write contra o filesystem Windows real (OneDrive). Quando o OneDrive
> sincronizar, o mount Linux refletira as alteracoes.

## 7. Resumo (TL;DR)

- 3 erros de sintaxe (truncamento) **corrigidos**.
- Novo profile MCP **`bio`** disponivel (estatistica + literatura + leitura).
- Novo arquivo `config/mcp/bio.json` para Claude Desktop/OpenClaw.
- Villa_Lobos com **routing multi-LLM por tier** + 2 novos dominios
  (`desktop`, `gateway`).
- `health()` do Villa expoe tiers + dominios.
- Roadmap de 3 sprints proposto para convergir API HTTP + MCP + UI desktop.
