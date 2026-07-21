# LILO — Roadmap de desenvolvimento

**Última atualização:** 2026-06-11
**Versão atual:** v10.6

---

## Onde estamos (v10.0 → v10.6)

| Versão | Marco principal |
|---|---|
| v10.0 | Arquitetura unificada — `lilo_mcp.py --profile`, Desktop Commander, Claude 4.5/4.6 |
| v10.1 | Aba Desktop no dashboard, smart routing Villa-Lobos, pre-commit hook AST |
| v10.2 | 8 novas tools MCP centralizadas (memory + cost + ollama manager); skills `schema_version` |
| v10.2.1 | Hotfix menu `/` no dashboard |
| v10.3 | Memória robusta (TTL, search, WAL, fora do OneDrive) + 4 tools novas |
| v10.4 | Profile MCP `opus` (curado) + descriptions reescritas |
| v10.5 | Plataforma híbrida (`lilo_api`/`lilo_serve`), dashboard estilo Claude Desktop, Villa **V11.2** (guarda fast-path unificada, retry 4xx, de-viés de domínio), juiz LLM (`quality_judge`) |
| **v10.6** | **V12**: roteamento semântico como porta única (`route_target`), Modo IA → Auto, delegação por etapa + **cadeia multi-especialista** (`_decompose_chain`); busca ampliada (OpenAlex, Europe PMC, Google Books, Wikipedia); empty state do dashboard |

**Estado atual:** 7 subagentes; core skills no menu `/` + skills geradas
(contagem viva em `lilo_skills/registry`); tools MCP por profile em
`lilo_mcp.py` `_PROFILE_TOOLS`.

---

## v10.4 — Próxima sprint sugerida (curto prazo, 1-2 sprints)

### A. Unificar `chat_memory` e `kv_memory`

Hoje há dois bancos SQLite separados (`chat_history.db` e `kv_memory.db`).
Cada um com loader/conexão próprios. Quando o agente quer "lembrar do
chat anterior do projeto X", precisa de plumbing manual.

**Proposta:**
- Manter os dois bancos (escopos diferentes), mas criar `shared/memory_facade.py` com API unificada `get_relevant_context(query, project_id, k=5)` que:
  - Busca no `kv_memory` (search textual + filtra por ns="project:<id>")
  - Busca no `chat_memory` (últimas N mensagens do projeto + match textual nos titles)
  - Retorna lista ordenada por relevância simples (recência + match score)
- Plugar essa fachada no chat do dashboard 8100, no `lilo_chat`, e no Villa-Lobos `_orchestrate_decision()` (se a query mencionar "lembra do que falamos sobre X").

**Entregáveis:**
- `shared/memory_facade.py`
- Doc em `docs/tecnico/memoria.md` com seção "API unificada"
- Tool MCP `lilo_recall(query, project_id="")` que retorna o contexto.

### B. Tool MCP `lilo_pull_model` com progress streaming

Hoje `lilo_pull_model` retorna apenas o output final do `ollama pull`.
Para downloads grandes (modelos de 5-10 GB), o usuário fica "no escuro".

**Proposta:**
- Adicionar tool `lilo_pull_model_stream(name)` que usa `subprocess.Popen` e retorna chunks via SSE (compatível com `/v1/chat/stream` na API HTTP).
- Variante simplificada para clientes não-stream: log periódico em `kv_memory` ns=`pull_progress` que pode ser consultado por outra tool.

### C. Smart context para Villa-Lobos

Atualmente o Reader (stage 3) lê o `base_path` mas não consulta `kv_memory` nem `chat_memory`.

**Proposta:**
- Reader chama `memory_facade.get_relevant_context(query, project_id)` antes de varrer arquivos.
- Reduz latência (não precisa varrer árvore inteira) e melhora qualidade (puxa decisões anteriores).

### D. Embeddings semânticos opcionais (`mxbai-embed-large` já está no .env)

**Proposta:**
- Adicionar coluna `embedding BLOB` em `kv` (opcional, só popula quando solicitado).
- `mem.set(..., embed=True)` calcula e salva o vetor.
- `mem.search_semantic(query, k=5)` faz cosine similarity.
- Tool MCP `lilo_memory_semantic_search(query, k)`.

---

## v10.5 — Médio prazo (2-4 sprints)

### E. `dashboard.py` — Quebrar em módulos

`dashboard.py` está com **2139 linhas**. Ficou grande demais.

**Proposta:**
- Mover cada `elif page == "X"` para `dashboard/pages/<x>.py`.
- `dashboard.py` vira só roteador/sidebar (~200 linhas).
- Streamlit nativo suporta multipage com pasta `pages/`.

### F. PRISM AI — Worker queue para análises pesadas

Análises de PRISM em datasets grandes (>10k linhas) bloqueiam o dashboard.

