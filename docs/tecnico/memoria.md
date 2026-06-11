# LILO — Sistema de Memória

**Versão:** v10.3 (2026-05-07)
**Path:** `shared/kv_memory.py`

---

## Duas camadas de memória

LILO tem dois sistemas de memória independentes, cada um com propósito distinto:

| Camada | Path | Propósito |
|---|---|---|
| **`chat_memory.py`** | `data/chat_history.db` | Histórico de mensagens de chats e projetos (Streamlit dashboard) |
| **`kv_memory.py`** | `%LOCALAPPDATA%\LILO\memory\kv_memory.db` | Pares chave/valor persistentes (preferências, fatos, cache) |

Este documento foca no `kv_memory.py`, que é o sistema acessível como tools MCP (`lilo_memory_*`).

---

## Localização do banco (v10.3)

A partir da v10.3, o banco fica **fora do OneDrive** por padrão para evitar `disk I/O error` e locks de sync:

- **Windows:** `%LOCALAPPDATA%\LILO\memory\kv_memory.db`
- **Unix:** `~/.local/share/lilo/memory/kv_memory.db`
- **Override:** env `LILO_KV_MEMORY_DB=<caminho_absoluto>`

Ao iniciar pela primeira vez após o upgrade, o LILO **migra automaticamente** o banco legado de `memory/kv_memory.db` (no OneDrive) para o novo local. O arquivo original é mantido como backup.

---

## Schema

```sql
CREATE TABLE kv (
    ns TEXT NOT NULL DEFAULT 'default',
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    tags TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    expires_at TEXT,                    -- v10.3: TTL opcional
    PRIMARY KEY (ns, key)
);
CREATE INDEX idx_kv_ns ON kv(ns);
CREATE INDEX idx_kv_expires ON kv(expires_at);
CREATE INDEX idx_kv_tags ON kv(tags);

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL                 -- ex: schema_version=2
);
```

**PRAGMA aplicados na conexão:**

- `journal_mode=WAL` — permite leituras concorrentes durante escrita
- `synchronous=NORMAL` — boa relação durabilidade/performance
- `busy_timeout=5000` — espera até 5s se outro processo segura lock

---

## Namespaces — convenção sugerida

| Namespace | Uso |
|---|---|
| `default` | Catch-all |
| `user` | Preferências do usuário (`preferred_model`, `default_db`, `editor_dark_mode`) |
| `project` | Estado de projetos ativos (`current_pdf`, `last_query`, `pipeline_stage`) |
| `cache` | Resultados temporários, normalmente com `ttl_seconds` |
| `session` | Estado da sessão atual (limpo periodicamente) |
| `audit` | Registros para auditoria/replay |

---

## API Python

```python
from shared.kv_memory import get_memory

mem = get_memory()                                  # singleton

# CRUD básico
mem.set("preferred_model", "claude-sonnet-4-5", ns="user")
mem.set("scratch", "tmp data", ns="cache", ttl_seconds=3600)
val = mem.get("preferred_model", ns="user")
exists = mem.delete("preferred_model", ns="user")   # bool

# Listagem com filtros
rows = mem.list(ns="user")                          # todos do user
rows = mem.list(ns="user", tag="hotkey")            # filtra por tag
rows = mem.list(include_expired=True)               # inclui expirados

# Busca textual (case-insensitive em key/value/tags)
hits = mem.search("claude", ns="user", limit=50)

# Manutenção
n = mem.cleanup_expired()                           # remove expirados
mem.clear_namespace("cache")                        # limpa ns inteiro

# Diagnóstico
mem.stats()
# {
#   "total": 42, "by_namespace": {"user": 12, "project": 30},
#   "expired": 0, "db_path": "...", "db_size_bytes": 81920,
#   "schema_version": 2
# }

# Backup/restore
backup_json = mem.export_json(ns="user")
mem.import_json(backup_json, overwrite=False)
```

---

## API MCP (8 tools)

Disponíveis em **todos os clientes** (Claude Desktop, Code, PyCharm,
dashboard 8100, API HTTP `/v1/tools/call`):

| Tool | Args |
|---|---|
| `lilo_memory_set` | `key, value, namespace="default", tags="", ttl_seconds=opcional` |
| `lilo_memory_get` | `key, namespace="default"` |
| `lilo_memory_list` | `namespace="", tag=""` |
| `lilo_memory_delete` | `key, namespace="default"` |
| `lilo_memory_search` | `query, namespace="", limit=50` |
| `lilo_memory_stats` | — |
| `lilo_memory_export` | `namespace=""` |
| `lilo_memory_cleanup` | — |

**Exemplos no chat (`/` no dashboard):**

```
/lilo_memory_set key=ollama_warmup value=qwen2.5-coder:14b namespace=user tags=preferred
/lilo_memory_set key=session_token value=abc namespace=cache ttl_seconds=3600
/lilo_memory_search query=qwen
/lilo_memory_stats
/lilo_memory_export namespace=user
```

---

## TTL — quando usar

| Cenário | `ttl_seconds` sugerido |
|---|---|
| Token de sessão temporário | `3600` (1h) |
| Cache de resposta de API externa | `300` a `86400` |
| Resultado intermediário de pipeline | `1800` (30min) |
| Preferência permanente do usuário | **omitir** (sem TTL) |
| Decisão arquitetural anotada | **omitir** |

Use `lilo_memory_cleanup` periodicamente (ou agende) para liberar espaço de entradas expiradas.

---

## Migração da v10.2 → v10.3

Sem ação necessária — a migração é **automática**:

1. Na primeira execução de qualquer código que importe `shared.kv_memory`, o LILO detecta o banco antigo em `memory/kv_memory.db` (OneDrive).
2. Copia para o novo local fora-OneDrive.
3. Cria a coluna `expires_at` se ausente (`_ensure_column`).
4. Insere `schema_version=2` na tabela `meta`.

Se algo der errado:

```cmd
:: forçar uso do banco legado:
set LILO_KV_MEMORY_DB=C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente\memory\kv_memory.db
python lilo.py
```

---

## Limitações conhecidas

- **Não é multi-processo seguro** em escala alta — para uso single-user, WAL + busy_timeout cobre 99% dos casos. Para múltiplos serviços batendo no mesmo DB simultaneamente, considere migrar para Redis ou PostgreSQL.
- **Busca textual** é `LIKE %query%` — não tem ranking por relevância. Para milhares de entradas, performance ainda é boa por causa do índice em `tags`. Se crescer >100k entradas, considere FTS5.
- **Sem replicação** — backup é manual via `export_json` ou cópia do arquivo `.db`.

---

## Roadmap futuro

- **`lilo_memory_import`** como tool MCP (hoje só Python).
- **FTS5** opcional (full-text search com ranking).
- **Backup automático** (snapshot diário do banco em pasta versionada).
- **Embeddings opcionais** — armazenar vetor sentence-transformers junto a cada entrada para busca semântica via `mem.search_semantic("conceito")`.
- **Sync entre máquinas** via tool dedicada (export/import periódico para um Gist privado ou pasta sincronizada explícita, evitando o problema OneDrive-em-cima-do-DB).
