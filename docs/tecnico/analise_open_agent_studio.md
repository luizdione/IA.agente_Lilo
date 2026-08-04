# Análise de gap — spec "Open Agent Studio" × LILO v12.4

Data: 2026-08-04 · Base de código: branch `arch-v11` mergeado no `main` (v12.4 / V17.2, 120 testes) · Método: exploração do repositório com evidência `arquivo:linha`, verificação por grep dos achados críticos.

## 1. Origem e método

O dono do LILO trouxe uma spec de projeto hipotético — **"Open Agent Studio"**, um ambiente de desenvolvimento open-source inspirado no Claude Code (roteador multi-LLM, sistema de agentes com supervisor, memória em Markdown, RAG multi-formato, Docker Compose completo, UI React com editor, cliente MCP, workflows automáticos, dashboard de telemetria, segurança e plugins/SDK) — e pediu: *onde o LILO pode melhorar?*

Este documento compara cada dimensão da spec com o estado real do código e classifica cada uma em **ADOTAR** (gap real, vale fechar), **ADAPTAR** (a ideia vale, a implementação proposta não — fazer do jeito LILO) ou **REJEITAR** (inadequado ao contexto: dev solo, Windows nativo + RTX 3060 12GB, local-first, budget cloud US$1/dia, frugalidade de tokens).

## 2. Diagnóstico central: esqueleto pronto, fiação desconectada

Mesmo padrão que a V15 diagnosticou em `docs/ROADMAP_claude_alignment.md` ("o LILO já tinha o esqueleto, mas desconectado"). A spec valida muito do que o LILO já tem de estrutura; **o gap dominante não é feature faltando, é canal morto**:

- O Policy Engine decide tier/modelo por query (`shared/policy.py:185-268`) e grava em `ctx["_tier"]`/`ctx["_model"]` (`lilo.py:189-190`) — **nenhum subagente lê essas chaves** (verificado por grep). Cada agente escolhe o próprio modelo em 4 padrões dispersos; a decisão do Policy vira só telemetria.
- `latency_class`/`cost_tier` são declarados por todos os agentes (`shared/base_agent.py:69-83`) e nunca entram na decisão de modelo.
- O custo registrado é **estimado por chars/4** (`lilo.py:285-293`, `tokens_in/out=0`); o `msg.usage` real da resposta Anthropic é descartado (`shared/llm_client.py:323-355`) — inclusive `cache_read_input_tokens`, relevante porque o prompt caching já está ativo.
- `LILO_ALLOW_CLOUD` (`.env.example:38`) nunca é lido — o gate real de nuvem é a mera presença de `ANTHROPIC_API_KEY` (`policy.py:85`). `LILO_MAX_SINGLE_COST` é lido (`policy.py:80`) e nunca aplicado.
- 4 agentes têm default cloud `gpt-oss:120b-cloud` (Ollama Cloud) — skillsmith (`agents/skillsmith/agent.py:37`), docgen (`agents/docgen/agent.py:37`), scholar review (`agents/scholaragent/agent.py:359`), villa worker geral (`agents/villa_lobos/agent.py:278-279`) — um provedor que o Policy Engine **nem modela**: invisível ao budget e à telemetria de custo.

Conclusão estratégica: **religar canais antes de construir salas novas.** ~60% da spec converge com o backlog que o LILO já registrou em `docs/ROADMAP.md`; o genuinamente novo e valioso que ela acrescenta é (a) fiação policy→agentes como prioridade, (b) cliente MCP, (c) gate de privacidade pré-cloud, (d) CI.

## 3. Matriz de gap (15 dimensões)

