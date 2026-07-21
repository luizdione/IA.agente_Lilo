# LILO MCP — Profile `opus` (padrão Claude Desktop)

**Data:** 2026-05-14  
**Motivo da mudança:** O profile `desktop` registra **todas** as tools MCP do LILO (sem filtro de profile), sobrecarregando o contexto do modelo e causando erros de inicialização no Opus 4.7. (As ~199 skills geradas do Conda são acessíveis via `/skill` no dashboard, mas **não** são tools MCP expostas — a contagem real de tools MCP é da ordem de algumas dezenas, definida em `_PROFILE_TOOLS`.)

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

Contagem viva em `_PROFILE_TOOLS` (`lilo_mcp.py`); valores abaixo são aproximados:

| Profile | Contexto | Tools MCP |
|---------|----------|-------|
| `desktop` | Todas as tools MCP (sem filtro) | todas (~dezenas; skills Conda ficam no `/skill`, não são tools MCP) |
| `opus` | Claude Desktop com Opus | ~21 (curadas, sem redundância) |
| `claude_code` | Claude Code CLI | ~22 (sem fs/exec, CC já tem nativos) |
| `pycharm` | PyCharm IDE | ~33 (foco refactoring) |
| `bio` / `cowork` | Pesquisa biomolecular / automação | ~30 (sem exec, segurança) |

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