**Proposta:**
- Adicionar worker em background (Celery local com Redis, ou simples `concurrent.futures.ProcessPoolExecutor`).
- `prism_analyze` retorna imediatamente um `job_id`.
- Tool nova `lilo_job_status(job_id)` para acompanhar.

### G. Plugin marketplace local

Hoje as 7 skills CORE + 4 subagentes especialistas estão hard-coded.

**Proposta:**
- Pasta `plugins/<nome>/{plugin.json, agent.py, schema.json}`
- Loader em `lilo._load_agents()` faz discovery.
- Permite instalar plugins customizados sem editar `lilo.py`.

### H. Observabilidade — dashboard de custos com gráficos

A aba Custos hoje mostra apenas tabelas. Adicionar:
- Gráfico de gasto diário (últimos 30 dias) com `st.line_chart`.
- Pizza de gastos por subagente.
- Alerta visual quando passa de 80% do `LILO_DAILY_BUDGET`.

---

## v11 — Longo prazo (refactor maior)

### I. API HTTP de produção

`lilo_api.py` está OK para uso local. Para uso remoto/produção, precisa:
- HTTPS via `uvicorn` + cert (Let's Encrypt ou self-signed).
- Rate limiting (slowapi).
- Multi-tenant (tokens por usuário, isolamento de `kv_memory`).
- Métricas Prometheus em `/metrics`.

### J. RAG estruturado para PDFs

`PDFs_library` hoje faz sumarização ad-hoc. Migrar para:
- Pipeline `ingest → chunk → embed → index (FAISS local) → retrieve → answer`.
- Persistir embeddings em `data/pdf_embeddings.db`.
- Tool `lilo_pdf_ask(query, top_k=5)` com citações dos PDFs.

### K. Cliente CLI dedicado

Hoje `python lilo.py "query"` funciona, mas não tem REPL nem histórico.
- `lilo-cli` (nome próprio) com prompt-toolkit, autocomplete de tools, histórico em `~/.lilo_history`.
- Suporte a slash commands (`/health`, `/cost`, `/memory list`).

### L. Multi-LLM por estágio em Villa-Lobos

Hoje todos os 5 stages usam Ollama. A v10.1 abriu caminho com smart routing.
**Próximo:** permitir mix por estágio:
- `Orchestrator=claude_haiku` (decisão barata e rápida)
- `Planner=ollama phi3:14b`
- `Worker=ollama qwen2.5-coder:14b`
- `Reporter=claude_sonnet` (qualidade redacional)
- Configurável via `VILLA_MODELS_OVERRIDE` no `.env`.

---

## Débitos técnicos a tratar quando puder

| Item | Severidade | Esforço |
|---|---|---|
| OneDrive trunca arquivos editados via Edit tool | Alta (já mitigado por pre-commit hook) | -- (workaround documentado) |
| `dashboard.py` com 2139 linhas | Média | 1-2 dias |
| `agents/PDFs_library/app/` ainda tem código antigo redundante | Baixa | 2 dias (deletar `_ARCHIVE_v10/to_delete/` definitivamente após confirmação) |
| Sem testes unitários automatizados | Média | 1 semana (pytest + cobertura mínima 50%) |
| `config.yaml` referencia modelos Claude antigos (não usado, mas confunde) | Baixa | 30min |
| Skills `complexity=high` ainda zero (esquema futuro-proof, mas sem uso real) | Baixa | -- |

---

## Como priorizar

**Para o usuário (você, biólogo molecular + cientista de dados):**

1. **A (memória unificada)** — maior ROI imediato, melhora qualidade do chat e do Villa-Lobos drasticamente.
2. **C (smart context)** — reduz tempo perdido re-explicando contexto.
3. **D (embeddings)** — habilita "pesquisa por conceito" — útil para PDFs e notas de projeto.
4. **F (worker queue PRISM)** — só prioritário se você fizer análises grandes regularmente.
5. **G (plugin marketplace)** — só importante se você quiser compartilhar/distribuir LILO.

**Padrão sugerido de execução:** entregar A + C juntas (são complementares), depois D, depois B em paralelo com a próxima frente.

---

## Próxima sessão — checklist de retomada

Quando voltar a desenvolver, comece por:

```cmd
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente

:: 1. Confirmar saúde do sistema
python scripts\lilo_diag.py

:: 2. Validar tools (deve mostrar 236)
python -c "import lilo; print(len(lilo.list_all_tools()))"

:: 3. Verificar custos do dia (com a tool nova)
python -c "from lilo import handle_tool_call; print(handle_tool_call('lilo_cost_today', {}))"

:: 4. Ver memória ativa
python -c "from lilo import handle_tool_call; print(handle_tool_call('lilo_memory_stats', {}))"
```

Boa noite! 🌙
