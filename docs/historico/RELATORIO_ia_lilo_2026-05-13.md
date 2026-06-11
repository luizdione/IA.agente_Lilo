# Relatorio ia_lilo -- 2026-05-13 (auto)

**Tarefa agendada:** `ia_lilo`
**Modo:** execucao autonoma (usuario ausente)
**Escopo:** verificar erros em scripts; propor/implementar correcoes; sugerir desenvolvimento continuo da plataforma hibrida (API + agente tipo Claude Desktop); melhorar MCP/Skills para Claude Desktop, OpenClaw, ClaudeCode e PyCharm; ajustar Villa_Lobos como orquestrador LLM chamando agentes especializados conforme setup do servidor.

---

## 1. Resumo executivo

* **1 bug critico de sintaxe** detectado em `shared/kv_memory.py` -- bloqueava `import shared.kv_memory` em qualquer codigo dependente -- **corrigido**.
* **AST scan completo** (49 arquivos `.py` ativos, excluindo `_ARCHIVE_v10`, `obsoletos`, `__pycache__`): apos a correcao, **zero erros de sintaxe**.
* **Smoke test (`scripts/smoke_test_v11.py`):** 13/13 verificacoes passam apos as correcoes.
* **Docstring desatualizada em `lilo.py`** (afirmava 4 subagentes; existem 7 ativos) -- **atualizada**.
* **`health_check()` aprimorado**: passa a exibir backend LLM ativo (`litellm | ollama | anthropic | mock`) e detalhes (`url`, `default_model`) no topo do relatorio.
* **Roadmap de desenvolvimento continuo** consolidado abaixo nas secoes 4-7.

---

## 2. Correcoes aplicadas nesta execucao

### 2.1 `shared/kv_memory.py` -- SyntaxError linha 402

**Sintoma**
```
SyntaxError: unindent does not match any outer indentation level (line 402)
```
O bloco singleton estava triplicado e duas das copias tinham `# -- Singleton --` sem o `#` inicial, virando codigo invalido.

**Causa provavel**
Edicao manual / merge que repetiu o trecho final do arquivo e perdeu o `#` do comentario.

**Fix**
Truncado o arquivo no final do primeiro bloco singleton (linha 401) preservando exatamente:
```python
# -- Singleton -----------------------------------------------------------------
_instance: Optional[KVMemory] = None

def get_memory() -> KVMemory: ...
def reset_singleton() -> None: ...
```

**Validacao**
* `ast.parse()` retorna OK.
* `import shared.kv_memory` e `KVMemory().set/get` funcionam (smoke test 02).

### 2.2 `lilo.py` -- docstring 4 agentes -> 7 agentes

Atualizado o docstring de cabecalho de `lilo.py` para listar os 7 subagentes efetivamente registrados em `_AGENT_REGISTRY` (`sql`, `pdf`, `scholar`, `prism`, `villa`, `gateway`, `desktop`).

### 2.3 `lilo.py:health_check()` -- exibe backend LLM

Antes:
```
ok **gateway**: ok
```

Agora:
```
**LLM backend**: anthropic (api-key configurada | model=llama3.1:8b-instruct-q8_0)

ok **gateway**: ok
...
```

Util para diagnosticar rapidamente se Ollama caiu ou se LiteLLM nao subiu, sem precisar inspecionar manualmente `shared/llm_client.py`.

---

## 3. Estado atual da plataforma (snapshot)

| Camada | Componente | Status |
|---|---|---|
| **Orquestrador** | `lilo.py` (CLI + import) | OK (7 agentes carregam) |
| | `agents/villa_lobos/agent.py` (5-stage) | OK (V7 explain_routing) |
| | `shared/policy.py` (cost tier) | OK |
| **Servidores** | `lilo_mcp.py` (FastMCP, stdin/stdout) | OK (Claude Desktop, PyCharm) |
| | `lilo_server.py` (HTTP MCP) | OK (Cowork) |
| | `lilo_api.py` (FastAPI/SSE) | OK (opcional, 8088) |
| **UI** | `dashboard.py` (Streamlit, 8100) | OK |
| | `agents/PDFs_library` webapp (8101) | OK |
| **Memoria** | `shared/kv_memory.py` (SQLite KV) | OK (apos fix 2.1) |
| | `shared/chat_memory.py` | OK |
| | `memory/agent_memory.db` (~80 MB) | sem backup automatico |
| **Backends LLM** | Anthropic (chave ativa) | configurado |
| | Ollama local (11434) | usado em modo barato |
| | LiteLLM proxy (4000) | opcional |
| **MCP profiles** | `config/mcp/{claude_desktop,claude_code,pycharm,bio,openclaw}.json` | OK |
| **Testes** | `scripts/smoke_test_v11.py` | 13/13 OK |
| **CI / lint** | nenhum | LACUNA |

