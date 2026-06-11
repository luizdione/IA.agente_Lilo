"""
agents/PDFs_library/scripts/library_app.py  (v2 — cards estilo /referencias)
=====================================================================
Biblioteca cientifica do LILO. Foco em:
    D:\\OneDrive\\Documentos\\Workaholics\\Artigos PDF
(o banco workaholics.db pode conter outros dirs, mas a UI mostra so esse).

Caracteristicas:
- Sidebar com lista de TEMAS (= subdiretorios de Artigos PDF) e estrelas
  para favoritar. Favoritos aparecem primeiro.
- PDFs com DOI ou ISSN sao apresentados como REFERENCIA cientifica
  no estilo do /11.referencias (header navy, contribuicao editavel,
  chips de meta, botoes Abrir PDF / Resumo Detalhado).
- PDFs sem DOI/ISSN aparecem como "Documento (nao indexado)" — card
  reduzido sem o bloco de contribuicao.
- Campo "Contribuicao para o projeto" persiste em _curation no banco
  (editavel inline, salvo automaticamente).

Uso:
    streamlit run agents/PDFs_library/scripts/library_app.py --server.port 8101

Pre-req:
    pip install streamlit pymupdf
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st

_HERE = Path(__file__).resolve().parent
_LIBROOT = _HERE.parent
_DEFAULT_DB = _LIBROOT / "data" / "workaholics.db"
_SCANNER = _HERE / "build_workaholics_db.py"
_TARGET_ROOT = r"D:\OneDrive\Documentos\Workaholics\Artigos PDF"

# -- Page config -------------------------------------------------------------

st.set_page_config(
    page_title="LILO — Biblioteca",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -- CSS — replica o layout do /referencias do localhost:3838 ---------------
# Header navy com gradiente; corpo branco; bloco azul claro p/ contribuicao;
# botoes azul "Abrir PDF" e verde "Resumo Detalhado".
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg-app:        #f1f4f8;
    --paper-bg:      #ffffff;
    --paper-border:  #e2e8f0;
    --header-from:   #1f3a5f;
    --header-to:     #2d4a73;
    --text-strong:   #0f172a;
    --text-body:     #334155;
    --text-muted:    #64748b;
    --accent-blue:   #3b82f6;
    --accent-green:  #22c55e;
    --contribution-bg: #eff6ff;
    --contribution-bd: #bfdbfe;
    --chip-bd:       #cbd5e1;
}

html, body, [class*="st-"] {
    font-family: 'Inter', -apple-system, sans-serif;
}

/* Fundo geral */
section[data-testid="stMain"], div[data-testid="stAppViewContainer"] > .main {
    background-color: var(--bg-app) !important;
}
div[data-testid="stMainBlockContainer"] {
    padding-top: 1rem !important;
    padding-bottom: 4rem !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0f172a !important;
}
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #f8fafc !important;
}

/* Botoes da sidebar — compactos como linha de tree */
section[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    text-align: left;
    background: transparent !important;
    color: #cbd5e1 !important;
    border: 1px solid transparent !important;
    padding: 3px 6px !important;
    margin: 0 !important;
    font-size: 0.78rem !important;
    line-height: 1.25 !important;
    min-height: 0 !important;
    border-radius: 3px !important;
    font-family: 'Inter', sans-serif !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(59, 130, 246, 0.12) !important;
    border-color: rgba(59, 130, 246, 0.3) !important;
    color: #f8fafc !important;
}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
    gap: 0 !important;
}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
    gap: 0.15rem !important;
    margin: 0 !important;
}
/* Espacamento mais apertado nas colunas da arvore */
section[data-testid="stSidebar"] .stColumn > div {
    padding: 0 !important;
}
/* Rotulo do tema selecionado */
section[data-testid="stSidebar"] .topic-active button {
    background: rgba(59, 130, 246, 0.20) !important;
    border-color: var(--accent-blue) !important;
    color: #f8fafc !important;
    font-weight: 500 !important;
}
/* Estrela */
section[data-testid="stSidebar"] .star-on > button {
    color: #fbbf24 !important;   /* dourado */
}
section[data-testid="stSidebar"] .star-off > button {
    color: #475569 !important;   /* cinza */
}
section[data-testid="stSidebar"] .star-on > button:hover,
section[data-testid="stSidebar"] .star-off > button:hover {
    background: rgba(251, 191, 36, 0.10) !important;
    color: #fbbf24 !important;
}

/* Area principal — cabecalhos */
h1.lilo-header {
    color: var(--text-strong);
    font-weight: 700;
    font-size: 1.7rem;
    margin: 0 0 8px 0;
}
.lilo-subhead {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin-bottom: 18px;
}

/* ---------- CARD DE REFERENCIA (estilo /11.referencias) ---------------- */
.ref-card {
    background: var(--paper-bg);
    border: 1px solid var(--paper-border);
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}
.ref-header {
    background: linear-gradient(135deg, var(--header-from) 0%,
                                          var(--header-to) 100%);
    color: #ffffff;
    padding: 14px 20px;
    position: relative;
}
.ref-title {
    font-weight: 700;
    font-size: 1.02rem;
    line-height: 1.35;
    margin: 0 0 4px 0;
}
.ref-meta-line {
    font-size: 0.82rem;
    opacity: 0.86;
    margin: 0;
}
.ref-meta-line .sep {
    margin: 0 6px;
    opacity: 0.55;
}
.ref-body {
    padding: 16px 20px;
    color: var(--text-body);
    font-size: 0.92rem;
    line-height: 1.55;
}
.ref-body p { margin: 0 0 10px 0; }
.ref-body strong { color: var(--text-strong); }

.ref-contribution {
    background: var(--contribution-bg);
    border: 1px solid var(--contribution-bd);
    border-left: 4px solid var(--accent-blue);
    border-radius: 6px;
    padding: 10px 14px;
    margin: 8px 0 12px 0;
    color: #1e3a8a;
    font-size: 0.88rem;
}
.ref-contribution .lbl {
    font-weight: 700;
    color: #1e40af;
}

.ref-data-line {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    margin: 8px 0 4px 0;
    font-size: 0.85rem;
    color: var(--text-body);
}
.ref-badge {
    background: #d1fae5;
    color: #065f46;
    border: 1px solid #a7f3d0;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 500;
}
.ref-doi {
    color: var(--accent-blue);
    text-decoration: none;
    font-family: 'Consolas', monospace;
    font-size: 0.82rem;
}
.ref-doi:hover { text-decoration: underline; }

.ref-actions {
    display: flex;
    gap: 8px;
    padding: 0 20px 16px 20px;
}
.btn-pdf, .btn-detail {
    display: inline-block;
    padding: 7px 16px;
    border-radius: 5px;
    font-size: 0.82rem;
    font-weight: 600;
    text-decoration: none;
    border: none;
    cursor: pointer;
    transition: filter 0.15s;
}
.btn-pdf {
    background: var(--accent-blue);
    color: #ffffff !important;
}
.btn-detail {
    background: var(--accent-green);
    color: #ffffff !important;
}
.btn-pdf:hover, .btn-detail:hover { filter: brightness(0.92); }

/* Card simples para PDFs nao indexados */
.simple-card {
    background: var(--paper-bg);
    border: 1px solid var(--paper-border);
    border-left: 3px solid var(--text-muted);
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-size: 0.86rem;
}
.simple-card .name {
    font-weight: 600;
    color: var(--text-strong);
}
.simple-card .path {
    font-family: 'Consolas', monospace;
    font-size: 0.74rem;
    color: var(--text-muted);
    margin-top: 4px;
    word-break: break-all;
}

/* Inputs/textarea brancos */
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea {
    background: #ffffff !important;
    color: var(--text-strong) !important;
}

/* Botoes de acao no main (Atualizar, etc) */
section[data-testid="stMain"] div.stButton > button {
    background: #ffffff !important;
    color: var(--text-strong) !important;
    border: 1px solid var(--paper-border) !important;
    font-weight: 500;
}
section[data-testid="stMain"] div.stButton > button:hover {
    border-color: var(--accent-blue) !important;
    color: var(--accent-blue) !important;
}
</style>
""", unsafe_allow_html=True)