| # | Dimensão da spec | LILO hoje | Veredito | Por quê |
|---|---|---|---|---|
| 1 | Router multi-provedor (DeepSeek/Gemini/OpenAI/OpenRouter) | **Parcial** — LiteLLM→Ollama→Anthropic→mock (`shared/llm_client.py:82-118`); zero código p/ outros provedores | **ADAPTAR** | Não codar clients: LiteLLM proxy já é o backend nº 1 — provedores extras entram por YAML, zero Python (H3·S2) |
| 2 | Seleção automática por contexto/custo/velocidade/capacidade | **Parcial com bug** — Policy decide e ninguém obedece; latência/tokens/capacidade fora dos critérios | **ADOTAR** (prioridade máxima) | O motor existe; falta obedecê-lo (H1·QW2 + H2·E1) |
| 3 | Controle de custo (real, com limites) | **Parcial** — SQLite ok (`shared/cost_tracker.py`), mas custo estimado, `MAX_SINGLE_COST` morto | **ADOTAR** | `msg.usage` vem de graça na resposta; colunas `tokens_in/out` já existem no schema (H1·QW3-QW4) |
| 4 | Supervisor que decompõe tarefas | **Já tem** — Villa 5 estágios + `_decompose_chain` (máx 4 steps, whitelist) + delegação a especialista | **REJEITAR ampliação** | Cobre o caso de uso real; "empresa de agentes" genérica é overengineering p/ dev solo |
| 5 | Agentes conversando entre si | **Não tem** — encadeamento é concat textual sequencial | **ADAPTAR (mínimo)** | Handoff leve (dict de artefatos entre steps) resolve 80%; mensageria genérica, não (H2·E7) |
| 6 | Memória Markdown de projeto (CLAUDE.md, TASKS.md…) | **Parcial** — `notes.md` interno por projeto; `dir_synthesis` **não** lê CLAUDE.md/TASKS.md/DECISIONS.md (`shared/dir_synthesis.py:51-60`) | **ADOTAR** leitura / **ADAPTAR** escrita | Ler é estender `_KEY_FILES`; escrever no projeto do usuário só via gate `write_outside` (H2·E4) |
| 7 | Memória de longo prazo (semântica, versionada) | **Parcial** — KV SQLite maduro (ns/tags/TTL, 8 tools MCP), busca LIKE, sem histórico | **ADOTAR** | ROADMAP item D já previa; `mxbai-embed-large` já está no `.env` e em `MODELS["embed"]` (H2·E2) |
| 8 | RAG multi-formato (DOCX/XLSX/notebooks/código) | **Parcial** — pipeline forte só p/ PDF (Chroma + reranker + **gate factual**, diferencial que a spec nem pede); escopo travado no lab | **ADAPTAR** (H3) | Generalizar o pipeline que JÁ existe (`scholaragent/brain/`), não criar outro (H3·S1) |
| 9 | Docker completo (redis/nginx/watchtower) | **Parcial** — compose existe (ollama/litellm/lilo_api), com ref quebrada `scistudio` | **REJEITAR** (manter opcional) | Windows nativo + GPU é o ambiente real; redis/nginx/watchtower respondem a problemas multi-usuário que não existem aqui |
| 10 | UI React + editor estilo VS Code | **Não tem** — Streamlit 2437 linhas maduro (chat c/ exec modes, STT+voiceprint, custos, GPU) | **REJEITAR** | Meses de reescrita p/ paridade, mantida por 1 pessoa; o editor real já existe (PyCharm + perfil MCP `pycharm` com `fs_*`/`run_*`/`fs_codemod`) |
| 11 | Cliente MCP (consumir servidores externos) | **Não tem** — zero `ClientSession` no repo | **ADAPTAR** (H2) | Gap real e estratégico: destrava o ecossistema (github, fetchers) sem escrever integrações próprias (H2·E6) |
| 12 | Servidor MCP | **Já tem** — FastMCP, 53 tools em 13 grupos, 7 perfis com hot-reload (`lilo_mcp.py`, `config/profiles.yaml`) | **manter** | LILO está à frente da spec aqui; só faltam tools git (H2·E7) |
| 13 | Workflow dev (executa→testa→commita→docs→memória) | **Parcial** — peças soltas: verify-stage sandbox (off), gate `git_write` escopado, notes.md | **ADAPTAR** | Encadear o que existe num stage opt-in do Villa, não construir motor novo (H2·E7) |
| 14 | Segurança (permissão por agente, privacidade pré-cloud, secrets) | **Parcial** — allow-list de paths robusta + DANGEROUS_PATTERNS + exec modes; MAS nuvem = presença de key, sem gate de privacidade; chaves em `.env` texto plano | **ADOTAR** (gate cloud) | Com 4 agentes defaultando cloud em silêncio, o gate pré-envio é a lacuna de segurança mais real (H2·E5) |
| 15 | Plugins/SDK/marketplace + lifecycle de skills | **Parcial** — 199 skills auto-geradas (registry.json); novo agente = registro manual em 4-5 lugares | **ADAPTAR** loader / **REJEITAR** marketplace | Manifest + discovery reduz atrito; marketplace distribui para usuários que não existem (H3·S3) |

