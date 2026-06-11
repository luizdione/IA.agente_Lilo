# Relatorio ia_lilo -- 2026-05-23 (v2, auto)

**Tarefa agendada:** `ia_lilo`
**Modo:** execucao autonoma (usuario ausente)
**Continuidade:** segunda rodada de 2026-05-23, retomando o roadmap do
relatorio `RELATORIO_ia_lilo_2026-05-23.md` (v1) e a diretriz do CLAUDE.md
("sempre completar as tarefas anteriores que pararam por limite de creditos").

---

## 1. Resumo executivo

Diferente da v1 (dominada por recuperacao de corrupcao), esta rodada partiu de
um **nucleo saudavel** e focou em **resiliencia, alinhamento de perfis e um
ponto de recuperacao independente**. Nenhuma corrupcao nova foi detectada.

Principais resultados:

* **Bug de robustez real encontrado e corrigido** (`shared/cost_tracker.py`):
  a telemetria de custo **derrubava o chat inteiro** quando a escrita no
  SQLite falhava (disco cheio / lock). `_init_db()` e `log_request()` agora
  sao **fail-soft** -- a resposta do agente chega ao usuario mesmo se a
  telemetria falhar. Comprovado: `lilo.route()` que antes quebrava com
  `disk I/O error` no disco cheio agora **responde normalmente** (secao 2).
* **Perfis MCP alinhados ao perfil de servidor V9** (5 arquivos em
  `config/mcp/`): antes **so o `cowork`** injetava `LILO_SERVER_PROFILE`; agora
  Claude Desktop, PyCharm, Claude Code, OpenClaw e bio tambem -- o pedido
  "atuar de acordo com o setup do servidor" passa a valer em **todos** os
  clientes, nao so na automacao. Tambem foi corrigido o interpretador
  inconsistente do `claude_desktop.json` (`python` -> miniforge) (secao 3).
* **Villa_Lobos: roteamento cost-aware por perfil (V9.2)** -- o desempate de
  `_route_via_capabilities` agora respeita `prefer_local`/`allow_cloud` do
  perfil. Em perfis enxutos, empates de keyword pendem para o agente
  local/barato; agentes cloud-only sao penalizados quando o perfil proibe
  nuvem. Implementa a parte de roteamento da proposta 6.1 (secao 4).
* **Ponto de recuperacao independente criado:**
  `backups/source_snapshot_2026-05-23.tar.gz` (562 arquivos, gzip-OK) --
  protege o codigo-fonte mesmo se git **e** `.pyc` faltarem na proxima
  corrupcao (era o gap exato apontado na v1) (secao 7).
* **Testes 1 e 2 iteracoes:** roteamento sub-ms; Villa nao trava e
  auto-corrige; cap de iteracoes por perfil confirmado em runtime
  (cowork: 3 pedidas -> 2 efetivas); chat 24 ms frio / 10 ms quente (secao 5).
* **Verificacoes finais:** AST 261 arquivos = **0 erros, 0 NUL**; smoke =
  **13/13**; pytest = **12/12**.

> **Risco estrutural persistente (inalterado da v1):** `agents/` segue
> *untracked* no git. A causa nao e o `.gitignore` (que **nao** ignora
> `agents/`) -- e uma **reorganizacao nao commitada**: o HEAD ainda rastreia
> o layout antigo (`Analise_SQL/`, `PDFs_library/`, `backend/` na raiz, vistos
> como `D`) enquanto a nova arvore `agents/` esta untracked. O script
> `sincronizacao_github.bat` ja usa `git add -A` e resolveria isso -- ele
> **so nao foi executado** desde a reorg (secao 7).

---

## 2. Erro encontrado e corrigido -- telemetria derrubava o chat (CRITICO)

### 2.1 Diagnostico

Durante o benchmark de chat, `lilo.route()` quebrou com
`sqlite3.OperationalError: disk I/O error`. O traceback apontou a origem:

```
lilo.py:127  tracker = get_tracker()
cost_tracker.py:51  self._init_db()
cost_tracker.py:55  conn.execute(""" CREATE TABLE ... """)  <-- disk I/O error
```

