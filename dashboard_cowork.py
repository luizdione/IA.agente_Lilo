"""dashboard_cowork.py — Recursos estilo Claude Cowork para o dashboard LILO.

V10.5 (2026-05-31). Pedido por Dione: aproximar o dashboard Streamlit do
LILO das funcionalidades do Claude Cowork — não só visual, mas técnico.

Este módulo concentra a LÓGICA (testável, sem dependência de Streamlit) e as
funções de RENDERIZAÇÃO de páginas novas. As funções de render recebem o
módulo `st` (streamlit) por parâmetro, então este arquivo importa sem exigir
streamlit instalado — facilita teste isolado da lógica de dados.

Páginas/recursos adicionados:
  * Tarefas      — to-do list persistente (KVMemory) + tarefas agendadas.
  * Memória      — CRUD/busca da memória de longo prazo (KVMemory).
  * Conectores   — manifesto de capacidades dos subagentes + tools por perfil MCP.
  * Streaming    — exibição token-a-token no chat e stage-a-stage no Villa Lobos.
"""

import os
import json
import time
import uuid
from datetime import datetime
from pathlib import Path

# ── Constantes ───────────────────────────────────────────────────────────────
TASK_NS = "lilo_tasks"
TASK_STATES = ("pending", "in_progress", "completed")
SCHOLAR_SOURCES = ["auto", "all", "pubmed", "arxiv", "clinicaltrials",
                   "opentargets", "npi", "crossref", "semanticscholar"]
SOURCE_LABELS = {
    "auto": "Auto (PubMed+arXiv)", "all": "Todas as fontes",
    "pubmed": "PubMed", "arxiv": "arXiv",
    "clinicaltrials": "ClinicalTrials.gov", "opentargets": "Open Targets",
    "npi": "NPI Registry", "crossref": "Crossref",
    "semanticscholar": "Semantic Scholar",
}


# ── Memória (helper) ─────────────────────────────────────────────────────────
def _mem():
    from shared.kv_memory import get_memory
    return get_memory()


# ── Tarefas (CRUD via KVMemory) ──────────────────────────────────────────────
def list_tasks(status=None, mem=None):
    """Lista tarefas do LILO (ns=lilo_tasks). Filtra por status se dado."""
    mem = mem or _mem()
    out = []
    for row in mem.list(ns=TASK_NS):
        v = row.get("value")
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                continue
        if not isinstance(v, dict):
            continue
        v["_key"] = row.get("key")
        if status and v.get("status") != status:
            continue
        out.append(v)
    out.sort(key=lambda t: t.get("created_at", ""), reverse=True)
    return out


def add_task(title, notes="", mem=None):
    mem = mem or _mem()
    key = "task_%s" % uuid.uuid4().hex[:12]
    rec = {"id": key, "title": title.strip(), "notes": notes.strip(),
           "status": "pending", "created_at": datetime.now().isoformat(timespec="seconds")}
    mem.set(key, rec, ns=TASK_NS, tags="lilo_task,status:pending")
    return key


def set_task_status(key, status, mem=None):
    mem = mem or _mem()
    if status not in TASK_STATES:
        return False
    rec = mem.get(key, ns=TASK_NS)
    if not isinstance(rec, dict):
        return False
    rec["status"] = status
    rec["updated_at"] = datetime.now().isoformat(timespec="seconds")
    mem.set(key, rec, ns=TASK_NS, tags="lilo_task,status:%s" % status)
    return True


def delete_task(key, mem=None):
    mem = mem or _mem()
    return mem.delete(key, ns=TASK_NS)


def task_counts(mem=None):
    tasks = list_tasks(mem=mem)
    c = {s: 0 for s in TASK_STATES}
    for t in tasks:
        c[t.get("status", "pending")] = c.get(t.get("status", "pending"), 0) + 1
    c["total"] = len(tasks)
    return c


# ── Tarefas agendadas (leitura de SKILL.md) ──────────────────────────────────
def _scheduled_dirs():
    env = os.getenv("LILO_SCHEDULED_DIRS", "")
    dirs = [d for d in env.split(os.pathsep) if d.strip()]
    # Defaults plausíveis (Cowork): ...\Claude\Scheduled
    defaults = [
        os.path.expanduser("~/OneDrive/Documentos/LGM/Documentos/Claude/Scheduled"),
        os.path.expanduser("~/Documentos/Claude/Scheduled"),
        "D:/OneDrive/Documentos/LGM/Documentos/Claude/Scheduled",
    ]
    return dirs + defaults


