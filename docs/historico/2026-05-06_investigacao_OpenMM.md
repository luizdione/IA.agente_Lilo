# Investigação LILO — Erro OpenMM "Particle coordinate is NaN" e Auditoria do Orquestrador

**Data:** 2026-05-06
**Escopo:** Verificar erros em scripts, sugerir/realizar correções, propor desenvolvimento contínuo da plataforma híbrida (API + agente similar ao Claude Desktop), MCP/Skills no Claude / OpenClaw / ClaudeCode / PyCharm, e Orquestrador Villa-Lobos.

---

## 1. Contexto do erro reportado no log

A frase localizada em `logs/lilo.log` (06/05/2026 20:02:25) é:

> **OpenMM "Particle coordinate is NaN" error during NVT equilibration**

Trata-se de uma **query enviada pelo usuário ao GatewayAgent (modo bioinfo)**, *não* de um traceback de execução interna do LILO. A nota Obsidian gerada (`20260506_200311 - OpenMM Particle coordinate is NaN error during NVT equilibra.md`) está em `C:/Users/luizd/obsidion/00_SYSTEM/vault_system/LILO/` (vault local não montado neste runtime), portanto a resposta do modelo não foi auditada.

### Causas típicas do "Particle coordinate is NaN" em OpenMM

1. **Clashes estéricos iniciais** — falta de minimização de energia (use `LocalEnergyMinimizer` ou `simulation.minimizeEnergy(maxIterations=10000)` antes do termostato).
2. **Timestep alto demais** — reduzir para `1*fs` no início; subir para `2*fs` apenas com `HBonds` constraints e `HMR` (Hydrogen Mass Repartitioning).
3. **Hidrogênios não resolvidos** — usar `Modeller.addHydrogens(forcefield, pH=7.4)` antes de gerar o sistema.
4. **Caixa de solvatação curta** — `padding ≥ 1.0*nm` com `Modeller.addSolvent`.
5. **Ramping de temperatura ausente** — termostato Langevin de 0 K → T_alvo em rampas (ex.: 25 K a cada 5 ps).
6. **Restrições mal configuradas** — usar `HBonds` (não `AllBonds` se o forcefield não estiver preparado).
7. **Plataforma CUDA com `Mixed`/`Single` precision em sistema mal-formado** — testar com `precision=double` para diagnóstico.

> **Recomendação:** registrar no LILO um *snippet* canônico de equilibração NVT robusta (skill `openmm_nvt_equilibration_safe`). Inseri proposta no item §6.

---

## 2. Erros e fragilidades identificados no código LILO

### 2.1. `shared/web_search.py` — DuckDuckGo retornando 0 resultados (CONFIRMADO no log)

```
2026-05-04 21:25:19 [LILO.WebSearch] INFO: DuckDuckGo HTML: 0 resultados
2026-05-04 21:25:19 [LILO.WebSearch] INFO: DuckDuckGo Lite: 0 resultados
```

**Causa:** os regex `result__a` e `result__snippet` (linhas 161-165) dependem do HTML atual do DuckDuckGo, que muda silenciosamente. Sem fallback robusto, o agente fica cego para a web.

**Correção mínima (alta prioridade):**

- Adicionar fallback para SearXNG público ou Brave Search API (key gratuita).
- Tornar `duckduckgo-search` (lib `ddgs`) **dependência declarada** em `requirements.txt` em vez de "se instalado".
- Cache local (sqlite) de queries por 24 h para reduzir chamadas e suportar modo offline.

### 2.2. `shared/llm_client.py` — ordem de detecção de backend invertida (linhas 63-78)

O código tenta **Ollama primeiro** e só depois LiteLLM. O docstring (linhas 4-6) afirma o oposto:
> "1. LiteLLM Proxy ... 2. Ollama direto ... 3. Anthropic Claude"

**Impacto:** se o LiteLLM Proxy estiver rodando (porta 4000), ele nunca é usado — o cliente sempre fala direto com Ollama. Isso quebra roteamento multi-modelo via LiteLLM e impede uso de Claude via proxy.

**Correção sugerida:** alinhar ordem ao docstring **ou** atualizar o docstring para refletir a estratégia atual (Ollama-first). Recomendo a primeira opção, pois LiteLLM unifica observabilidade e fallback.

### 2.3. `agents/villa_lobos/agent.py` — pipeline sem cancel/timeout cooperativo

Stages 1-5 chamam `_call_agent` sequencialmente. Se um modelo trava (visto no log do dia 28/04, pipeline ficou no `Stage 4/5: Worker` sem conclusão), não há `asyncio.wait_for` nem `concurrent.futures.TimeoutError` global — só o retry de 2 tentativas com 5 s de delay.