Ou seja: o `CostTracker` (singleton lazy) tenta escrever no SQLite **na
instanciacao** (`_init_db`) e a cada request (`log_request`). Nenhum dos dois
tinha `try/except`. Quando o disco estava cheio (ou o `.db` travado), a
**escrita de telemetria** propagava a excecao e **matava a chamada inteira** --
mesmo que a resposta do agente (`result`) ja estivesse pronta.

Contraste revelador: a gravacao no Obsidian, logo abaixo em `route()`, **ja
era** envolvida por `try/except ... pass # Obsidian eh opcional`. A telemetria
de custo merece o mesmo tratamento -- ela e medida acessoria, calculada
**depois** da resposta.

### 2.2 Correcao (fail-soft)

`shared/cost_tracker.py` (165 -> 171 linhas):

* `_init_db()` -- bloco de escrita envolvido em `try/except`, com
  `log.warning(...)` em vez de propagar.
* `log_request()` -- idem: a falha de escrita vira aviso, nao excecao.

Resultado: o `CostTracker` e agora **totalmente fail-soft** no caminho de
`route()`. Telemetria perdida em condicao degradada, mas o usuario recebe a
resposta.

### 2.3 Comprovacao

| Cenario | Antes | Depois |
|---|---|---|
| `route()` com DB de custo em disco **cheio** (default) | `disk I/O error` (quebra) | **responde** em 40 ms |
| `log_request()` com alvo de escrita invalido | levanta excecao | engole erro (warning) |
| `_init_db()` com alvo de escrita invalido | levanta excecao | engole erro (warning) |

Isto atende diretamente o requisito da tarefa ("se travar, se autocorrigir"):
o chat **se autocorrige** de uma falha de I/O de telemetria em vez de travar.

> **Nota de ambiente (nao e bug):** o sandbox desta execucao estava com o
> filesystem `/sessions` a **100%** (0 B livres, ocupado por outros tenants),
> o que tambem fazia o `pytest` falhar 1 teste (criacao de `~/.local`) e o
> smoke pular 2 (pip install de `mcp`). Apontando `HOME`/`PYTHONPATH`/
> `LILO_COST_DB` para o filesystem `/` (com espaco), tudo passou 12/12 e 13/13.
> O bug da secao 2.1, porem, e **real** e independente do ambiente: foi so o
> disco cheio que o **expos**.

---

## 3. MCP & Skills

### 3.1 Perfis MCP alinhados ao perfil de servidor V9 (implementado)

Antes desta rodada, **apenas** `cowork.json` setava `LILO_SERVER_PROFILE`.
Os demais clientes nao setavam nada -> Villa caia sempre no default
`desktop_dev` (max_iterations=3, allow_cloud=True), **ignorando** o setup
real do cliente. A politica V9 (`shared/server_profile.py`) existia mas so
tinha efeito na automacao Cowork.

Correcao (5 arquivos, gerados em disco e copiados com `cp` -- metodo seguro):

| Arquivo MCP | `LILO_SERVER_PROFILE` injetado | Efeito (V9) |
|---|---|---|
| `claude_desktop.json` | `claude_desktop` | prefer_local=False, allow_cloud=True, max_it=3 |
| `pycharm.json` | `pycharm_assistant` | prefer_local=True, allow_cloud=True, max_it=2 |
| `claude_code.json` | `desktop_dev` | prefer_local=True, allow_cloud=True, max_it=3 |
| `openclaw.json` | `desktop_dev` | idem |
| `bio.json` | `bio` | prefer_local=True, allow_cloud=False, max_it=2 |
| `cowork.json` | `cowork` (ja existia) | prefer_local=True, allow_cloud=False, max_it=2 |

Agora os **dois sistemas de perfil** (tool-profile do MCP e behavior-profile
do orquestrador) ficam alinhados em **todos** os clientes.

### 3.2 Interpretador padronizado (correcao)

`claude_desktop.json` usava `"command": "python"` (depende do PATH) enquanto
todos os outros usam o caminho absoluto do miniforge. Padronizado para
`C:\Users\luizd\miniforge3\python.exe`. Isto remove uma fonte real de "o
servidor MCP nao inicia no Claude Desktop" quando o `python` do PATH nao e o
ambiente com as dependencias. Tambem foi adicionado `OLLAMA_HOST` aos perfis
que nao o tinham (consistencia; default local inofensivo).

