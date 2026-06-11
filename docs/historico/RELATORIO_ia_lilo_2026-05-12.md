# Relatorio de execucao -- ia_lilo (2026-05-12)

> Tarefa agendada `ia_lilo` -- continuidade automatizada apos a run de
> 2026-05-11 (que mapeou Sprint 2 do Villa_Lobos). Esta passada **implementou
> os 4 itens de maior ROI do Sprint 2** (V1, V2, V6, V7), criou o profile
> MCP enxuto para Claude Code, expandiu o smoke test e validou tudo
> end-to-end (13/13 verificacoes passaram). Toda a execucao ocorreu sem
> interacao humana.

---

## 1. Resumo executivo

| Item Sprint 2 | Status | Esforco | Arquivos tocados |
|---|---|---|---|
| **V1** cache LRU em `_orchestrate_decision` | OK | baixo | `agents/villa_lobos/agent.py` |
| **V2** telemetria stage-level no `cost_tracker` | OK | medio | `agents/villa_lobos/agent.py` |
| **V6** domain registry pluggable via YAML | OK | baixo | `agents/villa_lobos/agent.py`, `config/villa/domains.yaml` (novo) |
| **V7** tool MCP `villa_explain_routing` | OK | baixo | `agents/villa_lobos/agent.py`, `lilo.py`, `lilo_mcp.py` |
| V3 Reader com tool-use loop | DEFER | alto | proximo sprint |
| V4 Worker iterativo self-critique | DEFER | medio | proximo sprint |
| V5 Policy Engine + tier dinamico | DEFER | medio | proximo sprint |
| Profile `claude_code` enxuto | OK | baixo | `lilo_mcp.py`, `config/mcp/claude_code.json`, `config/mcp/claude_code_full.json` (novo) |
| Smoke test expandido (V1-V7 + profile) | OK | baixo | `scripts/smoke_test_v11.py` |

**Resultado final dos testes**: `PASSOU: 13 | FALHOU: 0`.

---

## 2. Verificacao de scripts

| Camada | Resultado |
|---|---|
| Sintaxe Python (`ast.parse`) em 249 arquivos `.py` ativos | OK -- zero erros |
| Imports principais (`lilo`, `lilo_api`, `lilo_mcp`, `agents/*`, `shared/*`) | OK |
| Smoke test `scripts/smoke_test_v11.py` (baseline pre-edits) | **PASSOU: 8 / FALHOU: 0** |
| Smoke test apos hotfixes + novos testes V1-V7 | **PASSOU: 13 / FALHOU: 0** |

### 2.1 Incidentes operacionais

**Truncamento do OneDrive (recorrente).**
Durante os edits incrementais via `Edit` em `lilo.py` (758 linhas finais
esperadas) e `lilo_mcp.py` (1062+ linhas) o final dos arquivos foi cortado
pelo OneDrive enquanto a Edit estava em andamento. O hook
`scripts/pre_commit_ast_check.py` ja cobre isso em commits, mas nao no
fluxo "Edit -> save -> sync". **Correcao aplicada nesta run**: reescrita
end-to-end via shell heredoc / Write completo para `agents/villa_lobos/agent.py`
(762 linhas) e reconstituicao das caudas truncadas de `lilo.py` e `lilo_mcp.py`.

**Recomendacao reiterada** (terceira run a registrar isto): considerar
migrar o projeto para fora do OneDrive (link simbolico para pasta local
+ sync agendado) ou desativar o sync em tempo real para esse diretorio.

---

## 3. Implementacao -- detalhes tecnicos

### 3.1 V1 -- Cache LRU em `_orchestrate_decision`

- Estrutura: `collections.OrderedDict` per-instance (nao usa
  `functools.lru_cache` para evitar reter `self` indefinidamente).
- Chave: SHA1 do texto normalizado (`re.sub(r"\s+", " ", q.strip().lower())[:512]`).
- Bound: `_CACHE_MAX = 256` entradas (eviccao LRU `popitem(last=False)`).
- Diagnostico: novo metodo `cache_stats()` expoe `{hits, misses, size, hit_ratio}`.
- Decisao cacheada inclui chave `_source` (`llm` / `heuristic` / `fallback`)
  para tracing.

**Impacto esperado**: queries similares dentro de uma sessao economizam
~0.5-1.0s/chamada de classificador, sem alterar comportamento.

### 3.2 V2 -- Telemetria stage-level

- Cada `_call_agent` agora cronometra a duracao do estagio e chama
  `cost_tracker.log_request` com:
  - `subagent="villa_<role>"` (ex.: `villa_planner`, `villa_worker`)
  - `tier=<effective_tier>` (lido do `.env`/`DEFAULT_STAGE_TIERS`)
  - `backend="ollama"` ou `"ollama_fallback"` ou o nome do tier Claude
  - `duration_ms` real
- Schema do `cost_tracker` ja suportava `duration_ms` (coluna criada em
  versao anterior), entao **zero migracao de DB**.
- Tratamento defensivo: falhas em `cost_tracker` nao derrubam o pipeline.

