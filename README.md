# LILO — Local Intelligent LLM Orchestrator

![status](https://img.shields.io/badge/status-ativo-brightgreen)
![version](https://img.shields.io/badge/version-v13.0-blue)
![arch](https://img.shields.io/badge/branch-arch--v11-purple)
![python](https://img.shields.io/badge/python-3.10%2B-yellow)
![local-first](https://img.shields.io/badge/local--first-Ollama-blue)

**LILO** é um orquestrador pessoal de IA **local-first** para bioinformática e
ciência de dados. A maioria das tarefas é resolvida por **modelos locais via
Ollama** (privacidade + custo zero); a **API do Claude (Anthropic)** entra
apenas como *fallback* para tarefas complexas, com **orçamento diário** para não
gastar demais.

- 🧠 **Chat "Auto" como porta única** — você pergunta em linguagem natural e o
  orquestrador (Villa-Lobos + roteador por embeddings) escolhe sozinho o
  especialista; em tarefas multi-etapa, encadeia vários em sequência.
- 🖥️ **Dashboard Streamlit** em `http://localhost:8100`.
- 🔌 **Servidor MCP** para plugar no Claude Desktop, Claude Code, PyCharm, etc.
- 💰 **Policy Engine** decide o *tier* (NO_LLM → Ollama → Claude) pelo conteúdo
  da pergunta e respeita o `LILO_DAILY_BUDGET`.

> **Licença:** uso **científico/acadêmico**, mediante **autorização do autor**.
> Ver [`LICENSE`](LICENSE).

---

## ✨ Funcionalidades

### Interface (dashboard `:8100`)
- **Chat (Auto)** — porta principal; o LILO roteia sozinho para o especialista
  certo. Toggle **"🔀 Pipeline completo"** roda o pipeline multi-estágio Villa.
- **Especialistas** — **Scholar** (busca acadêmica) e **Biblioteca** (resumir
  PDFs + RAG local sobre seus PDFs).
- **Ferramentas** — **Desktop** (filesystem/shell com allow-list), **Skills**,
  **Custos** (gasto Claude/dia), **Saúde** (status de backends).
- **Cowork** — **Tarefas**, **Memória** persistente, **Conectores**.

### Especialistas (subagentes)
| Agente | O que faz |
|---|---|
| **Scholar** | Busca acadêmica estruturada (PubMed, arXiv, Europe PMC, Crossref, Semantic Scholar, ClinicalTrials, Open Targets…) com síntese e DOI. |
| **Biblioteca / PDFs** | Sumariza PDFs científicos (PyMuPDF) e responde perguntas sobre sua biblioteca local (RAG com ChromaDB + embeddings). |
| **Prism** | Análise estatística de `.xlsx`/`.csv` (EDA, testes, classificação) e auditoria de dados. |
| **SQL** | Consultas SQLite + estatística sobre dados tabulares. |
| **Villa-Lobos** | Pipeline multi-estágio (Orchestrator → Planner → Reader → Worker → Reporter) — é o motor do Chat. |
| **Desktop** | Filesystem + shell locais, restritos por allow-list (`LILO_DESKTOP_ALLOW`). |
| **Gateway** | Fallback genérico de chat (Ollama direto ou LiteLLM). |
| **SkillSmith** | Meta-skill: cria o scaffold de novos subagentes/skills. |

### Tools MCP (complementares) — destaques
- `lilo_scholar`, `scholar_review` — literatura biomédica estruturada.
- `lilo_pdf`, `lilo_summarize_file` — destila PDFs/arquivos **via Ollama local**
  (economiza tokens do Claude — o arquivo bruto nunca cruza a fronteira MCP).
- `parse_bio_log` — parseia logs de bioinformática (AutoDock Vina, qPCR, FastQC,
  VCF) em uma tabela compacta.
- `prism_analyze`, `prism_classify`, `prism_audit` — pipeline estatístico.
- `villa_pipeline`, `villa_quick_ask` — orquestração multiagente.
- `lilo_memory_*` — memória persistente (KV) entre sessões.
- `lilo_web_search`, `lilo_web_fetch` — busca/coleta web.

---

## 🚀 Instalação

### Requisitos
- **Python 3.10+** (recomendado 3.11–3.13)
- **[Ollama](https://ollama.com/download)** instalado nativamente
- (Opcional, recomendado) GPU NVIDIA com CUDA para os modelos locais
- (Opcional) **`ANTHROPIC_API_KEY`** para habilitar o *fallback* Claude

### Instalador automático (recomendado)
Instala as dependências, baixa os modelos Ollama base, cria o `.env` e configura
a chave do Claude.

**Windows** (PowerShell):
```powershell
python install.py
# ou: .\install.ps1
```

**Linux / macOS**:
```bash
python3 install.py
# ou: bash install.sh
```

> O instalador é interativo: pergunta (opcionalmente) sua `ANTHROPIC_API_KEY` e
> grava no `.env` local. A chave **nunca** é versionada (`.env` está no
> `.gitignore`).

### Instalação manual
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
# edite o .env e coloque sua ANTHROPIC_API_KEY (opcional)
ollama pull gemma3:12b      # modelo de chat padrão
```

---

## ▶️ Como usar

### Dashboard (interface principal)
```bash
streamlit run dashboard.py --server.port 8100
```
Abre em **http://localhost:8100**. Digite no Chat (modo **Auto**) — o LILO
escolhe o especialista sozinho.

### CLI
```bash
python lilo.py "erro NaN durante equilibração NVT no OpenMM"
python lilo.py health          # status de backends e subagentes
```

### Servidor MCP (Claude Desktop, Claude Code, PyCharm…)
O servidor expõe conjuntos de tools por **profile**:

| Profile | Quando usar |
|---|---|
| `claude_code` | **Claude Code CLI** — só o complementar (o CC já tem Read/Write/Bash nativos). |
| `opus` (`claude_desktop`) | **Claude Desktop** — adiciona filesystem/web/exec que faltam nativamente. |
| `bio` | Setup biomolecular (somente leitura, sem shell). |
| `desktop` | Todas as tools (legado). |

```bash
python lilo_mcp.py --profile claude_code
python scripts/test_mcp_stdio.py --profile claude_code   # valida o MCP
```

Exemplo de registro no Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "lilo": {
      "command": "python",
      "args": ["<caminho>/lilo_mcp.py", "--profile", "opus"],
      "env": { "PYTHONPATH": "<caminho>", "OLLAMA_HOST": "http://localhost:11434" }
    }
  }
}
```

---

## ⚙️ Configuração (`.env`)

| Variável | Default | O que faz |
|---|---|---|
| `ANTHROPIC_API_KEY` | (vazio) | Habilita o *fallback* Claude. Sem ela, LILO roda 100% local. |
| `LILO_DAILY_BUDGET` | `1.0` | Teto de gasto do Claude por dia (USD). |
| `OLLAMA_HOST` | `http://localhost:11434` | Endpoint do Ollama. |
| `OLLAMA_MODEL` | `gemma3:12b` | Modelo de chat padrão. |
| `OLLAMA_MODEL_PLAN` | `qwen3:14b` | Modelo de planejamento. |
| `OLLAMA_MODEL_CODE` | `qwen2.5-coder:14b` | Modelo de código. |
| `OLLAMA_KEEP_ALIVE` | `2h` | Tempo que o modelo fica na VRAM. |
| `LILO_SERVER_PROFILE` | `claude_code` | Profile MCP default. |
| `LILO_DESKTOP_ALLOW` | (pastas) | Diretórios que `fs_*`/`run_shell` podem acessar. |

Todas as variáveis têm exemplo comentado em [`.env.example`](.env.example).

---

## 🗂️ Estrutura

```
IA.agente_Lilo/
├── lilo.py            Orquestrador (route() + Policy Engine)
├── lilo_mcp.py        Servidor MCP unificado (--profile)
├── dashboard.py       Dashboard Streamlit (:8100)
├── install.py         Instalador multiplataforma (deps + Ollama + .env)
├── agents/            Subagentes (scholar, pdf, prism, sql, villa, desktop, gateway, skillsmith)
├── shared/            llm_client, policy, roteador, memória, base_agent
├── scripts/           utilitários (test_mcp_stdio, sleep_consolidate, backup_memory…)
├── config/            profiles.yaml (perfis MCP) + config/mcp/*.json
└── docs/              uso/, tecnico/, versoes/CHANGELOG.md
```

---

## 🧹 Manutenção de memória (opcional)

`scripts/sleep_consolidate.py` faz a **consolidação da memória do agente** no
tempo ocioso (comprime conversas antigas via Ollama local, arquiva tarefas,
poda logs) — **sem gastar tokens do Claude** e **sem alterar pesos de modelo**.
Dry-run por padrão:

```bash
python scripts/sleep_consolidate.py          # mostra o plano (não altera nada)
python scripts/sleep_consolidate.py --apply  # efetiva
```

---

## 📄 Licença e autoria

Uso **científico e acadêmico**, mediante **autorização prévia do autor** — ver
[`LICENSE`](LICENSE).

**Autor:** Luiz Dione Barbosa de Melo — IFRJ, Rio de Janeiro, Brasil
[ORCID 0000-0003-2445-9943](https://orcid.org/0000-0003-2445-9943) ·
luiz.melo@ifrj.edu.br
