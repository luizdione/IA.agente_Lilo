# LILO — Comandos e Tools (V14.6)

## CLI

| Comando | O que faz |
|---|---|
| `python lilo.py "query"` | Auto-roteia para o subagente correto |
| `python lilo.py sql "..."` | Força o subagente SQL |
| `python lilo.py pdf "..." --file paper.pdf --mode introduction` | Sumariza PDF |
| `python lilo.py scholar "TcTR inhibitors"` | Busca acadêmica |
| `python lilo.py villa "tarefa complexa" ` | Pipeline 5-stage |
| `python lilo.py health` | Status de todos os subagentes e backends |

### Overrides explícitos de tier (em qualquer query)

| Prefixo | Tier forçado |
|---|---|
| `\lilo opus <query>` | Claude Opus |
| `\lilo sonnet <query>` | Claude Sonnet |
| `\lilo heavy <query>` | Ollama heavy (qwen2.5-coder:14b) |
| `\lilo local <query>` | Ollama (llama3.1:8b) |
| `\lilo fast <query>` | Ollama fast (qwen2.5-coder:7b) |

---

## MCP Tools

> O conjunto exposto **varia por profile**. **Fonte da verdade:**
> `config/profiles.yaml` (`profiles.<nome>.mcp_tools`), que sobrepõe o
> `_PROFILE_TOOLS` embarcado em `lilo_mcp.py` (fallback). Perfis com
> `mcp_tools: null` (`desktop_dev`, `openclaw`) expõem **todas**. Profile por
> cliente: **Claude Code → `claude_code`**, **Claude Desktop → `opus`**
> (=`claude_desktop`). Conferir ao vivo: `python scripts/test_mcp_stdio.py --profile <nome>`.

### Núcleo LILO (6)

| Tool | O que faz | Args |
|---|---|---|
| `lilo_chat` | Chat geral com Policy Engine | `query`, `mode` (chat/code/bioinfo/sql), `model` |
| `lilo_sql` | Query SQL + estatística | `query`, `db_path`, `table` |
| `lilo_pdf` | Sumariza PDF científico | `query`, `file_path`, `mode` |
| `lilo_scholar` | Busca PubMed + arXiv | `query`, `source`, `max_results`, `synthesize` |
| `lilo_health` | Status de todos os subagentes | — |
| `lilo_models` | Lista modelos Ollama | — |

### Prism AI (4)

| Tool | O que faz |
|---|---|
| `prism_analyze` | Análise estatística completa de .xlsx/.csv |
| `prism_classify` | Classifica tipo de experimento |
| `prism_audit` | Audita análise estatística |
| `prism_eda` (V13.3) | Perfil exploratório rápido (dimensões, nulos, describe, histogramas, correlação) |

### Villa-Lobos (4)

| Tool | O que faz |
|---|---|
| `villa_pipeline` | Pipeline 5-stage (Orchestrator → Reporter) |
| `villa_quick_ask` | Pergunta direta a um agente Villa específico |
| `villa_explain_routing` | Debug do roteamento (sem executar o pipeline) |
| `villa_route` (V10) | Roteamento puro: decide o alvo sem rodar stages |

### Redação científica, documentos e meta (V13/V14)

Complementares ao Claude; expostos no profile `claude_code` e nos completos.

| Tool | O que faz |
|---|---|
| `scholar_review` | Revisão de literatura estruturada (multi-fonte + dedup + refs reais) |
| `paper_outline` / `paper_section` / `paper_references` / `paper_draft` / `paper_build` | Redação científica (skill build_paper): estrutura, seções com refs reais, build DOCX/TEX/PDF |
| `make_report_docx` / `make_docx` / `make_xlsx` / `make_pptx` | Documentos de escritório (Word/Excel/PowerPoint) |
| `create_agent_scaffold` / `propose_agent` | Cria o scaffold de um novo subagente LILO (meta-skill) |

> Subagentes redatores (`paper`, `docgen`, `scholar_review`) usam modelo **cloud**
> por padrão (`gpt-oss:120b-cloud`) — qualidade alta **sem GPU local**. Ver
> `docs/agentes/` para detalhes de cada subagente.

### Web (2)

| Tool | O que faz |
|---|---|
| `lilo_web_search` | Busca DuckDuckGo restrita a domínios confiáveis |
| `lilo_web_fetch` | Baixa URL (allow-list de domínios) |

### Desktop Commander (7)