# -- Helpers DB --------------------------------------------------------------

def get_db_path() -> Path:
    env_db = os.environ.get("LILO_PDFS_DB")
    return Path(env_db) if env_db else _DEFAULT_DB


def _conn():
    p = get_db_path()
    if not p.exists():
        return None
    return sqlite3.connect(str(p))


@st.cache_data(ttl=15)
def list_topics(_db_mtime: float, target_root: str) -> list[dict]:
    """Lista temas (subdirs de Artigos PDF) com estado de favorito.
    Usa _db_mtime para invalidar cache quando DB eh re-escrito."""
    p = get_db_path()
    if not p.exists():
        return []
    target_norm = os.path.normpath(target_root).lower()
    with sqlite3.connect(str(p)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT i.table_name, i.dir_path, i.n_pdfs, i.last_scan, "
            "       COALESCE(f.starred, 0) AS starred, "
            "       COALESCE(f.sort_order, 0) AS sort_order "
            "FROM _index i "
            "LEFT JOIN _favorites f ON f.table_name = i.table_name")
        rows = [dict(r) for r in cur.fetchall()]
    # Filtra apenas dirs sob Artigos PDF
    rows = [r for r in rows
            if os.path.normpath(r["dir_path"]).lower().startswith(target_norm)]
    # Ordena: starred desc, sort_order asc, n_pdfs desc, nome
    rows.sort(key=lambda r: (-r["starred"], r["sort_order"],
                              -r["n_pdfs"], r["table_name"]))
    return rows