> Validacao: os 6 JSONs parseiam; o valor do interpretador em memoria e
> **identico** ao ja usado pelos outros configs (assert no gerador). O escape
> de barras foi conferido (`C:\\Users\\...` no arquivo = caminho real com
> barra simples ao carregar).

### 3.3 Skills -- mantido como roadmap

Reitero a recomendacao da v1: maior ROI seria skills de **bioinformatica**
(FASTA/GenBank, codons, qPCR/ddCt, `.pzfx`/GraphPad, mdtraj) e **triggers
PT-BR**. Nao implementadas autonomamente por exigirem decisao de escopo do
usuario (que bibliotecas, que formato de saida). Ficam para uma rodada com o
usuario presente.

---

## 4. Villa_Lobos -- roteamento cost-aware por perfil (V9.2, implementado)

Diagnostico: nenhum subagente especialista sobrescreve `capabilities()` --
todos usam o default de `base_agent` (cost_tier `ollama`, local_only=True). O
`_route_via_capabilities` ranqueava **so por contagem de keywords**, sem
considerar o perfil do servidor.

Mudanca em `agents/villa_lobos/agent.py` (`_route_via_capabilities`):

```python
from shared.server_profile import get_profile_policy
_pol = get_profile_policy()
_prefer_local = bool(_pol.get("prefer_local"))
_allow_cloud  = bool(_pol.get("allow_cloud", True))
...
score = float(kw_hits)
is_local = bool(cap.get("local_only", True)) or cap.get("cost_tier","ollama") == "ollama"
if _prefer_local:
    score += 0.10 if is_local else -0.10      # epsilon < 1 match
if not _allow_cloud and not is_local:
    score -= 0.50                              # nao priorizar cloud onde e proibido
```

Propriedades (testadas):

* O ajuste e um **epsilon (<1)**, logo **nunca supera 1 match de keyword** --
  so reordena candidatos de pontuacao igual ou quase igual. Roteamento por
  relevancia textual e preservado.
* Sob `prefer_local` (desktop_dev, pycharm, cowork, bio): empate
  local-vs-cloud -> ganha o **local**. Verificado nos 4 perfis.
* Sob `allow_cloud=False` (cowork, bio): agente cloud-only e penalizado
  (mas ainda selecionavel se for o unico relevante -- relevancia > custo).
* Sob `claude_desktop` (prefer_local=False): sem epsilon -> comportamento
  original preservado (sem regressao).

Implementa a **parte de roteamento** da proposta 6.1. A parte declarativa
(cada subagente expor seu proprio `cost_tier`/`local_only`) fica no roadmap --
hoje todos os especialistas sao local/ollama, entao o default ja esta correto
e sobrescrever traria pouco ganho com algum risco.

---

## 5. Benchmarks -- 1 e 2 iteracoes

> **Metodo:** 100% offline, backend forcado a `mock` na instancia
> (`client._backend = "mock"`), `VILLA_RETRY_DELAY=0`. Mede o **overhead
> estrutural** (roteamento, montagem de pipeline, retry/fallback), nao a
> inferencia real (que depende do Ollama local, segundos por stage).

### 5.1 Latencia de roteamento (`explain_routing`)

| Metrica | valor |
|---|---|
| media | **~0.2-0.4 ms** |
| max | 1.27 ms (warm-up do 1o call) |

Overhead desprezivel; consistente com a v1 (0.26 ms). Delegacao a
especialistas (prism/sql/pdf/scholar) operacional.

### 5.2 Pipeline Villa_Lobos -- 1 vs 2 (vs 3) iteracoes (mock, allow_delegate=False)

| Perfil | iters pedidas | iters efetivas | Wall | Travou? | Auto-corrigiu? (out) |
|---|---|---|---|---|---|
| desktop_dev | 1 | 1 | 0.048 s | nao | sim (454 ch) |
| desktop_dev | 2 | 2 | 0.045 s | nao | sim (514 ch) |
| desktop_dev | 3 | **3** | 0.135 s | nao | sim (582 ch) |
| cowork | 1 | 1 | 0.039 s | nao | sim (454 ch) |
| cowork | 2 | 2 | 0.048 s | nao | sim (514 ch) |
| cowork | 3 | **2** (cap) | 0.114 s | nao | sim (522 ch) |

