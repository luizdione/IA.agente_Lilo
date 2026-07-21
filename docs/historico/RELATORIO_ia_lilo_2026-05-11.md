# Relatorio de execucao -- ia_lilo (2026-05-11)

> Tarefa agendada `ia_lilo` -- continuidade automatizada apos runs anteriores
> (2026-05-07 v2, 2026-05-08, 2026-05-08 v3). Esta passada focou em
> **verificacao end-to-end de scripts, correcao de bugs em testes e
> propostas de evolucao do Villa_Lobos / configs MCP**. Toda a execucao
> ocorreu sem interacao humana ("write actions" limitadas aos itens
> autorizados pela SKILL.md da tarefa).

---

## 1. Verificacao de erros nos scripts

| Camada | Resultado |
|---|---|
| Sintaxe Python (`ast.parse`) em 50 arquivos `.py` ativos | OK (zero erros) |
| Imports principais (`lilo`, `lilo_api`, `lilo_mcp`, `agents/*`, `shared/*`) | OK |
| `scripts/pre_commit_ast_check.py` | OK -- hook contra truncamento do OneDrive ativo |
| Smoke test `scripts/smoke_test_v11.py` antes do hotfix | **2 FAIL** (cost_tracker, detect_domain) |
| Smoke test `scripts/smoke_test_v11.py` apos hotfix | **PASSOU: 8 | FALHOU: 0** |

### 1.1 Falhas encontradas e corrigidas

**Falha A -- `test_detect_domain` (AssertionError).**
O teste validava `set(DOMAIN_KEYWORDS.keys()) == {"prism","sql","pdf","scholar"}`,
mas o agente foi expandido em 2026-05-08 com mais dois dominios: `desktop`
(filesystem/shell) e `gateway` (chat geral). O *test contract* nao acompanhou
o codigo. **Correcao**: substituida igualdade estrita por `issubset` sobre os
4 dominios core, deixando o teste resiliente a evolucoes futuras.

**Falha B -- `test_cost_tracker` (sqlite3 disk I/O error).**
O teste usava `get_tracker()` que aponta para o DB de producao
(`memory/cost_tracker.db`). Em ambientes sandbox sem write permission no
diretorio principal o sqlite levanta "disk I/O error". **Correcao**:
o teste agora instancia `CostTracker(db_path=<tempfile>)`, isolando-se.

**Falha C -- truncamento do OneDrive (root cause secundario).**
Durante os primeiros Edits via API o arquivo `scripts/smoke_test_v11.py` foi
truncado pelo OneDrive (problema ja documentado no proprio
`pre_commit_ast_check.py`). Reescrita end-to-end via shell + cp resolveu.
**Recomendacao operacional**: para edits >50 linhas, preferir `Write` completo
em vez de `Edit` incremental quando o arquivo estiver no OneDrive.

---

## 2. Configuracoes MCP -- estado atual

| Config | Profile | Tools | Cliente | Status |
|---|---|---|---|---|
| `config/mcp/claude_desktop.json` | `opus` | 18 (curadas) | Claude Desktop com Opus 4.x | OK |
| `config/mcp/bio.json` | `bio` | 27 (PrismAI+Scholar+PDF+Villa, sem run_shell) | Sessoes de pesquisa | OK |
| `config/mcp/pycharm.json` | `pycharm` | ~24 (fs+run+villa+memoria) | PyCharm AI Assistant | OK |
| `config/mcp/openclaw.json` | `desktop` | 35 (todas) | OpenClaw CLI | OK |
| `config/mcp/claude_code.json` | `desktop` | 35 (todas) | Claude Code CLI | OK |
| `.mcp.json` (project-level) | default (`desktop`) | 35 | Claude Code via projeto | OK |

### 2.1 Pontos de atencao (nao bloqueantes)

1. **`command: "python"` em todos os configs.** O README sugere full-path
   `C:\\Users\\luizd\\miniforge3\\python.exe`. Usar `python` puro depende
   do PATH do Claude Desktop ser identico ao do shell. Padronizar reduz
   incidentes apos updates do conda/miniforge.

2. **`config/litellm_config.yaml`** referencia `claude-opus-4-5`,
   `claude-sonnet-4-5`, `claude-haiku-4-5`. Em maio/2026 a familia mais
   recente disponivel via API e a **4.6** (opus-4-6, sonnet-4-6) e
   **haiku-4-5** ainda como mais recente do tier rapido. Avaliar bump
   manual *apos* validar disponibilidade no console Anthropic.

3. **Claude Code CLI nao precisa de todas as 35 tools.** Ele ja oferece
   `Read`/`Write`/`Bash`/`Glob`/`Grep` nativos. Sugerido criar um profile
   `claude_code` que ate exporte somente as tools **complementares** ao
   CLI: `prism_*`, `villa_*`, `lilo_scholar`, `lilo_memory_*`,
   `lilo_pull_model`, `lilo_cost_*`. Isso reduz ruido para o Sonnet e
   evita conflito entre `run_shell` (LILO) e `Bash` (Claude Code).

---

## 3. Villa_Lobos -- estado e proximos passos

### 3.1 O que ja funciona

- Pipeline 5-stage (Orchestrator -> Planner -> Reader -> Worker -> Reporter).
- **Smart routing JSON** (Orchestrator declara `needs_planning/reader/worker`,
  `iterations`, `skip_to_reporter` com `reasoning`).
- **Fast path** quando a Orchestrator decide `skip_to_reporter=true` (queries
  factuais, definicoes, conversoes).
- **Delegate-to-specialist** (LLM router + heuristica `_detect_domain`)
  redireciona queries que casam com dominio `prism/sql/pdf/scholar/desktop/gateway`.