## 4. Bugs e inconsistências encontrados na análise (valor imediato)

1. **`agents/paper/` fantasma.** Registrado em `lilo.py:61`, citado no README, `docs/agentes/paper.md` e `tests/test_paper_agent.py` — mas `git log -- agents/paper` é **vazio**: o diretório nunca foi commitado (existe só na máquina Windows do dono). O import falha em silêncio (`lilo.py:71-72`), as tools `paper_draft/paper_section/paper_references` expostas no MCP (`lilo_mcp.py:421-453`) caem no vazio e o teste erra em qualquer máquina limpa.
2. **`ctx["_tier"]`/`ctx["_model"]` nunca consumidos** — a decisão do Policy Engine não chega ao modelo executado (ver §2).
3. **`LILO_MAX_SINGLE_COST` nunca aplicado**; **`LILO_ALLOW_CLOUD` nunca lido** (`policy.py:80,85`).
4. **`usage` da Anthropic descartado** — custo real e cache hits invisíveis (`llm_client.py:323-355`).
5. **`pdf_search` não é semântica** — o nome promete busca semântica, mas `_semantic_search()` (`agents/PDFs_library/agent.py:209`) só lista nomes de arquivo e pede ao LLM para adivinhar. A busca semântica real está em `shared/scholar_brain.py` (tool `scholar_brain`).
6. **Compose com ref quebrada** — serviço `scistudio` aponta p/ `./conteudo_digital/studio`, ausente do repo (`docker-compose.yml:119-125`); `Dockerfile.api` usa py3.11 vs py3.13 do repo.
7. **Envs fora do `.env.example`**: `LILO_LLM_RETRIES/BACKOFF`, `LILO_ANTHROPIC_CACHE`, `LILO_COST_DB`, `LILO_SERVER_PROFILE`, `LILO_SKILLSMITH_MODEL`, `LILO_DOCGEN_MODEL`, `LILO_REVIEW_MODEL`; `LLM_TIMEOUT` divergente (120 no .env.example vs 300 no código). `OPENAI_API_KEY` é placeholder morto.
8. **`docs/tecnico/` desatualizado** — `arquitetura_v10.md` para em v10.5; não há doc de arquitetura v11/v12; `docs/ROADMAP.md` para em v10.6.

## 5. Roadmap priorizado

> Princípio (herdado da V15): **tudo aditivo e default-safe** — comportamento atual preservado; ativação por flag.

### H1 — Quick wins (dias; alto valor, baixo risco)

> **Status: QW1–QW7 aplicados na V18 (2026-08-04)** — detalhes em
> `docs/versoes/CHANGELOG.md` v12.5. Ressalvas: no QW1 o caminho executado foi
> o plano B (importorskip + teste do skillsmith desacoplado do fantasma — que,
> descobriu-se, **criava** `agents/paper/` em checkout limpo); commitar o
> diretório real continua pendente na máquina de origem. QW2 está na fase 1
> (log de divergência, sem enforcement — ver E1).