def toggle_favorite(table_name: str):
    p = get_db_path()
    if not p.exists():
        return
    now = datetime.now().isoformat()
    with sqlite3.connect(str(p)) as conn:
        cur = conn.execute(
            "SELECT starred FROM _favorites WHERE table_name = ?",
            (table_name,))
        row = cur.fetchone()
        new = 0 if (row and row[0]) else 1
        conn.execute(
            "INSERT INTO _favorites (table_name, starred, sort_order, updated_at) "
            "VALUES (?, ?, 0, ?) "
            "ON CONFLICT(table_name) DO UPDATE SET "
            "starred=excluded.starred, updated_at=excluded.updated_at",
            (table_name, new, now))
        conn.commit()
    st.cache_data.clear()


@st.cache_data(ttl=15)
def query_papers(table_name: str, search: str = "", limit: int = 200,
                  _db_mtime: float = 0.0) -> list[dict]:
    p = get_db_path()
    if not p.exists():
        return []
    with sqlite3.connect(str(p)) as conn:
        conn.row_factory = sqlite3.Row
        if search:
            q = f"%{search}%"
            cur = conn.execute(
                f'SELECT * FROM "{table_name}" '
                f'WHERE title LIKE ? OR authors LIKE ? OR abstract LIKE ? '
                f'   OR doi LIKE ? OR file_name LIKE ? OR species LIKE ? '
                f'ORDER BY indexed_journal DESC, year DESC LIMIT ?',
                (q, q, q, q, q, q, limit))
        else:
            cur = conn.execute(
                f'SELECT * FROM "{table_name}" '
                f'ORDER BY indexed_journal DESC, year DESC LIMIT ?',
                (limit,))
        return [dict(r) for r in cur.fetchall()]


