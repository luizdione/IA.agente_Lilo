# Relatorio ia_lilo -- 2026-05-20 (auto)

**Tarefa agendada:** `ia_lilo`
**Modo:** execucao autonoma (usuario ausente)
**Continuidade:** retomada apos o relatorio de 2026-05-14 ("Proximos passos sugeridos") e a diretriz do CLAUDE.md ("sempre completar as tarefas anteriores que pararam por limite de creditos").

---

## 1. Resumo executivo

Esta rodada focou no escopo da tarefa: **verificar erros, corrigir, e propor/avancar desenvolvimento continuo** do orquestrador Villa_Lobos e das configuracoes MCP/Skills.

Principais resultados:

* **1 erro critico corrigido:** `lilo_api.py` estava com `SyntaxError: unmatched ')'` na linha 859 -- o arquivo tinha um *tail* legado duplicado (um `)` solto, um `return` orfao e um segundo bloco `if __name__ == "__main__"`). Classico sintoma da *race* do OneDrive ja documentada. **O arquivo nao subia mais.** Reconstruido e validado (compila, 0 NUL, AST limpo).
* **1 code smell corrigido:** `agents/villa_lobos/agent.py` tinha `capability_registry()` e `_route_via_capabilities()` **definidos duas vezes** (linhas 660-699 e 810-849) -- artefato da reconstrucao de 2026-05-14. As primeiras eram codigo morto (Python usa a ultima definicao). Removidas; classe passou de 18 para 16 metodos sem duplicatas.
* **1 melhoria preventiva implementada:** `shared/cost_tracker.py` agora aceita `LILO_COST_DB` (env) para mover o SQLite volatil para fora de pastas sincronizadas. Motivada por falha observada nesta execucao (ver secao 4.4). Default inalterado.
* **Testes:** AST scan 260 arquivos = **0 erros**; pytest = **12/12**; smoke test v11 = **13/13**.
* **Benchmarks (1 e 2 iteracoes):** roteamento ~0.2 ms; pipeline Villa nao trava e auto-corrige (fallback acionado); chat LILO 215 ms a frio / 21 ms a quente. Detalhes na secao 4.

Achado estrutural relevante: **o working tree tem uma reorganizacao grande NAO commitada** -- `agents/` inteiro e `lilo_api.py` estao *untracked* (`??`). Ou seja, o arquivo que corrompeu **nao tinha ponto de recuperacao no git**. Ver secao 3.

---

## 2. Erros encontrados e corrigidos

### 2.1 `lilo_api.py` -- SyntaxError (CRITICO, corrigido)

O scan AST acusou:

```
./lilo_api.py -> SyntaxError line 859: unmatched ')'
```

Inspecao das linhas 846-869 revelou que, apos o entrypoint correto
(`if __name__ == "__main__":` usando `get_env`/`log`/`API_TOKEN`,
terminando em `uvicorn.run(...)`), havia um bloco legado colado:

```python
    uvicorn.run(app, host=host, port=port, log_level="info")
)                                                   # <- paren solto (linha 859)
    return {"deleted": True, "namespace": ns, "key": key}   # <- return orfao
                                                            # (fora de funcao)

if __name__ == "__main__":                          # <- entrypoint duplicado
    import uvicorn
    import os
    host = os.environ.get("LILO_HOST", "127.0.0.1")
    ...
```

Diagnostico byte a byte: o arquivo media 35.250 bytes; o conteudo bom
terminava em 34.904, e os 346 bytes finais eram o tail corrompido.
Pior: a primeira tentativa de correcao via a ferramenta de edicao
**regravou o arquivo mantendo o mesmo tamanho e preenchendo o espaco
liberado com 346 bytes NUL** -- exatamente a falha do OneDrive
descrita nos relatorios anteriores, agora capturada no proprio caminho
de escrita.