**Correção:** envolver cada `_call_agent` em `concurrent.futures.ThreadPoolExecutor` com timeout configurável (default 90 s/stage); ao expirar, registrar `STAGE_TIMEOUT` e tentar fallback para modelo menor. Isso permite que um pipeline de 5 stages tenha *budget* total de tempo conhecido.

### 2.4. `lilo.py` — fallback duplicado e silencioso (linhas 199-208)

Quando o subagente lança exceção, o código faz fallback para o `next_tier` mas chama `agents[target].run()` de novo **com o mesmo target**. Se o erro era do *agente*, não do *modelo*, a segunda chamada falha igual. Não há circuit breaker.

**Correção:** ao detectar exceção do agente, tentar primeiro re-rotear para `gateway` (que é robusto), e só depois cair pra outro tier de modelo.

### 2.5. `shared/policy.py` — keyword `"molecular dynamics"` em SIMPLE_INDICATORS por colisão

O termo `"molecular dynamics"` está em `COMPLEX_INDICATORS` (linha 106), mas a query "OpenMM 'Particle coordinate is NaN' error during NVT equilibration" foi classificada como **simple** (vide log: `Tarefa simples → Ollama local`). Isso aconteceu porque `_normalize` baixa caixa e remove acentos, mas não quebra `OpenMM`/`NVT`/`NaN` em tokens — eles ficam crus na query e nenhum casa com os indicadores.

**Correção:** adicionar lista de tokens bioinfo críticos:

```python
COMPLEX_INDICATORS += [
    "openmm", "gromacs", "amber", "namd", "charmm",
    "nvt", "npt", "equilibration", "minimization",
    "force field", "forcefield", "trajectory",
    "rmsd", "rmsf", "radius of gyration", "sasa",
    "mmgbsa", "mmpbsa", "umbrella sampling", "free energy",
]
```

Isso roteia automaticamente queries de DM para `OLLAMA_HEAVY` (qwen2.5-coder:14b) que tem capacidade técnica adequada, ou para `claude_sonnet` se o budget permitir.

### 2.6. `lilo_skills/registry.json` — 199 skills geradas, mas nenhuma de DM/química computacional

Skills atuais cobrem: matplotlib, numpy, scipy, tornado, mpmath, jsonschema, pandas, openpyxl, etc. **Não há OpenMM, MDAnalysis, MDTraj, RDKit, biopython, OpenBabel.** Gap crítico para o domínio do usuário.

---

## 3. Correções já implementáveis (patches sugeridos)

Estas alterações são pequenas e seguras. Aplicar com revisão antes de commit.

### Patch A — `shared/policy.py` (adicionar tokens DM)

```python
# Em COMPLEX_INDICATORS, depois de "molecular dynamics":
"openmm", "gromacs", "amber", "namd", "charmm-gui",
"nvt", "npt", "equilibration", "minimization", "force field",
"trajectory", "rmsd", "rmsf", "radius of gyration", "sasa",
"mmgbsa", "mmpbsa", "umbrella sampling", "free energy",
"steered md", "metadynamics", "pmf", "well-tempered",
```

### Patch B — `shared/llm_client.py` (corrigir ordem de detecção)

```python
def _detect_backend(self):
    # 1. LiteLLM proxy primeiro (unifica modelos)
    try:
        r = requests.get(LITELLM_URL + "/health", timeout=1.0)
        if r.status_code == 200:
            return "litellm"
    except Exception:
        pass
    # 2. Ollama direto
    try:
        r = requests.get(OLLAMA_URL + "/api/tags", timeout=1.0)
        if r.status_code == 200:
            return "ollama"
    except Exception:
        pass
    # 3. Anthropic
    if ANTHROPIC_KEY:
        return "anthropic"
    log.warning("Nenhum backend LLM disponivel! Respostas serao mock.")
    return "mock"
```

### Patch C — `agents/villa_lobos/agent.py` (timeout por stage)

```python
import concurrent.futures

STAGE_TIMEOUT_S = int(os.environ.get("VILLA_STAGE_TIMEOUT", "120"))

def _call_agent_with_timeout(self, role, prompt):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(self._call_agent, role, prompt)
        try:
            return fut.result(timeout=STAGE_TIMEOUT_S)
        except concurrent.futures.TimeoutError:
            log.error(f"  Stage {role} excedeu {STAGE_TIMEOUT_S}s — fallback")
            return f"[{role} TIMEOUT após {STAGE_TIMEOUT_S}s]"
```

E substituir as chamadas `self._call_agent(...)` por `self._call_agent_with_timeout(...)`.