* **Cap de iteracoes por perfil confirmado em runtime:** sob `cowork`
  (max=2), pedir 3 iteracoes resulta em **2 efetivas**; sob `desktop_dev`
  (max=3), as 3 rodam. Era a mudanca V9.1 da v1, agora **medida ao vivo**.
* Saida cresce com as iteracoes (454 -> 514 -> 582 ch) = pipeline
  iterando/refinando (caminho de auto-correcao exercitado).
* **Nenhuma execucao travou**; wall-times de 0.04-0.14 s confirmam que nenhum
  `sleep` de retry ocorreu.

### 5.3 Chat LILO -- 1 frio vs 2/3 quente

| Execucao | ms | observacao |
|---|---|---|
| 1 (frio) | 24.0 | load de agentes + init policy/tracker |
| 2 (quente) | 10.3 | **2.3x mais rapido** (singletons aquecidos) |
| 3 (quente) | 10.3 | estavel |

E, sobretudo: apos a correcao da secao 2, `route()` **completa no disco
cheio** (40 ms) em vez de quebrar.

### 5.4 Veredito de eficacia / estabilidade

* **Eficacia de tempo:** overhead do framework minimo (roteamento sub-ms,
  chat quente ~10 ms). O gargalo real continua sendo a inferencia do modelo.
* **Trava?** Nao. Retry limitado + circuit-breaker (V9) + agora **telemetria
  fail-soft** (V9.2) eliminam mais um ponto de travamento.
* **Auto-corrige?** Sim -- fallback de modelo, cascata de roteamento
  (LLM > heuristica > capabilities cost-aware), cloud-fallback gated por
  perfil, e recuperacao de falha de I/O de telemetria.

---

## 6. Plataforma hibrida (API estilo Claude Desktop) -- proposta

Estado atual (verificado): `lilo_serve.py` unifica `--transport
stdio|http|sse`; `lilo_api.py` (FastAPI) ja expoe `/health`, `/v1/health`,
`/v1/chat`, `/v1/chat/stream` (SSE), `/v1/agents`, `/v1/tools`, `/v1/skills`,
`/v1/tools/call`, console HTML em `/`, e auth por `LILO_TOKEN`. Base solida.

Ganho colateral desta rodada: como `/v1/chat` chama `lilo.route()`, a
**correcao fail-soft da secao 2 ja endurece o endpoint HTTP** -- o servidor
nao cai mais por falha de telemetria.

Proximos passos concretos propostos (diffs futuros, em ordem de ROI):

1. **Sessoes por `session_id`** em `/v1/chat` e `/v1/chat/stream` (memoria de
   conversa multi-turno; hoje cada request e stateless). Reusar
   `shared/chat_memory.py` chaveado por sessao.
2. **Paridade de roteamento HTTP vs MCP** -- garantir que `/v1/chat` e o
   `villa_pipeline` do MCP entram pelo mesmo `route()`/`run()` (evitar drift).
3. **Default de perfil no transporte HTTP** -- `lilo_serve.py --transport
   http` poderia setar `LILO_SERVER_PROFILE=cowork` por padrao (automacao
   local-only), espelhando o que o `config/mcp/cowork.json` ja faz.
4. **Readiness rico** em `/health` (backend ativo, modelos Ollama presentes,
   espaco em disco) -- alem do "ok" minimo atual.
5. **Auth multi-token** (por cliente/escopo) em vez de um `LILO_TOKEN` unico.
6. **CI minimo** (secao 8) -- a defesa mais barata contra a corrupcao da v1.

---

## 7. Ponto de recuperacao & estado do git

### 7.1 Snapshot de fonte criado (acao segura, nao-destrutiva)

`backups/source_snapshot_2026-05-23.tar.gz` -- 562 arquivos, 351 KB, gzip-OK,
contem `agents/ shared/ config/ scripts/ tests/ lilo_skills/ lilo*.py
dashboard.py config.yaml ...` (exclui caches/`.db`/`.pyc`). Verificado:
`agents/villa_lobos/agent.py` extraido e **AST-OK** (874 linhas).

Isto fecha o gap exato apontado na v1: "se um `.pyc` faltar na proxima
corrupcao, a recuperacao sera manual/impossivel". Agora ha um ponto de
recuperacao **independente de git e de `.pyc`**.

