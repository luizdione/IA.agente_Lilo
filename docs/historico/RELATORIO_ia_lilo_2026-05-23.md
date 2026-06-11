# Relatorio ia_lilo -- 2026-05-23 (auto)

**Tarefa agendada:** `ia_lilo`
**Modo:** execucao autonoma (usuario ausente)
**Continuidade:** retomada apos o relatorio de 2026-05-20 e a diretriz do
CLAUDE.md ("sempre completar as tarefas anteriores que pararam por limite de
creditos").

---

## 1. Resumo executivo

Rodada dominada por **recuperacao de corrupcao**: o scan AST inicial acusou
**7 arquivos-fonte truncados** -- praticamente todo o nucleo de subagentes
estava quebrado e o sistema **nao importava**. Causa: o bug recorrente do
OneDrive (truncamento de arquivos entre sessoes), agora atingindo arquivos
*untracked* sem ponto de recuperacao no git.

Principais resultados:

* **7 arquivos truncados recuperados e validados** (0 erros AST, imports OK,
  conjuntos de metodos identicos ao bytecode pre-corrupcao):
  `shared/base_agent.py`, `agents/villa_lobos/agent.py`,
  `agents/gateway/agent.py`, `agents/desktop/agent.py`,
  `agents/Analise_SQL/agent.py`, `agents/scholaragent/agent.py`,
  `agents/prism_ai/main.py`.
* **1 truncamento adicional causado pela ferramenta de edicao in-place**
  (`shared/obsidian.py`) -- detectado e corrigido na mesma rodada; licao
  operacional registrada (secao 2.3).
* **3 melhorias implementadas e testadas:**
  1. Villa_Lobos passa a **respeitar o teto de iteracoes do perfil do
     servidor** (`max_iterations`) -- o pedido literal "atuar de acordo com o
     setup do servidor" (secao 6).
  2. Novo **perfil MCP `cowork`** + `config/mcp/cowork.json`, espelhando o
     conjunto `bio` (local-only, sem `run_shell`), alinhado a policy `cowork`
     de `server_profile.py` (secao 5).
  3. **Guarda multiplataforma** em `shared/obsidian.py`: deixa de criar a
     pasta-lixo `C:/` no repo quando a tarefa roda fora do Windows (secao 2.4).
* **Confirmado ja implementado na V9 (2026-05-22) e recuperado intacto:**
  `shared/server_profile.py`, retry adaptativo (`VILLA_RETRY_DELAY=1.5`,
  circuit-breaker no backend mock) e cloud-fallback *gated* por
  `allow_cloud` do perfil. Eram as propostas 6.2/6.3/6.4 do relatorio de
  2026-05-20 -- a corrupcao quase as destruiu.
* **Testes finais:** AST 261 arquivos = **0 erros, 0 NUL**; pytest =
  **12/12**; smoke v11 = **13/13**.
* **Benchmarks (1 e 2 iteracoes):** roteamento media 0.26 ms; pipeline Villa
  nao trava e auto-corrige; chat 285 ms a frio / 54 ms a quente. Secao 4.

> **Risco estrutural persistente:** `agents/` continua *untracked* no git.
> Os 7 arquivos que corromperam **nao tinham ponto de recuperacao versionado**;
> a recuperacao so foi possivel por introspeccao do bytecode `.pyc` (e do git,
> no caso do `base_agent.py`). **Commitar `agents/` e a acao mais urgente.**

---

## 2. Erros encontrados e corrigidos

### 2.1 Sete arquivos-fonte truncados (CRITICO, corrigido)

O scan AST inicial:

```
agents/Analise_SQL/agent.py  -> SyntaxError 156: '[' was never closed
agents/desktop/agent.py      -> SyntaxError 410: '{' was never closed
agents/gateway/agent.py      -> SyntaxError 152: '{' was never closed
agents/prism_ai/main.py      -> SyntaxError 438: unterminated string literal
agents/scholaragent/agent.py -> SyntaxError 235: unterminated string literal
agents/villa_lobos/agent.py  -> SyntaxError 804: unterminated string literal
shared/base_agent.py         -> SyntaxError 56: expected 'except'/'finally'
```

Todos terminavam **no meio de um token** (ex.: `base_agent.py` parava em
`from agents.villa_lobos.agent import get_domain_ke`). Padrao classico de
**truncamento de cauda do OneDrive**: cada arquivo perdeu o trecho final.
O `villa_lobos/agent.py` estava *integro e validado* ao fim da rodada de
2026-05-20 -- ou seja, **corrompeu entre sessoes**, fora do meu controle.

**Metodo de recuperacao (alta fidelidade):**

1. O *cabecalho* de cada arquivo estava intacto (a maior parte do codigo).
2. Os `.pyc` em `__pycache__/` (compilados quando o fonte estava completo)
   foram introspectados via `marshal`+`dis` para extrair, dos metodos
   perdidos, **a lista exata de metodos, assinaturas, todas as strings
   (docstrings, schemas de tools, prompts) e a logica (bytecode)**.
3. As caudas foram reconstruidas a partir disso e *spliceadas* ao cabecalho
   intacto.
4. `base_agent.py` teve recuperacao reforcada: versao do **git HEAD**
   (compila) combinada com o cabecalho V9 (2026-05-22) intacto no working tree.

**Validacao da fidelidade:** para cada classe, o conjunto de metodos do fonte
reconstruido foi comparado ao do `.pyc` original -- **100% identico** nos 7
arquivos (`BaseAgent` 6/6, `SQLAgent` 5/5, `ScholarAgent` 8/8, `PrismAgent`
18/18, `GatewayAgent` 6/6, `VillaLobosAgent` 16/16, `DesktopAgent` 3/3). Todos
**compilam, importam em runtime e tem 0 NUL**.

### 2.2 Fidelidade do `villa_lobos/agent.py` vs V9 (verificacao extra)

O `.pyc` 3.10 do villa era de 2026-05-20 (pre-V9), mas o cabecalho do fonte
era V9 (2026-05-22). Confirmei por `grep` que a unica integracao V9 ativa
(`get_profile_policy()`) esta em `explain_routing` (linha 738, no cabecalho
intacto); os 4 metodos da cauda reconstruida (`health`,
`capability_registry`, `_route_via_capabilities`, `capabilities`) **nao**
chamam o profile (apenas mencao em docstring). Logo a reconstrucao representa
fielmente a versao V9.

### 2.3 `shared/obsidian.py` -- truncamento causado pela edicao in-place

Ao aplicar a melhoria da secao 2.4 **via a ferramenta de edicao de arquivo**,
o arquivo foi **truncado** (perdeu o fim de `save_lilo_run` e a funcao inteira
`_update_index`), terminando em `    except E`. Isto reproduz, ao vivo, o
risco ja documentado: **escrita in-place na pasta sincronizada e insegura**.

Corrigido recuperando o `obsidian.py` do **git HEAD** (157 linhas, completo) e
reaplicando a guarda **via disco local + `cp`** (metodo seguro). Resultado:
168 linhas, 5 funcoes, compila, 0 NUL, importa.

> **Licao operacional reforcada:** nesta pasta (OneDrive), **toda escrita**
> deve ser feita montando o conteudo em disco local e copiando por cima
> (`cp`). A edicao in-place via API de arquivo pode truncar a cauda. Todas as
> demais correcoes desta rodada usaram o metodo seguro.

### 2.4 `shared/obsidian.py` -- guarda multiplataforma (melhoria)

`OBSIDIAN_VAULT=C:/Users/luizd/obsidion/...` (caminho Windows com `/`). No
Windows e absoluto e funciona. Mas quando a tarefa agendada roda em sandbox
Linux, `Path("C:/...")` e **relativo** e o `mkdir` cria uma pasta-lixo `C:/`
**dentro do repo** -- uma nota por query. (As rodadas de 2026-05-20 e a deste
benchmark deixaram 4 notas la.)

Correcao: `_get_vault_folder()` agora so persiste se o vault for **absoluto no
SO atual**; caso contrario faz `log.warning` e retorna `None`. No Windows o
comportamento e identico (o caminho e absoluto); fora do Windows, nao polui
mais o repo. Validado: em Linux retorna `None` e `lilo.route()` nao cria nota.

---

## 3. Estado do repositorio (git) -- ATENCAO (recorrente)

`git status` continua mostrando a reorganizacao **nao commitada**:

| Situacao | Itens |
|---|---|
| `?? agents/` | toda a arvore de subagentes -- os 7 arquivos que corromperam |
| `?? config/`, `?? docs/`, `?? data/` | untracked |
| `M shared/*` | base_agent, cost_tracker, llm_client, policy, obsidian |
| `M lilo.py`, `M lilo_mcp.py`, `M dashboard.py` | modificados |

**Implicacao:** os arquivos mais criticos do projeto seguem **sem versao no
git**. So nao houve perda definitiva porque os `.pyc` ainda existiam. Se um
`.pyc` faltar na proxima corrupcao, a recuperacao sera manual/impossivel.

**Recomendacao (acao manual, nao executei git):**

```cmd
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
git add agents/ shared/ config/ docs/ tests/ scripts/ lilo*.py
git commit -m "Reorg + recuperacao de 7 arquivos truncados + cowork profile + cap iter por perfil + guarda obsidian"
```

---

## 4. Benchmarks -- 1 e 2 iteracoes

> **Metodo:** 100% offline em **modo MOCK** (backend forcado a `mock` na
> instancia; sem chamadas pagas). O `.env` resolve backend `anthropic` -- rodar
> ao vivo enviaria nomes de modelo Ollama para a API Anthropic, que os
> rejeitaria, alem de gerar custo. Mock exercita os caminhos de
> retry/fallback e mede o overhead estrutural. Inferencia real depende do
> Ollama local (segundos por stage).

### 4.1 Latencia de roteamento (`explain_routing`)

| Query | ms | dominio | fonte |
|---|---|---|---|
| "o que e PCR?" | 0.46 | gateway | heuristic |
| "faca uma ANOVA comparando 3 grupos" | 0.80 | prism | heuristic |
| "rode uma query SQL com join" | 0.08 | sql | fallback |
| "resuma este artigo PDF" | 0.07 | pdf | heuristic |
| "busque papers no pubmed sobre CRISPR" | 0.07 | scholar | heuristic |
| "pipeline completo multi-dominio" | 0.08 | (villa) | heuristic |

**Overhead: media 0.26 ms, max 0.80 ms.** Desprezivel. Delegacao a
especialistas (prism/sql/pdf/scholar) funcionando.

### 4.2 Pipeline Villa_Lobos -- 1 vs 2 iteracoes (mock, RETRY_DELAY=0)

| Perfil | iters | Wall | Travou? | Auto-corrigiu? |
|---|---|---|---|---|
| desktop_dev | 1 | 0.047 s | nao | sim (saida 498 ch) |
| desktop_dev | 2 | 0.031 s | nao | sim (saida 558 ch) |
| cowork | 1 | 0.070 s | nao | sim (saida 498 ch) |
| cowork | 2 | 0.053 s | nao | sim (saida 558 ch) |

Pipeline **completa sem travar**; caminho de auto-correcao (fallback)
exercitado. O **cap de iteracoes por perfil** (secao 6) so reduz quando a
decisao pede mais que o teto: com `iterations=3` sob `cowork` (teto 2) o
efetivo cai para 2 (verificado: desktop/claude_desktop=3; cowork/bio/pycharm=2).

### 4.3 Risco de freeze / retry (melhorado na V9, confirmado)

Com `VILLA_RETRY_DELAY=1.5` (era 5) e **circuit-breaker no mock**
(`effective_retries=1`), os pipelines em modo degradado **nao acumulam mais
os ~5 s/stage** do relatorio de 2026-05-13. Os wall-times de 0.03-0.07 s
confirmam que **nenhum `sleep` de retry** ocorreu.

### 4.4 Chat LILO -- 1 vs 2 execucoes

| Execucao | ms | observacao |
|---|---|---|
| 1 (frio) | 285.7 | load de agentes + init de policy/tracker |
| 2 (quente) | 54.0 | ~5x mais rapido (singletons aquecidos) |

### 4.5 Veredito de eficacia / estabilidade

* **Eficacia de tempo:** overhead do framework minimo (roteamento sub-ms,
  chat quente ~54 ms). Gargalo real e sempre a inferencia do modelo.
* **Trava?** Nao. Retries limitados + circuit-breaker; deteccao de backend
  com timeout curto.
* **Auto-corrige?** Sim -- fallback de modelo + cascata de roteamento
  (LLM > heuristica > capabilities) + cloud-fallback gated por perfil.

---

## 5. MCP & Skills

### 5.1 Novo perfil MCP `cowork` (implementado)

Adicionado `_PROFILE_TOOLS["cowork"]` em `lilo_mcp.py` (espelha `bio`: 30
tools, **sem `run_shell`/`run_python`/`fs_write`** -- seguro para automacao nao
supervisionada) e criado `config/mcp/cowork.json` (interpretador miniforge,
`LILO_SERVER_PROFILE=cowork` no env -- **alinha os dois sistemas de perfil**:
o MCP `cowork` e a policy `cowork` do orquestrador). Validado: o profile
carrega, e `set`, exclui execucao e inclui pesquisa (scholar/prism/villa/pdf).

### 5.2 Perfis MCP -- gaps remanescentes (sem acao, ROI futuro)

* Caminho `C:\Users\luizd\...` hardcoded em todos os perfis -- quebram juntos
  se o repo mudar de lugar. Sugestao reiterada: `scripts/render_mcp_profiles.py`
  a partir de `LILO_HOME`.
* Interpretador inconsistente (`python` no `claude_desktop.json` vs miniforge
  nos demais). Padronizar no miniforge.

### 5.3 Skills -- recomendacoes (sem acao nesta rodada)

`lilo_skills/registry.json` cobre bibliotecas genericas (matplotlib, numpy,
scipy, pandas...). Maior ROI para o perfil do usuario (biologo molecular):
skills de **bioinformatica** (FASTA/GenBank, codons, qPCR/ddCt, `.pzfx`/
GraphPad, mdtraj) e **triggers PT-BR**. Nao implementadas autonomamente por
exigirem decisao de escopo do usuario; ficam no roadmap.

---

## 6. Villa_Lobos -- "de acordo com o setup do servidor" (implementado)

O `shared/server_profile.py` (V9) ja define policies por perfil
(`desktop_dev`, `pycharm_assistant`, `claude_desktop`, `cowork`, `bio`) com
`prefer_local`, `allow_cloud`, `max_iterations`. Mas o campo `max_iterations`
**nao era aplicado** -- era apenas reportado em `health()`.

**Mudanca (V9.1, 2026-05-23):** em `run()`, apos calcular
`effective_iterations`, aplica-se o teto do perfil:

```python
_max_it = get_profile_policy().get("max_iterations")
if _max_it:
    _capped = max(1, min(effective_iterations, int(_max_it)))
    if _capped != effective_iterations:
        log.info("  Perfil '%s': iters %d -> %d (teto do servidor)",
                 get_server_profile(), effective_iterations, _capped)
    effective_iterations = _capped
```

Efeito: o **mesmo Villa** roda no maximo 2 iteracoes em perfis enxutos
(`cowork`/`bio`/`pycharm`) e 3 em `desktop_dev`/`claude_desktop` -- exatamente
"atuar conforme o setup do servidor". Verificado por teste de comportamento.
A delegacao a especialistas e o cloud-fallback gated por `allow_cloud` ja
faziam parte desse mesmo principio (V9).

### Propostas remanescentes (diffs futuros)

* **6.1 Capabilities reais por subagente** -- sobrescrever `capabilities()` em
  cada agente p/ ranking cost-aware (hoje usa o default de `base_agent`).
* **6.5 Multi-agente simultaneo** -- `asyncio.gather` para queries multi-dominio.

---

## 7. Plataforma hibrida (API estilo Claude Desktop)

Sem mudancas nesta rodada (a prioridade foi recuperar o nucleo). Estado:
`lilo_serve.py` (`--transport stdio|http|sse`) e `/health` ja existem;
`lilo_api.py` importa e compila. Proximos passos inalterados: sessoes+streaming
por `session_id`, paridade de roteamento HTTP vs MCP, readiness rico, auth
multi-token, e **CI minimo** (a defesa mais barata contra a corrupcao de hoje).

---

## 8. Roadmap atualizado -- proxima execucao

1. **Commitar `agents/` + `shared/` + `config/`** (secao 3) -- URGENTE, cria
   ponto de recuperacao. Sem isso, a proxima corrupcao pode ser irreversivel.
2. **Mover repo + DBs para fora do OneDrive** (`C:\dev\IA.agente`) -- causa-raiz
   recorrente do truncamento. (manual)
3. **CI minimo** (pytest + smoke + AST scan em push) -- teria pego os 7
   arquivos truncados antes de quebrar.
4. **Remover a pasta-lixo `C:/`** do repo (4 notas Obsidian; ver secao 2.4).
   Nao consegui deletar (mount sem permissao de delete nesta sessao).
5. **Capabilities reais por subagente** (6.1) e **multi-agente** (6.5).
6. **Skills de bioinformatica + triggers PT-BR** (5.3).

---

## 9. Debitos tecnicos remanescentes

| Item | Severidade | Sugestao |
|---|---|---|
| `agents/` untracked (sem recuperacao git) | **alta** | commit imediato |
| OneDrive trunca arquivos (cauda) entre/durante escritas | **alta** | mover repo; escrever via disco local + `cp` |
| Edicao in-place via API de arquivo trunca (secao 2.3) | **alta** | usar sempre `cp` nesta pasta |
| Sem CI | media | GitHub Actions: pytest + smoke + AST |
| Pasta-lixo `C:/` no repo | baixa | deletar (guarda ja impede recriacao) |
| Caminhos MCP hardcoded | baixa | render a partir de `LILO_HOME` |
| Skills sem dominio bio molecular | media (ROI) | FASTA/qPCR/pzfx + triggers PT |
| Subagentes sem `capabilities()` proprios | baixa | sobrescrever (6.1) |

---

## 10. Verificacoes finais

```
AST scan completo .......... 261 arquivos, 0 erros, 0 NUL
pytest ..................... 12 passed
smoke_test_v11.py .......... PASSOU: 13 | FALHOU: 0
7 arquivos recuperados ..... compilam + importam; metodos 100% == bytecode
shared/obsidian.py ......... recuperado do git + guarda; compila, 0 NUL
lilo_mcp.py (cowork) ....... profile carrega; 30 tools; sem run_shell
villa max_iterations ....... cap por perfil verificado (cowork=2, desktop=3)
guarda obsidian (Linux) .... _get_vault_folder()=None; sem pasta-lixo nova
Benchmark roteamento ....... media 0.26 ms / max 0.80 ms
Benchmark Villa 1 iter ..... 0.047 s, sem travar, auto-corrige
Benchmark Villa 2 iter ..... 0.031 s, sem travar, auto-corrige
Benchmark chat LILO ........ 285 ms frio / 54 ms quente
```

**Arquivos alterados nesta execucao (working tree, prontos para commit):**
`shared/base_agent.py`, `agents/villa_lobos/agent.py`,
`agents/gateway/agent.py`, `agents/desktop/agent.py`,
`agents/Analise_SQL/agent.py`, `agents/scholaragent/agent.py`,
`agents/prism_ai/main.py` (recuperados); `agents/villa_lobos/agent.py`
(+cap por perfil); `lilo_mcp.py` (+profile cowork);
`shared/obsidian.py` (+guarda multiplataforma); `config/mcp/cowork.json` (novo).

_Relatorio gerado automaticamente via tarefa agendada `ia_lilo` em 2026-05-23._