**Correcao definitiva:** o conteudo limpo foi montado em disco local
(fora da pasta sincronizada), validado (`py_compile` + AST), e copiado
de volta com `cp` (que trunca para o tamanho menor corretamente).
Resultado: 34.904 bytes, **0 NUL**, compila, AST limpo.

> Licao operacional: para arquivos > ~30 KB nesta pasta, **editar em
> disco local e copiar por cima** e mais seguro que editar in-place. A
> regravacao in-place pode deixar NUL/whitespace de cauda quando o
> conteudo encolhe.

### 2.2 `agents/villa_lobos/agent.py` -- metodos duplicados (corrigido)

`capability_registry()` (linha 660 e 810) e `_route_via_capabilities()`
(linha 682 e 832) estavam definidos duas vezes, identicos exceto por um
comentario. Python usa sempre a ultima definicao, entao o primeiro par
(660-699) era codigo morto remanescente da reconstrucao por bytecode de
2026-05-14.

Removido o primeiro bloco (linhas 660-700). Validacao AST: classe
`VillaLobosAgent` agora com **16 metodos, 0 duplicatas**, todos os
metodos-chave presentes exatamente uma vez (`run`, `_call_agent`,
`explain_routing`, `get_tools`, `capabilities`, `capability_registry`,
`_route_via_capabilities`). Compila; comportamento identico (dead-code
removal puro).

### 2.3 `shared/cost_tracker.py` -- caminho de DB configuravel (melhoria)

Antes: `DB_PATH = PROJECT_ROOT / "logs" / "cost_tracking.db"` (fixo,
dentro do OneDrive).

Depois:

```python
DB_PATH = Path(os.environ.get(
    "LILO_COST_DB", str(PROJECT_ROOT / "logs" / "cost_tracking.db")))
```

Backward-compatible (default igual). Permite ao usuario apontar o SQLite
volatil para disco local (ex. `set LILO_COST_DB=C:\lilo_data\cost.db`),
evitando os "disk I/O error" observados em pastas sincronizadas.
Validado: com a env setada, `get_tracker().log_request(...)` grava sem
erro no caminho alternativo.

### 2.4 Lint geral (sem acao -- ruido benigno)

`pyflakes` nos modulos core nao achou nome indefinido nem bug real.
Apenas ruido: um `global _agents` desnecessario em `lilo.py:47` e
algumas f-strings sem placeholder em `scripts/`. Nao corrigidos (zero
impacto funcional); listados aqui por completude.

---

## 3. Estado do repositorio (git) -- ATENCAO

`git status` revela uma **reorganizacao grande ainda nao commitada**:

| Situacao | Itens |
|---|---|
| `?? agents/` (untracked) | toda a arvore `agents/` -- inclusive `villa_lobos/agent.py` |
| `?? lilo_api.py` (untracked) | o entrypoint HTTP que corrompeu |
| `D` (deletados do HEAD) | layout antigo na raiz (`Analise_SQL/`, `PDFs_library/`, `CHANGELOG.md`, ...) |
| `M .env.example` | modificado |
| HEAD | so contem 2 commits "LILO auto-sync" do layout antigo |

**Implicacao de risco:** o `lilo_api.py` que corrompeu **nao tinha
versao no git** para restaurar -- se eu nao tivesse feito backup em
disco local, a recuperacao seria manual. A combinacao
*untracked + OneDrive + arquivo > 30 KB* e o pior cenario para o bug de
truncamento.

**Recomendacao (acao manual do usuario):** commitar a reorganizacao
agora para criar um ponto de recuperacao:

```cmd
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
git add agents/ lilo_api.py lilo_serve.py shared/ docs/ config/ tests/ scripts/
git commit -m "Reorg agents/ + entrypoints + fix lilo_api tail + dedup villa + cost_tracker env"
```

(Nao executei commit/push: a tarefa pede correcoes de codigo, nao
operacoes de git, e a politica e nao tomar acoes de "write" externas nao
solicitadas. As correcoes estao no working tree, prontas para commit.)

---

## 4. Benchmarks -- 1 e 2 iteracoes