| ID | O quê | Onde | Nota |
|---|---|---|---|
| QW1 | Resolver o `paper` fantasma: commitar o diretório da máquina Windows (preferido) **ou** desregistrar (`lilo.py:61`, tools MCP) + `pytest.importorskip` no teste | `agents/paper/`, `lilo.py`, `lilo_mcp.py`, `tests/test_paper_agent.py` | Recuperação de estado; risco zero |
| QW2 | Fiação policy→agentes, fase 1: helper `resolve_model(ctx, default)` no `BaseAgent` (precedência: env explícito do agente > `ctx["_model"]` > default) + **log de divergência** ("policy pediu X, agente usou Y") | `shared/base_agent.py` + 4 agentes com modelo próprio | Só observar antes de forçar: o bench 2026-06-12 mostrou worker cloud +107% de qualidade vs 8b local — enforcement vem com E1 |
| QW3 | Aplicar `LILO_MAX_SINGLE_COST` em `_budget_allows` e reviver `LILO_ALLOW_CLOUD` (`allow_cloud = env && bool(key)`) | `shared/policy.py:393-397,85` + teste | ~5 linhas |
| QW4 | Custo real: gravar `msg.usage` (input/output/cache_read) no CostTracker **dentro** do `llm_client` — todos os callers ganham de graça | `shared/llm_client.py`, `shared/cost_tracker.py` | Cuidado com dupla contagem vs estimativa gravada em `lilo.route` |
| QW5 | Latência p50/p95 no dashboard (`duration_ms` já é gravado por request) | `shared/cost_tracker.py` (novo `latency_summary()`), `dashboard.py` aba Custos | Risco zero |
| QW6 | CI mínimo: `.github/workflows/tests.yml` com pytest (suíte já é offline por design — mock backend) | novo workflow | Depende do QW1 (hoje `test_paper_agent.py` erra em máquina limpa — o CI teria pego isso há meses) |
| QW7 | Higiene do compose: remover/comentar `scistudio`, alinhar py3.11→3.13; limpar `OPENAI_API_KEY` morta e completar `.env.example` (§4.7) | `docker-compose.yml`, `Dockerfile.api`, `.env.example` | — |

### H2 — Estruturais (semanas)

> **Status (V18.1, 2026-08-04):** E1 (catálogo de modelos + tier
> `OLLAMA_CLOUD` + telemetria; enforcement e validação de boot pendentes),
> E4 (leitura de CLAUDE.md/TASKS.md/docs//prompts/; refresh por mtime
> pendente) e E5 (gate `cloud_send`; scrubber de segredos pendente)
> aplicados — ver CHANGELOG v12.6. Pendentes: E2, E3, E6, E7, E8.

