# LILO — Changelog

## [7.0.0] — 2026-04-25

### Adicionado
- **Policy Engine** — roteamento custo-inteligente com 6 tiers (NO_LLM → CLAUDE_OPUS), budget diário, 35 indicadores de complexidade (bio + stats + DS), normalização de acentos via `_normalize()`
- **3 MCP servers** — `lilo_mcp.py` (Claude Desktop, 11 tools), `lilo_pycharm_mcp.py` (PyCharm, 7 tools + Villa Lobos), `lilo_server.py` (HTTP :8899)
- **Integração Obsidian** — `shared/obsidian.py` salva execuções como notas .md com YAML frontmatter e wikilinks
- **Integração Villa Lobos** — pipeline de 5 agentes do osquestrador_ollama acessível via PyCharm MCP
- **Dashboard aba "Custos"** — visualização de gastos por backend e subagente
- **START_LILO_WINDOWS.bat** — inicialização automática com o Windows (Ollama + Streamlit + Docker)
- **sincronizacao_github.bat** — auto-sync com repositório GitHub
- **GLOSSARIO.md** — 50+ termos de IA, ML, MCP, bioinformática explicados
- **COMANDOS.md** — referência completa de tools, overrides, portas e scripts

### Modificado
- `shared/llm_client.py` — detecção de backend agora é lazy (property), timeout reduzido de 3s para 1s, Ollama verificado primeiro
- `dashboard.py` — porta alterada de 8501 para 8506, adicionada aba Custos
- `docker-compose.yml` — porta dashboard 8506, estrutura validada para 5 serviços
- `frontend/package.json` — adicionado `@types/react-syntax-highlighter`, versão bumped para 7.0.0
- `frontend/Dockerfile` — `npm ci` → `npm install --legacy-peer-deps` para compatibilidade
- `.gitignore` — expandido para proteger API keys, excluir IDEs, caches e artefatos

### Corrigido
- `shared/__init__.py` — truncamento por OneDrive sync → reescrito via bash
- `backend/app/core/logging.py` — crash por `mkdir /app/logs` fora do Docker → guard com try/except
- `backend/app/tools/file_operations.py` — AuditLogger crash no import → lazy property
- `osquestrador_ollama/villa_lobos/mcp_server.py` — código corrompido (junk debug code) removido
- `RUN_LILO.bat` — referência a `docker-compose.new.yml` inexistente → `docker-compose.yml`

### Removido
- `src/`, `maintenance/`, `ajuda_atualizacao/`, `examples/`, `scripts obsoletos` — via LIMPAR_LIXO.bat
- `Analise_SQL/.venv` (371MB) — ambiente virtual antigo
- `.env.docker` — substituído por `.env` unificado
- `config/lilo_optimized.json`, `config/settings.example.yaml` — configs de versões anteriores

## [6.0.0] — 2026-04 (anterior)
- Primeira versão com Docker Compose e subagentes separados
- Dashboard Streamlit 5 abas
- Backend FastAPI com file_operations

## [5.0.0] — 2026-03 (anterior)
- Versão com src/ monolítico
- LiteLLM como proxy principal
- Sem Policy Engine