> **Metodo:** rodados 100% offline em **modo MOCK** (portas Ollama/LiteLLM
> mortas, sem chave Anthropic). Isso e deliberado: o `.env` tem
> `ANTHROPIC_API_KEY`, e o smoke test detectou backend `anthropic` --
> rodar o pipeline ao vivo faria **chamadas pagas** e, pior, enviaria
> nomes de modelo Ollama (`qwen2.5-coder`) para a API Anthropic, que os
> rejeitaria. O modo mock exercita os caminhos de retry/fallback e mede
> o overhead estrutural sem custo. Numeros de inferencia real dependem do
> Ollama local (segundos por stage).

### 4.1 Latencia de roteamento (smart routing)

Todos os 7 subagentes carregaram (`sql, pdf, scholar, prism, villa,
gateway, desktop`). `explain_routing()` por query:

| Query | ms | dominio | stages planejados | fonte |
|---|---|---|---|---|
| "o que e PCR?" | 0.41 | gateway | orchestrator, reporter | heuristic |
| "faca uma ANOVA comparando 3 grupos" | 0.62 | prism | orchestrator, reporter | heuristic |
| "rode uma query SQL com join" | 0.06 | sql | 5 stages | fallback |
| "resuma este artigo PDF" | 0.05 | pdf | orchestrator, reporter | heuristic |
| "busque papers no pubmed sobre CRISPR" | 0.05 | scholar | orchestrator, reporter | heuristic |
| "pipeline completo multi-dominio" | 0.10 | (nenhum) | 5 stages | fallback |

**Overhead de roteamento: media 0.21 ms, max 0.62 ms.** Desprezivel
frente a qualquer inferencia. A delegacao a especialistas
(`prism`, `sql`, `pdf`, `scholar`) esta funcionando -- e exatamente o
comportamento "LLM chamando agentes capacitados por tarefa" pedido na
tarefa.

### 4.2 Pipeline Villa_Lobos -- 1 vs 2 iteracoes

| Iteracoes | Wall (mock, RETRY_DELAY=0) | Travou? | Auto-corrigiu? |
|---|---|---|---|
| 1 | 0.088 s | nao | sim (fallback acionado) |
| 2 | 0.073 s | nao | sim (fallback acionado) |

O pipeline **completa sem travar** e o caminho de auto-correcao (fallback
de modelo em `_call_agent`) e exercitado. Em mock, stages cujo modelo ==
modelo de fallback (`orchestrator`/`reporter`, ambos usam `llama3.1`)
nao tem segundo fallback e retornam string de erro -- **artefato do mock**
(com backend real a primeira chamada ja responde). Isso revela uma sutileza
de design: o fallback so ajuda quando o modelo do stage difere do
`MODELS["chat"]`. Ver proposta 6.2.

### 4.3 Penalidade de retry (freeze risk real)

`MAX_RETRIES=2`, `RETRY_DELAY=5 s` (constantes do modulo). Quando um
stage realmente falha, ha `(2-1) x 5 = 5 s` de `sleep` antes do fallback.
Num cenario degradado/offline, um pipeline completo (ate ~4 stages LLM x
iteracoes) pode **demorar ~20-25 s** antes de entregar saida de fallback.
**Nao e um hang** (retries sao limitados; deteccao de backend tem timeout
de 1 s), mas e a unica fonte de lentidao perceptivel. Ver proposta 6.3
(retry adaptativo / circuit breaker).

### 4.4 Chat LILO -- 1 vs 2 execucoes

| Execucao | ms | observacao |
|---|---|---|
| 1 (frio) | 215.1 | inclui load de agentes + init de policy/tracker |
| 2 (quente) | 21.4 | ~10x mais rapido (singletons aquecidos) |

**Achado colateral (importante):** na 1a tentativa o chat falhou com
`OperationalError: disk I/O error`. Investigado: **SQLite nao grava na
pasta sincronizada** (`logs/cost_tracking.db`), mas grava em disco local.
Confirmado com sonda:

```
MOUNT (logs/): FAIL -> OperationalError: disk I/O error
LOCAL (/tmp):  OK
```

Isso motivou a melhoria 2.3. No Windows nativo (NTFS) o sintoma pode nao
aparecer sempre, mas SQLite em pasta sincronizada e reconhecidamente
fragil (locking + sync concorrente). Recomenda-se mover `*.db`
(`cost_tracking.db`, `chat_history.db`, `kv_memory.db`) para fora do
OneDrive via as envs correspondentes.

### 4.5 Veredito de eficacia / estabilidade

* **Eficacia de tempo:** overhead do framework e minimo (roteamento sub-ms,
  chat quente ~21 ms). O gargalo real e sempre a inferencia do modelo.
* **Trava?** Nao. Retries limitados, timeouts de deteccao curtos.
* **Auto-corrige?** Sim -- fallback de modelo + cascata de roteamento
  (LLM > heuristica > capabilities). Unico ponto de lentidao: os 5 s de
  `RETRY_DELAY` por stage falho em modo degradado.

---

## 5. MCP & Skills -- avaliacao e melhorias

### 5.1 Perfis MCP (`config/mcp/`)

Estado bom e coerente. 6 perfis: `claude_desktop` (opus, 18 tools),
`claude_code` (complementar ao CLI nativo), `pycharm`, `openclaw`,
`bio` (27 tools, sem `run_shell`), `claude_code_full`. A documentacao
inline (tokens, como desligar Desktop Commander) esta excelente.

**Gaps / melhorias sugeridas:**

1. **Perfil `cowork`** -- nao existe um perfil para o ambiente Cowork
   (este). Sugiro um `config/mcp/cowork.json` apontando para o profile
   `bio` (foco biomolecular, sem `run_shell`, seguro para automacao). So
   criar o arquivo apos confirmar que `lilo_mcp.py` aceita o profile.
2. **Caminho hardcoded** -- todos os perfis fixam
   `C:\Users\luizd\...\IA.agente`. Apos mover o repo (recomendacao
   recorrente), todos quebram juntos. Sugiro um placeholder + script
   `scripts/render_mcp_profiles.py` que gera os JSON a partir de
   `LILO_HOME`.
3. **Inconsistencia de interpretador** -- `claude_desktop.json` usa
   `"command": "python"` (PATH), os demais usam
   `C:\Users\luizd\miniforge3\python.exe`. Padronizar para o miniforge
   evita "funciona no PyCharm mas nao no Desktop".

### 5.2 Skills (`lilo_skills/`)

`registry.json` com 199 funcoes; 13 `SKILL.md` por pacote gerados em
2026-05-14 (matplotlib, numpy, scipy, pandas, seaborn, etc.). Front-matter
compativel com Anthropic Skills.

**Melhorias sugeridas:**

1. **Skills de dominio do usuario** -- as skills hoje sao bibliotecas
   genericas (matplotlib, numpy). Faltam skills de **bio molecular /
   bioinformatica** (parsing FASTA/GenBank, traducao de codons, analise de
   qPCR/ddCt, leitura de `.pzfx`/GraphPad, MDAnalysis/mdtraj). Sao o maior
   ROI para o perfil do usuario.
2. **Triggers em PT-BR** -- varios SKILL.md tem triggers so em ingles.
   Adicionar sinonimos PT (ex. `grafico`, `figura`, `tabela`) melhora o
   match no uso real.
3. **`complexity=high` zerado** -- o schema preve, mas nenhuma skill usa.
   Sem acao urgente; remover do schema se nao for usar.

---

## 6. Villa_Lobos -- desenvolvimento continuo (propostas com codigo)

A tarefa pede ajustar o orquestrador para "atuar como LLM chamando
diferentes agentes capacitados, sempre de acordo com o setup do servidor".
Hoje a cascata LLM > heuristica > capabilities ja faz o roteamento. As
propostas abaixo (em ordem de ROI) avancam isso. **Nao foram aplicadas
ao vivo** porque tocam arquivos grandes/multiplos e nao sao bug fixes --
entrego como diffs prontos para revisao do usuario.

