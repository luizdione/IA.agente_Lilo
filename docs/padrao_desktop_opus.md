# LILO MCP — Profile `opus` (padrão Claude Desktop)

**Data:** 2026-05-14  
**Motivo da mudança:** O profile `desktop` registra todas as ~220 tools (incluindo 199 skills do Conda), sobrecarregando o contexto do modelo e causando erros de inicialização no Opus 4.7.

---

## O que mudou

Arquivo: `%APPDATA%\Claude\claude_desktop_config.json`

```json
"lilo": {
  "command": "C:\\Users\\luizd\\miniforge3\\python.exe",
  "args": [
    "C:\\Users\\luizd\\OneDrive\\Data_Science\\Projetos\\IA.agente\\lilo_mcp.py",
    "--profile",
    "opus"
  ]
}
```

Antes: `--profile desktop` (todas as tools).  
Agora: `--profile opus` (~20 tools curadas).

---

## Tools incluídas no profile `opus`

| Categoria | Tools | Finalidade |
|-----------|-------|------------|
| Internet | `lilo_web_search`, `lilo_web_fetch` | Acesso web (Opus não tem nativo no Desktop) |
| Filesystem | `fs_read`, `fs_write`, `fs_list`, `fs_stat`, `fs_search` | Leitura/escrita de arquivos no PC |
| Execução local | `run_python`, `run_shell` | Executar código Python e shell |
| Memória | `lilo_memory_set`, `lilo_memory_get`, `lilo_memory_list`, `lilo_memory_search` | KV persistente entre sessões (SQLite) |
| Pesquisa acadêmica | `lilo_scholar` | PubMed/arXiv/bioRxiv estruturado |
| Estatística | `prism_analyze`, `prism_classify` | Pipeline estatístico em .xlsx/.csv |
| Ollama | `lilo_list_local_models`, `lilo_pull_model` | Gerenciar modelos locais |
| Compostas | `fs_batch_read`, `grep_and_read`, `fs_codemod` | Reduzem round-trips MCP |

---

## O que ficou de fora (e por quê)

| Tool excluída | Motivo |
|---------------|--------|
| `lilo_chat` | Redundante — Opus já é o LLM |
| `lilo_pdf` | Redundante — Opus processa PDFs nativamente |
| `villa_pipeline`, `villa_quick_ask`, `villa_explain_routing` | Orquestração multi-agente desnecessária quando Opus é o modelo principal |
| `prism_audit` | Redundante com capacidade nativa do Opus |
| `lilo_list_skills`, `lilo_run_skill`, `lilo_skill_info` | 199 skills do Conda inflam o contexto; usar `run_python` diretamente |
| `lilo_sql` | Disponível via `run_python` + sqlite3/pandas |
| `lilo_health`, `lilo_models` | Diagnóstico; chamar manualmente quando necessário |
| `lilo_cost_*` | Tracking de custo; acessível via memória |

---

## Profiles disponíveis (referência)

| Profile | Contexto | Tools |
|---------|----------|-------|
| `desktop` | Todas as tools | ~220 (inclui 199 skills Conda) |
| `opus` | Claude Desktop com Opus | ~20 (curadas, sem redundância) |
| `claude_code` | Claude Code CLI | ~20 (sem fs/exec, CC já tem nativos) |
| `pycharm` | PyCharm IDE | ~30 (foco refactoring) |
| `bio` | Pesquisa biomolecular | ~25 (sem exec, segurança) |

---

## Como reverter

Editar `%APPDATA%\Claude\claude_desktop_config.json` e trocar:

```json
"--profile", "opus"
```

de volta para:

```json
"--profile", "desktop"
```

Reiniciar o Claude Desktop após a mudança.

---

## Notas

- A mudança requer **reiniciar o Claude Desktop** para ter efeito.
- As skills do Conda continuam acessíveis via `run_python` — basta importar scipy, numpy, pandas etc. diretamente no código.
- Para uso pontual de tools excluídas (ex: `villa_pipeline`), considere o profile `claude_code` ou crie um profile customizado em `lilo_mcp.py` na seção `_PROFILE_TOOLS`.