### Patch D — `requirements.txt` (declarar deps de busca)

```
duckduckgo-search>=6.0
brave-search>=0.3   # opcional, requer BRAVE_API_KEY
```

---

## 4. Plataforma híbrida (API + cliente desktop "Claude-like")

Recomendação de arquitetura para evolução do LILO em produto híbrido:

```
┌──────────────────────────────────────────────────────────────┐
│  Cliente desktop (Tauri / Electron + React)                   │
│  - Chat UI similar ao Claude Desktop                          │
│  - File picker → /upload                                      │
│  - Visualização de notas Obsidian                             │
└──────────────────────────────────────────────────────────────┘
                  │ HTTPS / WebSocket
                  ▼
┌──────────────────────────────────────────────────────────────┐
│  FastAPI gateway  (lilo_api.py — NOVO)                        │
│  POST /chat        → route()         (com SSE streaming)      │
│  POST /tools/call  → handle_tool_call()                       │
│  GET  /health                                                 │
│  GET  /models                                                 │
│  POST /skills/run  → call_skill()                             │
│  WS   /stream      (token-by-token)                           │
└──────────────────────────────────────────────────────────────┘
                  │
   ┌──────────────┼──────────────┬──────────────┐
   ▼              ▼              ▼              ▼
 LILO core     LiteLLM        Ollama       Anthropic
 (lilo.py)    (gateway)      (local)         (API)
```

**Ações concretas (próximas 2 semanas):**

1. Criar `lilo_api.py` com FastAPI expondo `route()` e `handle_tool_call()` como endpoints REST + SSE.
2. Adicionar autenticação por token simples (header `X-LILO-Token`) lendo de `.env`.
3. Empacotar com `pyinstaller` em `dist/LILO-API.exe` para iniciar via `START_LILO_WINDOWS.bat`.
4. Cliente desktop: começar com PyWebView ou Tauri carregando o atual `dashboard.py` (Streamlit) ou um React mínimo.

---

## 5. Configurações MCP & Skills (Claude Desktop, Claude Code, PyCharm, OpenClaw)

### 5.1. Estado atual

`.mcp.json` (raiz do projeto) registra **um único servidor**: `lilo` via `lilo_mcp.py`. Bom ponto de partida, mas:

- Não há skills declaradas em formato MCP (apenas `lilo_skills/skills/*.py` carregadas runtime).
- Não há separação entre clientes (Claude Desktop, Claude Code, PyCharm).

### 5.2. Proposta de arquivos de configuração

Criar 4 perfis MCP em `config/mcp/`:

| Arquivo | Cliente | Conteúdo |
|---|---|---|
| `claude_desktop.json` | Claude Desktop | LILO + Notion + Gmail + GitHub MCP |
| `claude_code.json` | Claude Code (CLI) | LILO + filesystem + git + bash |
| `pycharm.json` | PyCharm (via lilo_pycharm_mcp.py) | LILO + sqlite + jupyter |
| `openclaw.json` | OpenClaw | LILO + browser-use + scholar |

**Skills "biológicas" a criar (prioridade alta):**

- `openmm_nvt_equilibration_safe` — gera script de equilibração com minimização + ramp.
- `mdanalysis_rmsd_rmsf` — wrapper para análise de trajetória.
- `rdkit_compound_2d3d` — converte SMILES em PDB/SDF 3D.
- `biopython_pdb_clean` — remove águas/heteroátomos, atribui estados de protonação.
- `chimera_x_publication_image` — render publication-quality.

Estas devem ir em `lilo_skills/skills/bio/` com schemas em `lilo_skills/schemas/bio/`.

---

## 6. Orquestrador Villa-Lobos — evolução para LLM-as-router

### 6.1. Limitação atual

`agents/villa_lobos/agent.py` é uma **pipeline fixa** Orchestrator → Planner → Reader → Worker → Reporter. Os 5 stages rodam *sempre*, gastando ≈ 2-5 min mesmo para tarefas simples.

### 6.2. Evolução proposta — "Villa-Lobos Router"

Transformar o **Orchestrator (stage 1)** em router de fato:

```
Orchestrator → emite JSON estruturado:
  {
    "complexity": "simple|medium|complex",
    "needs_reader": true|false,
    "needs_worker_iterations": 1-5,
    "delegate_to": ["scholar"|"sql"|"pdf"|"prism"|null],
    "skip_to_stage": null|"reporter"
  }
→ Router LILO consome o JSON e decide quais stages executar.
```

**Vantagens:**