Restritos à allow-list em `LILO_DESKTOP_ALLOW`.

| Tool | O que faz |
|---|---|
| `fs_read` | Lê arquivo texto |
| `fs_write` | Escreve/anexa em arquivo |
| `fs_list` | Lista diretório (glob, recursive) |
| `fs_stat` | Metadados de arquivo |
| `fs_search` | Grep recursivo |
| `run_shell` | Executa shell (bloqueia comandos perigosos) |
| `run_python` | Executa snippet Python em subprocess |

### Memória persistente (8) — v10.2 + v10.3

KV store SQLite com TTL, busca textual e backup JSON. Sobrevive entre
sessões e está disponível em **todos os clientes** (Desktop, Code,
PyCharm, dashboard, API HTTP).

**Localização do DB (v10.3):**
- Windows: `%LOCALAPPDATA%\LILO\memory\kv_memory.db` (fora do OneDrive)
- Unix: `~/.local/share/lilo/memory/kv_memory.db`
- Override: env `LILO_KV_MEMORY_DB=<caminho_absoluto>`
- Migração automática do `memory/kv_memory.db` legado na primeira execução.

**CRUD básico (v10.2):**

| Tool | O que faz | Args |
|---|---|---|
| `lilo_memory_set` | Salva valor (com TTL opcional v10.3) | `key`, `value`, `namespace=default`, `tags=""`, `ttl_seconds=opcional` |
| `lilo_memory_get` | Lê valor (retorna vazio se expirou) | `key`, `namespace=default` |
| `lilo_memory_list` | Lista entradas (filtros opcionais) | `namespace=""`, `tag=""` |
| `lilo_memory_delete` | Remove entrada | `key`, `namespace=default` |

**Avançado (v10.3):**

| Tool | O que faz | Args |
|---|---|---|
| `lilo_memory_search` | Busca textual em key/value/tags | `query`, `namespace=""`, `limit=50` |
| `lilo_memory_stats` | Estatísticas (total, by_ns, expired, db_size) | — |
| `lilo_memory_export` | Backup JSON (filtra por ns opcional) | `namespace=""` |
| `lilo_memory_cleanup` | Remove entradas expiradas | — |

**Exemplos:**

```
/lilo_memory_set key=ollama_warmup value=qwen2.5-coder:14b namespace=user tags=preferred
/lilo_memory_set key=session_token value=abc123 namespace=cache ttl_seconds=3600
/lilo_memory_search query=qwen
/lilo_memory_stats
/lilo_memory_export namespace=user
```

### Cost tracker (2) — v10.2

| Tool | O que faz | Args |
|---|---|---|
| `lilo_cost_today` | Resumo do dia (JSON: por backend e subagente) | `target_date=""` (hoje) |
| `lilo_cost_recent` | Últimas N requests (modelo, custo, duração) | `limit=20` (max 200) |

### Ollama model manager (2) — v10.2

| Tool | O que faz | Args |
|---|---|---|
| `lilo_pull_model` | Baixa modelo do Hub (`ollama pull <name>`) | `name`, `timeout=600` |
| `lilo_list_local_models` | Lista modelos instalados localmente | — |

### Skills geradas (3 + 199 dinâmicas)

| Tool | O que faz |
|---|---|
| `lilo_list_skills` | Lista as 199 skills (filtros: tag/package/search) |
| `lilo_run_skill` | Executa uma skill por nome + JSON args |
| `lilo_skill_info` | Schema completo de uma skill |

**Prefixo MCP** (v10.2):
- `skill_<nome>` — skills com `complexity` simple/medium (193 + 6 atualmente)
- `skill_advanced_<nome>` — skills com `complexity=high` (0 atualmente, reservado)

---

## Modos de execução e voz (V14)

### Modos de execução (`LILO_EXEC_MODE` ou seletor no dashboard)

Controlam quanta confirmação o LILO pede antes de **agir** (escrever/rodar):

| Modo | Comportamento |
|---|---|
| `plan` | Só planeja; não executa escrita/shell/python |
| `ask` | Confirma toda ação de risco (shell/python/write fora da allow-list) |
| `accept_edits` | Edita arquivos direto; confirma shell/python |
| `auto` (default) | Executa tudo (comportamento histórico) |

### Microfone e reconhecimento de voz (dashboard)

- **Voz→texto (V14.1):** ícone de microfone no chat → transcrição **local** com
  faster-whisper (CPU, nenhum áudio sai da máquina). Config `LILO_WHISPER_*`.
