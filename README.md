# LILO v11.0 — Agente Pessoal de IA com Subagentes Especializados

![Status](https://img.shields.io/badge/status-ativo-brightgreen)
![Version](https://img.shields.io/badge/version-11.0.0-blue)
![Python](https://img.shields.io/badge/python-3.13-yellow)
![Arch](https://img.shields.io/badge/arch-v11-purple)
![Tests](https://img.shields.io/badge/tests-120%20passed-brightgreen)

**LILO** (Local Intelligent LLM Orchestrator) é uma plataforma híbrida de IA pensada para um pesquisador (PhD biologia molecular + ciência de dados senior) que combina:

- **LLMs locais via Ollama** (RTX 3060 12GB) — privacidade e custo zero
- **Claude API** (Sonnet/Opus) como fallback para tarefas complexas
- **Policy Engine** que decide automaticamente o tier de execução pelo conteúdo da query (NO_LLM → Ollama_fast → Ollama → Ollama_heavy → Claude_sonnet → Claude_opus)
- **Roteamento semântico (V12)** — uma porta única (Villa Lobos) escolhe o melhor subagente pela semântica da pergunta e, em tarefas multi-etapa, **encadeia vários especialistas em sequência**
- **10 subagentes especializados** — cada um com sua expertise
- **Busca na internet** — web geral (DuckDuckGo) + 10 fontes estruturadas (PubMed, OpenAlex, Europe PMC, Crossref, Semantic Scholar, Google Books, Wikipedia, arXiv, ClinicalTrials, Open Targets…)
- **MCP server unificado** com integração nativa ao Claude Desktop e PyCharm
- **Dashboard Streamlit** local em http://localhost:8100 (tema Claude Desktop, modo **Auto**)

---

## Subagentes (10)

| Agente | Especialidade | Tools MCP |
|---|---|---|
| **SQL** (`agents/Analise_SQL/`) | Queries SQLite, análise estatística (ANOVA, t-test, regressão, correlação) | `lilo_sql` |
| **PDFs** (`agents/PDFs_library/`) | Sumarização de PDFs científicos (PyMuPDF), busca por DOI/ISSN | `lilo_pdf` |
| **Scholar** (`agents/scholaragent/`) | Busca acadêmica (PubMed, arXiv + ClinicalTrials, Open Targets, NPI, CrossRef, Semantic Scholar) com síntese de literatura | `lilo_scholar` |
| **Prism AI** (`agents/prism_ai/`) | Análise estatística completa (.xlsx/.csv), gráficos publication-grade | `prism_analyze`, `prism_classify`, `prism_audit` |
| **Villa-Lobos** (`agents/villa_lobos/`) | Pipeline multi-estágio: Orchestrator → Planner → Reader → Worker → Reporter | `villa_pipeline`, `villa_quick_ask` |
| **Gateway** (`agents/gateway/`) | Fallback genérico via LiteLLM proxy ou Ollama direto | `lilo_chat`, `lilo_models` |
| **Desktop Commander** (`agents/desktop/`) | Filesystem + shell com allow-list de segurança | `fs_read`, `fs_write`, `fs_list`, `fs_stat`, `fs_search`, `run_shell`, `run_python` |
| **Paper** (`agents/paper/`) | Redação científica (skill build_paper): outline, seções com referências reais, build DOCX/TEX/PDF. Escritor via Ollama Cloud | `paper_outline`, `paper_section`, `paper_references`, `paper_draft`, `paper_build` |
| **DocGen** (`agents/docgen/`) | Documentos de escritório: relatórios `.docx`, planilhas `.xlsx`, apresentações `.pptx` | `make_report_docx`, `make_docx`, `make_xlsx`, `make_pptx` |
| **SkillSmith** (`agents/skillsmith/`) | Cria o scaffold de novos subagentes/skills do LILO (meta-skill) | `propose_agent`, `create_agent_scaffold` |

---

## Como rodar

### Dashboard Streamlit (interface principal)

```cmd
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
streamlit run dashboard.py
```

Abre em **http://localhost:8100** (porta travada via `.streamlit/config.toml`).

### PDFs Library (interface secundária)

```cmd
agents\PDFs_library\scripts\BUILD_E_ABRIR.bat
```

Abre em **http://localhost:8101**.

### CLI

```cmd
python lilo.py "OpenMM erro NaN durante NVT equilibration"
python lilo.py sql "SELECT COUNT(*) FROM genomas"
python lilo.py scholar "trypanothione reductase inhibitors"
python lilo.py health
```

### MCP server (Claude Desktop, Claude Code, OpenClaw, PyCharm)

> Trabalhando neste repo com o Claude? Veja [`CLAUDE.md`](CLAUDE.md) — guia
> enxuto de profiles e de como evitar gastar tokens com tools duplicadas.

O servidor expõe diferentes conjuntos de tools por **profile**, escolhido via
`--profile`. Default no Claude Desktop é **`opus`**; no Claude Code é
**`claude_code`** (ver tabela abaixo).

A contagem exata por profile evolui conforme tools são adicionadas — a **fonte
de verdade** é `_PROFILE_TOOLS` em [`lilo_mcp.py`](lilo_mcp.py); o servidor loga
`profile=<nome> (<N> tools)` ao subir. Conjuntos atuais:

| Profile   | Conjunto de tools | Quando usar |
|-----------|-------------------|-------------|
| `opus`    | curado: internet, filesystem, exec local, memória, `lilo_scholar`, `prism_*`, ollama, composed (`fs_batch_read`/`grep_and_read`/`fs_codemod`) | **Claude Desktop com Opus 4.x** — só tools que AGREGAM ao Opus. Redundantes (`lilo_chat`, `lilo_pdf`, `villa_*`...) ficam ocultas mas acessíveis no dashboard via slash (`/lilo_chat`...). |
| `bio`     | pesquisa biomolecular: scholar, pdf, sql, prism, villa, web, fs **só leitura** (sem `run_shell`/`run_python`) | Setup biomolecular (segurança). |
| `pycharm` | dev/refactor: `fs_*`, `run_*`, `villa_*`, prism, memória, composed | PyCharm AI Assistant. |
| `claude_code` | complementar ao Claude Code CLI: `villa_*`, `prism_*`, scholar, pdf, memória, ollama (sem `fs_*`/`run_*`, que o CC já tem nativos) | Claude Code CLI. |
| `cowork`  | espelha `bio` (local-only, sem exec) | Automação Cowork sem supervisão. |
| `desktop` | **todas** | Legado / OpenClaw. |
| `http`    | **todas** | `lilo_api.py`. |

```cmd
python lilo_mcp.py --profile opus       # recomendado p/ Claude Desktop
python lilo_mcp.py --profile desktop    # todas as tools
python lilo_mcp.py --profile bio        # subset biomolecular
python lilo_mcp.py --profile pycharm    # subset PyCharm
```

#### Configurar no Claude Desktop

Edite `%APPDATA%\Claude\claude_desktop_config.json` (ou copie de
`config/mcp/claude_desktop.json` neste repositório):

```json
{
  "mcpServers": {
    "lilo": {
      "command": "C:\\Users\\luizd\\miniforge3\\python.exe",
      "args": [
        "C:\\Users\\luizd\\OneDrive\\Data_Science\\Projetos\\IA.agente\\lilo_mcp.py",
        "--profile", "opus"
      ],
      "env": {
        "PYTHONPATH": "C:\\Users\\luizd\\OneDrive\\Data_Science\\Projetos\\IA.agente",
        "OLLAMA_HOST": "http://localhost:11434",
        "LILO_KEEP_ALIVE": "2h"
      }
    }
  }
}
```

Reinicie o Claude Desktop (fechar pela bandeja do Windows e abrir de novo) — a
lista de tools é cacheada por sessão.

#### Validar antes de plugar no cliente

```cmd
python scripts\test_mcp_stdio.py --profile opus
```

Saída esperada:

```
[run] C:\Users\luizd\miniforge3\python.exe ...\lilo_mcp.py --profile opus
[env] PYTHONPATH=C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
[OK] initialize  -> server: lilo
[OK] tools/list  -> 18 tools
      - lilo_scholar: Busca estruturada em PubMed e arXiv...
      - prism_analyze: Pipeline cientifico completo sobre um .xlsx...
      - prism_classify: Inspeciona um arquivo de dados e CLASSIFICA...
      - lilo_web_search: Busca web via DuckDuckGo, filtrada para dominios...
      - lilo_web_fetch: Baixa o conteudo textual de uma URL...
      ... +13 mais
[OK] lilo_list_local_models -> NAME ... ID ... SIZE ...
[SUCCESS] Servidor MCP LILO esta funcional via stdio.
```

#### Como reverter (voltar a expor todas as tools no Claude Desktop)

No `claude_desktop_config.json`, troque `"--profile", "opus"` por
`"--profile", "desktop"` e reinicie o Claude Desktop.

> Detalhes completos (como o profile escolhe tools, slash commands, troubleshooting):
> ver `docs/uso/PROFILE_OPUS.md`.

---

## Portas em uso

| Serviço | Porta | URL |
|---|---|---|
| Dashboard LILO | 8100 | http://localhost:8100 |
| PDFs Library | 8101 | http://localhost:8101 |
| Ollama | 11434 | http://localhost:11434 |
| LiteLLM proxy (opcional) | 4000 | http://localhost:4000 |

---

## Arquitetura v10.0

```
┌────────────────────────────────────────────────────────────┐
│ CLIENTES                                                    │
│  Claude Desktop (stdio)  PyCharm (stdio)  CLI  Streamlit    │
└──────────────────────────────┬─────────────────────────────┘
                               │
                    ┌──────────▼─────────────┐
                    │   lilo_mcp.py          │
                    │ --profile {claude_code| │
                    │   opus|bio|pycharm|...} │
                    └──────────┬─────────────┘
                               │
                    ┌──────────▼───────────┐
                    │   lilo.py            │
                    │   route() + Policy   │
                    └──────────┬───────────┘
                               │
   ┌────┬─────┬──────┬─────────┼─────────┬───────┬──────┐
   ▼    ▼     ▼      ▼         ▼         ▼       ▼      ▼
  SQL  PDFs Scholar Prism  Villa-Lobos Gateway Desktop Skills
                          (5 stages)                  (199)

         Backends LLM (transparente):
         LiteLLM proxy → Ollama → Anthropic
```

Mudança principal vs v9.0: **subagentes não duplicados** (apenas em `agents/`), **MCP unificado** (era `lilo_mcp.py` + `lilo_pycharm_mcp.py`), **Desktop Commander integrado**, **portas dedicadas** (8100/8101 livres de conflitos com outras APIs do usuário).

Detalhes em `docs/tecnico/arquitetura_v10.md`.

---

## Estrutura de diretórios

```
IA.agente/
├── lilo.py                    Orquestrador central
├── lilo_mcp.py                MCP server unificado (--profile)
├── lilo_api.py                API HTTP FastAPI :8088 (plataforma híbrida)
├── lilo_serve.py              Multiplexer de transporte (stdio/http/sse)
├── dashboard.py               Streamlit UI :8100 (tema Claude Desktop)
├── agents/                    10 subagentes (sql, pdf, scholar, prism, villa, gateway, desktop, paper, docgen, skillsmith)
├── shared/                    Cliente LLM, Policy Engine, base_agent, chat_memory, web_search
├── lilo_skills/               199 skills auto-geradas + bio/openmm_nvt_equilibration_safe
├── config/
│   ├── litellm_config.yaml    Config LiteLLM proxy
│   └── mcp/                   Perfis MCP prontos (Desktop/PyCharm/Claude Code)
├── docs/
│   ├── uso/COMANDOS.md
│   ├── tecnico/arquitetura_v10.md, GLOSSARIO.md
│   ├── versoes/CHANGELOG.md
│   ├── historico/             Auditorias e investigações
│   └── agentes/               READMEs dos subagentes
├── data/, memory/, logs/      Dados persistentes
└── _ARCHIVE_v10/              Código removido na refatoração (não tocar)
```

---

## Pré-requisitos

- Windows 10/11 + Python 3.10+ (testado com miniforge)
- **Ollama** instalado nativamente (não Docker) — https://ollama.com/download
- Modelos: `llama3.1:8b-instruct-q8_0`, `qwen2.5-coder:14b`, `phi3:14b-medium-128k-instruct-q4_K_M`, `qwen2.5-coder:7b-instruct`
- Driver NVIDIA + CUDA (RTX 3060 12GB testada)
- `pip install -r requirements.txt`
- (Opcional) `ANTHROPIC_API_KEY` no `.env` para fallback Claude

---

## Variáveis de ambiente principais (`.env`)

| Var | Default | O que faz |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Endpoint Ollama |
| `OLLAMA_MODEL` | `llama3.1:8b-instruct-q8_0` | Modelo padrão (chat) |
| `OLLAMA_MODEL_CODE` | `qwen2.5-coder:14b` | Para tarefas de código |
| `OLLAMA_MODEL_PLAN` | `phi3:14b-medium-128k-instruct-q4_K_M` | Para planejamento |
| `OLLAMA_MODEL_FAST` | `qwen2.5-coder:7b-instruct` | Para tarefas triviais |
| `OLLAMA_KEEP_ALIVE` | `2h` | Tempo que modelo fica em VRAM (default Ollama é 5min) |
| `LILO_DAILY_BUDGET` | `1.0` | Orçamento Claude/dia em USD |
| `LILO_DESKTOP_ALLOW` | `IA.agente;Workaholics` | Pastas que `fs_*` e `run_shell` podem acessar |
| `ANTHROPIC_API_KEY` | (vazio) | Habilita Claude Sonnet/Opus quando aplicável |

---

## Próximos passos do projeto

Veja `docs/tecnico/arquitetura_v10.md` para o roadmap. Itens prioritários:

1. Aba "Desktop" no dashboard 8100 com formulário visual para as 7 tools.
2. `lilo_api.py` (FastAPI + SSE) para abrir o LILO como serviço HTTP autenticado.
3. Skills bio adicionais (RDKit, MDAnalysis, Biopython, OpenBabel).
4. Smart routing no Villa-Lobos (Orchestrator emite JSON e pula stages quando aplicável).

---

**Versão:** 10.0 (arch-v10) — 2026-05-07
**Mantenedor:** Luiz Dione (luiz.dione.melo@gmail.com)