---

## 4. Roadmap -- plataforma hibrida (API + Desktop)

Objetivo: empacotar LILO como um produto local "Claude Desktop-like" + endpoint HTTP que outros clientes (PyCharm, OpenClaw, ClaudeCode, scripts batch) consomem com o mesmo set de ferramentas.

### Fase A -- consolidacao (curto prazo, 1-2 semanas)

1. **Empacotar `lilo_api.py` + `lilo_mcp.py` como servico unico** com flag `--transport {stdio,http,sse}` (`uvicorn`-based). Hoje sao tres entry points; um `lilo_serve` unico simplifica deploy.
2. **Health endpoint padronizado** -- `/health` JSON que reusa o `health_check()` recem-ampliado. Permite que o Streamlit/Front exiba semaforo verde/vermelho.
3. **Backup automatico do `memory/agent_memory.db`** via `kv_memory.export_json()` em diretorio rotativo (7 dias). Crontab/agendamento ja existente da pasta `scripts/`.
4. **Auto-detect Ollama na partida**: helper `shared/llm_client.LLMClient.health()` ja faz a sonda; logar "WARN: Ollama indisponivel, usando anthropic" 1x no boot ao inves de propagar erro tardio.

### Fase B -- desktop-like UX (medio prazo, 3-6 semanas)

5. **Frontend Tauri/Electron** consumindo `lilo_api.py` via SSE. Reaproveita o React em `_ARCHIVE_v10/v6_fastapi/frontend` como ponto de partida (mas refatorar contra a API atual).
6. **Conta de uso** integrado ao `shared/cost_tracker.py` -- painel "tokens hoje", "USD hoje", por agente, ja exposto via `lilo_cost_today`/`lilo_cost_recent`.
7. **Permission gating** estilo Claude Desktop -- adapter sobre `agents/desktop/agent.py` que exige confirmacao do usuario antes de cada `fs_write`/`fs_codemod`. Aproveitar o allow-list ja implementado.

### Fase C -- ecossistema (longo prazo)

8. **Plugin marketplace local** -- pasta `lilo_skills/` ja gera skills a partir do conda env. Formalizar manifest `.lilo-plugin.json` (analogo aos `.plugin` do Cowork) para terceiros adicionarem MCPs.
9. **Multi-tenant** -- segregar `kv_memory` por `user_id` (hoje e single user). Coluna `user` ja existe no schema, basta expor.

---

## 5. Roadmap -- MCP & Skills (Claude Desktop / ClaudeCode / OpenClaw / PyCharm)

### 5.1 Perfis MCP

O projeto ja mantem `config/mcp/*.json`. Plano:

* **claude_desktop.json** (perfil `opus`, 18 tools, 2400 tokens overhead) -- **mantido como default**. Bom equilibrio.
* **claude_code.json** -- full set; manter como esta.
* **pycharm.json** -- recomendado **reduzir ainda mais** (PyCharm faz tab-completion frequente, contexto pesa). Sugerir set <=10 tools: `sql_query`, `pdf_summarize`, `villa_explain_routing`, `lilo_memory_*`, `lilo_health`.
* **openclaw.json** -- alinhar set as ferramentas que OpenClaw realmente consome; revisitar com smoke test.
* **bio.json** -- atualmente 27 tools sem `run_shell`. Sugerir adicionar `prism_*` (ja exposto) e `scholar_synthesize` para nichar para biologia molecular.

### 5.2 Skills

* **Atualmente** `lilo_skills/` cria registry JSON a partir do conda env. **Lacuna**: nao ha `SKILL.md` por skill -- LLMs/Claude que esperam o formato Anthropic Skills nao conseguem descobrir.
* **Acao**: gerar `lilo_skills/<nome>/SKILL.md` com front-matter (`name`, `description`, `triggers`) a partir do registry. Permite reusar em ClaudeCode e Cowork.

### 5.3 Tool naming

Padronizar prefixos: `lilo_*` para introspeccao, `villa_*` para orquestrador, `<dominio>_*` para subagentes (`sql_`, `pdf_`, `scholar_`, `prism_`). Hoje ja segue isso na maioria; auditar `lilo_mcp.get_tool_map()` periodicamente.

### 5.4 Telemetria

Aproveitar o `cost_tracker` por **tool call** (nao so por sessao) -- inserir hook no `lilo_mcp.py` que loga o nome da tool antes de invocar `route()`. Habilita dashboards do tipo "tool mais cara da semana".