**Visibilidade**: `lilo_cost_recent` agora mostra granularidade por stage:
```
2026-05-12T21:12:14 ollama llama3.1:8b              sub=villa_orchestrator   $0.0000 1230ms | ...
2026-05-12T21:12:14 ollama qwen2.5-coder:14b        sub=villa_worker         $0.0000 4870ms | ...
```

### 3.3 V6 -- Domain registry pluggable

- Novo arquivo: `config/villa/domains.yaml` (definicao declarativa).
- Funcao `_load_domains_from_yaml()` com hot-reload via `mtime` (sem
  rescan se o arquivo nao mudou).
- Fallback automatico para `_DOMAIN_DEFAULTS` embarcados se YAML ausente
  ou `PyYAML` nao instalado.
- Merge: dominios YAML SOBRESCREVEM defaults; dominios so-em-defaults
  sao preservados (zero breaking change).
- **Dominios novos adicionados (3)**:
  - `genomics` (genoma, vcf, fastq, snp, variant calling, ...)
  - `proteomics` (mass spectrometry, maxquant, ptm, fosfoproteomica)
  - `bioinformatics` (blast, bwa, deseq2, edger, kegg, go enrichment)
- Ampliacoes em dominios existentes:
  - `prism`: + qpcr, rt-pcr, western blot, elisa, citometria, imunofluorescencia
  - `sql`: + duckdb
  - `pdf`: + figura suplementar
  - `scholar`: + biorxiv, medrxiv, meta-analise, revisao sistematica

**Resultado**: a heuristica `_detect_domain` agora reconhece queries
cientificas que antes caiam no fallback de pipeline completo. Ex.:
- `"analyze whole genome variant calling"` -> `genomics`
- `"mass spectrometry maxquant"` -> `proteomics`
- `"blast bowtie deseq2"` -> `bioinformatics`

### 3.4 V7 -- `villa_explain_routing` (debug tool)

- Novo metodo `VillaLobosAgent.explain_routing(query, allow_delegate)` que
  **nao chama o LLM completo** (so o orchestrator-classificador) e
  retorna dict com:
  ```json
  {
    "query": "...",
    "domain_heuristic": "prism|sql|...|null",
    "delegate_target": "<agent>|null",
    "decision": { complexity, needs_planning, ..., reasoning, _source },
    "stages_planned": ["orchestrator", "planner?", "reader?", "worker?", "reporter"],
    "stage_tiers": { stage: tier },
    "cache": { hits, misses, size, hit_ratio },
    "domains_supported": [ ... ]
  }
  ```
- Tool MCP `villa_explain_routing`:
  - Registrada em `VillaLobosAgent.get_tools()`
  - Adicionada ao `get_tool_map()` em `lilo.py`
  - Handler dedicado em `handle_tool_call()` (bypass de `route()` e
    `policy.decide()` -- nao registra custo nem incrementa o gasto diario)
  - Wrapper em `lilo_mcp.py` com docstring rica (USE WHEN / DO NOT USE WHEN)
  - Incluida nos profiles `bio`, `pycharm` e `claude_code`

**Uso final no Claude Desktop/Code**:
```
> villa_explain_routing(task="compare grupos com anova one-way")
{"query":"compare grupos com anova one-way","domain_heuristic":"prism",
 "delegate_target":"prism","decision":{...,"_source":"heuristic"},
 "stages_planned":["orchestrator","reporter"], ...}
```

### 3.5 Profile `claude_code` enxuto

`lilo_mcp.py:_PROFILE_TOOLS["claude_code"]` agora exporta apenas tools
**complementares** ao Claude Code CLI (que ja tem Read/Write/Bash/Glob/Grep
nativos):

```
villa_pipeline, villa_quick_ask, villa_explain_routing,
prism_analyze, prism_classify, prism_audit,
lilo_scholar, lilo_pdf,
lilo_memory_{set,get,list,search,stats,export,delete,cleanup},
lilo_cost_{today,recent},
lilo_pull_model, lilo_list_local_models,
lilo_health, lilo_models
```

- Total: **22 tools** (vs 35 do profile `desktop`).
- **Evita** conflito entre `run_shell` (LILO) e `Bash` (CC).
- **Evita** redundancia: nao exporta `fs_read/fs_write/fs_list/...` porque
  o CC ja faz isso melhor com Read/Write/Glob.

Configuracoes JSON:
- `config/mcp/claude_code.json` -- agora aponta para `--profile claude_code`.
- `config/mcp/claude_code_full.json` -- backup que mantem `--profile desktop`
  para quem quiser todas as tools.

Tambem alinhado: `command: "C:\\Users\\luizd\\miniforge3\\python.exe"` (full
path), conforme recomendacao operacional da run 2026-05-11.

---

## 4. Configs MCP -- estado atualizado