@st.cache_data(ttl=30)
def get_curation(file_path: str) -> dict:
    p = get_db_path()
    if not p.exists():
        return {"contribution_to_project": "", "dataset_status": ""}
    with sqlite3.connect(str(p)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT contribution_to_project, dataset_status "
            "FROM _curation WHERE file_path = ?", (file_path,))
        row = cur.fetchone()
        if row:
            return dict(row)
    return {"contribution_to_project": "", "dataset_status": ""}


def save_curation(file_path: str, contribution: str, dataset_status: str):
    p = get_db_path()
    if not p.exists():
        return
    with sqlite3.connect(str(p)) as conn:
        conn.execute(
            "INSERT INTO _curation (file_path, contribution_to_project, "
            "dataset_status, updated_at) VALUES (?,?,?,?) "
            "ON CONFLICT(file_path) DO UPDATE SET "
            "contribution_to_project=excluded.contribution_to_project, "
            "dataset_status=excluded.dataset_status, "
            "updated_at=excluded.updated_at",
            (file_path, contribution, dataset_status,
             datetime.now().isoformat()))
        conn.commit()
    st.cache_data.clear()


def db_mtime() -> float:
    p = get_db_path()
    return p.stat().st_mtime if p.exists() else 0.0


# -- Render ------------------------------------------------------------------

def _esc(s: str) -> str:
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _first_author_etal(authors_raw: str) -> str:
    """De 'Last1, First1; Last2, First2' produz 'Last1 et al.'"""
    if not authors_raw:
        return ""
    raw = authors_raw.replace(" and ", ";").replace(",", ";")
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    if not parts:
        return authors_raw[:60]
    first = parts[0]
    # Pega ultimo token (sobrenome) se nome estiver "First Last"
    tokens = first.split()
    surname = tokens[-1] if tokens else first
    return f"{surname} et al." if len(parts) > 1 else surname


