# CLAUDE.md — LILO

Guia enxuto para o Claude (Desktop e Code) trabalhar neste repositório gastando o mínimo de tokens. Mantenha este arquivo curto — ele entra no contexto a cada sessão.

## O que é
LILO (Local Intelligent LLM Orchestrator) — orquestrador pessoal de IA para bioinformática/ciência de dados. **Local-first**: Ollama (RTX 3060) resolve a maioria; Claude API é fallback para tarefas complexas, com budget diário (`LILO_DAILY_BUDGET`, default US$1). Branch de desenvolvimento: `arch-v10`.

## Como rodar
```cmd
streamlit run dashboard.py          # UI principal -> http://localhost:8100
python lilo.py "pergunta"           # CLI
python lilo.py health               # status de backends/subagentes
python scripts\test_mcp_stdio.py --profile claude_code   # valida o MCP
```

## MCP: qual profile usar (importante p/ tokens)
O servidor `lilo_mcp.py` expõe conjuntos de tools por `--profile` (fonte de verdade: `config/profiles.yaml` + `_PROFILE_TOOLS` em `lilo_mcp.py`). O perfil é resolvido por `--profile` (CLI) > `LILO_MCP_PROFILE` > `LILO_SERVER_PROFILE`.

| Cliente | Profile | Por quê |
|---|---|---|
| **Claude Code** | `claude_code` | CC já tem Read/Write/Bash/Glob/Grep/WebSearch nativos. O LILO só expõe o **complementar** (`prism_*`, `lilo_scholar`, `lilo_pdf`, `villa_*`, `lilo_memory_*`, custo, Ollama). Evita duplicar tools e inflar contexto. |
| **Claude Desktop** | `opus` (=`claude_desktop`) | Desktop não tem filesystem/web/exec nativos → o LILO adiciona `fs_*`, `run_*`, `lilo_web_*`. |

**Regra de ouro:** no Claude Code, prefira as tools **nativas** (Read/Bash/Grep/WebSearch) às equivalentes do LILO. Use o LILO só para o que ele agrega: estatística (`prism_*`), literatura biomédica estruturada (`lilo_scholar`), PDFs científicos (`lilo_pdf`), pipeline multiagente (`villa_*`) e memória persistente entre sessões (`lilo_memory_*`).

## Estrutura
```
lilo.py            Orquestrador (route() + Policy Engine)
lilo_mcp.py        MCP server unificado (--profile)
dashboard.py       Streamlit :8100
agents/            Subagentes (sql, pdf, scholar, prism, villa, gateway, desktop, paper, docgen, skillsmith)
shared/            llm_client (Ollama->LiteLLM->Anthropic), policy, server_profile, base_agent
config/profiles.yaml   Perfis MCP + policy (hot-reload por mtime)
lilo_skills/       Skills auto-geradas
docs/              uso/, tecnico/, versoes/CHANGELOG.md
_ARCHIVE_v10/      Código legado — NÃO TOCAR
```

## Convenções
- **Idioma:** PT-BR.
- **Não duplicar subagentes** — vivem só em `agents/`.
- **Após editar profiles/tools:** reinicie o cliente MCP (a lista de tools é cacheada por sessão).
- **Segurança fs/shell:** `fs_*`/`run_shell` respeitam a allow-list `LILO_DESKTOP_ALLOW`.
- Mudanças de modelo/budget vêm do `.env` (ver tabela no `README.md`).
