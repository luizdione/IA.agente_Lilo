# LILO v7.0 — Agente Pessoal Integrado de IA

![Status](https://img.shields.io/badge/status-ativo-brightgreen)
![Version](https://img.shields.io/badge/version-7.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-yellow)
![License](https://img.shields.io/badge/license-MIT-green)

**LILO** (Linguagem Inteligente, Lógica Operacional) é um orquestrador de IA multiagente pessoal, projetado para bioinformática e ciência de dados. Combina modelos locais (Ollama) com APIs cloud (Claude, GPT) usando roteamento custo-inteligente.

## Arquitetura

```
                    ┌─────────────────────┐
                    │   Policy Engine     │
                    │  Roteamento custo-  │
                    │  inteligente        │
                    └────────┬────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │ lilo_mcp   │  │lilo_pycharm│  │lilo_server │
     │  .py       │  │  _mcp.py   │  │   .py      │
     │Claude Desk │  │  PyCharm   │  │  HTTP API  │
     └────┬───────┘  └────┬───────┘  └────┬───────┘
          │               │               │
          └───────────┬───┘───────────────┘
                      ▼
              ┌──────────────┐
              │   lilo.py    │
              │ Orquestrador │
              └──────┬───────┘
                     │
       ┌─────────┬───┴───┬──────────┐
       ▼         ▼       ▼          ▼
  ┌─────────┐┌───────┐┌────────┐┌─────────┐
  │SQL Agent││PDF    ││Scholar ││Gateway  │
  │ANOVA    ││PyMuPDF││PubMed  ││Fallback │
  │t-test   ││       ││arXiv   ││         │
  └─────────┘└───────┘└────────┘└─────────┘
```

## Componentes

### Core (`shared/`)
- **policy.py** — Policy Engine: roteamento `NO_LLM → OLLAMA_FAST → OLLAMA → OLLAMA_HEAVY → CLAUDE_SONNET → CLAUDE_OPUS`. Budget diário configurável ($1/dia default). 35 indicadores de complexidade para bioinformática e estatística.
- **llm_client.py** — Cliente unificado com detecção lazy de backend (Ollama → LiteLLM → Anthropic), timeout 1s.
- **cost_tracker.py** — Tracking de custos em SQLite com relatórios diários.
- **obsidian.py** — Integração Obsidian: salva execuções como notas Markdown com YAML frontmatter.
- **base_agent.py** — ABC para subagentes (interface `run()`, `get_tools()`, `health()`).

### 4 Subagentes
| Subagente | Descrição | Ferramentas |
|-----------|-----------|-------------|
| **Analise_SQL** | Análise SQL + estatística | ANOVA, t-test, regressão, visualização |
| **PDFs_library** | Processamento de PDFs | PyMuPDF, modos: simple/intro/methods/results |
| **scholaragent** | Busca acadêmica | PubMed + arXiv + síntese de literatura |
| **llm-gateway** | Gateway de LLMs | Fallback multi-modo, chat geral |

### 3 MCP Servers
| Server | Interface | Tools | Uso |
|--------|-----------|-------|-----|
| `lilo_mcp.py` | JSON-RPC stdio | 11 | Claude Desktop |
| `lilo_pycharm_mcp.py` | FastMCP | 7 | PyCharm AI Assistant |
| `lilo_server.py` | StreamableHTTP :8899 | 11 | HTTP/Cowork |

### Dashboard
Streamlit com 6 abas: **Chat**, **SQL**, **PDFs**, **Scholar**, **Custos**, **Health**.

### Docker (5 serviços)
| Serviço | Porta | Descrição |
|---------|-------|-----------|
| ollama | 11434 | Motor LLM local (GPU) |
| memory | 8001 | ChromaDB — memória vetorial |
| backend | 8000 | FastAPI + subagentes |
| dashboard | 8506 | Streamlit |
| frontend | 3000 | React + Nginx |

### Villa Lobos (integrado)
Pipeline de 5 agentes do osquestrador_ollama: Orchestrator → Planner → Reader → Worker → Reporter. Integrado via `lilo_pycharm_mcp.py` (tools `villa_pipeline`, `villa_quick_ask`).

## Início Rápido

### 1. Pré-requisitos
- Python 3.11+
- Ollama (`winget install Ollama.Ollama`)
- Docker Desktop (opcional, para stack completa)

### 2. Instalação
```bash
git clone https://github.com/luizdione/IA.gente_Lilo.git
cd IA.gente_Lilo
cp .env.example .env
# Edite .env com suas chaves API
pip install -r requirements.txt
```

### 3. Executar
```bash
# Dashboard apenas (recomendado para uso diário)
start_dashboard.bat

# Stack completa Docker
RUN_LILO.bat

# Inicialização automática com Windows
# Coloque atalho de START_LILO_WINDOWS.bat em shell:startup
```

### 4. Configurar MCP

**Claude Desktop** — adicione em `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "lilo": {
      "command": "python",
      "args": ["C:/caminho/para/lilo_mcp.py"],
      "env": { "PYTHONPATH": "C:/caminho/para/IA.agente" }
    }
  }
}
```

**PyCharm** — Settings → Tools → AI Assistant → MCP → Add:
- Name: `LILO`
- Command: `python`
- Arguments: `C:/caminho/para/lilo_pycharm_mcp.py`
- Working Dir: `C:/caminho/para/IA.agente`
- Env: `PYTHONPATH=C:/caminho/para/IA.agente`

## Estrutura de Diretórios

```
IA.agente/
├── shared/              # Utilitários comuns (policy, llm_client, logger...)
├── Analise_SQL/         # Subagente SQL + estatística
├── PDFs_library/        # Subagente PDFs
├── scholaragent/        # Subagente busca acadêmica
├── llm-gateway/         # Subagente gateway LLM
├── backend/             # FastAPI backend (Docker)
├── frontend/            # React frontend (Docker)
├── memory/              # ChromaDB (Docker)
├── ollama-service/      # Ollama Docker config
├── lilo.py              # Orquestrador principal
├── lilo_mcp.py          # MCP server — Claude Desktop
├── lilo_pycharm_mcp.py  # MCP server — PyCharm
├── lilo_server.py       # MCP server — HTTP
├── dashboard.py         # Dashboard Streamlit
├── config.yaml          # Configuração geral
├── docker-compose.yml   # Stack Docker 5 serviços
├── requirements.txt     # Dependências Python
├── .env.example         # Template de variáveis
├── GLOSSARIO.md         # Glossário de termos de IA
├── COMANDOS.md          # Referência de comandos LILO
├── CHANGELOG.md         # Histórico de mudanças
└── docs/                # Diagramas e figuras
    └── lilo_v7_arquitetura.svg
```

## Documentação

- [GLOSSARIO.md](GLOSSARIO.md) — Termos de IA, ML, MCP, LLM explicados
- [COMANDOS.md](COMANDOS.md) — Referência de comandos e tools do LILO
- [CHANGELOG.md](CHANGELOG.md) — Histórico de versões

## Licença
MIT — Uso pessoal e acadêmico.

## Autor
**Luiz Dione Melo** — Biólogo molecular / Cientista de dados