def render_indexed_paper(p: dict):
    """Card completo no estilo /11.referencias (PDF com DOI ou ISSN)."""
    title = p.get("title") or p.get("file_name") or "(sem titulo)"
    authors_short = _first_author_etal(p.get("authors", ""))
    year = p.get("year") or "?"
    journal = p.get("journal") or ""
    doi = (p.get("doi") or "").rstrip(".,;)")
    paper_type = p.get("paper_type") or "Artigo"
    species = p.get("species") or ""
    abstract = p.get("abstract") or ""
    file_path = p.get("file_path") or ""

    cur = get_curation(file_path)
    contribution = cur.get("contribution_to_project", "")
    dataset_status = cur.get("dataset_status", "")

    # Linha de meta no header
    meta_bits = []
    head_label = f"{authors_short} ({year})" if authors_short else year
    meta_html = f"{_esc(head_label)}"
    if journal:
        meta_html += f' <span class="sep">—</span> {_esc(journal)}'
    if paper_type:
        meta_html += f' <span class="sep">|</span> {_esc(paper_type)}'
    if species:
        meta_html += f' <span class="sep">|</span> {_esc(species)}'

    # Resumo
    abstract_html = ""
    if abstract:
        abstract_html = (
            f'<p><strong>Resumo:</strong> {_esc(abstract[:1200])}</p>'
        )

    # Contribuicao
    contribution_html = ""
    if contribution.strip():
        contribution_html = (
            f'<div class="ref-contribution">'
            f'<span class="lbl">🧠 Contribuicao para o projeto:</span> '
            f'{_esc(contribution)}'
            f'</div>'
        )

    # Linha "Dados:"
    data_html = '<div class="ref-data-line"><strong>Dados:</strong>'
    if dataset_status:
        data_html += f'<span class="ref-badge">{_esc(dataset_status)}</span>'
    elif paper_type and "evis" in paper_type.lower():
        data_html += '<span class="ref-badge">Revisao (sem dados brutos)</span>'
    if doi:
        doi_url = f"https://doi.org/{_esc(doi)}"
        data_html += (f'<a href="{doi_url}" target="_blank" class="ref-doi">'
                      f'DOI: {_esc(doi)}</a>')
    data_html += '</div>'

    # Botoes — usamos data: URI para abrir PDF local em nova aba
    pdf_btn = ""
    if file_path:
        try:
            file_url = Path(file_path).as_uri()
            pdf_btn = (f'<a href="{file_url}" target="_blank" class="btn-pdf">'
                       f'Abrir PDF</a>')
        except Exception:
            pass

    detail_btn = (
        f'<a href="#detail_{_esc(p["id"])}" class="btn-detail">'
        f'Resumo Detalhado</a>'
    )

    html = f"""
    <div class="ref-card">
        <div class="ref-header">
            <div class="ref-title">{_esc(title)}</div>
            <p class="ref-meta-line">{meta_html}</p>
        </div>
        <div class="ref-body">
            {abstract_html}
            {contribution_html}
            {data_html}
        </div>
        <div class="ref-actions">
            {pdf_btn}
            {detail_btn}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    # Editor inline (expander) para a contribuicao
    with st.expander("✏️ Editar contribuicao para o projeto",
                       expanded=False):
        new_contrib = st.text_area(
            "Contribuicao",
            value=contribution,
            key=f"contrib_{p['id']}",
            height=120,
            label_visibility="collapsed",
            placeholder="Descreva como este paper contribui para o projeto..."
        )
        new_status = st.text_input(
            "Status dos dados (badge)",
            value=dataset_status or (
                "Revisao (sem dados brutos)"
                if "evis" in (paper_type or "").lower() else ""),
            key=f"status_{p['id']}",
            placeholder="Ex: Dados publicos GEO GSE12345 / Revisao",
        )
        col_save, col_cancel = st.columns([1, 4])
        with col_save:
            if st.button("Salvar", key=f"save_{p['id']}", type="primary"):
                save_curation(file_path, new_contrib.strip(),
                              new_status.strip())
                st.success("Salvo.")
                st.rerun()


def render_simple_paper(p: dict):
    """Card simples — PDF sem DOI/ISSN."""
    name = _esc(p.get("file_name") or "")
    fp = _esc(p.get("file_path") or "")
    n_pages = p.get("n_pages") or 0
    year = _esc(p.get("year") or "")
    title = _esc(p.get("title") or "")

    title_line = title if title else name
    meta_bits = []
    if year:
        meta_bits.append(year)
    if n_pages:
        meta_bits.append(f"{n_pages} pgs")
    meta_str = " · ".join(meta_bits)

    # Botao abrir PDF
    pdf_link = ""
    if p.get("file_path"):
        try:
            file_url = Path(p["file_path"]).as_uri()
            pdf_link = (f'<a href="{file_url}" target="_blank" '
                        f'style="color:#3b82f6; font-size:0.8rem;">Abrir PDF</a>')
        except Exception:
            pass

    html = f"""
    <div class="simple-card">
        <div class="name">{title_line}</div>
        <div style="color:#64748b; font-size:0.78rem; margin-top:2px;">
            {_esc(meta_str)} {pdf_link}
        </div>
        <div class="path">{fp}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# -- Acoes -------------------------------------------------------------------