---

## 6. Roadmap -- Villa_Lobos como orquestrador LLM

Hoje o Villa_Lobos e um pipeline 5-stage (`plan -> read -> work -> report`) que ja roteia por dominio (`domains.yaml`) e tem `explain_routing` (V7). Para evoluir como "LLM-orchestrator chamando subagentes especializados conforme setup do servidor":

### 6.1 Curto prazo

1. **Server profile detection** -- ler `config.yaml` no boot e expor `lilo_server_profile` (ex: `desktop_dev`, `pycharm_assistant`, `claude_desktop`, `cowork`). Villa usa esse profile para decidir delegacoes.
2. **Capability registry** -- cada subagente expoe um manifesto `capabilities()` (ja existe `health()`); Villa consulta para decidir delegacao em vez de keyword matching duro.
3. **Delegate tool** -- Villa deveria poder chamar **outros agentes via MCP** (nao so via import). Permite split horizontal (agente PDF rodando em outra maquina).

### 6.2 Medio prazo

4. **LLM-as-router** -- alem do `_detect_domain()` heuristico, ter um **prompt classificador curto** (`llama3.1` local) que decide `tool_to_call` quando keyword match falhar. Acrescentar `policy.tier="ollama_fast"` para essa decisao -- custo zero.
5. **Stage-level retries com fallback** -- ja existe telemetria stage-level; falta wiring para retry com modelo mais caro (`ollama -> claude_sonnet -> claude_opus`) quando stage retorna erro.
6. **Cache semantico** -- LRU atual cacheia por `(query, profile)` exato; substituir por embedding-based (cosine) usando `shared/embeddings` se existir, ou adicionar `sentence-transformers`.

### 6.3 Longo prazo

7. **Multi-agent simultaneo** -- hoje Villa serializa (Worker apos Reader). Para tarefas "compare paper X e SQL Y", paralelizar Worker chamando 2 subagentes concorrentemente (`asyncio.gather`).
8. **Self-reflection** -- Reporter avalia se Worker output atende a query; se nao, re-prompt com feedback. Ja existem hooks de `iterations` no `villa_pipeline()`.

---

## 7. Lacunas / debitos tecnicos identificados

| Item | Severidade | Sugestao |
|---|---|---|
| Sem testes unitarios | media | comecar com `pytest` em `shared/` (deterministico, sem LLM) |
| Sem CI | media | GitHub Actions: smoke_test + AST scan em push para `main` |
| Sem lint | baixa | `ruff` minimo (linha-comprimento + imports) |
| `memory/agent_memory.db` sem backup | media | cron diario chamando `kv_memory.export_json()` |
| Pasta `obsoletos/` polui o repo | baixa | mover para `_ARCHIVE_v11/` ou apagar apos checklist |
| Docstrings inconsistentes entre lilo.py e README | baixa | ja corrigido em lilo.py; alinhar README na proxima iteracao |
| OneDrive race (descrito abaixo) | baixa | considerar mover repo para fora de OneDrive, ou usar `.git`-only sync |

**Nota operacional sobre OneDrive**: durante esta execucao, edicoes via tool de arquivos sofreram truncamento intermitente porque o repo vive em `C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente`. OneDrive faz upload incremental e janela pequena de inconsistencia gera arquivos com final cortado. Recomendacao: mover repo para `C:\dev\IA.agente` (fora do OneDrive) e usar Git para sincronizacao.

---

## 8. Validacao final

Comandos executados:

```bash
# 1) AST scan completo
python -c "import ast,os; ..."   # 49 arquivos, 0 erros

# 2) Smoke test
python scripts/smoke_test_v11.py # 13/13 OK

# 3) Health check com nova saida
python -c "from lilo import health_check; print(health_check())"
# >> LLM backend: anthropic (api-key configurada | model=...)
# >> ok sql, pdf, scholar, villa, gateway, desktop
# >> degraded prism  (deps cientificas faltando no ambiente de teste)
```

---

## 9. Proxima execucao recomendada

1. Adicionar `pytest` minimo em `tests/shared/test_kv_memory.py` (regressao do bug 2.1).
2. Mover repo para fora do OneDrive.
3. Implementar Fase A do roadmap (servico unico + health endpoint + backup memoria).
4. Gerar `SKILL.md` por skill em `lilo_skills/`.
5. Implementar capability registry no Villa_Lobos.

---

_Relatorio gerado automaticamente via tarefa agendada `ia_lilo` em 2026-05-13._