| Config | Profile | Tools (aprox.) | Cliente | Status |
|---|---|---|---|---|
| `config/mcp/claude_desktop.json` | `opus` | 18 | Claude Desktop Opus 4.x | OK |
| `config/mcp/bio.json` | `bio` | 28 (+ villa_explain_routing) | Pesquisa biomolecular | OK |
| `config/mcp/pycharm.json` | `pycharm` | 25 (+ villa_explain_routing) | PyCharm AI Assistant | OK |
| `config/mcp/openclaw.json` | `desktop` | 35 | OpenClaw CLI | OK |
| `config/mcp/claude_code.json` (NEW) | `claude_code` | 22 | **Claude Code CLI -- enxuto** | OK |
| `config/mcp/claude_code_full.json` (NEW) | `desktop` | 35 | Claude Code CLI -- completo | OK |
| `.mcp.json` (project-level) | `desktop` | 35 | Claude Code via projeto | OK |

---

## 5. Villa_Lobos -- roadmap atualizado

### 5.1 Concluido nesta run (Sprint 2 fase 1)

- [x] V1 cache LRU
- [x] V2 telemetria stage-level
- [x] V6 domain registry YAML + 3 dominios cientificos novos
- [x] V7 villa_explain_routing

### 5.2 Pendente (Sprint 2 fase 2 -- proxima janela)

| # | Item | Por que esperar |
|---|---|---|
| V3 | Reader com tool-use (`fs_search`+`lilo_scholar`+`lilo_memory_search`) | Requer refator significativo do prompt; alto risco -- merece sessao dedicada |
| V4 | Worker iterativo self-critique (Worker -> Critic -> Worker') | Aumenta custo de Haiku; primeiro precisamos do dashboard de custo stage-level (V2) coletar dados por 1-2 semanas |
| V5 | Policy Engine integration em DEFAULT_STAGE_TIERS dinamico | Depende de Policy Engine entender stages (hoje so entende subagent) |

### 5.3 Skills / Plugins LILO (recomendacoes operacionais)

- ~200 wrappers automaticos (matplotlib_*, numpy_*, pandas_*, scipy_*) ainda
  inflam o servidor MCP. **Recomendacao reiterada**: consolidar em um
  unico skill `python_stdlib` com sub-roteamento via parametro `function`.
- Profile `claude_code` ja exclui esses wrappers (CC pode chamar tudo via
  Bash + python -c).

---

## 6. Validacao -- 13/13 smoke tests

```
============================================================
LILO smoke test v11 (2026-05-12 -- Sprint 2)
============================================================
  OK  01 sintaxe (.py)
  OK  02 KVMemory (set/get/list/delete)
  OK  03 CostTracker
  OK  04 Villa _detect_domain heuristica
  OK  05 lilo.py imports
  OK  06 VillaLobosAgent imports
  OK  07 lilo_mcp.py imports + tools
  OK  08 lilo_api.py imports (opcional)
  OK  09 V1 cache LRU em _orchestrate_decision
  OK  10 V2 telemetria stage-level (schema)
  OK  11 V6 domain registry pluggable (YAML)
  OK  12 V7 explain_routing (debug sem pipeline)
  OK  13 profile claude_code enxuto
============================================================
PASSOU: 13 | FALHOU: 0
```

Verificacao adicional end-to-end:
```
handle_tool_call('villa_explain_routing', {...}) ->
  domain: sql
  delegate: sql
  stages: ['orchestrator', 'reporter']
```

---

## 7. Plataforma hibrida API + MCP -- progresso

A arquitetura alvo definida na run 2026-05-11 (entrypoint unificado
`handle_tool_call` compartilhado entre `lilo_api.py` REST e `lilo_mcp.py`
stdio) **continua coerente**: a nova tool `villa_explain_routing` foi
adicionada em UM unico lugar (`lilo.py:get_tool_map()` + `handle_tool_call`)
e automaticamente fica disponivel em ambos os transportes.

```
   MCP (stdio) - Claude Desktop, OpenClaw, Claude Code, PyCharm
       |
       v                                 HTTP (REST) - Cowork, web, scripts
   lilo_mcp.py                                      |
       \                                            v
        \                                       lilo_api.py
         \                                       /
          v                                     v
            handle_tool_call(name, args)  <-- ENTRY POINT UNIFICADO
                       |
                       v
                  get_tool_map()  <-- 1 mapa, ambos transportes
                       |
                       v
              agentes (7): SQL | PDF | Scholar | Prism | Villa | Gateway | Desktop
```

---

## 8. Acoes humanas sugeridas (proxima sessao interativa)

1. **Validar uso real do profile `claude_code`** abrindo Claude Code CLI e
   confirmando que apenas as 22 tools enxutas aparecem (vs 35 antes).
2. **Coletar 1-2 semanas de telemetria stage-level (V2)** para identificar
   o gargalo real do pipeline (Planner? Reader? Worker iter 2?) antes de
   investir em V3/V4.
3. **Adicionar dominios ao `config/villa/domains.yaml`** sem editar codigo:
   por exemplo `crispr`, `single_cell`, `metabolomics` -- o agente faz
   hot-reload na proxima chamada.
4. **Migrar o projeto para fora do OneDrive** (3a recomendacao registrada)
   para eliminar a classe de bugs de truncamento.
5. Considerar bump para `claude-opus-4-6` / `claude-sonnet-4-6` em
   `config/litellm_config.yaml` (pendente da run anterior).

---

*Relatorio gerado automaticamente. Run autonoma, sem interacao do
usuario, em 2026-05-12.*