- **Reconhecimento de locutor (V14.6):** cadastre 3+ amostras da sua voz; o LILO
  marca `owner_verified` quando reconhece o dono. É **conveniência, não
  segurança forte** (MFCC leve). Config `LILO_VOICE_THRESHOLD`/`LILO_VOICE_MARGIN`.

---

## Como configurar

### Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json`:

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

Sair do Claude Desktop pela bandeja (não basta fechar a janela) e reabrir.

### PyCharm AI Assistant

Settings → Tools → AI Assistant → MCP Servers:

| Campo | Valor |
|---|---|
| Name | `lilo` |
| Command | `C:\Users\luizd\miniforge3\python.exe` |
| Arguments | `C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente\lilo_mcp.py --profile pycharm` |
| Env | `PYTHONPATH=C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente` |

### Smoke test (antes de plugar nos clientes)

```cmd
python scripts\test_mcp_stdio.py --profile desktop
```

Esperado: `[SUCCESS] Servidor MCP LILO esta funcional via stdio.`

### Saneamento periódico das skills (v10.2)

Após upgrade de pacotes Conda (scipy/numpy/pandas/etc), funções podem
ter sido **renomeadas, removidas ou ter assinatura alterada**. Rode o
ciclo completo de regeneração:

```cmd
:: 1) escaneia o env Conda atual e detecta funcoes publicas
python lilo_skills\scan_conda_env.py

:: 2) gera skills + schemas + registry.json (com schema_version atualizado)
python lilo_skills\generate_skills.py --validate
```

**Quando rodar:** sempre que `mamba update` ou `pip install -U` for
executado em pacotes científicos. Recomendado: agendar **mensalmente**
via Windows Task Scheduler ou cron.

**Cache invalidation automática:** o `registry.json` agora carrega o
campo `schema_version` (v1.1+). Se uma versão antiga for detectada na
inicialização, o `lilo_skills/__init__.py` emite warning e sugere
regenerar — útil ao trocar de máquina (laptop ↔ desktop).

**Skills `complexity: "high"`:** a partir da v10.2, skills com
complexidade alta recebem o prefixo `skill_advanced_<nome>` no MCP
(em vez de `skill_<nome>`), separando-as no menu `/` do dashboard.
Para reduzir poluição na UI, o dashboard pode chamar
`load_skills_as_tools(include_advanced=False)` e mostrar avançadas em
um filtro separado.

### Pre-commit hook AST (v10.1)

Bloqueia commit se algum `.py` modificado tem `SyntaxError` ou
truncamento OneDrive (null bytes, brackets/strings não fechados).

**Instalar uma vez:**

```cmd
python scripts\install_hooks.py
```

Cria:

- `.git/hooks/pre-commit` — wrapper bash que chama o validador.
- `.git/hooks/pre-commit_diag.bat` — script `.bat` para rodar o validador
  manualmente no Windows nativo (diagnóstico).

**Rodar manualmente** (sem commit):

```cmd
python scripts\pre_commit_ast_check.py                 # todos os .py staged
python scripts\pre_commit_ast_check.py arquivo1.py arquivo2.py
```

Saída exemplo:

```
[pre-commit-ast] validando 3 arquivo(s) Python...
  OK    dashboard.py
  OK    agents/villa_lobos/agent.py
  FAIL  scripts/legado.py  (truncamento provavel -- string aberta nao fechada)

[pre-commit-ast] commit BLOQUEADO -- 1 arquivo(s) invalido(s):
  - scripts/legado.py: truncamento provavel -- string aberta nao fechada

Para emergencias, use: git commit --no-verify
```

**Bypass de emergência:** `git commit --no-verify` (registre o motivo
na mensagem do commit).

**Desinstalar:** `python scripts\install_hooks.py --uninstall`

---

## Tabela de portas

| Serviço | Porta |
|---|---|
| Dashboard LILO Streamlit | 8100 |
| PDFs Library Streamlit | 8101 |
| Ollama | 11434 |
| LiteLLM proxy (opcional) | 4000 |

---

## Atalhos do dashboard (`/` no chat)

Digite `/` no campo de chat para ver autocompletar com:
- Tools core (`/lilo_chat`, `/lilo_sql`, `/villa_pipeline`, etc.)
- Skills geradas (`/scipy_ttest_ind`, `/numpy_mean`, `/pandas_groupby`, etc.)
