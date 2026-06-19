# Desktop Commander — Subagente LILO

**Path:** `agents/desktop/agent.py`
**Adicionado em:** v10.0 (arch-v10) — 2026-05-07
**Aba visual no dashboard 8100:** v10.1 — 2026-05-07
**Status:** Funcional, integrado ao MCP server, dashboard 8100 e formulário visual.

---

## O que faz

Desktop Commander é o subagente do LILO equivalente ao popular MCP `@desktop-commander`, mas:

- **Integrado nativamente** ao orquestrador LILO (não é um MCP separado)
- **Allow-list de paths** em `LILO_DESKTOP_ALLOW` para segurança
- **Bloqueio de comandos perigosos** (`rm -rf /`, `format c:`, `mkfs`, fork bomb)
- **Reaproveitável** via Claude Desktop, PyCharm, CLI e dashboard 8100

---

## Tools expostas (7)

| Tool | Função | Args |
|---|---|---|
| `fs_read` | Lê arquivo texto (UTF-8) | `path`, `max_bytes=200000` |
| `fs_write` | Escreve ou anexa em arquivo | `path`, `content`, `append=False` |
| `fs_list` | Lista diretório com glob | `path`, `glob="*"`, `recursive=False`, `limit=200` |
| `fs_stat` | Metadados (tamanho, mtime) | `path` |
| `fs_search` | Grep recursivo (substring/regex) | `root`, `pattern`, `regex=False`, `limit=50` |
| `run_shell` | Executa comando shell | `cmd`, `cwd`, `timeout=60` |
| `run_python` | Executa snippet Python isolado | `code`, `timeout=60` |

---

## Configuração de segurança

### Allow-list de paths

Edite `LILO_DESKTOP_ALLOW` no `.env` (paths separados por `;` no Windows):

```
LILO_DESKTOP_ALLOW=C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente;D:\OneDrive\Documentos\Workaholics
```

Default (se vazio): apenas a raiz do projeto LILO.

Tools `fs_*` e `run_shell` (com `cwd`) **rejeitam** qualquer path fora da allow-list.

### Comandos bloqueados

Padrões em `DANGEROUS_PATTERNS` (regex case-insensitive):

- `rm -rf /` ou `rm -rf ~`
- `format c:`
- `del /f /s /q ...`
- `mkfs ...`
- `dd if=... of=/dev/...`
- `> /dev/sd[a-z]`
- `:(){ :|:& }` (fork bomb)
- `shutdown`, `reboot`

---

### Modos de execução (V14, `shared/exec_mode.py`)

Além da allow-list, ações de **risco** passam por um *gate* conforme o modo
(`LILO_EXEC_MODE` ou seletor no dashboard). Risco = `run_shell`, `run_python` e
escrita **fora** da allow-list (`write_outside`):

| Modo | `run_shell`/`run_python` | `fs_write` (na allow-list) |
|---|---|---|
| `plan` | bloqueia (só planeja) | bloqueia |
| `ask` | confirma | confirma |
| `accept_edits` | confirma | passa |
| `auto` (default) | passa | passa |

Quando precisa de confirmação, a tool devolve `[[LILO_CONFIRMAR]] <prévia>` sem
executar; o dashboard mostra a prévia + botão **✅ Confirmar e executar**
(`grant_once()` libera a próxima ação). Modo `plan` devolve `[[LILO_PLANO]] …`.
Default `auto` → zero mudança de comportamento.

---

## Exemplos de uso

### Via Claude Desktop (após configurar MCP)

> *"Use `fs_list` para listar arquivos `.py` em `C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente\agents` recursivamente"*

> *"Use `fs_search` para encontrar todas as referências a 'OpenMM' nos meus scripts"*

> *"Use `run_shell` para rodar `nvidia-smi` e me mostrar o output"*

> *"Use `run_python` para calcular `sum(range(1, 101))`"*

### Via CLI (route automático)

```cmd
python lilo.py "liste todos os arquivos .py em agents/"
```

### Via dashboard 8100 (aba Desktop)

A partir da v10.1, a sidebar do dashboard tem um botão **Desktop** que abre uma página com 6 sub-abas, uma por tool:

| Sub-aba | Tool chamada | Campos |
|---|---|---|
| `fs_read` | `fs_read` | `path`, `max_bytes` |
| `fs_write` | `fs_write` | `path`, `content` (textarea), `append` |
| `fs_list` | `fs_list` | `path`, `glob`, `recursive`, `limit` |
| `fs_search` | `fs_search` | `root`, `pattern`, `regex`, `limit` |
| `run_shell` | `run_shell` | `cmd` (textarea), `cwd`, `timeout` |
| `run_python` | `run_python` | `code` (textarea), `timeout` |

Detalhes:

- A allow-list ativa é mostrada num expander no topo da página, para o usuário saber onde pode operar antes de digitar paths.
- Cada formulário chama `lilo.handle_tool_call(nome, args)` — zero duplicação de lógica em relação ao MCP server.
- Saída renderizada em `st.code(...)` com a linguagem apropriada (`bash` para shell, `python` para Python, plain para os demais).
- Resultados de `run_shell`/`run_python` mostram `[exit=N]` + `--- STDOUT ---` + `--- STDERR ---` truncado em 8000/2000 chars.

Caminho rápido: na aba **Chat**, comandos em linguagem natural ainda funcionam; a aba Desktop é para quando você quer operar uma tool específica diretamente.

---

## Arquitetura interna

```
agents/desktop/
├── __init__.py        Exporta DesktopAgent
└── agent.py           Implementação:
                       - _build_allowlist()
                       - _is_path_allowed()
                       - _is_cmd_dangerous()
                       - fs_read, fs_write, fs_list, fs_stat
                       - fs_search, fs_move
                       - run_shell, run_python
                       - DesktopAgent(BaseAgent)
```

`run_python` executa em **subprocess separado** (não no processo do MCP server), para que erros do snippet não derrubem o agente.

---

## Limitações conhecidas

- `fs_read` só decodifica UTF-8 e Latin-1 (não detecta outros encodings).
- `run_shell` tem timeout de 60s default — comandos longos (compilação, build) podem precisar `timeout` maior.
- `fs_search` é Python puro (não usa ripgrep) — pode ser lento em árvores muito grandes (>10k arquivos).
- Allow-list é checada por `Path.relative_to()` — symlinks que apontam fora da allow-list são bloqueados (comportamento desejado, mas pode confundir).

---

## Roadmap

1. ~~UI no dashboard 8100 com formulário visual.~~ **Feito em v10.1.**
2. Adicionar `fs_zip` / `fs_unzip` para arquivamento.
3. Suporte a `fs_diff` (mostrar diff entre dois arquivos).
4. `run_shell` com streaming (atualmente só retorna quando completa).
5. History de comandos executados (persistir últimos N na aba Desktop).