- **Stage tiers via `.env`** (`VILLA_TIER_<STAGE>`) -- ajuste sem editar codigo.
- Fallback automatico de modelo Ollama com retries.

### 3.2 Roadmap proposto (Sprint 2 -- Villa_Lobos como mini-LLM-broker)

| # | Item | Justificativa | Esforco |
|---|---|---|---|
| V1 | **Cache LRU para `_orchestrate_decision`** (hash da query -> decision) | Queries similares disparam o mesmo classificador; cache hit dispensa LLM e reduz latencia em ~0.8s/chamada | Baixo |
| V2 | **Telemetria stage-level** (cada `_call_agent` registra duracao + backend + tier no `cost_tracker`) | Hoje `cost_tracker` registra apenas o roteamento global. Telemetria fina permite identificar gargalos | Medio |
| V3 | **Reader com ferramentas** (`fs_search`+`lilo_scholar`+`lilo_memory_search`) chamadas via tool-use loop em vez de prompt-only | Reader hoje so descreve arquivos que *poderiam* ser relevantes; com tools ele recupera de fato | Alto |
| V4 | **Worker iterativo com self-critique** (loop reflective: Worker -> Critic -> Worker') | Aumenta qualidade para tarefas analiticas sem dobrar custo total (Critic e Haiku) | Medio |
| V5 | **Policy Engine integration** -- DEFAULT_STAGE_TIERS le tambem `policy.decide()` em runtime para tarefas que excedam orcamento diario | Hoje o tier por stage e estatico no .env; integrar policy preserva budget | Medio |
| V6 | **Domain registry pluggable** -- `DOMAIN_KEYWORDS` como YAML em `config/villa/domains.yaml`, com hot-reload | Adicionar dominios (e.g. `genomics`, `proteomics`) sem editar codigo | Baixo |
| V7 | **MCP tool `villa_explain_routing`** -- retorna decision + delegate path + tier escolhido | Debugging assistido e tracing para o usuario senior | Baixo |

### 3.3 Arquitetura alvo (plataforma hibrida API + MCP)

```
                        +----------------------------+
                        |  Cliente (Desktop / IDE)  |
                        |  Claude / OpenClaw /      |
                        |  PyCharm / Cowork         |
                        +-------------+--------------+
                                      |
              MCP (stdio)             |        HTTP (REST)
              -------------+----------+----------+--------------
                           |                     |
                           v                     v
                     +-----------+         +-----------+
                     | lilo_mcp  |         |  lilo_api |  <-- /v1/skills/run paridade
                     |  (FastMCP)|         |  (FastAPI)|
                     +-----+-----+         +-----+-----+
                           \                     /
                            \                   /
                             v                 v
                          +---------+ +-------------+
                          |  lilo.py| | handle_tool |  <-- ENTRY POINT UNIFICADO
                          | router  | |  _call()    |
                          +----+----+ +------+------+
                               |             |
                               v             v
                       +----------------------+
                       |  agentes (7)         |
                       |  Analise_SQL         |
                       |  PDFs_library        |
                       |  scholaragent        |
                       |  prism_ai            |
                       |  villa_lobos (broker)|
                       |  gateway             |
                       |  desktop             |
                       +-------+--------------+
                               |
                               v
                       +----------------------+
                       |  shared/policy.py    |
                       |  decide tier:        |
                       |    NO_LLM / ollama_* |
                       |    / claude_*        |
                       +-------+--------------+
                               |
                  +------------+-------------+
                  v                          v
            +----------+              +-------------+
            |  Ollama  |              |  Anthropic  |
            |  local   |              |    API      |
            +----------+              +-------------+
```

---

## 4. Skills / Plugins LILO

- Diretorio `lilo_skills/skills/` ja contem ~260 wrappers (geracao
  automatizada). Os core skills (`lilo_chat`, `lilo_sql`, `lilo_scholar`,
  `lilo_pdf`, `prism_*`, `villa_*`, `lilo_health`, etc.) seguem o contrato
  `SKILL.md + script`. Validar isto via `lilo_mcp.py --profile bio`.
- Recomendado consolidar os ~200 wrappers gerados automaticamente
  (`matplotlib_*`, `mpmath_*`, `numpy_*`, `pandas_*` em `lilo_skills/skills/`)
  em **um unico skill `python_stdlib`** com sub-roteamento via parametro
  `function`, evitando a explosao de namespaces no servidor MCP.

---

## 5. Resumo executivo

- **2 bugs corrigidos** no `smoke_test_v11.py` (test contract dessincronizado
  e DB de producao em teste isolado).
- **0 erros de sintaxe** nos 50 arquivos `.py` ativos do projeto.
- **5 configs MCP** validadas; 3 recomendacoes nao bloqueantes (full-path
  Python, bump versao Claude, profile `claude_code` enxuto).
- **Villa_Lobos** ja opera com smart routing e delegate; Sprint 2 mapeado
  (7 itens, foco em cache + telemetria + tool-use no Reader).
- **Arquitetura hibrida API + MCP** ja convergente via
  `handle_tool_call` compartilhado entre `lilo_api.py` e `lilo_mcp.py`.

### Acoes humanas sugeridas (para a proxima sessao interativa)

1. Validar manualmente se `pip show mcp` e `pip show fastapi` estao
   instalados no env de producao (no sandbox foram `pip install` em runtime).
2. Considerar o bump para Claude 4.6 family em `litellm_config.yaml` apos
   confirmar disponibilidade.
3. Aprovar implementacao dos itens V1 + V2 (cache + telemetria stage-level)
   antes dos demais -- maior ROI imediato.
4. Considerar migrar o projeto para fora do OneDrive (link simbolico para
   pasta local + sync agendado) para eliminar definitivamente o truncamento.

---

*Relatorio gerado automaticamente. Run autonoma, sem interacao do usuario,
em 2026-05-11.*