def _parse_frontmatter(text):
    """Extrai name/description do frontmatter YAML simples de um SKILL.md."""
    name = desc = ""
    if text.startswith("---"):
        block = text.split("---", 2)
        if len(block) >= 3:
            for line in block[1].splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    k = k.strip().lower()
                    if k == "name":
                        name = v.strip()
                    elif k == "description":
                        desc = v.strip()
    return name, desc


def list_scheduled(dirs=None):
    """Lista tarefas agendadas lendo */SKILL.md nos diretórios conhecidos."""
    dirs = dirs or _scheduled_dirs()
    out = []
    seen = set()
    for d in dirs:
        p = Path(d)
        if not p.is_dir():
            continue
        for skill in p.glob("*/SKILL.md"):
            try:
                txt = skill.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            name, desc = _parse_frontmatter(txt)
            tid = name or skill.parent.name
            if tid in seen:
                continue
            seen.add(tid)
            body = txt.split("---", 2)[-1].strip() if txt.startswith("---") else txt
            out.append({"name": tid, "description": desc,
                        "path": str(skill), "prompt": body[:600]})
    return out


# ── Conectores / Capabilities ────────────────────────────────────────────────
def get_capabilities():
    """Manifesto de capacidades de todos os subagentes (capability_registry)."""
    try:
        from agents.villa_lobos.agent import VillaLobosAgent
        return VillaLobosAgent().capability_registry()
    except Exception as e:  # noqa: BLE001
        return {"_error": str(e)}


def get_profile_tools():
    """Mapa perfil MCP -> conjunto de tools (de lilo_mcp._PROFILE_TOOLS)."""
    try:
        import lilo_mcp
        pt = getattr(lilo_mcp, "_PROFILE_TOOLS", {})
        return {k: (sorted(v) if v else "TODAS") for k, v in pt.items()}
    except Exception as e:  # noqa: BLE001
        return {"_error": str(e)}


# ── Streaming ────────────────────────────────────────────────────────────────
def stream_words(text, delay=0.012):
    """Gerador para st.write_stream: emite o texto em pedaços (exibição
    progressiva tipo Cowork). Não é streaming de LLM nativo — é efeito de
    digitação sobre a resposta já calculada. Seguro e sem custo extra."""
    if not text:
        yield ""
        return
    buff = []
    for i, tok in enumerate(str(text).split(" ")):
        buff.append(tok)
        if i % 3 == 0:
            yield " ".join(buff) + " "
            buff = []
            time.sleep(delay)
    if buff:
        yield " ".join(buff)


