# Profile MCP `opus` — guia de uso e reversao

> Criado em **2026-05-08**. Refactor do `lilo_mcp.py` para que o Claude Opus
> (Desktop) tenha acesso apenas as tools que **agregam capacidade real** ao
> modelo, evitando redundancia e desperdicio de tokens.

> **Atualização (2026-06-11):** o conjunto do profile `opus` cresceu de 18 para
> **21 tools** — foram somadas as 3 *composed tools* (`fs_batch_read`,
> `grep_and_read`, `fs_codemod`), que reduzem round-trips MCP. Os números "18"
> citados abaixo refletem a versão original; a **fonte de verdade** é
> `_PROFILE_TOOLS["opus"]` em `lilo_mcp.py` (o servidor loga a contagem ao subir).

---

## TL;DR

```cmd
:: Validar
python scripts\test_mcp_stdio.py --profile opus

:: Reverter (voltar a expor as 35 tools)
:: edite %APPDATA%\Claude\claude_desktop_config.json
:: troque  "--profile", "opus"  por  "--profile", "desktop"
:: e reinicie o Claude Desktop
```

---

## Por que existe

Antes do refactor, o Claude Desktop carregava 35 tools do LILO mas usava
apenas duas: `lilo_web_search` e `lilo_web_fetch`. Razao:

- 17 das 35 tools sao **redundantes** com o Opus 4.x (`lilo_chat`, `lilo_pdf`,
  `villa_pipeline`, `villa_quick_ask`, `prism_audit`, `lilo_sql`, etc.). Opus
  responde melhor sozinho e nao se da ao trabalho de chamar uma tool que vai
  delegar a outro LLM (Ollama) menos capaz.
- As outras 18 tools sao **complementares** ao Opus (acesso ao filesystem do
  PC, execucao de codigo Python local, internet, memoria persistente entre
  sessoes, pipeline estatistico em arquivos do usuario, busca biomedica
  estruturada, controle de modelos Ollama).

A solucao foi criar o profile `opus` que expoe apenas as 18 tools complementares.

---

## As 18 tools do profile `opus`

| Categoria   | Tools | Por que |
|-------------|-------|---------|
| Internet    | `lilo_web_search`, `lilo_web_fetch` | Opus nao tem internet nativa no Claude Desktop |
| Filesystem  | `fs_read`, `fs_write`, `fs_list`, `fs_stat`, `fs_search` | Le/escreve no PC do usuario (allow-list `LILO_DESKTOP_ALLOW`) |
| Execucao    | `run_python`, `run_shell` | Opus nao executa codigo; aqui roda no ambiente conda do usuario |
| Memoria     | `lilo_memory_set`, `_get`, `_list`, `_search` | Persistencia entre sessoes (SQLite local) |
| Literatura  | `lilo_scholar` | PubMed/arXiv com metadados estruturados |
| Estatistica | `prism_analyze`, `prism_classify` | Pipeline ANOVA/t-test/grafico sobre `.xlsx` ou `.csv` |
| Ollama      | `lilo_list_local_models`, `lilo_pull_model` | Inspeciona/baixa modelos locais |

Todas as descriptions foram reescritas com o template
`USE WHEN ... DO NOT USE WHEN ... Exemplo:` para dar ao Opus triggers
inequivocos de quando chamar.

---

## As 17 tools "ocultas" (continuam acessiveis no dashboard)

Tools redundantes com Opus (nao registradas no MCP do Claude Desktop, mas
ainda disponiveis no dashboard Streamlit em http://localhost:8100 via slash
command):

```
/lilo_chat        /lilo_pdf         /lilo_health     /lilo_models
/lilo_sql         /villa_pipeline   /villa_quick_ask /prism_audit
/lilo_run_skill   /lilo_skill_info  /lilo_list_skills
/lilo_memory_delete  /lilo_memory_stats  /lilo_memory_export  /lilo_memory_cleanup
/lilo_cost_today  /lilo_cost_recent
```