def run_scanner_async(extra_root: Optional[str] = None):
    cmd = [sys.executable, str(_SCANNER), "--out", str(get_db_path())]
    if extra_root:
        cmd += ["--root", extra_root]
    return subprocess.Popen(cmd, creationflags=getattr(
        subprocess, "CREATE_NEW_CONSOLE", 0))


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("## 📚 LILO Biblioteca")
    st.caption(f"Raiz: `Artigos PDF`")

    # Acoes globais
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 Atualizar", use_container_width=True,
                      help="Reindexar Artigos PDF"):
            run_scanner_async(extra_root=_TARGET_ROOT)
            st.success("Scanner em background.")
            st.cache_data.clear()
    with col_b:
        if st.button("🧹 Cache", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")
    search_q = st.text_input(
        "🔍 Buscar artigos",
        placeholder="titulo, autor, especie, DOI...",
        key="search_q")

    st.markdown("---")
    # Cabecalho da arvore com icone SVG de biblioteca (estantes verticais)
    # Estilo Lucide "library" — bem mais elegante que pasta amarela do Windows
    st.markdown("""
    <div style="display:flex; align-items:center; gap:6px;
                color:#94a3b8; font-size:0.78rem; font-weight:600;
                text-transform:uppercase; letter-spacing:0.5px;
                margin: 4px 0 6px 0;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
             stroke="#fbbf24" stroke-width="2" stroke-linecap="round"
             stroke-linejoin="round" style="flex-shrink:0;">
            <path d="m16 6 4 14"/>
            <path d="M12 6v14"/>
            <path d="M8 8v12"/>
            <path d="M4 4v16"/>
        </svg>
        <span>Biblioteca · Artigos PDF</span>
    </div>
    """, unsafe_allow_html=True)

    topics = list_topics(db_mtime(), _TARGET_ROOT)
    if not topics:
        st.info("Banco vazio para Artigos PDF. Clique em 🔄 Atualizar.")
    else:
        if "selected_topic" not in st.session_state:
            st.session_state["selected_topic"] = topics[0]["table_name"]
        if "expanded_nodes" not in st.session_state:
            # Por padrao, expande nivel 1 (filhos diretos do root)
            st.session_state["expanded_nodes"] = set([""])

        # ---- Constroi arvore hierarquica a partir dos dir_path ------------
        target = Path(_TARGET_ROOT)
        tree_root = {"name": "", "path": "", "is_topic": False,
                      "n_pdfs": 0, "starred": 0,
                      "table_name": "", "children": {}}

        for t in topics:
            try:
                rel = Path(t["dir_path"]).relative_to(target)
            except ValueError:
                continue
            parts = rel.parts if rel.parts not in ((), (".",)) else ()
            if not parts:
                # Raiz tem PDFs proprios
                tree_root["is_topic"] = True
                tree_root["table_name"] = t["table_name"]
                tree_root["n_pdfs"] = t["n_pdfs"]
                tree_root["starred"] = t["starred"]
                continue
            node = tree_root
            for i, p in enumerate(parts):
                if p not in node["children"]:
                    node["children"][p] = {
                        "name": p,
                        "path": "/".join(parts[:i+1]),
                        "is_topic": False,
                        "n_pdfs": 0,
                        "starred": 0,
                        "table_name": "",
                        "children": {},
                    }
                node = node["children"][p]
            node["is_topic"] = True
            node["table_name"] = t["table_name"]
            node["n_pdfs"] = t["n_pdfs"]
            node["starred"] = t["starred"]

        # Calcula PDFs cumulativos (folha + descendentes) e flag de favorito
        # cumulativo (qualquer descendente starred) p/ ordenar pais
        def _cum(n):
            total = n["n_pdfs"]
            any_star = bool(n["starred"])
            for c in n["children"].values():
                ct, cs = _cum(c)
                total += ct
                any_star = any_star or cs
            n["cum_pdfs"] = total
            n["cum_starred"] = 1 if any_star else 0
            return total, any_star
        _cum(tree_root)

        # ---- SVGs inline para os icones (definidos uma vez) --------------
        SVG_FOLDER = (
            '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" '
            'stroke="#94a3b8" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round" style="vertical-align:-2px;">'
            '<path d="M2 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2H4a2 2 0 0 1 -2-2z"/>'
            '<path d="M2 10h20"/></svg>')
        SVG_FOLDER_OPEN = (
            '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" '
            'stroke="#60a5fa" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round" style="vertical-align:-2px;">'
            '<path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.55 6a2 2 0 0 1-1.94 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.93a2 2 0 0 1 1.66.9l.82 1.2a2 2 0 0 0 1.66.9H18a2 2 0 0 1 2 2v2"/>'
            '</svg>')
        SVG_BOOK = (
            '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" '
            'stroke="#a5b4fc" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round" style="vertical-align:-2px;">'
            '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>'
            '<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>')

        # ---- Renderizacao recursiva da arvore ----------------------------
        expanded = st.session_state["expanded_nodes"]
        selected = st.session_state["selected_topic"]

        def render_node(node, level=0):
            """Renderiza um nivel da arvore (filhos do node passado)."""
            children = sorted(
                node["children"].values(),
                key=lambda c: (-(c["cum_starred"]),
                                c["name"].lower())
            )
            for child in children:
                is_open = child["path"] in expanded
                has_kids = bool(child["children"])

                # Linha estilo Windows Explorer com 3 colunas:
                # [chevron expand/collapse]  [nome com indent + emoji]  [estrela]
                # O nome usa emoji (📚 pasta, 📖 livro/tema) — para um icone
                # SVG real ao lado do botao, renderizamos um label markdown
                # antes do botao numa subcoluna pequena. Aqui mantemos
                # apenas emoji no label (Streamlit nao aceita HTML em
                # st.button label) — os SVG SVG_FOLDER/SVG_BOOK ficam para
                # o cabecalho da arvore.

                # 4 colunas: [chevron] [icone SVG] [nome] [estrela]
                # Os SVG_FOLDER/FOLDER_OPEN/BOOK definidos acima sao
                # renderizados via st.markdown na coluna 2 — visual
                # bem mais elegante que o emoji 📁 do Windows.
                c_chev, c_icon, c_main, c_star = st.columns(
                    [0.22, 0.22, 1.0, 0.18])

                with c_chev:
                    if has_kids:
                        if st.button("▾" if is_open else "▸",
                                       key=f"exp_{child['path']}",
                                       help="Expandir/colapsar"):
                            if is_open:
                                expanded.discard(child["path"])
                            else:
                                expanded.add(child["path"])
                            st.session_state["expanded_nodes"] = expanded
                            st.rerun()
                    else:
                        st.markdown(
                            '<div style="height:22px;">&nbsp;</div>',
                            unsafe_allow_html=True)

                with c_icon:
                    if has_kids:
                        svg_html = SVG_FOLDER_OPEN if is_open else SVG_FOLDER
                    else:
                        svg_html = SVG_BOOK
                    st.markdown(
                        f'<div style="display:flex; align-items:center; '
                        f'justify-content:center; height:22px; '
                        f'padding:0 2px;">{svg_html}</div>',
                        unsafe_allow_html=True)

                with c_main:
                    # Indent em espacos nao-quebraveis (visual de tree)
                    indent_str = "   " * level
                    # Icone — book aberto p/ tema folha, livros p/ pasta
                    icon_emoji = "📂" if (has_kids and is_open) else \
                                 "📁" if has_kids else "📖"
                    display_name = child["name"]
                    if len(display_name) > 30:
                        display_name = display_name[:28] + "..."
                    label = f"{indent_str}{display_name}"
                    if child["is_topic"]:
                        label += f"  · {child['n_pdfs']}"
                    elif child["cum_pdfs"]:
                        label += f"  ({child['cum_pdfs']})"

                    is_active = (child["is_topic"] and
                                  child["table_name"] == selected)
                    if is_active:
                        st.markdown('<div class="topic-active">',
                                    unsafe_allow_html=True)
                    if st.button(label, key=f"sel_{child['path']}",
                                   use_container_width=True):
                        if child["is_topic"]:
                            st.session_state["selected_topic"] = \
                                child["table_name"]
                            if has_kids and not is_open:
                                expanded.add(child["path"])
                            st.rerun()
                        elif has_kids:
                            # Pasta sem tabela: clique alterna expand
                            if is_open:
                                expanded.discard(child["path"])
                            else:
                                expanded.add(child["path"])
                            st.session_state["expanded_nodes"] = expanded
                            st.rerun()
                    if is_active:
                        st.markdown('</div>', unsafe_allow_html=True)

                with c_star:
                    if child["is_topic"]:
                        css_class = "star-on" if child["starred"] else "star-off"
                        st.markdown(f'<div class="{css_class}">',
                                    unsafe_allow_html=True)
                        star_char = "★" if child["starred"] else "☆"
                        if st.button(star_char, key=f"st_{child['path']}",
                                       help="Favoritar tema"):
                            toggle_favorite(child["table_name"])
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(
                            '<div style="height:22px;">&nbsp;</div>',
                            unsafe_allow_html=True)

                # Recursao se aberto e tem filhos
                if is_open and has_kids:
                    render_node(child, level + 1)

        # Renderiza arvore a partir do root
        render_node(tree_root, level=0)

        # Se a propria raiz tem PDFs (caso raro mas possivel)
        if tree_root["is_topic"]:
            st.markdown(
                f'<div style="border-top:1px solid #1e293b; '
                f'padding:6px 0; margin-top:6px; color:#cbd5e1; '
                f'font-size:0.78rem;">{SVG_BOOK} '
                f'(raiz · {tree_root["n_pdfs"]})</div>',
                unsafe_allow_html=True)
            cr1, cr2 = st.columns([5, 1])
            with cr1:
                if st.button(f"📖 (raiz · {tree_root['n_pdfs']})",
                              key="sel_root", use_container_width=True):
                    st.session_state["selected_topic"] = tree_root["table_name"]
                    st.rerun()
            with cr2:
                star = "★" if tree_root["starred"] else "☆"
                if st.button(star, key="st_root"):
                    toggle_favorite(tree_root["table_name"])
                    st.rerun()

# ============================================================================
# MAIN
# ============================================================================

p = get_db_path()
if not p.exists():
    st.markdown('<h1 class="lilo-header">Biblioteca cientifica</h1>',
                unsafe_allow_html=True)
    st.warning(
        f"Banco nao encontrado em `{p}`. Clique em **🔄 Atualizar** "
        f"na sidebar para varrer `{_TARGET_ROOT}`.")
    st.stop()

topics = list_topics(db_mtime(), _TARGET_ROOT)
if not topics:
    st.markdown('<h1 class="lilo-header">Biblioteca cientifica</h1>',
                unsafe_allow_html=True)
    st.info(f"Nenhum tema indexado em `{_TARGET_ROOT}`. "
            "Clique em **🔄 Atualizar**.")
    st.stop()

selected = st.session_state.get("selected_topic", topics[0]["table_name"])
sel_topic = next((t for t in topics if t["table_name"] == selected),
                  topics[0])

# Header
st.markdown(
    f'<h1 class="lilo-header">Biblioteca · {_esc(sel_topic["table_name"])}</h1>',
    unsafe_allow_html=True)
st.markdown(
    f'<div class="lilo-subhead">📂 <code>{_esc(sel_topic["dir_path"])}</code> · '
    f'{sel_topic["n_pdfs"]} arquivo(s) · '
    f'ult. varredura: '
    f'{_esc(sel_topic["last_scan"][:19] if sel_topic["last_scan"] else "-")}'
    f'</div>',
    unsafe_allow_html=True)

papers = query_papers(sel_topic["table_name"], search=search_q or "",
                       limit=300, _db_mtime=db_mtime())
if not papers:
    st.info("Nenhum artigo neste tema (ou nenhum bate com a busca).")
    st.stop()

# Separa indexados (DOI/ISSN) de simples
indexed = [p for p in papers if p.get("indexed_journal")]
simple = [p for p in papers if not p.get("indexed_journal")]

if indexed:
    st.markdown(f"### Artigos indexados ({len(indexed)})")
    for p in indexed:
        render_indexed_paper(p)

if simple:
    with st.expander(f"📄 Documentos nao indexados ({len(simple)})",
                       expanded=not indexed):
        for p in simple:
            render_simple_paper(p)
