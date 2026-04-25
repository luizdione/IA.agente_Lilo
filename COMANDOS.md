# LILO — Referência de Comandos e Tools

## Overrides do Policy Engine

Prefixe qualquer query com estes comandos para forçar um tier específico:

| Comando | Tier | Exemplo |
|---------|------|---------|
| `\lilo fast` | OLLAMA_FAST (7B local) | `\lilo fast o que é CRISPR?` |
| `\lilo local` | OLLAMA (8B local) | `\lilo local resuma este artigo` |
| `\lilo heavy` | OLLAMA_HEAVY (14B local) | `\lilo heavy revise este código` |
| `\lilo sonnet` | CLAUDE_SONNET (cloud) | `\lilo sonnet análise detalhada de dados` |
| `\lilo opus` | CLAUDE_OPUS (cloud) | `\lilo opus revisão sistemática completa` |

## MCP Tools — Claude Desktop (`lilo_mcp.py`)

11 tools disponíveis quando LILO está configurado no Claude Desktop:

| Tool | Descrição | Parâmetros |
|------|-----------|------------|
| `lilo_chat` | Chat geral | `query`, `model?` |
| `lilo_sql` | Análise SQL/estatística | `query`, `db_path?`, `table?` |
| `lilo_pdf` | Análise de PDFs | `query`, `file_path?`, `mode?` |
| `lilo_scholar` | Busca acadêmica | `query`, `max_results?` |
| `lilo_health` | Status dos serviços | — |
| `lilo_cost_summary` | Resumo de custos do dia | — |
| `lilo_list_models` | Modelos disponíveis | — |
| `lilo_route_info` | Info de roteamento para query | `query` |
| `lilo_policy_status` | Status do Policy Engine | — |
| `lilo_obsidian_save` | Salvar nota no Obsidian | `title`, `content`, `tags?` |
| `lilo_config` | Ver/alterar configuração | `key?`, `value?` |

## MCP Tools — PyCharm (`lilo_pycharm_mcp.py`)

7 tools disponíveis no PyCharm AI Assistant:

| Tool | Descrição | Parâmetros |
|------|-----------|------------|
| `lilo_chat` | Chat geral LILO | `query`, `model?` |
| `lilo_sql` | Análise SQL | `query`, `db_path?`, `table?` |
| `lilo_pdf` | Análise de PDFs | `query`, `file_path?`, `mode?` |
| `lilo_scholar` | Busca PubMed + arXiv | `query`, `max_results?` |
| `lilo_health` | Status dos serviços | — |
| `villa_pipeline` | Pipeline Villa Lobos (5 agentes) | `task`, `iterations?`, `use_reader?`, `base_path?` |
| `villa_quick_ask` | Pergunta rápida a 1 agente | `question`, `agent?` |

## Dashboard Streamlit (abas)

| Aba | Descrição |
|-----|-----------|
| **Chat** | Conversa direta com LILO via LLM |
| **SQL** | Upload de banco SQLite, queries, estatísticas |
| **PDFs** | Upload e análise de PDFs científicos |
| **Scholar** | Busca acadêmica PubMed + arXiv com síntese |
| **Custos** | Métricas: requests/dia, custo por backend/subagente |
| **Health** | Status de todos os serviços e backends |

## Scripts Windows (.bat)

| Script | Descrição |
|--------|-----------|
| `START_LILO_WINDOWS.bat` | Inicialização automática (Ollama + Dashboard + Docker). Colocar em `shell:startup` |
| `RUN_LILO.bat` | Build + start completo via Docker Compose |
| `start_dashboard.bat` | Apenas dashboard Streamlit (porta 8506) |
| `LIMPAR_LIXO.bat` | Remove arquivos desnecessários de versões anteriores |
| `sincronizacao_github.bat` | Sync automático com GitHub |

## Portas

| Serviço | Porta |
|---------|-------|
| Ollama | 11434 |
| Dashboard Streamlit | 8506 |
| Backend FastAPI | 8000 |
| Frontend React | 3000 |
| ChromaDB | 8001 |
| LILO HTTP MCP | 8899 |

## Modos do PDF Agent

| Modo | Descrição |
|------|-----------|
| `simple` | Resumo geral do documento |
| `introduction` | Foco na introdução e contexto |
| `methods` | Foco na metodologia |
| `results` | Foco nos resultados e discussão |

## Villa Lobos — Agentes

| Agente | Modelo | Função |
|--------|--------|--------|
| `orchestrator` | phi3:14b | Coordena o pipeline |
| `planner` | phi3:14b | Cria plano de execução |
| `reader` | llama3.1:8b | Lê e analisa arquivos do projeto |
| `worker` | qwen2.5-coder:14b | Executa tarefas de código |
| `reporter` | llama3.1:8b | Gera relatório final |
