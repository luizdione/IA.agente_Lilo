# LILO — Glossário (v10.0)

## Componentes principais

| Termo | Definição |
|---|---|
| **LILO** | Local Intelligent LLM Orchestrator. Plataforma híbrida do projeto. |
| **Subagente** | Módulo Python especializado (SQL, PDF, Scholar, Prism, Villa-Lobos, Gateway, Desktop). Implementa `BaseAgent` com `run()`, `get_tools()`, `health()`. |
| **Orquestrador (`lilo.py`)** | Roteia queries para o subagente correto via `route()`. Consulta o Policy Engine para decidir tier de execução. |
| **MCP server (`lilo_mcp.py`)** | Servidor Model Context Protocol. Expõe tools via stdio para Claude Desktop e PyCharm. Suporta profiles. |
| **Policy Engine (`shared/policy.py`)** | Decide se uma query roda em NO_LLM / Ollama_fast / Ollama / Ollama_heavy / Claude_sonnet / Claude_opus baseado em complexidade, tamanho, indicadores e budget. |
| **Backend LLM (`shared/llm_client.py`)** | Cliente unificado que abstrai LiteLLM proxy, Ollama direto e Anthropic API. |
| **Skill** | Função pequena auto-gerada do ambiente Conda (199 funções de scipy/numpy/pandas/biopython/etc.) acessível via `skill_<nome>`. |

---

## Subagentes em detalhe

| Subagente | Path | Descrição |
|---|---|---|
| **SQL** | `agents/Analise_SQL/` | Queries SQLite + análise estatística (ANOVA, t-test, regressão, correlação, normalidade). |
| **PDFs** | `agents/PDFs_library/` | Extração e sumarização de PDFs científicos com PyMuPDF. Indexa por DOI/ISSN no `workaholics.db`. |
| **Scholar** | `agents/scholaragent/` | Busca em PubMed e arXiv. Sintetiza literatura. |
| **Prism AI** | `agents/prism_ai/` | Análise estatística completa para .xlsx/.csv. Detecta tipo de experimento, testa pressupostos, gera plots publication-grade. |
| **Villa-Lobos** | `agents/villa_lobos/` | Pipeline 5-stage para tarefas complexas (Orchestrator → Planner → Reader → Worker → Reporter). |
| **Gateway** | `agents/gateway/` | Fallback genérico via LiteLLM ou Ollama. Modos: chat/code/bioinfo/sql. |
| **Desktop Commander** | `agents/desktop/` | Filesystem + shell com allow-list. 7 tools: `fs_read`, `fs_write`, `fs_list`, `fs_stat`, `fs_search`, `run_shell`, `run_python`. |

---

## Tiers de execução (Policy Engine)

| Tier | Quando | Modelo |
|---|---|---|
| `NO_LLM` | Comandos diretos (listar, health, SELECT) | nenhum |
| `OLLAMA_FAST` | Tarefas triviais (traduzir, contar) | qwen2.5-coder:7b-instruct |
| `OLLAMA` | Padrão local | llama3.1:8b-instruct-q8_0 |
| `OLLAMA_HEAVY` | Complexidade média / código | qwen2.5-coder:14b |
| `CLAUDE_SONNET` | Tarefas complexas (com budget) | claude-sonnet-4 |
| `CLAUDE_OPUS` | Tarefas críticas (com budget) | claude-opus-4 |

Indicadores de complexidade alta incluem termos de DM (`openmm`, `nvt`, `npt`, `equilibration`, `rmsd`, `mmgbsa`, `metadynamics`, `gromacs`, `amber`, etc.) — adicionados em 2026-05-06 após a auditoria.

---

## Termos técnicos do ecossistema