- **E1. Catálogo de modelos + roteamento centralizado de verdade.** Novo `shared/model_catalog.py`: `{provider, context_tokens, capabilities: [code|reasoning|general], latency_class, cost_per_1k}` por modelo, validado no boot contra `list_models()` (`llm_client.py:190-201`, hoje não alimenta nada). Policy ganha tier `OLLAMA_CLOUD` (modela os `gpt-oss:*-cloud`, hoje invisíveis ao budget), estimativa de contexto em tokens e uso do `latency_class` que os agentes já declaram. Completa o QW2 (enforcement) e absorve o item L do ROADMAP (multi-LLM por estágio do Villa).
- **E2. Embeddings semânticos no KV** (= ROADMAP item D). Coluna `embedding BLOB` em `shared/kv_memory.py`, embed via Ollama `MODELS["embed"]` (mxbai já configurado), `search_semantic()` com cosine em numpy, tool `lilo_memory_semantic_search`. **Não** trazer ChromaDB para o KV — SQLite+numpy basta na escala de memória pessoal; Chroma fica no scholaragent.
- **E3. `memory_facade` + `lilo_recall` + smart context do Reader** (= ROADMAP itens A+C). `get_relevant_context(query, project_id, k)` combinando KV (semântico do E2, LIKE como fallback) e chat_memory; plugar no chat, no `lilo.route` (substitui o inject manual de `lilo.py:211-229`) e no Reader do Villa. Sequência: E2 antes de E3.
- **E4. Memória Markdown do projeto — leitura ampla, escrita gated.** Estender `_KEY_FILES` (`shared/dir_synthesis.py:51-60`) com `CLAUDE.md, TASKS.md, CONTEXT.md, DECISIONS.md, NOTES.md, AGENTS.md` + varrer `docs/` e `prompts/` (1 nível); refresh automático por mtime (cache em KV com TTL) em vez do botão manual. Escrita nos markdowns do usuário: tool opt-in passando pelo gate `write_outside` do `shared/exec_mode.py` — nunca automática. O KV continua sendo o storage primário; markdown é interface.
- **E5. Gate de privacidade pré-cloud.** Novo tipo `cloud_send` no `gate()` do `shared/exec_mode.py:114`, chamado em `llm_client._dispatch_chat` quando o destino é Anthropic ou `*-cloud`: em `ask`/`plan` pede confirmação com preview do payload; em `auto` mantém comportamento atual mas **loga destino+bytes** (default-safe); scrubber regex de segredos (API keys, paths `C:\Users\`) antes do envio. Respeita o `LILO_ALLOW_CLOUD` revivido no QW3. Fecha o requisito da spec "nunca enviar sem autorização explícita".
- **E6. Cliente MCP mínimo.** `shared/mcp_client.py` (`ClientSession` stdio) sobre servidores declarados em `config/mcp/clients.yaml` com allow-list de servidores **e** de tools (espelha a filosofia da allow-list de paths). Exposição inicial: tool interna `mcp_call(server, tool, args)` para Worker do Villa e desktop agent — sem injeção dinâmica de tools externas no servidor MCP do LILO (evita explosão de superfície). Impedância async/sync: `anyio.run` por chamada.
- **E7. Workflow dev opt-in** (`LILO_DEV_WORKFLOW=1`): stage pós-Worker do Villa encadeando o que já existe — pytest alvo no sandbox do verify-stage → commit via gate `git_write` escopado → atualizar notes.md → gravar resumo no KV. Complemento: tools MCP `git_status/git_diff/git_commit` no perfil `pycharm`, todas sob o mesmo gate.
- **E8. Split do dashboard em páginas multipage** (= ROADMAP item E; o trabalho começou na v12.4 com `dashboard_styles.py`). Pré-requisito para os painéis crescerem (latência, roteamento, MCP).

### H3 — Estratégicos/opcionais (avaliar custo/benefício com caso de uso na mão)

- **S1. RAG multi-formato unificado** (= ROADMAP item J ampliado): generalizar `scholaragent/brain/` (embedder, vector_store, verify) com extractors plugáveis p/ DOCX/XLSX/ipynb. Passo zero barato: mover `LAB_THEMES` hardcoded (`scholaragent/brain/classifier.py:7-16`) para `config/`. BM25 híbrido só se benchmark próprio mostrar recall ruim.
- **S2. DeepSeek/Gemini/OpenRouter via LiteLLM YAML** — zero código Python; DeepSeek pode multiplicar o orçamento efetivo de US$1/dia. **Só após E5** (gate de privacidade) existir.
- **S3. Loader de agentes por manifest** — `agents/<nome>/manifest.yaml` + discovery em `_load_agents()` **restrito a nomes listados em `config/profiles.yaml`** (preserva a decisão de segurança do não-auto-registro do scaffold); reduz os 4-5 pontos de registro manual para 2. Teria evitado o bug do paper.
- **S4. Hardening do `lilo_api`** — token obrigatório quando bind ≠ 127.0.0.1 + rate limit. Só se exposto na rede.
- **S5. Versionamento da memória KV** — tabela `kv_history` (append via trigger no UPDATE) com retenção N; fazer junto com E2 se o schema abrir de qualquer forma (o backup diário externo já mitiga).

**Sequenciamento:** H1 inteiro em 1-2 sprints curtos (QW1→QW3→QW4 independentes; QW6 depois de QW1). H2: E1 → E2 → E3 (dependência real), E4/E5 em paralelo, E6/E7 depois. H3 só com caso de uso concreto.

## 6. Rejeições explícitas (com o custo nomeado)

1. **UI React + editor embutido.** 2437 linhas de Streamlit funcionais vs meses de reescrita para paridade, mantida por uma pessoa. O "editor" da spec já existe melhor: PyCharm/VS Code + perfil MCP `pycharm`. O que a spec realmente pede (organização, painéis) o E8 entrega por ~2% do custo. Reavaliar só se surgir necessidade multi-dispositivo — e aí o caminho é `lilo_api` + front fino, não portar o dashboard.
2. **Redis/nginx/watchtower/Docker como caminho principal.** Respostas a problemas de multi-usuário/produção que um sistema single-user em Windows nativo com GPU local não tem; Docker+CUDA no Windows adiciona a camada WSL2 que a filosofia local-first evita. Compose permanece opcional (QW7 conserta o que está quebrado). Para a fila do PRISM (ROADMAP F): `ProcessPoolExecutor`, sem Celery+Redis.
3. **Marketplace de skills/plugins.** Marketplace serve distribuição para terceiros; o LILO tem um usuário, que é o autor. As 199 skills auto-geradas já são um catálogo auto-mantido. O útil fica no S3 (manifest) e, se doer, `skill disable/regenerate` no registry.
4. **Mensageria genérica inter-agente.** O Villa com `_decompose_chain` é deliberadamente simples e depurável; barramento de mensagens entre agentes autônomos multiplica estados e custo de debug sem caso de uso que o contexto-concatenado não resolva. Evolução, se precisar: dict de artefatos tipados entre steps (E7).
5. **Multi-tenant/RBAC.** Single-user por definição; o embrião (`LILO_API_TOKEN`) já cobre o único cenário real (expor na LAN → S4).
6. **Markdown como storage primário de memória.** O KV SQLite (ns/tags/TTL/8 tools) é superior como storage; markdown entra como leitura (E4) e export gated — nunca substituindo o KV.

## 7. Convergências spec ↔ ROADMAP existente (validação dupla — priorizar)

| Pendência do `docs/ROADMAP.md` | Dimensão da spec que a valida | Destino |
|---|---|---|
| D — embeddings semânticos no KV | Memória de longo prazo | **E2** (1ª prioridade estrutural) |
| A — `memory_facade` + `lilo_recall` | Memória de agente | **E3** |
| C — smart context do Reader | Supervisor/contexto | **E3** (mesma entrega) |
| L — multi-LLM por estágio do Villa | Router multi-LLM | **E1** |
| E — split do dashboard | Dashboard | **E8** |
| J — RAG estruturado | RAG multi-formato | **S1** |
| G — plugin loader local | Plugins/SDK | **S3** (manifest, sem marketplace) |
| F — worker queue PRISM | Workflows/async | H3 oportunista (`ProcessPoolExecutor`, sem Redis) |

## 8. Flags novas propostas (.env)

```
LILO_ALLOW_CLOUD=true       # revivido (QW3): passa a ser lido de fato (E && key)
LILO_MAX_SINGLE_COST=0.50   # passa a ser aplicado em _budget_allows (QW3)
LILO_CLOUD_GATE=telemetry   # E5: telemetry|ask — gate de privacidade pré-cloud
LILO_DEV_WORKFLOW=0         # E7: stage opt-in testa->commita->documenta
```

---

*Gerado a partir de exploração do código em 2026-08-04; todos os `arquivo:linha` citados foram verificados nesta data. Padrão do documento segue `docs/ROADMAP_claude_alignment.md` (V15).*