### 6.1 Capabilities reais por subagente (item #2 de 2026-05-14)

Hoje todo subagente cai no fallback de `domains.yaml`. Sobrescrever
`capabilities()` em cada agente permite *cost-aware routing* (decidir
Ollama local vs Anthropic por custo/latencia). Exemplo em
`agents/Analise_SQL/agent.py`:

```python
def capabilities(self):
    return {
        "domain": "sql",
        "keywords": ["sql", "select", "join", "sqlite", "duckdb", "schema"],
        "tools": [t["name"] for t in self.get_tools()],
        "cost_tier": "ollama",      # roda 100% local
        "local_only": True,
        "latency_class": "fast",
        "description": self.description,
    }
```

E o Villa passa a ranquear nao so por keyword, mas por
`(score_keyword, prefere_local, latency_class)`.

### 6.2 Fallback por tier (item #5)

`_call_agent` hoje so faz fallback de modelo dentro do Ollama. Estender
para escalar de tier quando o local falha repetidamente:

```python
# em _call_agent, apos esgotar Ollama:
if result_text is None and get_env("LILO_ALLOW_CLOUD_FALLBACK", "0") == "1":
    log.warning("    Escalando stage %s p/ claude_sonnet (Ollama falhou)", role)
    result_text = self.client.chat(prompt=prompt, system=system,
                                    tier="claude_sonnet", max_tokens=4096)
    backend_label = "claude_sonnet"
```

Gated por env (default off) para nunca gastar sem o usuario optar.

### 6.3 Retry adaptativo + circuit breaker (mitiga 4.3)

`RETRY_DELAY=5` e caro para Ollama local (que falha rapido). Tornar
adaptativo:

```python
RETRY_DELAY = float(_os.getenv("VILLA_RETRY_DELAY", "1.5"))
# e abrir circuito: se o backend == "mock"/indisponivel, pular retries
if self.client.backend == "mock":
    MAX_RETRIES_EFFECTIVE = 1   # nao adianta repetir contra mock
```

Elimina os 5 s/stage em cenario degradado.

### 6.4 Server profile detection (item #7) -- "de acordo com o setup do servidor"

Esta e a frase literal da tarefa. Propor um `lilo_server_profile` lido de
`config.yaml`/env no boot, que muda as decisoes de delegacao:

```python
# shared/server_profile.py (novo)
def get_server_profile():
    return get_env("LILO_SERVER_PROFILE", "desktop_dev")
    # desktop_dev | pycharm_assistant | claude_desktop | cowork | bio

# em VillaLobosAgent: ajustar tiers/delegacao por profile
PROFILE_POLICY = {
    "bio":            {"prefer_local": True,  "allow_cloud": False},
    "claude_desktop": {"prefer_local": False, "allow_cloud": True},
    "cowork":         {"prefer_local": True,  "allow_cloud": False},
}
```

Assim o mesmo Villa se comporta diferente conforme onde roda -- exatamente
o pedido.

### 6.5 Multi-agente simultaneo (item #3)