- Tarefa "liste tabelas" pula direto pro reporter (≈ 5 s vez de 2 min).
- Delegação para subagente especializado (`scholar` faz busca, Villa só sintetiza).
- Worker iterativo só quando necessário (ex.: deep-research multi-passo).

**Implementação mínima:**

1. Adicionar `_orchestrator_json()` em `agent.py` que pede saída JSON ao modelo `phi3:14b` e valida com `pydantic`.
2. Refatorar `run()` para consumir o JSON e *skipar* stages não-requeridos.
3. Tag de telemetria `villa_routing_decision` no `cost_tracker` para análise post-hoc.

### 6.3. Setup do servidor — alinhamento com hardware

Sugiro adicionar em `config.yaml`:

```yaml
villa_lobos:
  routing_mode: "smart"          # smart | full_pipeline | minimal
  stage_timeout_s: 120
  max_total_duration_s: 600
  models_per_stage:
    orchestrator: phi3:14b-medium-128k-instruct-q4_K_M
    planner:      phi3:14b-medium-128k-instruct-q4_K_M
    reader:       qwen2.5-coder:7b-instruct
    worker:       qwen2.5-coder:14b
    reporter:     llama3.1:8b-instruct-q8_0
  delegation:
    enabled: true
    allowed_targets: [scholar, prism, pdf]
```

Isso desacopla configuração de código, permitindo otimização sem redeploy.

---

## 7. Prioridades — punch list

| # | Item | Esforço | Impacto | Status |
|---|---|---|---|---|
| 1 | Patch A (tokens DM em policy.py) | 5 min | Alto (roteamento correto) | **Aplicar agora** |
| 2 | Patch B (ordem de backend) | 5 min | Médio | **Aplicar agora** |
| 3 | Patch C (timeout Villa stages) | 30 min | Alto (evita travas) | Próximo sprint |
| 4 | Patch D (deps web search) | 5 min | Médio | **Aplicar agora** |
| 5 | Skill `openmm_nvt_equilibration_safe` | 2 h | Alto (resolve erro reportado) | Próximo sprint |
| 6 | Villa-Lobos smart routing | 1 dia | Alto (perf + custo) | 2 semanas |
| 7 | FastAPI `lilo_api.py` | 2-3 dias | Estratégico (plataforma híbrida) | 1 mês |
| 8 | 4 perfis MCP (Desktop/Code/PyCharm/OpenClaw) | 4 h | Médio (DX) | 2 semanas |
| 9 | Skills bio (RDKit, Biopython, MDAnalysis) | 2 dias | Alto (domínio) | 1 mês |

---

## 8. Bugs CRÍTICOS encontrados durante a investigação (corrigidos)

### 8.1. `shared/llm_client.py` truncado — `NameError: _client_instance`

Durante a auditoria, ao tentar importar `shared.llm_client`, descobri que o arquivo estava **truncado** no commit `9e6c3d6 LILO auto-sync` (git diff confirmou). As últimas linhas haviam sido cortadas, restando apenas:

```python
_client_instance 
```

Sem `: Optional[LLMClient] = None`, sem a função `get_client()`, sem newline final. **Toda chamada `get_client()` falhava em produção** — isso explica por que os logs mostraram queries roteadas mas várias paradas em silêncio.

**Correção aplicada:** restaurado o singleton completo:

```python
_client_instance: Optional[LLMClient] = None

def get_client() -> LLMClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = LLMClient()
    return _client_instance
```

### 8.2. `shared/policy.py` truncado — `SyntaxError` em `get_status()`

Mesmo problema, no método `get_status()`. Restaurado.

**Lição:** o script `sincronizacao_github.bat` ou alguma rotina de auto-format está cortando arquivos no fim. **Recomendação:** adicionar pre-commit hook com `python -c "import ast; ast.parse(open(f).read())"` para os arquivos modificados, bloqueando push se sintaticamente inválidos.

---

## 9. Notas finais

- **A query OpenMM NaN em si não foi um bug do LILO** — foi corretamente recebida e roteada. Mas o roteamento foi sub-ótimo (tier `simple` em vez de `complex`/`heavy`), por isso o Patch A é prioritário.
- **Vault Obsidian não está acessível neste runtime** — para auditar a *resposta* gerada pelo LILO àquela query, abrir manualmente `C:/Users/luizd/obsidion/00_SYSTEM/vault_system/LILO/20260506_200311 - OpenMM Particle coordinate is NaN error during NVT equilibra.md` ou re-executar a query depois do Patch A para comparar a qualidade.
- **Próxima execução agendada deste task (`ia_lilo`)** deveria começar lendo o `CHANGELOG.md` para detectar mudanças desde a última auditoria — sugestão de adicionar este passo ao `SKILL.md`.