| Termo | Definição |
|---|---|
| **Ollama** | Servidor local de LLMs em `localhost:11434`. Roda GGUF/safetensors com aceleração CUDA. |
| **LiteLLM** | Proxy que unifica APIs (OpenAI, Anthropic, Ollama, etc.) em endpoint único `localhost:4000`. Configuração em `config/litellm_config.yaml`. |
| **MCP** | Model Context Protocol da Anthropic. Permite que Claude Desktop e PyCharm chamem tools externas via stdio. |
| **FastMCP** | Framework Python de alto nível pra criar servidores MCP. Usado em `lilo_mcp.py`. |
| **stdio transport** | Comunicação MCP via stdin/stdout do subprocess. Usado por Claude Desktop. |
| **Streamlit** | Framework Python para dashboards web. Roda em `localhost:8100` (LILO) e `localhost:8101` (PDFs library). |
| **PyMuPDF** | Biblioteca de extração de texto/metadados de PDFs. |
| **Profile flag** | `--profile {desktop\|pycharm\|http}` no `lilo_mcp.py` filtra quais tools são expostas. |
| **Allow-list** | Lista de paths permitidos em `LILO_DESKTOP_ALLOW`. Tools `fs_*` e `run_shell` rejeitam paths fora dessa lista. |
| **VRAM** | Video RAM da GPU (12 GB na RTX 3060). Modelos quantizados (Q4/Q8) ocupam de ~5 a ~10 GB. |
| **keep_alive** | Tempo que o Ollama mantém um modelo carregado em VRAM após uso. Default Ollama: 5min. LILO: 2h (`OLLAMA_KEEP_ALIVE=2h` no `.env`). |
| **CoT** | Chain-of-Thought. Prompt suffix que pede ao modelo raciocinar entre `<thinking>...</thinking>`. Habilitado por padrão no `_chat_ollama`. |

---

## Bioinformática (contexto do usuário)

| Termo | Definição |
|---|---|
| **NVT** | Ensemble canônico (N partículas, V volume, T temperatura) em dinâmica molecular. |
| **NPT** | Ensemble isotérmico-isobárico (N, P, T). |
| **Equilibration** | Etapa que precede produção: minimização → aquecimento gradual → estabilização. |
| **Force field** | Conjunto de parâmetros que define interações inter/intramoleculares (AMBER14, CHARMM36, OPLS-AA). |
| **HMR** | Hydrogen Mass Repartitioning. Permite timestep 2 fs estável. |
| **OpenMM** | Engine de DM em Python/C++/CUDA. |
| **MDAnalysis / MDTraj** | Bibliotecas de pós-análise de trajetórias. |
| **TcTR** | Trypanothione Reductase (proteína-alvo de Trypanosoma cruzi para drug design). |
| **PDB** | Protein Data Bank — formato e repositório de estruturas 3D. |
| **DOI / ISSN** | Identificadores de publicação científica usados pelo subagente PDFs para indexar `workaholics.db`. |

---

## Arquivos de configuração

| Arquivo | Conteúdo |
|---|---|
| `.env` | Variáveis sensíveis (API keys, paths, OLLAMA_KEEP_ALIVE, LILO_DESKTOP_ALLOW). Não commitar. |
| `.env.example` | Template versionado. |
| `config.yaml` | Config geral do LILO (Obsidian vault, etc.). |
| `config/litellm_config.yaml` | Modelos do LiteLLM proxy. |
| `config/mcp/*.json` | Perfis MCP prontos para Claude Desktop, PyCharm, Claude Code. |
| `.streamlit/config.toml` | Trava porta 8100 do dashboard. |
| `.mcp.json` | Config MCP local do projeto (usada por Claude Code). |

---

## Diretórios de dados

| Path | O que tem |
|---|---|
| `data/` | `chat_history.db` (SQLite com chats e projetos) |
| `memory/` | ChromaDB + preferências do usuário |
| `logs/` | `lilo.log` (rotativo), `cost_tracking.db` |
| `agents/PDFs_library/data/` | `workaholics.db` (índice de PDFs) |
| `_ARCHIVE_v10/` | Arquivos removidos na refatoração arch-v10 (não tocar) |