Quando a query menciona >1 dominio ("compare o paper X com a tabela SQL
Y"), chamar 2+ subagentes via `asyncio.gather` e sintetizar no Reporter.
Os "cabos" ja existem em `_orchestrate_decision`; falta o wire. Esforco
medio; alto valor para fluxos de pesquisa do usuario.

---

## 7. Plataforma hibrida (API rodando o agente, estilo Claude Desktop)

A tarefa pede "plataforma hibrida com API rodando o agente similar ao
Claude Desktop". A Fase A (2026-05-14) ja entregou `lilo_serve.py`
(`--transport stdio|http|sse`) e `/health` publico. Proximos passos para
"estilo Claude Desktop":

1. **Sessoes + streaming** -- `POST /v1/chat/stream` (SSE) ja previsto;
   ligar ao `chat_memory` por `session_id` para conversas continuas
   (estado server-side, como o Desktop).
2. **Roteamento server-side identico ao MCP** -- a API HTTP deve chamar
   o mesmo `lilo.route()` e Villa que o MCP usa, garantindo paridade de
   comportamento entre Claude Desktop (MCP/stdio) e clientes HTTP.
3. **Healthcheck rico + readiness** -- `/health` (liveness, ja existe) +
   `/v1/health` (readiness: Ollama up? modelos baixados? budget ok?).
4. **Auth multi-token** (ROADMAP item I) -- tokens por cliente para uso
   alem do localhost.
5. **CI minimo (item #4)** -- 1 workflow GitHub Actions rodando
   `pytest tests/` + `python scripts/smoke_test_v11.py` em push. E a
   defesa mais barata contra regressoes como a de hoje.

---

## 8. Roadmap atualizado -- proxima execucao

Concluido hoje: fix `lilo_api.py`, dedup Villa, DB configuravel, suite de
benchmarks 1/2 iteracoes.

**Prioridade para a proxima rodada:**

1. **Commitar a reorg** (secao 3) -- cria ponto de recuperacao. Sem isso,
   qualquer corrupcao de arquivo untracked e perda definitiva. (manual)
2. **Mover repo + DBs para fora do OneDrive** (`C:\dev\IA.agente`,
   `LILO_COST_DB`, etc.) -- causa-raiz recorrente. (manual)
3. **CI minimo** (pytest + smoke + AST) -- pega o proximo `lilo_api.py`
   antes de quebrar.
4. **Capabilities reais por subagente** (6.1) + **server profile** (6.4) --
   o nucleo do "LLM chamando agentes conforme o setup do servidor".
5. **Retry adaptativo** (6.3) -- elimina os 5 s/stage degradado.
6. **Fallback por tier** (6.2, gated) e **multi-agente** (6.5).

---

## 9. Debitos tecnicos remanescentes

| Item | Severidade | Sugestao |
|---|---|---|
| Reorg `agents/`/`lilo_api.py` untracked | **alta** | commit imediato |
| OneDrive corrompe arquivos > 30 KB (NUL/truncamento) | **alta** | mover repo; editar via disco local + copia |
| SQLite em pasta sincronizada (disk I/O error) | media | `LILO_COST_DB` + mover `*.db` |
| Sem CI | media | GitHub Actions: pytest + smoke + AST |
| Subagentes sem `capabilities()` proprios | baixa | sobrescrever (6.1) |
| `RETRY_DELAY=5` fixo penaliza Ollama local | baixa | adaptativo (6.3) |
| Skills sem dominio bio molecular | media (ROI) | criar skills FASTA/qPCR/pzfx |
| Perfil MCP `cowork` ausente | baixa | criar apos validar profile |

---

## 10. Verificacoes finais

```
AST scan completo .......... 260 arquivos, 0 erros
pytest ..................... 12 passed in ~1.5s
smoke_test_v11.py .......... PASSOU: 13 | FALHOU: 0
lilo_api.py ................ compila, 0 NUL (corrigido)
agents/villa_lobos/agent.py  16 metodos, 0 duplicatas (corrigido)
shared/cost_tracker.py ..... LILO_COST_DB funcional (melhoria)
Benchmark roteamento ....... media 0.21 ms / max 0.62 ms
Benchmark Villa 1 iter ..... 0.088 s, sem travar, auto-corrige
Benchmark Villa 2 iter ..... 0.073 s, sem travar, auto-corrige
Benchmark chat LILO ........ 215 ms frio / 21 ms quente
```

**Arquivos alterados nesta execucao:**
`lilo_api.py`, `agents/villa_lobos/agent.py`, `shared/cost_tracker.py`
(no working tree, prontos para commit; backups em disco local da sessao).

_Relatorio gerado automaticamente via tarefa agendada `ia_lilo` em 2026-05-20._
