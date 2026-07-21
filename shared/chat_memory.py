"""
shared/chat_memory.py -- Persistencia de historico de chats do LILO
====================================================================
Salva e carrega conversas em SQLite para continuidade entre sessoes.
Suporta projetos (workspaces) e busca por conteudo.

Uso:
    from shared.chat_memory import ChatMemory
    mem = ChatMemory()
    chat_id = mem.new_chat("Analise de genomas")
    mem.add_message(chat_id, "user", "Liste as tabelas")
    mem.add_message(chat_id, "assistant", "Tabelas: genomas, sequencias...")
    chats = mem.list_chats()
"""

import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
# 2026-05-25: caminho configuravel via env -- mesma convencao de
# LILO_COST_DB / LILO_KV_MEMORY_DB. Permite mover o SQLite de historico
# para fora de pastas sincronizadas (OneDrive) e facilita testes.
DB_PATH = Path(os.environ.get(
    "LILO_CHAT_DB", str(_ROOT / "data" / "chat_history.db")))


class ChatMemory:
    """Gerencia historico de chats e projetos em SQLite."""

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    project_id TEXT DEFAULT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    subagent TEXT DEFAULT 'chat',
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (chat_id) REFERENCES chats(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    description TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_chat
                ON messages(chat_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chats_project
                ON chats(project_id)
            """)
            # 2026-05-08: tasks por projeto (sidebar 'Progresso')
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    done INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_project
                ON project_tasks(project_id)
            """)
            conn.commit()

    # -- Chats -----------------------------------------------------------------

    def new_chat(self, title="Novo chat", subagent="chat", project_id=None):
        """Cria um novo chat e retorna seu ID."""
        chat_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO chats (id, title, project_id, created_at, updated_at, subagent) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (chat_id, title, project_id, now, now, subagent))
            conn.commit()
        return chat_id

    def ensure_chat(self, chat_id, title="Sessao", subagent="chat",
                    project_id=None):
        """Garante (idempotente) que um chat com id EXPLICITO exista.

        Diferente de `new_chat`, que gera o id, aqui o cliente controla o id
        -- caso de uso: sessoes da API HTTP (`/v1/chat` com `session_id`), onde
        o mesmo id reentra em multiplas requests para dar memoria multi-turno.
        Usa INSERT OR IGNORE: nao sobrescreve um chat ja existente. Retorna o
        proprio chat_id.
        """
        now = datetime.now().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO chats "
                "(id, title, project_id, created_at, updated_at, subagent) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (chat_id, title, project_id, now, now, subagent))
            conn.commit()
        return chat_id

    def add_message(self, chat_id, role, content):
        """Adiciona mensagem a um chat existente."""
        now = datetime.now().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO messages (chat_id, role, content, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (chat_id, role, content, now))
            conn.execute(
                "UPDATE chats SET updated_at = ? WHERE id = ?",
                (now, chat_id))
            # Auto-titulo: usar primeiras palavras da primeira msg do user
            cur = conn.execute(
                "SELECT title FROM chats WHERE id = ?", (chat_id,))
            row = cur.fetchone()
            if row and row[0] == "Novo chat" and role == "user":
                short = content[:60].strip()
                if len(content) > 60:
                    short += "..."
                conn.execute(
                    "UPDATE chats SET title = ? WHERE id = ?",
                    (short, chat_id))
            conn.commit()

    def get_messages(self, chat_id):
        """Retorna todas as mensagens de um chat."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT role, content, timestamp FROM messages "
                "WHERE chat_id = ? ORDER BY id ASC",
                (chat_id,))
            return [dict(r) for r in cur.fetchall()]

    def distill_facts(self, chat_id, max_facts=6, model=None):
        """V15 FASE 3: destila FATOS DURAVEIS do historico (preferencias
        estaveis, decisoes, caminhos, ferramentas) via Ollama BARATO e grava em
        kv ns='user'. Prompt anti-invencao estrito (so o que aparece no
        historico). Retorna a lista de fatos gravados. NB: usa Ollama -> GPU."""
        import json as _json
        import os as _os
        import re as _re
        msgs = self.get_messages(chat_id)
        if not msgs:
            return []
        convo = "\n".join(
            "%s: %s" % ("Usuario" if m["role"] == "user" else "LILO",
                        m.get("content", ""))
            for m in msgs)[:8000]
        try:
            from shared.llm_client import get_client, MODELS
            cli = get_client()
            mdl = model or _os.getenv("LILO_DISTILL_MODEL",
                                      MODELS.get("autocomplete"))
            prompt = (
                "Extraia ate %d FATOS DURAVEIS sobre o usuario a partir do "
                "historico (preferencias estaveis, decisoes, caminhos de "
                "arquivos/projetos, ferramentas). Use SOMENTE o que aparece "
                "LITERALMENTE no historico; NAO invente nem deduza. Ignore o "
                "efemero. Responda APENAS JSON: "
                '{"facts":[{"key":"snake_case_curto","value":"texto curto"}]}.'
                "\n\nHISTORICO:\n%s" % (max_facts, convo))
            raw = cli.chat(prompt,
                           system="Extrator de fatos. Responda JSON valido. PT-BR.",
                           model=mdl, temperature=0.1, max_tokens=512)
            m = _re.search(r"\{.*\}", raw or "", _re.DOTALL)
            facts = (_json.loads(m.group(0)).get("facts") if m else []) or []
        except Exception:
            return []
        written = []
        try:
            from shared.kv_memory import get_memory
            kv = get_memory()
            for f in facts[:max_facts]:
                k = str((f or {}).get("key", "")).strip()
                v = str((f or {}).get("value", "")).strip()
                if k and v:
                    kv.set(k, v, ns="user", tags="distilled")
                    written.append({"key": k, "value": v})
        except Exception:
            pass
        return written

    def list_chats(self, project_id=None, limit=50):
        """Lista chats recentes, opcionalmente filtrados por projeto."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if project_id:
                cur = conn.execute(
                    "SELECT id, title, subagent, created_at, updated_at, project_id "
                    "FROM chats WHERE project_id = ? "
                    "ORDER BY updated_at DESC LIMIT ?",
                    (project_id, limit))
            else:
                cur = conn.execute(
                    "SELECT id, title, subagent, created_at, updated_at, project_id "
                    "FROM chats ORDER BY updated_at DESC LIMIT ?",
                    (limit,))
            return [dict(r) for r in cur.fetchall()]

    def delete_chat(self, chat_id):
        """Remove um chat e suas mensagens."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
            conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
            conn.commit()

    def rename_chat(self, chat_id, new_title):
        """Renomeia um chat."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "UPDATE chats SET title = ? WHERE id = ?",
                (new_title, chat_id))
            conn.commit()

    def get_chat_context(self, chat_id, max_messages=20):
        """Retorna contexto formatado para continuar conversa."""
        msgs = self.get_messages(chat_id)
        recent = msgs[-max_messages:] if len(msgs) > max_messages else msgs
        lines = []
        for m in recent:
            prefix = "Usuario" if m["role"] == "user" else "LILO"
            lines.append(prefix + ": " + m["content"])
        return "\n\n".join(lines)

    # -- Projetos ---------------------------------------------------------------

    def new_project(self, name, path="", description=""):
        """Cria um novo projeto."""
        proj_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO projects (id, name, path, created_at, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (proj_id, name, path, now, description))
            conn.commit()
        return proj_id

    def list_projects(self):
        """Lista todos os projetos."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT id, name, path, created_at, description FROM projects "
                "ORDER BY created_at DESC")
            return [dict(r) for r in cur.fetchall()]

    def delete_project(self, project_id):
        """Remove projeto (chats ficam orfaos)."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "UPDATE chats SET project_id = NULL WHERE project_id = ?",
                (project_id,))
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()

    # -- Notas Markdown por projeto (auto-update) ------------------------------
    # Para cada projeto, mantem-se um notes.md em data/projects/<proj_id>/notes.md
    # com 4 secoes fixas:
    #   ## Estado atual
    #   ## Etapas concluidas
    #   ## Etapas pendentes
    #   ## Historico de execucoes
    # LILO consulta este arquivo no inicio de cada chat (build_project_context)
    # e o atualiza ao fim (update_project_notes_after_chat).

    def _project_notes_path(self, project_id):
        """Retorna o caminho do notes.md do projeto, criando o diretorio."""
        from pathlib import Path
        notes_dir = self.db_path.parent / "projects" / project_id
        notes_dir.mkdir(parents=True, exist_ok=True)
        return notes_dir / "notes.md"

    def _ensure_project_notes(self, project_id):
        """Cria notes.md com template se nao existir."""
        path = self._project_notes_path(project_id)
        if path.exists():
            return path
        # Buscar nome do projeto
        name = "Projeto"
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute(
                "SELECT name, description FROM projects WHERE id = ?",
                (project_id,))
            row = cur.fetchone()
            if row:
                name = row[0]
                desc = row[1] or ""
            else:
                desc = ""
        template = (
            f"# {name}\n\n"
            f"{desc}\n\n" if desc else f"# {name}\n\n"
        )
        template += (
            "## Estado atual\n"
            "_Ainda nao iniciado._\n\n"
            "## Etapas concluidas\n"
            "<!-- LILO adiciona aqui automaticamente apos cada chat -->\n\n"
            "## Etapas pendentes\n"
            "<!-- LILO adiciona aqui automaticamente apos cada chat -->\n\n"
            "## Historico de execucoes\n"
            "<!-- LILO adiciona timeline aqui apos cada chat -->\n\n"
            "## Decisoes e contexto\n"
            "_(livre — adicione contexto que LILO deve lembrar)_\n"
        )
        path.write_text(template, encoding="utf-8")
        return path

    def get_project_notes(self, project_id):
        """Retorna o conteudo do notes.md do projeto (criando se necessario)."""
        if not project_id:
            return ""
        path = self._ensure_project_notes(project_id)
        return path.read_text(encoding="utf-8")

    def get_project_notes_path(self, project_id):
        """Retorna o caminho absoluto do notes.md (para abrir em nova janela)."""
        if not project_id:
            return None
        return str(self._ensure_project_notes(project_id))

    def append_to_section(self, project_id, section, line):
        """Adiciona uma linha ao final de uma secao do notes.md.
        Section: 'Estado atual', 'Etapas concluidas', 'Etapas pendentes',
                 'Historico de execucoes', 'Decisoes e contexto'."""
        if not project_id or not line:
            return
        path = self._ensure_project_notes(project_id)
        content = path.read_text(encoding="utf-8")
        marker = f"## {section}"
        idx = content.find(marker)
        if idx == -1:
            # Secao nao existe, anexar no final
            content = content.rstrip() + f"\n\n{marker}\n{line}\n"
        else:
            # Achar fim da secao (proxima ## ou fim do arquivo)
            after = content.find("\n## ", idx + len(marker))
            insert_at = after if after != -1 else len(content)
            # Inserir antes do proximo ## ou no fim
            head = content[:insert_at].rstrip()
            tail = content[insert_at:]
            content = head + f"\n{line}\n\n" + tail.lstrip("\n")
        path.write_text(content, encoding="utf-8")

    # -- Project tasks (Progresso) ---------------------------------------------

    def add_task(self, project_id: str, title: str) -> str:
        """Adiciona uma task ao projeto. Retorna id curto (8 chars)."""
        task_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO project_tasks "
                "(id, project_id, title, done, created_at, updated_at) "
                "VALUES (?, ?, ?, 0, ?, ?)",
                (task_id, project_id, title, now, now),
            )
            conn.commit()
        return task_id

    def list_tasks(self, project_id: str) -> list:
        """Lista tasks de um projeto (pendentes primeiro, mais recentes no topo)."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT id, project_id, title, done, created_at, updated_at "
                "FROM project_tasks WHERE project_id = ? "
                "ORDER BY done ASC, updated_at DESC",
                (project_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    def set_task_done(self, task_id: str, done: bool) -> None:
        """Marca task como feita / pendente."""
        now = datetime.now().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "UPDATE project_tasks SET done = ?, updated_at = ? WHERE id = ?",
                (1 if done else 0, now, task_id),
            )
            conn.commit()

    def delete_task(self, task_id: str) -> None:
        """Remove uma task."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM project_tasks WHERE id = ?", (task_id,))
            conn.commit()

    def rename_task(self, task_id: str, new_title: str) -> None:
        """Atualiza o titulo de uma task."""
        now = datetime.now().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "UPDATE project_tasks SET title = ?, updated_at = ? WHERE id = ?",
                (new_title, now, task_id),
            )
            conn.commit()

    def task_progress(self, project_id: str) -> dict:
        """Retorna {total, done, pct} para barra de progresso."""
        tasks = self.list_tasks(project_id)
        total = len(tasks)
        done = sum(1 for t in tasks if t["done"])
        pct = int(done * 100 / total) if total else 0
        return {"total": total, "done": done, "pct": pct}

    # -- Resumo heuristico -----------------------------------------------------

    def _summarize_chat_heuristic(self, chat_id, max_words=40):
        """Resumo heuristico (sem LLM, zero tokens) do chat:
        primeira pergunta do user + ultima resposta do assistente, truncadas."""
        msgs = self.get_messages(chat_id)
        if not msgs:
            return ""
        first_user = next((m for m in msgs if m["role"] == "user"), None)
        last_asst = next(
            (m for m in reversed(msgs) if m["role"] == "assistant"), None)
        parts = []
        if first_user:
            q = " ".join(first_user["content"].split()[:max_words])
            parts.append(f"Pergunta: {q}")
        if last_asst:
            r = " ".join(last_asst["content"].split()[:max_words])
            parts.append(f"Resposta: {r}")
        return " | ".join(parts)

    def update_project_notes_after_chat(self, project_id, chat_id,
                                         tags=None, status="ok"):
        """Auto-atualiza notes.md apos um chat: registra timeline.
        Chamar no fim de cada interacao do dashboard."""
        if not project_id or not chat_id:
            return
        # Pega titulo e timestamp do chat
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT title, subagent, updated_at FROM chats WHERE id = ?",
                (chat_id,))
            row = cur.fetchone()
            if not row:
                return
            title = row["title"]
            subagent = row["subagent"]
            ts = row["updated_at"]
        # Resumo heuristico (sem gastar tokens)
        summary = self._summarize_chat_heuristic(chat_id, max_words=30)
        ts_short = ts[:19].replace("T", " ")
        tag_str = f" [{', '.join(tags)}]" if tags else ""
        line = (
            f"- **{ts_short}** ({subagent}{tag_str}) — _{title}_  \n"
            f"  Chat `{chat_id}` · status: `{status}`"
        )
        if summary:
            line += f"  \n  > {summary}"
        self.append_to_section(project_id, "Historico de execucoes", line)

    def build_project_context(self, project_id, max_chars=3000):
        """Monta o contexto que LILO deve injetar no system prompt
        ao iniciar um chat dentro de um projeto. Retorna o notes.md
        truncado se necessario."""
        if not project_id:
            return ""
        notes = self.get_project_notes(project_id)
        if len(notes) <= max_chars:
            return notes
        # Truncar preservando inicio (estado atual) + fim (recente)
        head = notes[:max_chars // 2]
        tail = notes[-(max_chars // 2):]
        return head + "\n\n[...truncado...]\n\n" + tail

    # -- Busca -----------------------------------------------------------------

    def search_chats(self, query, limit=20):
        """Busca em mensagens por conteudo."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT DISTINCT c.id, c.title, c.subagent, c.updated_at "
                "FROM chats c JOIN messages m ON c.id = m.chat_id "
                "WHERE m.content LIKE ? "
                "ORDER BY c.updated_at DESC LIMIT ?",
                ("%" + query + "%", limit))
            return [dict(r) for r in cur.fetchall()]


# Singleton
_memory_instance = None

def get_memory(db_path=None):
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = ChatMemory(db_path)
    return _memory_instance