# ── Render: páginas (recebem `st`) ───────────────────────────────────────────
def render_tasks_page(st):
    st.header("Tarefas")
    st.caption("Lista de tarefas do LILO (persistente) + tarefas agendadas.")
    mem = _mem()

    c = task_counts(mem=mem)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total", c["total"])
    m2.metric("Pendentes", c["pending"])
    m3.metric("Em progresso", c["in_progress"])
    m4.metric("Concluídas", c["completed"])

    with st.form("nova_tarefa", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        title = col1.text_input("Nova tarefa", placeholder="Descreva a tarefa…",
                                label_visibility="collapsed")
        if col2.form_submit_button("Adicionar", use_container_width=True) and title:
            add_task(title, mem=mem)
            st.rerun()

    st.markdown("---")
    tasks = list_tasks(mem=mem)
    if not tasks:
        st.info("Nenhuma tarefa ainda. Adicione acima.")
    for t in tasks:
        cols = st.columns([0.5, 5, 2, 1])
        done = t.get("status") == "completed"
        checked = cols[0].checkbox("", value=done, key="chk_" + t["_key"],
                                   label_visibility="collapsed")
        if checked != done:
            set_task_status(t["_key"], "completed" if checked else "pending", mem=mem)
            st.rerun()
        label = ("~~%s~~" % t["title"]) if done else t["title"]
        cols[1].markdown(label)
        new_status = cols[2].selectbox(
            "status", TASK_STATES, index=TASK_STATES.index(t.get("status", "pending")),
            key="st_" + t["_key"], label_visibility="collapsed")
        if new_status != t.get("status"):
            set_task_status(t["_key"], new_status, mem=mem)
            st.rerun()
        if cols[3].button("🗑", key="del_" + t["_key"]):
            delete_task(t["_key"], mem=mem)
            st.rerun()

    st.markdown("---")
    st.subheader("Tarefas agendadas")
    sched = list_scheduled()
    if not sched:
        st.caption("Nenhuma tarefa agendada encontrada. Defina LILO_SCHEDULED_DIRS "
                   "no .env apontando para a pasta Scheduled do Claude.")
    for s in sched:
        with st.expander("⏰ %s — %s" % (s["name"], s["description"][:80])):
            st.code(s["prompt"], language="markdown")
            st.caption(s["path"])


def render_memory_page(st):
    st.header("Memória persistente")
    st.caption("Memória de longo prazo do LILO (KVMemory). Sobrevive entre sessões.")
    mem = _mem()

    all_rows = mem.list()
    namespaces = sorted({r["ns"] for r in all_rows}) or ["default"]
    cols = st.columns([2, 3])
    ns_sel = cols[0].selectbox("Namespace", ["(todos)"] + namespaces)
    q = cols[1].text_input("Buscar", placeholder="texto em chave/valor/tags…")

    if q:
        rows = mem.search(q, ns=None if ns_sel == "(todos)" else ns_sel)
    else:
        rows = mem.list(ns=None if ns_sel == "(todos)" else ns_sel)

    st.caption("%d entrada(s)" % len(rows))
    for r in rows:
        with st.expander("**%s** / %s  ·  %s" % (r["ns"], r["key"],
                                                 (r.get("tags") or ""))):
            val = r["value"]
            if isinstance(val, (dict, list)):
                st.json(val)
            else:
                st.code(str(val))
            st.caption("atualizado: %s" % r.get("updated_at", ""))
            if st.button("Apagar", key="memdel_%s_%s" % (r["ns"], r["key"])):
                mem.delete(r["key"], ns=r["ns"])
                st.rerun()

    st.markdown("---")
    with st.expander("➕ Nova entrada de memória"):
        with st.form("nova_mem", clear_on_submit=True):
            k = st.text_input("Chave")
            ns = st.text_input("Namespace", value="user")
            tags = st.text_input("Tags (csv)")
            val = st.text_area("Valor")
            if st.form_submit_button("Salvar") and k and val:
                mem.set(k, val, ns=ns or "user", tags=tags)
                st.success("Salvo: %s/%s" % (ns, k))
                st.rerun()


def render_connectors_page(st):
    st.header("Conectores & Capacidades")
    st.caption("Manifesto dos subagentes do LILO e tools expostas por perfil MCP "
               "(Claude Desktop, Claude Code, PyCharm, OpenClaw, Cowork, bio).")

    caps = get_capabilities()
    if "_error" in caps:
        st.error("Falha ao carregar capacidades: %s" % caps["_error"])
    else:
        st.subheader("Subagentes (%d)" % len(caps))
        for name, cap in caps.items():
            with st.expander("🔌 %s — %s" % (name, cap.get("domain", ""))):
                cc = st.columns(3)
                cc[0].metric("Custo", cap.get("cost_hint", cap.get("cost_tier", "?")))
                cc[1].metric("Latência", cap.get("latency_hint",
                                                 cap.get("latency_class", "?")))
                cc[2].metric("Local-only", str(cap.get("local_only", "?")))
                st.write("**Tools:** ", ", ".join(cap.get("tools", []) or []) or "—")
                st.write("**Keywords:** ", ", ".join(cap.get("keywords", []) or [])[:400])
                st.caption(cap.get("description", ""))

    st.markdown("---")
    st.subheader("Tools por perfil MCP")
    pt = get_profile_tools()
    if "_error" in pt:
        st.warning("Perfis MCP indisponíveis: %s" % pt["_error"])
    else:
        for prof, tools in pt.items():
            with st.expander("⚙️ %s (%s)" % (prof, len(tools) if isinstance(tools, list) else tools)):
                if isinstance(tools, list):
                    st.write(", ".join(tools))
                else:
                    st.write(tools)


def run_villa_with_progress(st, query, iterations=1, allow_delegate=True,
                            use_reader=True, base_path="."):
    """Executa o pipeline Villa_Lobos exibindo progresso por estágio (Cowork-like).

    Usa o stream_callback adicionado em VillaLobosAgent.run() (V10.3).
    Retorna o texto final do pipeline.
    """
    from agents.villa_lobos.agent import VillaLobosAgent
    agent = VillaLobosAgent()
    events = []

    status = st.status("Executando pipeline Villa Lobos…", expanded=True)

    def _cb(stage, st_status, ms=None, preview=None):
        events.append((stage, st_status, ms))
        ms_txt = (" · %d ms" % ms) if ms else ""
        prev = (" — _%s_" % preview) if preview else ""
        status.write("**%s** — %s%s%s" % (stage, st_status, ms_txt, prev))

    ctx = {"iterations": int(iterations), "allow_delegate": allow_delegate,
           "use_reader": use_reader, "base_path": base_path,
           "stream_callback": _cb}
    result = agent.run(query, context=ctx)
    status.update(label="Pipeline concluído (%d eventos)" % len(events),
                  state="complete", expanded=False)
    return result
