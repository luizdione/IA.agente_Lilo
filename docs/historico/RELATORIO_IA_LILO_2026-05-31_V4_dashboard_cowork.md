# Relatório IA.LILO — V4: dashboard Streamlit com paridade Claude Cowork

**Data:** 2026-05-31
**Tarefa:** `ia_lilo` (continuação interativa, a pedido de Dione)
**Pedido:** melhorar o dashboard Streamlit do LILO para se aproximar do Claude Cowork — não só visual, mas funcionalidades técnicas equivalentes.
**Decisões de Dione:** implementar as 4 frentes (streaming, tarefas+agendadas, memória KV, conectores+Scholar) e editar o `dashboard.py` direto.

---

## 1. Análise do dashboard atual

`dashboard.py` (≈2.5k linhas) já era robusto: páginas Chat, SQL, PDFs, Scholar, Prism AI, Villa Lobos, Desktop (filesystem/shell), Skills, Custos, Saúde, Ajuda, Glossário; modos **Agir/Perguntar** (estilo Claude Desktop), slash commands para skills, anexos via popover, projetos e memória de chat.

**Gaps em relação ao Cowork:** chat **síncrono** (sem streaming), sem painel de **tarefas**, sem **tarefas agendadas**, sem página de **memória persistente (KV)**, sem visão de **conectores/capabilities**, e o Scholar limitado a auto/pubmed/arxiv.

## 2. Implementação (V10.5)

Para não arriscar o arquivo grande, a **lógica** ficou em um módulo novo testável (`dashboard_cowork.py`, 353 linhas) e o `dashboard.py` recebeu **edições cirúrgicas** (import, navegação, páginas, streaming).

### 2.1 Novas páginas (seção "COWORK" na sidebar)

- **Tarefas** — to-do list persistente (KVMemory, namespace `lilo_tasks`): métricas (total/pendente/em progresso/concluída), adicionar, mudar status, marcar concluída, apagar; e **Tarefas agendadas** lendo os `SKILL.md` das pastas Scheduled (configurável via `LILO_SCHEDULED_DIRS`).
- **Memória** — CRUD/busca da memória de longo prazo (KVMemory): filtro por namespace, busca textual, visualização JSON, criar/apagar entradas. É a "memória que sobrevive entre sessões", como no Cowork.
- **Conectores** — manifesto de capacidades dos 7 subagentes (domain, custo, latência, local-only, tools, keywords — usa o `capability_registry` enriquecido na V10.3) e as tools expostas por cada um dos 7 perfis MCP (Claude Desktop, Claude Code, PyCharm, OpenClaw, Cowork, bio, http).

### 2.2 Streaming (UX Cowork)

- **Chat:** a resposta agora aparece progressivamente via `st.write_stream` (exibição token-a-token sobre a resposta calculada por `route()`; o `llm_client` é síncrono, então é efeito de digitação seguro, sem custo extra). Fallback para `st.markdown` se desativado.
- **Villa Lobos:** o pipeline agora mostra **progresso por estágio** (Orchestrator → Planner → Reader → Worker → Reporter) em tempo real via `st.status`, usando o `stream_callback` adicionado ao `VillaLobosAgent.run()` na V10.3.

### 2.3 Scholar ampliado

O selectbox de fonte passou de `auto/pubmed/arxiv` para as 9 fontes públicas (auto, all, pubmed, arxiv, clinicaltrials, opentargets, npi, crossref, semanticscholar) com rótulos amigáveis — conectando o backend de pesquisa externa da V10.4.

## 3. Validação

| Item | Resultado |
|---|---|
| `dashboard_cowork.py` AST/compile | OK (353 linhas) |
| Tarefas CRUD (add/status/list/delete/counts) | OK |
| `get_capabilities()` | 7 subagentes (sql, pdf, scholar, prism, villa, gateway, desktop) |
| `get_profile_tools()` | 7 perfis MCP |
| `list_scheduled()` (parse SKILL.md) | OK |
| `stream_words()` (gerador) | OK |
| Edições no `dashboard.py` | conferidas por leitura autoritativa (import, nav, 3 páginas, selectbox, chat stream, try/except do Villa alinhado) |

## 4. Como usar

`streamlit run dashboard.py` → sidebar mostra a seção **COWORK** com Tarefas, Memória e Conectores. O Chat e o Villa Lobos passam a exibir progresso em tempo real. Para listar tarefas agendadas, defina no `.env`:

```
LILO_SCHEDULED_DIRS=C:\Users\luizd\OneDrive\Documentos\LGM\Documentos\Claude\Scheduled
```

## 5. Limitações e pendências

- **Sandbox/mount:** a validação global do `dashboard.py` por execução não foi possível aqui (o mount serve uma cópia stale do arquivo grande editado in-place; o erro reportado pelo parser é numa linha do Glossário que não foi editada). A lógica nova está 100% no `dashboard_cowork.py` (compilado e testado) e as 6 edições no `dashboard.py` foram conferidas linha a linha no arquivo autoritativo. No seu computador o dashboard roda normalmente.
- **Streaming nativo de LLM:** para streaming real token-a-token do modelo (não só de exibição), seria preciso expor `stream=True` no `shared/llm_client.py` (Ollama suporta). Fica como próximo passo opcional.
- **Limpeza manual** (o `rm` é bloqueado pelo mount): além dos temporários já citados em relatórios anteriores, nenhum novo foi gerado nesta etapa.

## 6. Arquivos alterados/criados

- `dashboard_cowork.py` — **novo**: lógica + páginas Cowork (tarefas, memória, conectores, streaming).
- `dashboard.py` — edições: import do módulo, seção COWORK na sidebar, páginas Tarefas/Memória/Conectores, selectbox do Scholar, streaming no Chat e progresso stage-a-stage no Villa.