Quando voce precisar de uma delas dentro do Claude Desktop, peca explicitamente
ao Opus para chamar `run_shell("python lilo.py <subagente> '<query>'")` ou abra
o dashboard.

---

## Como ativar

### 1. Editar config do Claude Desktop

Abra `%APPDATA%\Claude\claude_desktop_config.json` e use:

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

> Tambem disponivel em `config/mcp/claude_desktop.json` no repositorio.

### 2. Reiniciar o Claude Desktop

Fechar pela bandeja do Windows (clique direito no icone -> Quit) e abrir de
novo. A lista de tools eh cacheada por sessao.

### 3. Validar (opcional, mas recomendado)

```cmd
python scripts\test_mcp_stdio.py --profile opus
```

Saida esperada:

```
[run] C:\Users\luizd\miniforge3\python.exe ...\lilo_mcp.py --profile opus
[env] PYTHONPATH=C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
[OK] initialize  -> server: lilo
[OK] tools/list  -> 18 tools
      - lilo_scholar: Busca estruturada em PubMed e arXiv...
      - prism_analyze: Pipeline cientifico completo...
      - prism_classify: Inspeciona um arquivo de dados...
      - lilo_web_search: Busca web via DuckDuckGo...
      - lilo_web_fetch: Baixa o conteudo textual de uma URL...
      ... +13 mais
[OK] lilo_list_local_models -> NAME ID SIZE ...
[SUCCESS] Servidor MCP LILO esta funcional via stdio.
```

---

## Como reverter

Em qualquer momento, troque o profile no `claude_desktop_config.json`:

```json
"args": [
  "C:\\...\\lilo_mcp.py",
  "--profile", "desktop"
]
```

ou

```json
"args": [
  "C:\\...\\lilo_mcp.py",
  "--profile", "bio"
]
```

E reinicie o Claude Desktop.

| Profile   | # tools | Quando usar |
|-----------|---------|-------------|
| `opus`    | 18      | Default — Claude Desktop com Opus |
| `bio`     | 27      | Pesquisa biomolecular sem `run_shell` |
| `desktop` | 35      | Todas as tools (Cowork / OpenClaw / debug) |
| `pycharm` | ~17     | PyCharm AI Assistant |

---

## Troubleshooting

### "Server transport closed unexpectedly" no log

- Veja `%LOCALAPPDATA%\Claude\logs\mcp-server-lilo.log`.
- Se aconteceu apos varias horas de uso, geralmente eh o Claude Desktop sendo
  fechado/reiniciado ou a maquina suspensa. **Nao eh crash do servidor**.
- Se aconteceu segundos apos uma chamada, eh crash real -- o `_install_excepthook`
  adicionado em 2026-05-08 vai escrever stack trace em stderr.

### "Unknown tool: <nome>" ao chamar uma tool

Significa que a tool nao esta no profile ativo. Opcoes:

1. Trocar para `--profile desktop` (todas as 35 tools).
2. Adicionar a tool ao set `"opus"` em `lilo_mcp.py::_PROFILE_TOOLS`.
3. Chamar via dashboard (slash command).

### Como validar quais tools cada profile expoe

```cmd
python scripts\test_mcp_stdio.py --profile opus
python scripts\test_mcp_stdio.py --profile bio
python scripts\test_mcp_stdio.py --profile desktop
python scripts\test_mcp_stdio.py --profile pycharm
```

A saida `[OK] tools/list -> N tools` mostra a contagem por profile.

---

## Referencias

- Codigo do filtro: `lilo_mcp.py::_PROFILE_TOOLS` e `_profile_tool` decorator.
- Configs prontos: `config/mcp/claude_desktop.json`, `bio.json`, `pycharm.json`,
  `claude_code.json`, `openclaw.json`.
- Smoke test: `scripts/test_mcp_stdio.py`.
- Decisao tecnica: chat de 2026-05-08 (analise das 35 tools com Opus 4.x).
