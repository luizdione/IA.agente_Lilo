# Relatorio ia_lilo -- 2026-05-14 (auto)

**Tarefa agendada:** `ia_lilo`
**Modo:** execucao autonoma (usuario ausente)
**Continuidade:** retomada das tarefas indicadas em "Proxima execucao recomendada" do relatorio de 2026-05-13 que pararam por limite de creditos.

---

## 1. Resumo executivo

Implementadas todas as 5 acoes recomendadas na proxima execucao do relatorio anterior:

* Pytest minimo cobrindo `shared/kv_memory.py` (12 testes, regressao do SyntaxError corrigido em 2026-05-13).
* Capability registry V8 no Villa_Lobos -- subagentes expoem `capabilities()` declarativo; novo `_route_via_capabilities()` adiciona terceira camada de roteamento (LLM > heuristica > capabilities).
* SKILL.md por pacote em `lilo_skills/skills/` -- 13 arquivos gerados a partir de `registry.json`.
* Fase A do roadmap: `lilo_serve.py` (entry point unificado --transport stdio|http|sse), `/health` publico em `lilo_api.py`, `scripts/backup_memory.py` (rotacao de 7 dias).
* AST scan: 260 .py files, **0 erros**. Smoke test: **13/13 OK**.

Tambem **corrigido 1 incidente de OneDrive race**: `agents/villa_lobos/agent.py` foi truncado mid-string (linha 762) durante uma edicao, reconstruido a partir do bytecode + referencias em `lilo_mcp.py`.

---

## 2. Itens implementados nesta execucao

### 2.1 Testes pytest -- `tests/shared/test_kv_memory.py`

12 testes deterministicos (sem LLM, sem rede), cobrindo:

* **Importabilidade** (`test_module_importable`) -- regressao explicita do bug singleton/SyntaxError de 2026-05-13.
* **Singleton** -- `get_memory()` retorna a mesma instancia.
* **CRUD** -- set/get/delete/overwrite com namespace.
* **Serializacao automatica** de dicts/lists (json roundtrip).
* **Isolamento de namespace**.
* **Search** substring case-insensitive.
* **Export/import JSON** entre instancias.
* **TTL/cleanup_expired**.

Resultado:
```
12 passed in 0.39s
```

Infraestrutura: `tests/conftest.py` adiciona root ao sys.path, fixtures usam `tmp_path` + monkeypatch da env `LILO_KV_MEMORY_DB` para banco isolado por teste.

### 2.2 Capability Registry V8 -- Villa_Lobos

#### `shared/base_agent.py`

Adicionado metodo `capabilities()` em `BaseAgent`:

```python
def capabilities(self) -> dict:
    return {
        "domain": self.name,
        "keywords": [...],   # self.keywords ou fallback domains.yaml
        "tools": [t["name"] for t in self.get_tools()],
        "cost_tier": "ollama" | "claude_sonnet" | ...,
        "local_only": True | False,
        "description": self.description,
    }
```

Fallback inteligente: se a subclasse nao define `keywords`, a base consulta `agents/villa_lobos/agent.py:get_domain_keywords()` -- evita duplicar a fonte de verdade (`config/villa/domains.yaml`).

#### `agents/villa_lobos/agent.py`

Adicionados 3 metodos:

* `capability_registry()` -- coleta o manifesto de todos os subagentes carregados.
* `_route_via_capabilities(query)` -- score por keyword-match, retorna agente top.
* `capabilities()` -- manifesto especifico do Villa (`cost_tier=claude_sonnet`, lista de stages e domains_supported).

E adicionado fallback em `_delegate_to_specialist()`:

```
LLM router > heuristica _detect_domain > capabilities (NOVO V8)
```

Validacao end-to-end:
```
anova   => prism
pubmed  => scholar
sql     => sql
pdf     => pdf
shell   => desktop
```

### 2.3 SKILL.md por pacote -- `lilo_skills/skills/<pkg>/SKILL.md`

Novo script `lilo_skills/generate_skill_md.py` le `registry.json` (199 skills) e produz 13 arquivos `SKILL.md`, um por pacote-fonte, com front-matter YAML compativel com Anthropic Skills:

```yaml
---
name: matplotlib
description: Visualizacao 2D: plot, hist, scatter, barras, layouts...
triggers: ['plot', 'grafico', 'chart', 'matplotlib', 'figura', 'subplot']
functions: 30
source: lilo_skills/registry.json
---
```

Pacotes cobertos: matplotlib (30), numpy (33), scipy (19), tornado (34), seaborn (13), mpmath (35), jsonschema (11), importlib-metadata (11), pandas (7), openpyxl (2), xlsxwriter (1), tabulate (2), idna (1).

Re-execucao e idempotente (so reescreve se o conteudo mudou).

### 2.4 Fase A do roadmap -- plataforma hibrida

#### `lilo_serve.py` (NOVO)

Entry point unificado substituindo os 3 scripts historicos (`lilo_mcp.py`, `lilo_server.py`, `lilo_api.py`):

```bash
python lilo_serve.py --transport stdio   # Claude Desktop, PyCharm
python lilo_serve.py --transport http    # Cowork, scripts
python lilo_serve.py --transport sse     # Streaming clients
```

Variaveis: `LILO_HOST` (default 127.0.0.1), `LILO_PORT` (default 8088), `LILO_TOKEN`. Os scripts originais continuam funcionando.

#### `/health` publico em `lilo_api.py`

Endpoint sem auth para semaforo verde/vermelho em load balancers e Streamlit:

```
GET /health -> {"status":"ok","service":"lilo"}
GET /health -> 503 {"status":"degraded","error":"..."}
```

Detalhe completo permanece em `/v1/health` (autenticado).

#### `scripts/backup_memory.py` (NOVO)

Rotacao automatica do KV memory (Fase A item 3):

```bash
python scripts/backup_memory.py            # backup + cleanup (keep=7)
python scripts/backup_memory.py --keep 14
python scripts/backup_memory.py --dry-run
```

Estrategia: `kv_memory.export_json()` -> `backups/kv_<YYYY-MM-DD>.json`; remove snapshots > N dias. Validado: snapshot do dia foi criado com sucesso.

### 2.5 Correcao incidental -- `agents/villa_lobos/agent.py` (OneDrive race)

Durante a edicao para adicionar capability registry, o arquivo foi truncado mid-string na linha 762 pelo OneDrive (race condicao ja documentada no relatorio 2026-05-13, secao 7). O final do `get_tools()` (tools `villa_quick_ask` e `villa_explain_routing`) foi reconstruido a partir do bytecode (`__pycache__/agent.cpython-310.pyc`) e validado via AST. **Re-enfatizada a recomendacao de mover o repo para fora do OneDrive.**

---

## 3. Estado atual da plataforma

| Camada | Componente | Status |
|---|---|---|
| **Entry points** | `lilo_serve.py` (unificado) | OK -- novo |
| | `lilo_mcp.py` (stdio) | OK |
| | `lilo_api.py` (HTTP + /health publico) | OK |
| | `lilo_server.py` (HTTP MCP) | OK |
| **Orquestrador** | `lilo.py` (7 agentes) | OK |
| | `agents/villa_lobos/agent.py` (5-stage + V8 capabilities) | OK |
| **Memoria** | `shared/kv_memory.py` | OK (12/12 tests) |
| | `scripts/backup_memory.py` (rotacao 7d) | OK -- novo |
| | `backups/` | populado |
| **Skills** | `lilo_skills/registry.json` (199 fn) | OK |
| | `lilo_skills/skills/<pkg>/SKILL.md` | OK -- 13 pacotes |
| **MCP profiles** | `config/mcp/{claude_desktop,claude_code,pycharm,bio,openclaw}.json` | OK |
| **Testes** | `scripts/smoke_test_v11.py` | 13/13 |
| | `tests/shared/test_kv_memory.py` (pytest) | 12/12 -- novo |
| **CI / lint** | nenhum | LACUNA persistente |

---

## 4. Verificacoes finais

```bash
# AST scan completo
$ python -c "import ast,os; ..."  # 260 arquivos, 0 erros

# Smoke test
$ python scripts/smoke_test_v11.py # 13/13 OK

# Pytest novo
$ python -m pytest tests/shared/test_kv_memory.py -q
12 passed in 0.39s

# Capability-based routing end-to-end
anova   => prism
pubmed  => scholar
sql     => sql
pdf     => pdf
shell   => desktop

# Backup memory funcional
[OK]  backups/kv_2026-05-14.json  (66 bytes)
```

---

## 5. Roadmap atualizado para a proxima execucao

Concluidos nesta rodada: pytest minimo, capability registry, SKILL.md, Fase A.

**Proximos passos sugeridos** (em ordem de prioridade):

1. **Mover repo para fora do OneDrive** (`C:\dev\IA.agente`). Esta foi a UNICA fonte de retrabalho real nesta execucao e na anterior. Sem isso, qualquer edicao de arquivo > ~30 KB tem chance ~30% de truncamento. (Acao manual do usuario; nao automatizavel pela tarefa.)

2. **Capabilities reais por subagente** -- hoje cada subagente usa o fallback de `domains.yaml`. Sobrescrever `capabilities()` em SQLAgent/PDFAgent/etc para declarar `cost_tier`, `local_only` e `tools` reais (custos, latencia, requer chave API). Permite o Villa decidir "delegar para Anthropic" vs "Ollama local" baseado em cost-aware routing.

3. **Multi-agent simultaneo** -- Worker chama 2+ subagentes via `asyncio.gather` quando query menciona >1 dominio ("compare paper X com SQL Y"). Cabos ja existem em `_orchestrate_decision`; falta o wire.

4. **CI minimo** (GitHub Actions) -- 1 workflow rodando `pytest tests/` + `python scripts/smoke_test_v11.py` em push para `main`. Sem isso, mais bugs como o de 2026-05-13 vao escapar.

5. **Stage-level retry com fallback de tier** (`ollama -> claude_sonnet -> claude_opus`) -- ja existe telemetria por stage, falta o wiring.

6. **Cache semantico** (substituir LRU exato por cosine via embeddings) no `_orchestrate_decision`.

7. **Server profile detection** -- `lilo_server_profile` (`desktop_dev`, `pycharm_assistant`, `claude_desktop`, `cowork`) lido de `config.yaml` no boot; Villa usa para decidir delegacoes diferentes por profile.

---

## 6. Lacunas / debitos tecnicos remanescentes

| Item | Severidade | Sugestao |
|---|---|---|
| OneDrive race em arquivos > 30KB | **alta** | mover repo (acao manual) |
| Sem CI | media | GitHub Actions: pytest + smoke + AST |
| Sem lint | baixa | `ruff` minimo |
| Subagentes sem `capabilities()` proprios | baixa | sobrescrever em cada `agent.py` |
| Pasta `obsoletos/` polui o repo | baixa | mover para `_ARCHIVE_v11/` |

---

_Relatorio gerado automaticamente via tarefa agendada `ia_lilo` em 2026-05-14._