### 7.2 Por que `agents/` ainda esta untracked (raiz, confirmada)

* `.gitignore` **NAO** ignora `agents/` (conferido linha a linha).
* Causa real: **reorganizacao de diretorios nao commitada**. HEAD rastreia o
  layout antigo (`Analise_SQL/`, `PDFs_library/`, `backend/`, `CHANGELOG.md`...
  na raiz -> aparecem como `D`); a nova arvore `agents/` esta `??`.
  `git ls-files`: agents=0, config=0, shared=8 tracked.
* O `sincronizacao_github.bat` **ja faz `git add -A`** -- ele resolveria a
  reorg. Ha apenas 2 commits "LILO auto-sync" no historico, ambos pre-reorg:
  o script **so nao foi executado** desde entao.

**Acao recomendada (manual -- nao executei git/push autonomamente):** rodar
uma vez, no Windows:

```cmd
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
sincronizacao_github.bat "Reorg agents/ + cost_tracker fail-soft + perfis MCP V9 + villa cost-aware"
```

Isso cria os pontos de recuperacao local **e** remoto de uma so vez. (O
snapshot da 7.1 ja protege ate la.)

---

## 8. Roadmap atualizado -- proxima execucao

1. **Rodar `sincronizacao_github.bat`** (secao 7.2) -- URGENTE; o snapshot e
   so paliativo.
2. **Mover repo + DBs para fora do OneDrive** (`C:\dev\IA.agente`) -- causa-raiz
   do truncamento recorrente (manual).
3. **CI minimo** (GitHub Actions: pytest + smoke + AST scan em push) -- teria
   pego os 7 arquivos truncados da v1 antes de quebrar.
4. **Deletar a pasta-lixo `C:/`** (4 notas Obsidian, 12 KB). Tentei nesta
   rodada: o mount do sandbox nega (`Operation not permitted`). A guarda V9 ja
   impede recriacao (confirmado: meus `route()` de hoje nao criaram notas).
5. **Plataforma hibrida:** sessoes por `session_id` e default de perfil no
   transporte HTTP (secao 6, itens 1 e 3).
6. **Skills de bioinformatica + triggers PT-BR** (secao 3.3) -- com usuario.
7. **`capabilities()` proprio por subagente** (parte declarativa da 6.1) e
   **multi-agente simultaneo** (`asyncio.gather`, proposta 6.5).

---

## 9. Verificacoes finais

```
AST scan completo .......... 261 arquivos, 0 erros, 0 NUL
smoke_test_v11.py .......... PASSOU: 13 | FALHOU: 0
pytest ..................... 12 passed  (HOME em fs com espaco)
import sweep ............... 20/20 modulos OK
cost_tracker fail-soft ..... route() responde no disco cheio (era disk I/O error)
villa cost-aware ........... empate -> local nos 4 perfis prefer_local; sem regressao em claude_desktop
perfis MCP ................. 6 JSONs OK; LILO_SERVER_PROFILE em todos; interpretador miniforge
benchmark roteamento ....... ~0.2-0.4 ms / max 1.27 ms
benchmark Villa 1 iter ..... ~0.04-0.05 s, sem travar, auto-corrige
benchmark Villa 2 iter ..... ~0.05 s, sem travar, auto-corrige
benchmark Villa cap ........ cowork: 3 pedidas -> 2 efetivas (runtime)
benchmark chat ............. 24 ms frio / 10 ms quente (2.3x)
snapshot recuperacao ....... backups/source_snapshot_2026-05-23.tar.gz (562 arq, gzip-OK)
```

**Arquivos alterados nesta execucao (working tree, prontos para commit):**
`shared/cost_tracker.py` (fail-soft `_init_db`+`log_request`);
`agents/villa_lobos/agent.py` (`_route_via_capabilities` cost-aware V9.2);
`config/mcp/claude_desktop.json`, `config/mcp/pycharm.json`,
`config/mcp/claude_code.json`, `config/mcp/openclaw.json`,
`config/mcp/bio.json` (perfil V9 + interpretador + OLLAMA_HOST);
`backups/source_snapshot_2026-05-23.tar.gz` (novo, ponto de recuperacao).

_Relatorio gerado automaticamente via tarefa agendada `ia_lilo` em 2026-05-23 (v2)._
