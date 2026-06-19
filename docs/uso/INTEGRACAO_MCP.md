# Como integrar o LILO ao Claude Desktop e PyCharm

## Pré-checagem (rode SEMPRE antes)

```cmd
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
python scripts\test_mcp_stdio.py --profile desktop
```

Esperado (a contagem varia por profile e evolui — o importante é os 3 `[OK]`):
```
[OK] initialize  -> server: lilo
[OK] tools/list  -> N tools
[OK] lilo_health -> ## LILO -- Status dos Subagentes ...
[SUCCESS] Servidor MCP LILO esta funcional via stdio.
```

Se falhar aqui, **NÃO** configure o Claude Desktop ainda — o erro será silencioso lá.

---

## 1) Claude Desktop

### Configuração

Edite `C:\Users\luizd\AppData\Roaming\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lilo": {
      "command": "C:\\Users\\luizd\\miniforge3\\python.exe",
      "args": [
        "C:\\Users\\luizd\\OneDrive\\Data_Science\\Projetos\\IA.agente\\lilo_mcp.py",
        "--profile", "desktop"
      ],
      "env": {
        "PYTHONPATH": "C:\\Users\\luizd\\OneDrive\\Data_Science\\Projetos\\IA.agente"
      }
    }
  }
}
```

> **Importante:** Use o caminho **absoluto** do Python (`miniforge3\python.exe`), não apenas `"python"`. O Claude Desktop herda o PATH do sistema e pode pegar uma instalação errada.

### Reinicialização

1. Saia do Claude Desktop **pela bandeja do sistema** (clique direito → Quit). Fechar a janela não basta.
2. Abra de novo.
3. No chat, clique no ícone de tools (canto inferior direito do input).
4. Deve aparecer **lilo** com 29 tools.

### Teste

> *"Liste as tools do MCP lilo"*
>
> *"Use `fs_list` para listar `*.py` em `C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente\agents` recursivamente"*
>
> *"Use `lilo_health` e me mostre o status"*

---

## 2) PyCharm AI Assistant

### Configuração

Settings (Ctrl+Alt+S) → Tools → AI Assistant → MCP Servers → Add:

| Campo | Valor |
|---|---|
| Name | `lilo` |
| Command | `C:\Users\luizd\miniforge3\python.exe` |
| Arguments | `C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente\lilo_mcp.py --profile pycharm` |
| Environment Variables | `PYTHONPATH=C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente` |

Save → Apply.

### Por que profile `pycharm` (23 tools) e não `desktop` (29)?

O profile `pycharm` exclui tools que duplicam funcionalidade nativa do PyCharm:
- `lilo_models` (PyCharm já lista modelos)
- `lilo_web_search` / `lilo_web_fetch` (PyCharm tem busca web)
- `lilo_list_skills` / `lilo_run_skill` / `lilo_skill_info` (skills geradas raramente úteis no IDE)

Mantém todas as tools de filesystem (`fs_*`, `run_shell`, `run_python`) — essenciais para refatorar código.

---

## 3) Claude Code (CLI)

Já há um `.mcp.json` no projeto (commitado) que o Claude Code detecta automaticamente quando você abre o repositório. Não precisa configurar.

Para perfil customizado, copie `config/mcp/claude_code.json` para `~/.claude.json`.

---

## Tools disponíveis por profile

> A contagem por profile evolui; a **fonte de verdade é `config/profiles.yaml`**
> (`profiles.<nome>.mcp_tools`), que sobrepõe o `_PROFILE_TOOLS` embarcado em
> `lilo_mcp.py` (fallback). Para expor/ocultar uma tool, edite o YAML. Perfis com
> `mcp_tools: null` (`desktop_dev`, `openclaw`) expõem **todas**. Profile por
> cliente: **Claude Code → `claude_code`** (~32 tools), **Claude Desktop →
> `opus`** (=`claude_desktop`, ~30). Os demais: `bio`/`cowork` (~39, local-only),
> `pycharm_assistant` (~42). A V14.5 somou os tools de redação/docs/EDA/meta
> (`scholar_review`, `paper_*`, `make_*`, `prism_eda`, `create_agent_scaffold`).
> A lista abaixo enumera o núcleo histórico do `desktop`.

### `desktop` (todas as tools — sem filtro)

**Núcleo (6):** `lilo_chat`, `lilo_sql`, `lilo_pdf`, `lilo_scholar`, `lilo_health`, `lilo_models`

**Prism AI (3):** `prism_analyze`, `prism_classify`, `prism_audit`

**Villa-Lobos (2):** `villa_pipeline`, `villa_quick_ask`

**Web (2):** `lilo_web_search`, `lilo_web_fetch`

**Desktop Commander (7):** `fs_read`, `fs_write`, `fs_list`, `fs_stat`, `fs_search`, `run_shell`, `run_python`

**Memória + Custos (6):** `lilo_memory_set`, `lilo_memory_get`, `lilo_memory_list`, `lilo_memory_delete`, `lilo_cost_today`, `lilo_cost_recent`

**Skills (3):** `lilo_list_skills`, `lilo_run_skill`, `lilo_skill_info`

### `pycharm` (~33 tools)

Foco em desenvolvimento/refactoring: inclui `fs_*`, `run_shell`, `run_python`,
`villa_*`, `prism_*`, memória (incl. avançada), cost, ollama manager e as
*composed tools* (`fs_batch_read`, `fs_codemod`, `grep_and_read`). Sem
`lilo_web_*` e sem as meta-skills (`lilo_list_skills`/`run_skill`/`skill_info`).
Conjunto exato em `_PROFILE_TOOLS["pycharm"]`.

---

## Troubleshooting

### Claude Desktop não mostra a tool

1. Você fechou pela bandeja? Janela fechada não recarrega o config.
2. Path do Python está absoluto? `python` puro pode pegar versão errada.
3. Rodou `python scripts\test_mcp_stdio.py --profile desktop`?

### Erro "Module not found"

Falta `PYTHONPATH` no env do MCP server. Confirme que o JSON tem `"env": { "PYTHONPATH": "..." }`.

### Erro "mcp module not installed"

Rode `pip install mcp>=1.0.0` no Python que o Claude Desktop está usando (mesmo path do `command`).

### Tool aparece mas trava ao executar

1. Ollama está rodando? `curl http://localhost:11434/api/tags`
2. Modelo está carregado? Use `lilo_health` para checar.
3. Abrir `logs/lilo.log` e procurar a query — você verá o tier escolhido e qualquer erro.

### `fs_read` retorna "path fora da allow-list"

Edite `LILO_DESKTOP_ALLOW` no `.env` para incluir o diretório alvo. Reinicie o MCP server (sair do Claude Desktop pela bandeja e abrir de novo).
