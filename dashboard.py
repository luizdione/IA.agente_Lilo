"""
dashboard.py -- Dashboard LILO v9.1 (Streamlit)
=================================================
Interface web com:
- Sidebar esquerda: botoes 3D para sub-agentes e ferramentas
- Sidebar direita: historico de chats + projetos
- Botao Stop em todas as areas de input
- Slash commands (/) para skills
- Anexo de arquivos
- Busca web integrada

Uso:
    streamlit run dashboard.py --server.port 8100
"""

import streamlit as st
import sys
import json
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT))

from shared.utils import load_env, get_env
from shared.logger import get_logger
from shared.chat_memory import get_memory
from dashboard_styles import GLOBAL_CSS, HISTORICO_CSS, WELCOME_CSS

# V10.5 (2026-05-31): recursos estilo Claude Cowork (tarefas, memoria KV,
# conectores/capabilities, streaming). Import tolerante a falha p/ nao
# derrubar o dashboard caso o modulo nao esteja presente.
try:
    import dashboard_cowork as cowork
except Exception:  # pragma: no cover
    cowork = None

load_env()
# V19 (2026-07-23): no dashboard (sessão LONGA, modelo carrega 1x) o roteador por
# EMBEDDINGS (ML) é o default -> entrega "o orquestrador+ML decide o caminho" no
# Chat Auto. A CLI/MCP mantêm o keyword global (processo curto). A 1ª pergunta
# paga o cold-start do modelo (~7s, do cache). Reversível: LILO_ROUTER=keyword no .env.
import os as _os
_os.environ.setdefault("LILO_ROUTER", "embed")
log = get_logger("Dashboard")
memory = get_memory()

# Icone LILO no titulo da aba do navegador (favicon).
# Streamlit aceita path para .png/.ico/.jpg ou emoji.
_ICON_PATH = _ROOT / "lilo_icon.ico"
st.set_page_config(
    page_title="LILO -- Dashboard",
    page_icon=str(_ICON_PATH) if _ICON_PATH.exists() else "🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -- Estado da sessao --------------------------------------------------------
defaults = {
    "messages": [],
    "page": "Chat",
    "current_chat_id": None,
    "running": False,
    "stop_requested": False,
    "attached_files": [],
    "current_project": None,
    "skill_filter": "",
    "show_right_panel": True,
    # Task 2 — sintese de diretorio
    "attached_dir": "",
    "last_synthesis_md": "",
    "last_synthesis_html": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# -- Carregar agentes --------------------------------------------------------
@st.cache_resource
def load_agents():
    agents = {}
    errors = {}
    for name, mod_path, cls_name in [
        ("sql", "agents.Analise_SQL.agent", "SQLAgent"),
        ("pdf", "agents.PDFs_library.agent", "PDFAgent"),
        ("scholar", "agents.scholaragent.agent", "ScholarAgent"),
        ("prism", "agents.prism_ai", "PrismAgent"),
        ("gateway", "agents.gateway", "GatewayAgent"),
        ("desktop", "agents.desktop.agent", "DesktopAgent"),
    ]:
        try:
            mod = __import__(mod_path, fromlist=[cls_name])
            agents[name] = getattr(mod, cls_name)()
        except Exception as e:
            errors[name] = str(e)
    # Villa Lobos
    try:
        from agents.villa_lobos import VillaLobosAgent
        agents["villa"] = VillaLobosAgent()
    except Exception as e:
        errors["villa"] = str(e)
    return agents, errors


def check_ollama():
    try:
        r = requests.get(
            get_env("OLLAMA_HOST", "http://localhost:11434") + "/api/tags",
            timeout=3)
        if r.status_code == 200:
            return True, [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass
    return False, []


def check_ollama_gpu():
    try:
        r = requests.get(
            get_env("OLLAMA_HOST", "http://localhost:11434") + "/api/ps",
            timeout=3)
        if r.status_code == 200:
            return r.json().get("models", [])
    except Exception:
        pass
    return []


def check_nvidia_smi():
    """Detecta GPU NVIDIA e retorna info do driver. None se nao encontrar nvidia-smi."""
    import subprocess
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            line = r.stdout.strip().splitlines()[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 5:
                return {
                    "name": parts[0],
                    "driver": parts[1],
                    "vram_total_mb": int(parts[2]),
                    "vram_used_mb": int(parts[3]),
                    "util_pct": int(parts[4]),
                }
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    return None


def warm_up_gpu(model_name=None):
    """Forca Ollama a carregar um modelo na VRAM com keep_alive longo.
    Retorna (ok, mensagem)."""
    try:
        if not model_name:
            from shared.models import DEFAULT_MODEL
            model_name = get_env("OLLAMA_MODEL", DEFAULT_MODEL)
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": "ok"}],
            "stream": False,
            "keep_alive": "2h",  # mantem 2h em VRAM
            "options": {"num_predict": 1, "num_gpu": 99},
        }
        r = requests.post(
            get_env("OLLAMA_HOST", "http://localhost:11434") + "/api/chat",
            json=payload, timeout=120)
        if r.status_code == 200:
            return True, f"Modelo {model_name} aquecido (keep_alive=2h)."
        return False, f"Erro {r.status_code}: {r.text[:120]}"
    except Exception as e:
        return False, str(e)


@st.cache_data(ttl=60)
def load_skills_list():
    """Carrega lista de skills do registry + 16 skills CORE injetadas no topo
    (lilo_chat, lilo_sql, prism_*, villa_*, lilo_web_*, etc).
    Garante que o menu / do chat sempre mostre os comandos core do LILO."""
    try:
        from lilo_skills import get_full_registry
        return get_full_registry()
    except Exception:
        # Fallback: registry puro (apenas as 199 geradas, sem as core)
        registry_path = _ROOT / "lilo_skills" / "registry.json"
        if registry_path.exists():
            with open(registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"skills": [], "total_skills": 0}


def run_with_stop(func, *args):
    """Executa funcao com suporte a stop."""
    st.session_state.running = True
    st.session_state.stop_requested = False
    try:
        result = func(*args)
    except Exception as e:
        result = "Erro: " + str(e)
    finally:
        st.session_state.running = False
    return result



# -- CSS layout v10.10 — tema "Claude Desktop" (marfim quente + coral) -------
# Paleta inspirada no Claude Desktop: fundo marfim, sidebar creme com navegacao
# ghost, acento coral (#D97757), headings serifados, chat em bolhas suaves e
# composer arredondado com sombra.
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def nav_button(label, key, category="agent"):
    # Estado ativo via seletor .st-key-<key> (Streamlit >= 1.39). Os antigos
    # wrappers <div> em st.markdown NAO envolvem o botao no DOM renderizado,
    # entao o destaque nunca era aplicado de fato.
    if st.session_state.page == label:
        # Especificidade (0,2,3) — precisa vencer o ghost-style da sidebar
        # 'section[data-testid="stSidebar"] .stButton > button' (0,2,2).
        st.markdown(
            f'<style>section[data-testid="stSidebar"] '
            f'div[class*="st-key-{key}"] button {{'
            f'background: var(--lilo-accent-soft, #F5E8E1) !important;'
            f'color: var(--lilo-accent-dark, #C96442) !important;'
            f'font-weight: 600 !important; }}</style>',
            unsafe_allow_html=True)
    if st.button(label, key=key, use_container_width=True):
        st.session_state.page = label
        st.rerun()


def stop_button(key="stop_main"):
    """Botao de parar execucao (vermelho via .st-key, ver nav_button)."""
    st.markdown(
        f'<style>.st-key-{key} button {{'
        f'background: #C0392B !important; border-color: #C0392B !important;'
        f'color: #fff !important; animation: pulse 1.5s infinite; }}</style>',
        unsafe_allow_html=True)
    if st.button("PARAR", key=key, use_container_width=True):
        st.session_state.stop_requested = True
        st.session_state.running = False
        st.warning("Execucao interrompida pelo usuario.")


# -- Sidebar esquerda --------------------------------------------------------
with st.sidebar:
    # Logo LILO no topo (icone do projeto). Fallback p/ titulo se nao encontrar.
    if _ICON_PATH.exists():
        st.markdown('<div class="lilo-logo-wrap">', unsafe_allow_html=True)
        st.image(str(_ICON_PATH), width=64)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="lilo-title">LILO</div>', unsafe_allow_html=True)

    agents, agent_errors = load_agents()
    ollama_ok, ollama_models = check_ollama()

    n_agents = len(agents)
    status_icon = "ON" if ollama_ok else "OFF"
    st.caption(status_icon + " Ollama | " + str(n_agents) + " agentes (Auto decide)")

    st.markdown("---")
    # V19 (UI plan-first): a PORTA PRINCIPAL e o Chat (Auto) -- o LILO decide o
    # especialista pela semantica (roteador ML). As 9 abas de especialista deixam
    # de ser escolhas paralelas na cara do usuario e viram override/observabilidade
    # num expander, agrupadas por categoria (prenuncia a consolidacao 10->6).
    st.markdown("**CONVERSAR**")
    nav_button("Chat", "nav_chat", "agent")
    st.caption("No Chat (Auto) o LILO escolhe o especialista sozinho. Os "
               "especialistas abaixo sao so para forcar/inspecionar.")

    _spec_groups = [
        ("Dados & Estatistica", [("SQL", "nav_sql"), ("Prism AI", "nav_prism")]),
        ("Literatura", [("PDFs", "nav_pdf"), ("Scholar", "nav_scholar"),
                        ("Biblioteca", "nav_biblioteca")]),
        ("Execucao & Sistema", [("Desktop", "nav_desktop")]),
        ("Orquestracao", [("Villa Lobos", "nav_villa")]),
        ("Visual", [("SciStudio", "nav_scistudio")]),
    ]
    _spec_labels = {lbl for _g, _items in _spec_groups for lbl, _k in _items}
    with st.expander("Especialistas (override manual)",
                     expanded=st.session_state.page in _spec_labels):
        for _gname, _items in _spec_groups:
            st.caption(_gname)
            for _lbl, _key in _items:
                nav_button(_lbl, _key, "agent")

    st.markdown("---")
    st.markdown("**COWORK**")
    nav_button("Tarefas", "nav_tarefas", "tool")
    nav_button("Memoria", "nav_memoria", "tool")
    nav_button("Conectores", "nav_conectores", "tool")

    st.markdown("---")
    st.markdown("**FERRAMENTAS**")
    nav_button("Skills", "nav_skills", "tool")
    nav_button("Custos", "nav_custos", "tool")
    nav_button("Saude", "nav_health", "tool")

    st.markdown("---")
    st.markdown("**DOCUMENTOS**")
    nav_button("Glossario", "nav_glossario", "help")
    nav_button("Ajuda", "nav_help", "help")

    st.markdown("---")
    # V12 (2026-06-11): "Auto" e o default -- o roteador semantico do Villa
    # escolhe o subagente pela semantica da pergunta. Os demais sao OVERRIDE
    # manual (forcam um modo/agente especifico).
    mode = st.selectbox(
        "Modo IA",
        ["Auto", "chat", "code", "bioinfo", "sql"],
        index=0,
        help="Auto: o LILO decide o melhor subagente pela semantica da "
             "pergunta. chat/code/bioinfo forcam o modo do gateway; sql forca "
             "o agente SQL.")

    # V15 FASE 2: ESTILO de resposta -- eixo ORTOGONAL ao "Modo IA" (roteamento)
    # e ao "Modo de execucao" (gating). So muda a APRESENTACAO; nao degrada
    # codigo/tabelas/artefatos. Persiste em st.session_state.
    _STYLE_LABELS = {"Padrao": "default", "Conciso": "concise",
                     "Didatico": "explanatory", "Formal": "formal"}
    _style_label = st.selectbox(
        "Estilo de resposta",
        list(_STYLE_LABELS.keys()), index=0,
        help="Apresentacao da resposta (NAO muda o subagente nem o gating): "
             "Conciso = minimo de tokens; Didatico = passo-a-passo; Formal = "
             "polido. Nao afeta qualidade de codigo/tabelas/artefatos. No modo "
             "Conciso, pedir 'detalhe/aprofunde' suspende a concisao no turno.")
    st.session_state["response_style"] = _STYLE_LABELS[_style_label]

    # V14.2: biometria de voz -- cadastrar a voz do dono (enrollment).
    try:
        from shared import speaker_id as _sid
        if _sid.is_available():
            _n = _sid.n_samples()
            _reenroll = _sid.needs_reenroll()
            if _reenroll:
                _vlabel = "regravar — versão endurecida"
            elif _sid.is_enrolled():
                _vlabel = "ativa, %d amostras" % _n
            else:
                _vlabel = "%d/3 amostras" % _n
            with st.expander("🔊 Minha voz (%s)" % _vlabel):
                if _reenroll:
                    st.warning("🔄 Seu voiceprint foi criado numa versão anterior "
                               "(menos discriminativa) e foi **descartado** pelo "
                               "endurecimento V14.6. Regrave 3+ amostras para "
                               "reativar o reconhecimento.")
                st.caption("Grave 3+ amostras curtas (frase de ~5s) para o LILO "
                           "reconhecer sua voz e liberar comandos do dono.")
                _en = st.audio_input("Gravar amostra", key="enroll_mic",
                                     label_visibility="collapsed")
                if _en is not None:
                    _eb = _en.getvalue()
                    _esig = "%d:%s" % (len(_eb), hash(_eb[:2048]))
                    if st.session_state.get("_enroll_sig") != _esig:
                        st.session_state["_enroll_sig"] = _esig
                        _r = _sid.enroll(_eb)
                        if _r["ok"]:
                            st.success("Amostra %d adicionada." % _r["n_samples"])
                        else:
                            st.warning("Amostra inválida: %s" % _r.get("error", ""))
                if _sid.is_enrolled() and st.button("Limpar voiceprint",
                                                    key="voice_reset"):
                    _sid.reset()
                    st.session_state.pop("voice_owner", None)
                    st.rerun()
    except Exception as _enr_e:
        log.debug("enrollment de voz indisponivel: %s", _enr_e)

    st.caption("LILO v10.6 -- roteamento Auto -- " + datetime.now().strftime("%H:%M"))


# -- Pagina ativa -------------------------------------------------------------
page = st.session_state.page
agent_labels = {
    "sql": "SQL", "pdf": "PDFs", "scholar": "Scholar",
    "gateway": "Gateway", "prism": "Prism AI", "villa": "Villa Lobos",
    "desktop": "Desktop"}


# -- Layout principal: conteudo + sidebar direita ----------------------------
# Abas Ajuda e Glossario usam toda a largura (sem painel direito)
if page in ("Ajuda", "Glossario"):
    main_col = st.container()
    right_col = None
else:
    main_col, right_col = st.columns([4, 1], gap="medium")

if right_col is not None:
  with right_col:
    # 2026-05-08: sidebar direita simplificada (estilo Claude Desktop).
    # - "Projetos" foi movida para a aba Villa Lobos (area central).
    # - "Anexos" foi convertida em popover (+) na caixa de mensagem central.
    # Aqui ficam: Historico (lista flat) + Progresso (tasks com checkbox).

    # CSS minimalista para o historico em lista (sem botoes encaixotados)
    st.markdown(HISTORICO_CSS, unsafe_allow_html=True)

    st.markdown("### Historico")

    # Busca em chats
    search_q = st.text_input("Buscar chats", key="chat_search",
                              placeholder="Filtrar por conteudo...",
                              label_visibility="collapsed")

    # Atalho '+ Novo chat' (link discreto, no topo da lista)
    if st.button("+ Novo chat", key="new_chat_btn",
                 use_container_width=True):
        chat_id = memory.new_chat(subagent=page.lower())
        st.session_state.current_chat_id = chat_id
        st.session_state.messages = []
        st.rerun()

    # Lista de chats (filtrada pelo projeto ativo, se houver)
    if search_q:
        chats = memory.search_chats(search_q, limit=30)
    else:
        proj = st.session_state.current_project
        chats = memory.list_chats(project_id=proj, limit=30)

    # Render lista flat estilo Claude Desktop. Cada item e um link
    # `?lilo_chat=<id>` capturado pelo dashboard via query params.
    qp = st.query_params if hasattr(st, "query_params") else {}
    requested = qp.get("lilo_chat", None)
    if isinstance(requested, list):
        requested = requested[0] if requested else None
    if requested and requested != st.session_state.current_chat_id:
        st.session_state.current_chat_id = requested
        msgs = memory.get_messages(requested)
        st.session_state.messages = [
            {"role": m["role"], "content": m["content"]} for m in msgs]
        # limpa query param para nao rerender em loop
        try:
            del st.query_params["lilo_chat"]
        except Exception:
            pass
        st.rerun()

    if chats:
        items_html = ['<div class="lilo-history-list">']
        for ch in chats:
            is_active = ch["id"] == st.session_state.current_chat_id
            cls = "lilo-history-item active" if is_active else "lilo-history-item"
            title_safe = (ch["title"] or "(sem titulo)").replace("<", "&lt;").replace(">", "&gt;")[:48]
            items_html.append(
                f'<a class="{cls}" href="?lilo_chat={ch["id"]}" target="_self">'
                f'<span class="dot">·</span>{title_safe}</a>'
            )
        items_html.append("</div>")
        st.markdown("".join(items_html), unsafe_allow_html=True)
    else:
        st.caption("(sem conversas)")

    # Indicador discreto do projeto ativo + atalho para a aba Villa
    if st.session_state.current_project:
        st.markdown("---")
        try:
            _proj_obj = next(
                (p for p in memory.list_projects()
                 if p["id"] == st.session_state.current_project),
                None,
            )
            _proj_label = _proj_obj["name"][:28] if _proj_obj else (
                st.session_state.current_project[:8]
            )
        except Exception:
            _proj_label = st.session_state.current_project[:8]
        st.caption("Projeto: " + _proj_label)

        # ---- Progresso (tasks do projeto) ---------------------------------
        st.markdown("### Progresso")
        prog = memory.task_progress(st.session_state.current_project)
        if prog["total"]:
            st.markdown(
                f'<div class="lilo-progress-bar"><div style="width:{prog["pct"]}%"></div></div>'
                f'<div style="font-size:0.78rem;opacity:0.7;margin:-4px 0 6px 0">'
                f'{prog["done"]}/{prog["total"]} concluidas ({prog["pct"]}%)</div>',
                unsafe_allow_html=True,
            )
        tasks = memory.list_tasks(st.session_state.current_project)
        for t in tasks:
            tk_id = t["id"]
            checked = bool(t["done"])
            new_val = st.checkbox(
                t["title"][:60],
                value=checked,
                key=f"task_chk_{tk_id}",
            )
            if new_val != checked:
                memory.set_task_done(tk_id, new_val)
                st.rerun()
        # Adicionar nova task
        new_task = st.text_input(
            "Nova task",
            key="new_task_input",
            placeholder="+ adicionar task...",
            label_visibility="collapsed",
        )
        if new_task and st.session_state.get("new_task_last", "") != new_task:
            memory.add_task(st.session_state.current_project, new_task)
            st.session_state.new_task_last = new_task
            st.rerun()


# ============================================================================
# Helpers reutilizados pela area central
# ============================================================================

def _render_attachments_popover(key_prefix: str) -> None:
    """Renderiza um botao (+) acima da caixa de mensagem para anexar arquivos
    ou referenciar um diretorio. Substitui a antiga aba 'Anexos' da sidebar.

    Args:
        key_prefix: prefixo unico para as keys do widget Streamlit (evita
                    colisao quando varias paginas usam o popover na mesma sessao).
    """
    # Se houver popover (Streamlit >=1.32) usa, senao cai em expander.
    _container = (
        st.popover("+ Anexar arquivo ou pasta", use_container_width=False)
        if hasattr(st, "popover")
        else st.expander("+ Anexar arquivo ou pasta", expanded=False)
    )
    with _container:
        attach_mode = st.radio(
            "Tipo",
            ["Arquivos", "Diretorio"],
            horizontal=True,
            key=f"{key_prefix}_attach_mode",
        )

        if attach_mode == "Arquivos":
            uploaded = st.file_uploader(
                "Selecione um ou mais arquivos",
                type=["pdf", "csv", "xlsx", "txt", "py", "json", "tsv", "md"],
                key=f"{key_prefix}_file_attach",
                accept_multiple_files=True,
            )
            if uploaded:
                st.session_state.attached_files = uploaded
            if st.session_state.get("attached_files"):
                st.caption(
                    "Anexos ativos: " +
                    ", ".join(f.name for f in st.session_state.attached_files)
                )
                if st.button(
                    "Remover anexos",
                    key=f"{key_prefix}_clear_attach",
                    use_container_width=True,
                ):
                    st.session_state.attached_files = []
                    st.rerun()
        else:
            dir_path = st.text_input(
                "Caminho do diretorio",
                value=st.session_state.get("attached_dir", ""),
                placeholder=r"D:\OneDrive\meu_projeto",
                key=f"{key_prefix}_dir_path_input",
            )
            cb1, cb2 = st.columns(2)
            with cb1:
                if st.button("Procurar...", key=f"{key_prefix}_dir_browse",
                              use_container_width=True):
                    try:
                        import tkinter as tk
                        from tkinter import filedialog
                        root_tk = tk.Tk()
                        root_tk.withdraw()
                        root_tk.attributes("-topmost", True)
                        chosen = filedialog.askdirectory(title="Escolher diretorio")
                        root_tk.destroy()
                        if chosen:
                            st.session_state.attached_dir = chosen
                            st.rerun()
                    except Exception as e:
                        st.warning("Cole o caminho manualmente. (" + str(e) + ")")
            with cb2:
                if st.button("Sintetizar", key=f"{key_prefix}_dir_synth",
                              type="primary", use_container_width=True,
                              help="Gera .md com estrutura, etapas, TODOs"):
                    if not dir_path or not Path(dir_path).is_dir():
                        st.error("Caminho invalido ou nao e diretorio.")
                    else:
                        try:
                            from shared.dir_synthesis import (
                                synthesize_directory, synthesis_to_html)
                            with st.spinner("Sintetizando diretorio..."):
                                md_path = synthesize_directory(dir_path)
                                html_path = synthesis_to_html(md_path)
                            st.session_state.attached_dir = dir_path
                            st.session_state.last_synthesis_md = str(md_path)
                            st.session_state.last_synthesis_html = str(html_path)
                            if st.session_state.current_project:
                                link_line = (
                                    f"- Sintese de `{dir_path}` gerada em "
                                    f"{datetime.now().strftime('%Y-%m-%d %H:%M')} "
                                    f"-> `{md_path.name}`"
                                )
                                memory.append_to_section(
                                    st.session_state.current_project,
                                    "Decisoes e contexto",
                                    link_line)
                            st.success("Sintese gerada.")
                        except Exception as e:
                            st.error("Erro: " + str(e))

            if st.session_state.get("attached_dir"):
                st.caption("Diretorio: " + st.session_state.attached_dir)
            if st.session_state.get("last_synthesis_md"):
                md_p = Path(st.session_state["last_synthesis_md"])
                html_p = Path(st.session_state.get("last_synthesis_html", ""))
                if md_p.exists():
                    st.caption("Ultima sintese: " + md_p.name)
                    if html_p.exists() and st.button(
                        "Abrir em nova aba",
                        key=f"{key_prefix}_open_synth",
                        use_container_width=True,
                    ):
                        import webbrowser
                        webbrowser.open(html_p.as_uri(), new=2)


def _render_villa_project_explorer(base_path: str = ".") -> None:
    """Painel de Projetos + Explorador de arquivos (CRUD) embutido na aba
    Villa Lobos. Substitui a antiga seção 'Projetos' da sidebar direita.

    Funcionalidades:
      - Listar / criar / selecionar projeto LILO (memoria persistente).
      - Notas do projeto (notes.md auto-gerado).
      - Explorador do diretorio `base_path` com leitura, criacao, edicao
        e remocao de arquivos/pastas (delete sai com confirmacao dupla).

    Restricao de seguranca: o explorador respeita LILO_DESKTOP_ALLOW. Caminhos
    fora da allow-list resultam em erro retornado pelo agente Desktop.
    """
    st.markdown("#### Projetos")

    # ---- Projetos LILO -----------------------------------------------------
    cprj1, cprj2 = st.columns([2, 1])
    with cprj1:
        projects = memory.list_projects()
        proj_names = ["-- (sem projeto)"] + [p["name"] for p in projects]
        proj_ids   = [None]               + [p["id"]   for p in projects]
        try:
            cur_idx = proj_ids.index(st.session_state.current_project)
        except ValueError:
            cur_idx = 0
        sel = st.selectbox(
            "Projeto ativo",
            range(len(proj_names)),
            format_func=lambda i: proj_names[i],
            index=cur_idx,
            key="villa_proj_select",
        )
        if proj_ids[sel] != st.session_state.current_project:
            st.session_state.current_project = proj_ids[sel]
            st.rerun()
    with cprj2:
        new_proj = st.text_input("Novo projeto", key="villa_new_proj_name",
                                  placeholder="nome...")
        if st.button("Criar", key="villa_new_proj_btn",
                      use_container_width=True):
            name = (new_proj or "").strip() or (
                "Projeto " + datetime.now().strftime("%d/%m %H:%M"))
            pid = memory.new_project(name)
            st.session_state.current_project = pid
            st.rerun()

    if st.session_state.current_project:
        notes_path = memory.get_project_notes_path(
            st.session_state.current_project)
        if notes_path:
            with st.expander("Notas do projeto (notes.md)", expanded=False):
                from pathlib import Path as _P
                content = _P(notes_path).read_text(encoding="utf-8")
                st.code(content, language="markdown")
                st.download_button(
                    "Baixar notes.md",
                    data=content,
                    file_name="notes.md",
                    mime="text/markdown",
                    key="villa_dl_notes_" + st.session_state.current_project,
                )

    st.markdown("---")
    st.markdown("#### Explorador de arquivos")
    st.caption(
        "CRUD de arquivos e pastas no diretorio base do pipeline. "
        "Restrito a allow-list (LILO_DESKTOP_ALLOW)."
    )

    explorer_root = st.text_input(
        "Pasta a explorar",
        value=st.session_state.get("villa_explorer_root", base_path or "."),
        key="villa_explorer_root_input",
        help="Use caminho absoluto. Default: base_path do pipeline.",
    )
    st.session_state.villa_explorer_root = explorer_root

    try:
        from agents.desktop.agent import DesktopAgent
        _desktop = DesktopAgent()
    except Exception as e:
        st.error("DesktopAgent indisponivel: " + str(e))
        return

    # ---- Listar conteudo ---------------------------------------------------
    try:
        listing = _desktop.fs_list(explorer_root, glob="*", recursive=False,
                                     limit=500)
    except TypeError:
        # Fallback: assinatura antiga ou via run()
        listing = _desktop.run(
            "listar diretorio",
            {"action": "fs_list", "path": explorer_root,
             "glob": "*", "recursive": False},
        )
    with st.expander("Conteudo da pasta", expanded=True):
        st.code(listing or "(vazio)", language=None)

    # ---- Operacoes CRUD ----------------------------------------------------
    op_tabs = st.tabs(["Ler", "Escrever / Criar", "Renomear / Mover", "Remover"])

    with op_tabs[0]:  # ---- Ler ------------------------------------------------
        rd_path = st.text_input(
            "Caminho do arquivo a ler",
            key="villa_explorer_read_path",
            placeholder=str(Path(explorer_root) / "exemplo.py"),
        )
        if st.button("Ler arquivo", key="villa_explorer_read_btn",
                      use_container_width=True):
            try:
                content = _desktop.fs_read(rd_path)
                st.session_state.villa_explorer_last_read = content
                st.session_state.villa_explorer_last_read_path = rd_path
                st.success("Arquivo lido (" + str(len(content)) + " chars)")
            except Exception as e:
                st.error("Erro: " + str(e))
        if st.session_state.get("villa_explorer_last_read"):
            st.caption("Conteudo de " +
                       st.session_state.get("villa_explorer_last_read_path", ""))
            st.code(st.session_state["villa_explorer_last_read"][:5000],
                    language=None)

    with op_tabs[1]:  # ---- Escrever / Criar ----------------------------------
        wr_path = st.text_input(
            "Caminho do arquivo (sera criado se nao existir)",
            key="villa_explorer_write_path",
            placeholder=str(Path(explorer_root) / "novo.txt"),
        )
        wr_content = st.text_area(
            "Conteudo",
            key="villa_explorer_write_content",
            height=200,
            value=st.session_state.get("villa_explorer_last_read", "")
                  if st.session_state.get("villa_explorer_last_read_path") == wr_path
                  else "",
        )
        wr_append = st.checkbox(
            "Append (em vez de sobrescrever)",
            key="villa_explorer_write_append",
        )
        cwx, cmk = st.columns(2)
        with cwx:
            if st.button("Salvar arquivo", key="villa_explorer_write_btn",
                          type="primary", use_container_width=True):
                try:
                    res = _desktop.fs_write(wr_path, wr_content,
                                             append=wr_append)
                    st.success(res or "Arquivo salvo")
                except Exception as e:
                    st.error("Erro: " + str(e))
        with cmk:
            new_dir = st.text_input(
                "Nome de nova pasta (relativa ao root)",
                key="villa_explorer_mkdir_name",
                placeholder="subpasta",
                label_visibility="collapsed",
            )
            if st.button("Criar pasta", key="villa_explorer_mkdir_btn",
                          use_container_width=True):
                try:
                    target = Path(explorer_root) / (new_dir or "").strip()
                    if not (new_dir or "").strip():
                        st.warning("Informe o nome da pasta")
                    else:
                        # Cria pasta usando fs_write em arquivo placeholder
                        # ou diretamente via Path.mkdir se permitido.
                        target.mkdir(parents=True, exist_ok=True)
                        st.success("Pasta criada: " + str(target))
                        st.rerun()
                except Exception as e:
                    st.error("Erro: " + str(e))

    with op_tabs[2]:  # ---- Renomear / Mover ----------------------------------
        mv_src = st.text_input(
            "Origem", key="villa_explorer_mv_src",
            placeholder=str(Path(explorer_root) / "antigo.txt"),
        )
        mv_dst = st.text_input(
            "Destino", key="villa_explorer_mv_dst",
            placeholder=str(Path(explorer_root) / "novo.txt"),
        )
        if st.button("Mover / renomear", key="villa_explorer_mv_btn",
                      use_container_width=True):
            try:
                src_p = Path(mv_src)
                dst_p = Path(mv_dst)
                if not src_p.exists():
                    st.error("Origem nao existe.")
                else:
                    src_p.rename(dst_p)
                    st.success("Movido: " + str(src_p) + " -> " + str(dst_p))
                    st.rerun()
            except Exception as e:
                st.error("Erro: " + str(e))

    with op_tabs[3]:  # ---- Remover --------------------------------------------
        rm_path = st.text_input(
            "Caminho a remover",
            key="villa_explorer_rm_path",
            placeholder=str(Path(explorer_root) / "obsoleto.txt"),
        )
        confirm = st.checkbox(
            "Confirmo a remocao definitiva",
            key="villa_explorer_rm_confirm",
        )
        if st.button("Remover", key="villa_explorer_rm_btn",
                      use_container_width=True,
                      disabled=not confirm):
            import shutil
            try:
                p = Path(rm_path)
                if not p.exists():
                    st.error("Caminho nao existe.")
                elif p.is_dir():
                    shutil.rmtree(p)
                    st.success("Pasta removida: " + str(p))
                    st.rerun()
                else:
                    p.unlink()
                    st.success("Arquivo removido: " + str(p))
                    st.rerun()
            except Exception as e:
                st.error("Erro: " + str(e))


with main_col:

    # == CHAT =================================================================
    if page == "Chat":
        # V12: tela de boas-vindas (empty state) estilo Claude Desktop quando
        # ainda nao ha conversa -- saudacao serifada + capacidades atuais.
        if st.session_state.messages:
            st.header("Chat LILO")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        else:
            st.markdown(WELCOME_CSS, unsafe_allow_html=True)

        # ---- Modo de EXECUCAO (V14, estilo Claude) --------------------------
        # 4 modos que controlam quanta confirmacao o LILO pede antes de AGIR.
        # Ligados ao shared.exec_mode (gating no subagente desktop).
        from shared import exec_mode as _xm
        _MODE_LABELS = {
            "🧭 Planejamento (só planeja)": "plan",
            "🔐 Solicitar permissão": "ask",
            "✏️ Aceitar edições": "accept_edits",
            "⚡ Automático": "auto",
        }
        _labels = list(_MODE_LABELS)
        _cur = _xm.get_mode()
        _cur_label = next((l for l, m in _MODE_LABELS.items() if m == _cur),
                          _labels[3])
        _ec1, _ec2 = st.columns([2, 5])
        with _ec1:
            _sel_label = st.selectbox(
                "Modo de execução", _labels, index=_labels.index(_cur_label),
                label_visibility="collapsed",
                help="Planejamento: só planeja, não executa. Solicitar "
                     "permissão: confirma antes de rodar shell/python e de "
                     "escrever fora da allow-list. Aceitar edições: edita "
                     "arquivos sem pedir, confirma shell. Automático: executa tudo.")
        _exec_mode = _MODE_LABELS[_sel_label]
        _xm.set_mode(_exec_mode)
        # lilo_mode (compat): plan = nao age; demais = age.
        st.session_state.lilo_mode = "ask" if _exec_mode == "plan" else "act"
        with _ec2:
            st.caption({"plan": "Só planeja — nada é escrito/executado",
                        "ask": "Confirma cada ação de risco",
                        "accept_edits": "Edita arquivos direto; confirma shell",
                        "auto": "Executa tudo sem pedir"}[_exec_mode])

        # Anexos via popover (+) -- substitui sidebar 'Anexos'
        _render_attachments_popover("chat")

        # V14.1: microfone -- fala -> texto (faster-whisper local). O audio e
        # captado pelo navegador (st.audio_input), transcrito localmente e
        # injetado como prompt do chat (reusa o mecanismo _resend_text).
        try:
            from shared import transcribe as _tx
            if _tx.is_available():
                _mc1, _mc2 = st.columns([3, 5])
                with _mc1:
                    _audio = st.audio_input("🎤 Falar com o LILO",
                                            key="mic_input",
                                            label_visibility="collapsed")
                if _audio is not None:
                    _ab = _audio.getvalue()
                    _sig = "%d:%s" % (len(_ab), hash(_ab[:2048]))
                    if st.session_state.get("_last_audio_sig") != _sig:
                        st.session_state["_last_audio_sig"] = _sig
                        # V14.2: verifica o locutor (se ha voiceprint do dono).
                        try:
                            from shared import speaker_id as _sid
                            if _sid.is_available() and _sid.is_enrolled():
                                _v = _sid.verify(_ab)
                                st.session_state["voice_owner"] = _v["is_owner"]
                                with _mc2:
                                    st.caption(
                                        ("🔓 Voz reconhecida (dono) — score %.2f"
                                         % _v["score"]) if _v["is_owner"]
                                        else ("🔒 Voz não reconhecida (score %.2f "
                                              "< limiar %.2f)"
                                              % (_v["score"], _v.get("threshold", 0))))
                        except Exception as _se:
                            log.debug("speaker_id: %s", _se)
                        with st.spinner("Transcrevendo (local)..."):
                            _txt = _tx.transcribe(_ab)
                        if _txt:
                            st.session_state["_resend_text"] = _txt
                            st.rerun()
                        else:
                            with _mc2:
                                st.caption("Não entendi o áudio — tente de novo.")
        except Exception as _mic_e:
            log.debug("Microfone indisponivel: %s", _mic_e)

        # Input com slash commands
        _placeholder = (
            "Digite uma instrucao para o LILO executar... (/ para skills)"
            if st.session_state.lilo_mode == "act"
            else "Digite uma pergunta -- LILO nao tomara acoes (/ para skills)"
        )
        # V14: reenvio automatico apos o usuario CONFIRMAR uma acao de risco
        # (o grant one-shot ja foi concedido pelo botao "Confirmar e executar").
        _resend = st.session_state.pop("_resend_text", None)
        _typed = st.chat_input(_placeholder)
        prompt = _typed or _resend
        # V15: prompt NOVO (digitado) zera o plano acumulado; reenvio (pos
        # confirm/aprovacao) preserva o estado de aprovacao do plano.
        if _typed:
            try:
                from shared import exec_mode as _xpl
                _xpl.clear_plan()
            except Exception:
                pass

        if prompt:
            # Slash command: listar ou executar skill
            if prompt.startswith("/"):
                # Parsing v10.2.1: separa nome_skill de args (formato "/nome key=val")
                parts = prompt[1:].split()
                skill_name = parts[0] if parts else ""
                skill_args_raw = parts[1:]

                registry = load_skills_list()
                all_skills = registry.get("skills", [])
                # Match exato do nome (executar) tem prioridade sobre busca
                exact = next(
                    (s for s in all_skills if s["name"] == skill_name),
                    None,
                )

                # Caso 1: nome exato + tem argumentos -> executar com args
                # Caso 2: nome exato sem args -> executar com {} (tools com defaults)
                # Caso 3: nome parcial -> listar matches (autocomplete)
                if exact and (skill_args_raw or "=" not in prompt):
                    skill_args = {}
                    for p in skill_args_raw:
                        if "=" in p:
                            k, v = p.split("=", 1)
                            skill_args[k] = v
                    try:
                        from lilo_skills import call_skill
                        result = call_skill(skill_name, skill_args)
                        st.session_state.messages.append(
                            {"role": "user", "content": prompt})
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": "```\n" + str(result) + "\n```",
                        })
                    except Exception as e:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": "Erro skill: " + str(e),
                        })
                    st.rerun()
                else:
                    # Listar matches (autocomplete)
                    skill_query = skill_name.lower() if skill_name else ""
                    if skill_query:
                        matched = [
                            s for s in all_skills
                            if skill_query in s["name"].lower()
                            or any(skill_query in t for t in s.get("tags", []))
                        ]
                    else:
                        matched = all_skills[:30]

                    if matched:
                        lines = [
                            "**Skills disponiveis** (/" + skill_query + "):"]
                        for s in matched[:20]:
                            tags = ", ".join(s.get("tags", []))
                            lines.append(
                                "- `/" + s["name"] + "` ("
                                + s.get("source_package", "")
                                + ") [" + tags + "]"
                            )
                        lines.append("")
                        lines.append(
                            "Use `/<nome_skill>` (sem args) ou "
                            "`/<nome_skill> arg1=val1 arg2=val2` para executar."
                        )
                        skill_response = "\n".join(lines)
                        st.session_state.messages.append({
                            "role": "assistant", "content": skill_response,
                        })
                        st.rerun()
                    else:
                        st.info(
                            "Nenhuma skill encontrada para: " + skill_query)
            else:
                # Chat normal
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                # Garantir chat ativo
                if not st.session_state.current_chat_id:
                    st.session_state.current_chat_id = memory.new_chat(
                        title=prompt[:60], subagent="chat",
                        project_id=st.session_state.current_project)
                # V15 FASE 0: memoria de turno no chat do dashboard (paridade com
                # a API HTTP). Carrega o historico ANTES de gravar a msg atual,
                # senao o prompt do turno entraria duplicado (historico + query).
                _conv_hist = memory.get_chat_context(
                    st.session_state.current_chat_id, max_messages=12)
                memory.add_message(st.session_state.current_chat_id, "user", prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Pensando..."):
                        try:
                            from lilo import route
                            # Incluir contexto de arquivos anexados. O 'mode'
                            # do gateway so e setado no override (ver abaixo);
                            # em "Auto" o roteador semantico decide o subagente.
                            ctx = {}
                            # V15 FASE 0: memoria de turno (truncada p/ Ollama
                            # pequeno). route() prefixa os turnos anteriores.
                            if _conv_hist:
                                ctx["conversation_history"] = _conv_hist[-3000:]
                            # V15 FASE 2: estilo de resposta (apresentacao).
                            _rs = st.session_state.get("response_style", "default")
                            # ESCAPE: pedido explicito de detalhe suspende o
                            # conciso naquele turno (meta-regra do Concise Mode).
                            if _rs == "concise":
                                _pl = prompt.lower()
                                if any(k in _pl for k in (
                                        "detalh", "aprofund", "explique melhor",
                                        "mais longo", "completo", "passo a passo",
                                        "passo-a-passo")):
                                    _rs = "default"
                            if _rs and _rs != "default":
                                ctx["response_style"] = _rs
                            # V14: modo de EXECUCAO (plan/ask/accept_edits/auto).
                            # O gating fino (confirmar/bloquear acoes de risco) e
                            # feito por shared.exec_mode no subagente desktop; aqui
                            # so passamos o hint e desligamos tools no modo plan.
                            ctx["exec_mode"] = _exec_mode
                            ctx["intent"] = "ask" if _exec_mode == "plan" else "act"
                            ctx["allow_tools"] = (_exec_mode != "plan")
                            # V14.2: voz do dono reconhecida -> marca o contexto
                            # (carrega memorias do dono p/ otimizar as tarefas).
                            if st.session_state.get("voice_owner"):
                                ctx["owner_verified"] = True
                            ctx["system_hint"] = (
                                "Modo PLANEJAMENTO: apenas planeje/responda. Nao "
                                "execute, nao escreva arquivos. Descreva os passos."
                                if _exec_mode == "plan"
                                else "Voce pode executar a tarefa, usar tools/"
                                     "skills e escrever arquivos. Seja proativo."
                            )
                            if st.session_state.attached_files:
                                ctx["attached_files"] = [f.name for f in st.session_state.attached_files]
                            # Auto-consulta de notas do projeto: injeta o
                            # notes.md como contexto no inicio da conversa
                            # (Task 4 — auto-update + auto-consulta).
                            if st.session_state.current_project:
                                proj_ctx = memory.build_project_context(
                                    st.session_state.current_project,
                                    max_chars=3000)
                                if proj_ctx:
                                    ctx["project_notes"] = proj_ctx
                            # Sintese de diretorio anexado (Task 2)
                            if st.session_state.get("last_synthesis_md"):
                                synth_p = Path(st.session_state["last_synthesis_md"])
                                if synth_p.exists():
                                    synth_md = synth_p.read_text(encoding="utf-8")
                                    # truncamos para nao explodir o prompt
                                    ctx["dir_synthesis"] = synth_md[:4000]
                                    ctx["dir_synthesis_path"] = str(synth_p)
                            # V12: "Auto" -> roteamento semantico decide o
                            # subagente (tab=None). Override manual: "sql" forca
                            # o agente SQL; chat/code/bioinfo forcam o gateway no
                            # modo escolhido. (ctx['mode'] foi setado acima.)
                            if mode == "Auto":
                                _force_tab = None
                            elif mode == "sql":
                                _force_tab = "sql"
                            else:
                                _force_tab = "gateway"
                                ctx["mode"] = mode  # modo do gateway
                            response = route(prompt, context=ctx, tab=_force_tab)
                        except Exception as e:
                            response = "Erro: " + str(e)
                    # V14: trata pedido de confirmacao / bloqueio (modos de exec).
                    from shared import exec_mode as _xmd
                    _is_conf = _xmd.is_confirm(response)
                    _is_blk = _xmd.is_block(response)
                    if _is_conf:
                        response = ("🔐 **Confirmação necessária**\n\n"
                                    + response[len(_xmd.CONFIRM_PREFIX):])
                    elif _is_blk:
                        response = ("🧭 **Modo planejamento — nada foi executado**"
                                    "\n\n" + response[len(_xmd.BLOCK_PREFIX):])
                    # exibicao progressiva (estilo Cowork); direta em confirm/block.
                    if (cowork and st.session_state.get("stream_chat", True)
                            and not (_is_conf or _is_blk)):
                        try:
                            st.write_stream(cowork.stream_words(response))
                        except Exception:
                            st.markdown(response)
                    else:
                        st.markdown(response)
                    # V19 (plan-first): observabilidade do roteamento no Auto --
                    # mostra QUAL especialista o roteador ML escolheu, por que e o
                    # ranking de scores (fecha o ciclo "o orquestrador+ML decide").
                    if mode == "Auto" and not (_is_conf or _is_blk):
                        try:
                            from shared import router as _rt
                            _caps = {n: a.capabilities() for n, a in agents.items()}
                            _dec = _rt.route_query(prompt, _caps, available=set(agents))
                            with st.expander(
                                    "🧭 Como o LILO decidiu — roteador '%s'" % _dec.method,
                                    expanded=False):
                                st.caption(
                                    "Especialista: **%s**  ·  score %.2f  ·  %s"
                                    % (_dec.target, _dec.score, _dec.reason))
                                _ranked = sorted(_dec.scores.items(),
                                                 key=lambda kv: kv[1], reverse=True)[:6]
                                if _ranked:
                                    st.write("**Ranking (%s):**" % (
                                        "similaridade semântica" if _dec.method == "embed"
                                        else "match de keywords"))
                                    for _n, _s in _ranked:
                                        st.write("- `%s` — %.3f" % (_n, _s))
                        except Exception:
                            pass
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response})
                    memory.add_message(st.session_state.current_chat_id, "assistant", response)
                    if _is_conf:
                        # Botao confirma -> grant one-shot + reenvio do mesmo prompt.
                        if st.button("✅ Confirmar e executar", key="confirm_exec_btn"):
                            _xmd.grant_once()
                            st.session_state["_resend_text"] = prompt
                            st.rerun()
                    elif _is_blk:
                        # V15: PLANO APROVAVEL -- mostra as acoes acumuladas no
                        # modo plan e permite aprovar TUDO de uma vez (reenvia o
                        # mesmo prompt com o plano aprovado -> executa).
                        try:
                            _plan = _xmd.pending_plan()
                        except Exception:
                            _plan = []
                        if _plan:
                            st.caption("Plano (%d ação(ões) pendente(s)):" % len(_plan))
                            st.markdown("\n".join(
                                "%d. `%s` — %s" % (i + 1, p["kind"],
                                                   (p["preview"] or "")[:120])
                                for i, p in enumerate(_plan)))
                            if st.button("✅ Aprovar plano e executar",
                                         key="approve_plan_btn"):
                                _xmd.approve_plan()
                                st.session_state["_resend_text"] = prompt
                                st.rerun()
                    # Auto-update das notas do projeto apos cada turno
                    # (Task 4) — sem gastar tokens (resumo heuristico).
                    if st.session_state.current_project:
                        try:
                            memory.update_project_notes_after_chat(
                                project_id=st.session_state.current_project,
                                chat_id=st.session_state.current_chat_id,
                                tags=[mode] if mode else None,
                                status="ok",
                            )
                        except Exception as ne:
                            # Nunca quebrar o chat por falha em nota
                            st.caption(f"(aviso: nota nao atualizada: {ne})")

        # Botao stop (visivel durante execucao)
        if st.session_state.running:
            stop_button("stop_chat")


    # == SQL ==================================================================
    elif page == "SQL":
        st.header("Analise SQL")
        col1, col2 = st.columns([2, 1])
        with col2:
            db_files = list(_ROOT.rglob("*.db")) + list(_ROOT.rglob("*.sqlite"))
            db_names = [str(f.relative_to(_ROOT)) for f in db_files]
            selected_db = st.selectbox(
                "Banco de dados",
                db_names if db_names else ["Nenhum encontrado"])
            if selected_db and selected_db != "Nenhum encontrado":
                import sqlite3
                db_path = _ROOT / selected_db
                try:
                    conn = sqlite3.connect(str(db_path))
                    tables = pd.read_sql(
                        "SELECT name FROM sqlite_master WHERE type='table'", conn)
                    st.dataframe(tables, use_container_width=True)
                    if not tables.empty:
                        selected_table = st.selectbox("Tabela", tables["name"].tolist())
                        if selected_table:
                            schema = pd.read_sql(
                                "PRAGMA table_info(" + selected_table + ")", conn)
                            st.dataframe(
                                schema[["name", "type"]],
                                use_container_width=True)
                    conn.close()
                except Exception as e:
                    st.error("Erro: " + str(e))
        with col1:
            _render_attachments_popover("sql")
            query_input = st.text_area(
                "Query SQL ou pergunta (/ para skills)",
                height=100,
                placeholder="SELECT * FROM tabela LIMIT 10")
            c1, c2, c3 = st.columns(3)
            with c1:
                run_sql = st.button("Executar SQL", type="primary")
            with c2:
                ask_lilo = st.button("Perguntar ao LILO")
            with c3:
                if st.session_state.running:
                    stop_button("stop_sql")

            if run_sql and query_input:
                if selected_db and selected_db != "Nenhum encontrado":
                    try:
                        import sqlite3 as sql3
                        conn = sql3.connect(str(_ROOT / selected_db))
                        df = pd.read_sql(query_input, conn)
                        conn.close()
                        st.dataframe(df, use_container_width=True)
                        st.info(str(len(df)) + " registros")
                    except Exception as e:
                        st.error("Erro SQL: " + str(e))

            if ask_lilo and query_input:
                with st.spinner("Processando..."):
                    if "sql" in agents:
                        ctx = {}
                        if selected_db and selected_db != "Nenhum encontrado":
                            ctx["db_path"] = str(_ROOT / selected_db)
                        st.markdown(agents["sql"].run(query_input, ctx))
                    else:
                        st.error("SQLAgent indisponivel")


    # == PDFs =================================================================
    elif page == "PDFs":
        st.header("Biblioteca de PDFs")
        # Anexar PDFs via popover (+) -- substitui sidebar 'Anexos'
        _render_attachments_popover("pdfs")

        # --- Botoes de gestao da biblioteca (Task 5) ------------------------
        # Disparam o scanner offline e abrem a UI independente.
        _SCANNER_PATH = _ROOT / "agents" / "PDFs_library" / "scripts" / "build_workaholics_db.py"
        _LIBAPP_PATH = _ROOT / "agents" / "PDFs_library" / "scripts" / "library_app.py"
        # V11.2: path da biblioteca via env (portabilidade). O default
        # D:\... e a maquina do autor; outra maquina configura
        # LILO_WORKAHOLICS_ROOT no .env sem editar codigo.
        _WORKHOL_DEFAULT = get_env(
            "LILO_WORKAHOLICS_ROOT", r"D:\OneDrive\Documentos\Workaholics")

        bcol1, bcol2, bcol3, bcol4 = st.columns(4)
        with bcol1:
            if st.button("📁 Incluir pastas", use_container_width=True,
                          help="Adicionar diretorio e indexar PDFs"):
                st.session_state["_pdf_show_addfolder"] = True
        with bcol2:
            if st.button("📄 Incluir PDF", use_container_width=True,
                          help="Adicionar PDF avulso"):
                st.session_state["_pdf_show_addpdf"] = True
        with bcol3:
            if st.button("🔄 Atualizar diretorios",
                          use_container_width=True,
                          type="primary",
                          help="Re-indexa Workaholics em background"):
                try:
                    import subprocess
                    subprocess.Popen(
                        [sys.executable, str(_SCANNER_PATH),
                         "--root", _WORKHOL_DEFAULT],
                        creationflags=getattr(subprocess,
                                              "CREATE_NEW_CONSOLE", 0))
                    st.success("Scanner disparado em janela separada.")
                except Exception as e:
                    st.error("Erro: " + str(e))
        with bcol4:
            if st.button("🌐 Abrir biblioteca",
                          use_container_width=True,
                          help="Abre UI Streamlit independente em :8101"):
                try:
                    import subprocess
                    import webbrowser
                    # Inicia em janela separada (so se ainda nao estiver rodando)
                    subprocess.Popen(
                        [sys.executable, "-m", "streamlit", "run",
                         str(_LIBAPP_PATH), "--server.port", "8101",
                         "--server.headless", "true"],
                        creationflags=getattr(subprocess,
                                              "CREATE_NEW_CONSOLE", 0))
                    time.sleep(1.5)
                    webbrowser.open("http://localhost:8101", new=2)
                except Exception as e:
                    st.error("Erro: " + str(e))

        # Form: incluir pastas
        if st.session_state.get("_pdf_show_addfolder"):
            with st.expander("Incluir pasta", expanded=True):
                fp = st.text_input(
                    "Caminho da pasta",
                    placeholder=_WORKHOL_DEFAULT,
                    key="pdf_addfolder_path")
                if st.button("Indexar pasta", key="pdf_addfolder_run",
                              type="primary"):
                    if fp and Path(fp).is_dir():
                        try:
                            import subprocess
                            subprocess.Popen(
                                [sys.executable, str(_SCANNER_PATH),
                                 "--root", fp],
                                creationflags=getattr(subprocess,
                                                      "CREATE_NEW_CONSOLE", 0))
                            st.success(f"Indexando: {fp}")
                            st.session_state["_pdf_show_addfolder"] = False
                        except Exception as e:
                            st.error(str(e))
                    else:
                        st.error("Caminho invalido.")

        # Form: incluir PDF avulso
        if st.session_state.get("_pdf_show_addpdf"):
            with st.expander("Incluir PDF avulso", expanded=True):
                up_avulso = st.file_uploader(
                    "PDFs", type=["pdf"], accept_multiple_files=True,
                    key="pdf_avulso_uploader")
                dest = st.text_input(
                    "Pasta destino (sera indexada)",
                    value=str(_ROOT / "agents" / "PDFs_library" / "data"),
                    key="pdf_avulso_dest")
                if up_avulso and dest and st.button(
                        "Salvar e indexar", key="pdf_avulso_save",
                        type="primary"):
                    Path(dest).mkdir(parents=True, exist_ok=True)
                    for u in up_avulso:
                        with open(Path(dest) / u.name, "wb") as f:
                            f.write(u.getbuffer())
                    try:
                        import subprocess
                        subprocess.Popen(
                            [sys.executable, str(_SCANNER_PATH),
                             "--root", dest],
                            creationflags=getattr(subprocess,
                                                  "CREATE_NEW_CONSOLE", 0))
                        st.success(f"{len(up_avulso)} PDF(s) salvos e indexando.")
                        st.session_state["_pdf_show_addpdf"] = False
                    except Exception as e:
                        st.error(str(e))

        st.markdown("---")

        pdf_dir = Path(get_env("PDF_DIR", str(_ROOT / "agents" / "PDFs_library" / "data")))
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Arquivos")
            pdf_files = list(pdf_dir.rglob("*.pdf")) if pdf_dir.exists() else []
            pdf_files += list((_ROOT / "agents" / "PDFs_library").rglob("*.pdf"))
            pdf_files = list({str(f): f for f in pdf_files}.values())
            # Incluir anexos
            if st.session_state.attached_files:
                for af in st.session_state.attached_files:
                    if af.name.endswith(".pdf"):
                        save_path = pdf_dir / af.name
                        pdf_dir.mkdir(parents=True, exist_ok=True)
                        with open(save_path, "wb") as fout:
                            fout.write(af.getbuffer())
                        pdf_files.append(save_path)
            if pdf_files:
                pdf_names = [f.name for f in pdf_files]
                selected_pdf = st.selectbox("Selecione um PDF", pdf_names)
                selected_path = next(f for f in pdf_files if f.name == selected_pdf)
                st.caption("Caminho: " + str(selected_path))
            else:
                st.warning("Nenhum PDF encontrado")
                selected_pdf = None
                selected_path = None
            up_pdf = st.file_uploader("Upload PDF", type=["pdf"])
            if up_pdf:
                save_path = pdf_dir / up_pdf.name
                pdf_dir.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as fout:
                    fout.write(up_pdf.getbuffer())
                st.success("Salvo: " + str(save_path))
                st.rerun()
        with col2:
            if selected_path:
                analysis_mode = st.radio(
                    "Modo", ["simple", "introduction", "methods"],
                    horizontal=True)
                c1, c2 = st.columns([2, 1])
                with c1:
                    run_pdf = st.button("Analisar PDF", type="primary")
                with c2:
                    if st.session_state.running:
                        stop_button("stop_pdf")
                if run_pdf:
                    with st.spinner("Analisando " + selected_pdf + "..."):
                        if "pdf" in agents:
                            st.markdown(agents["pdf"].run(
                                "Analisar " + selected_pdf,
                                {"file_path": str(selected_path),
                                 "mode": analysis_mode}))
                        else:
                            st.error("PDFAgent indisponivel")


    # == Scholar ==============================================================
    elif page == "Scholar":
        st.header("Busca Academica")
        _render_attachments_popover("scholar")
        search_query = st.text_input(
            "Termos de busca",
            placeholder="Ex: CRISPR-Cas9 Trypanosoma cruzi drug targets")
        c1, c2, c3 = st.columns(3)
        with c1:
            _src_opts = (cowork.SCHOLAR_SOURCES if cowork
                         else ["auto", "pubmed", "arxiv"])
            source = st.selectbox(
                "Fonte", _src_opts,
                format_func=(lambda s: cowork.SOURCE_LABELS.get(s, s)) if cowork else str,
                help=("Fontes publicas (sem chave): PubMed, arXiv, "
                      "ClinicalTrials.gov, Open Targets, NPI, Crossref, "
                      "Semantic Scholar. 'all' agrega todas."))
        with c2:
            max_results = st.slider("Max resultados", 1, 20, 5)
        with c3:
            synthesize = st.checkbox("Sintetizar com LLM", value=True)
        bc1, bc2 = st.columns([2, 1])
        with bc1:
            run_scholar = st.button("Buscar", type="primary")
        with bc2:
            if st.session_state.running:
                stop_button("stop_scholar")
        if run_scholar and search_query:
            with st.spinner("Buscando artigos..."):
                if "scholar" in agents:
                    result = agents["scholar"].run(
                        search_query,
                        {"source": source, "max_results": max_results,
                         "synthesize": synthesize})
                    st.markdown(result)
                    # Salvar no historico
                    if not st.session_state.current_chat_id:
                        st.session_state.current_chat_id = memory.new_chat(
                            title="Scholar: " + search_query[:40], subagent="scholar")
                    memory.add_message(st.session_state.current_chat_id, "user", search_query)
                    memory.add_message(st.session_state.current_chat_id, "assistant", result)
                else:
                    st.error("ScholarAgent indisponivel")


    elif page == "Biblioteca":
        st.header("Biblioteca -- RAG local sobre seus PDFs")
        st.caption("Pergunta a biblioteca ja ingerida (ChromaDB local). Diferente "
                   "de Scholar (busca online): aqui a fonte sao seus proprios PDFs, "
                   "e a resposta passa pelo gate de verificacao factual.")
        _scholar_ask = None
        try:
            from shared.scholar_brain import (ask as _scholar_ask,
                                              library_count as _scholar_count)
            st.caption("Chunks indexados: %d" % _scholar_count())
        except Exception as _e:
            st.warning("ScholarAgent indisponivel: %s" % _e)
        _q = st.text_input(
            "Pergunta",
            placeholder="Ex: O que meus papers dizem sobre eQTL em Nelore?")
        _verify = st.checkbox("Verificar (gate factual)", value=True)
        if st.button("Perguntar", type="primary") and _q and _scholar_ask:
            with st.spinner("Consultando a biblioteca..."):
                _r = _scholar_ask(_q, verify=_verify)
            if _r.get("decision"):
                st.markdown("**Gate de verificacao:** %s" % _r["decision"].upper())
            st.markdown(_r.get("answer", ""))
            if _r.get("refs"):
                with st.expander("Referencias usadas"):
                    for _ref in _r["refs"]:
                        st.caption(_ref)


    # == Prism AI =============================================================
    elif page == "Prism AI":
        st.header("Prism AI -- Analise Cientifica")
        st.caption("Pipeline: deteccao > estatistica > graficos > texto > exportacao")
        _render_attachments_popover("prism")
        prism = agents.get("prism")
        if prism:
            up_data = st.file_uploader("Dados experimentais", type=["xlsx", "csv", "tsv"])
            c1, c2 = st.columns(2)
            with c1:
                lang = st.selectbox("Idioma do texto", ["en", "pt"])
            with c2:
                alpha = st.number_input(
                    "Significancia", value=0.05,
                    min_value=0.001, max_value=0.20,
                    step=0.01, format="%.3f")
            bc1, bc2 = st.columns([2, 1])
            with bc1:
                run_prism = st.button("Executar Pipeline", type="primary")
            with bc2:
                if st.session_state.running:
                    stop_button("stop_prism")
            if up_data and run_prism:
                import tempfile
                with tempfile.NamedTemporaryFile(
                        delete=False, suffix=Path(up_data.name).suffix) as tmp:
                    tmp.write(up_data.read())
                    tmp_path = tmp.name
                output_dir = str(Path(tmp_path).parent / "prism_output")
                with st.spinner("Pipeline Prism AI..."):
                    result = prism.run(
                        "analyze " + tmp_path,
                        context={"file_path": tmp_path,
                                 "output_dir": output_dir,
                                 "language": lang, "alpha": alpha,
                                 "enhance_with_llm": True})
                st.markdown(result)
                out_path = Path(output_dir)
                if out_path.exists():
                    for img in out_path.glob("*.png"):
                        st.image(str(img), caption=img.stem,
                                 use_container_width=True)
                    for pzfx in out_path.glob("*.pzfx"):
                        with open(pzfx, "r") as fh:
                            st.download_button(
                                "Baixar .pzfx", fh.read(),
                                file_name=pzfx.name, mime="application/xml")
            with st.expander("Status Prism AI"):
                health = prism.health()
                for pkg, status in health.get("dependencies", {}).items():
                    if status == "ok":
                        st.success(pkg)
                    else:
                        st.error(pkg + ": " + str(status))
        else:
            st.error("PrismAgent: " + agent_errors.get("prism", "?"))


    # == Villa Lobos ==========================================================
    elif page == "Villa Lobos":
        st.header("Villa Lobos -- Pipeline Multi-Estagio")
        st.caption("Orchestrator > Planner > Reader > Worker > Reporter")

        # 2026-05-08: a aba Villa agora hospeda o gerenciador de Projetos +
        # Explorador de arquivos (antes na sidebar direita). Selector simples
        # entre 'Pipeline' (default) e 'Projeto & Arquivos'.
        villa_view = st.radio(
            "Modo da aba Villa",
            ["Pipeline", "Projeto & Arquivos"],
            horizontal=True,
            label_visibility="collapsed",
            key="villa_view_mode",
        )

        if villa_view == "Projeto & Arquivos":
            _render_villa_project_explorer(
                base_path=st.session_state.get("villa_base_path", ".")
            )
            st.stop()

        # Anexos como popover (+) acima do input -- substitui a antiga
        # sidebar 'Anexos'.
        _render_attachments_popover("villa")

        task_input = st.text_area(
            "Tarefa para o pipeline (/ para skills)",
            height=100,
            placeholder="Descreva a tarefa...")
        c1, c2, c3 = st.columns(3)
        with c1:
            iterations = st.number_input(
                "Iteracoes do Worker",
                value=2, min_value=1, max_value=5,
                help=(
                    "Quantas vezes o Worker re-executa a tarefa, refinando o "
                    "resultado anterior. Default 2 = sweet spot para research-grade "
                    "(DM, sintese de literatura, analise estatistica profunda). "
                    "1 = resposta unica e rapida (~1-2 min). "
                    "2 = refinamento com auto-critica (~3-5 min). "
                    "3-5 = analise iterativa profunda (~5-15 min) — usar com cautela "
                    "na RTX 3060, pode saturar VRAM com modelos 14B."
                ),
            )
        with c2:
            use_reader = st.checkbox(
                "Usar Reader",
                value=True,
                help=(
                    "Ativa o estagio 3/5 do pipeline (Reader). O Reader le o plano "
                    "do Planner e identifica que arquivos/contexto sao necessarios "
                    "no diretorio Base path. Util quando: a tarefa precisa consultar "
                    "estrutura do projeto, analisar codigo existente, ou referenciar "
                    "PDFs locais. DESLIGUE quando: a tarefa e generica (ex: 'explique "
                    "tripanotione redutase') e nao depende de arquivos seus — economiza "
                    "~30 segundos por execucao."
                ),
            )
        with c3:
            base_path = st.text_input(
                "Base path",
                value=st.session_state.get("villa_base_path", "."),
                key="villa_base_path",
                help=(
                    "Diretorio raiz que o Reader vai inspecionar. Default '.' = raiz "
                    "do projeto LILO (C:\\Users\\luizd\\OneDrive\\Data_Science\\Projetos"
                    "\\IA.agente). Use caminho ABSOLUTO para apontar para outro projeto, "
                    "ex: D:\\OneDrive\\Documentos\\Workaholics\\Artigos PDF para "
                    "consultar artigos cientificos. Tambem usado pela aba "
                    "'Projeto & Arquivos' como root do explorador."
                ),
            )
        bc1, bc2 = st.columns([2, 1])
        with bc1:
            run_villa = st.button("Executar Pipeline", type="primary")
        with bc2:
            if st.session_state.running:
                stop_button("stop_villa")
        if run_villa and task_input:
            st.session_state.running = True
            try:
                # V10.5: progresso stage-a-stage (Cowork-like) quando disponivel.
                if cowork:
                    result = cowork.run_villa_with_progress(
                        st, task_input, iterations=iterations,
                        allow_delegate=True, use_reader=use_reader,
                        base_path=base_path)
                else:
                    from lilo import handle_tool_call
                    with st.spinner("Pipeline Villa Lobos em execucao..."):
                        result = handle_tool_call("villa_pipeline", {
                            "query": task_input,
                            "iterations": iterations,
                            "use_reader": use_reader,
                            "base_path": base_path})
                st.markdown(result)
                # Salvar no historico
                if not st.session_state.current_chat_id:
                    st.session_state.current_chat_id = memory.new_chat(
                        title="Villa: " + task_input[:40], subagent="villa")
                memory.add_message(st.session_state.current_chat_id, "user", task_input)
                memory.add_message(st.session_state.current_chat_id, "assistant", result)
            except Exception as e:
                st.error("Erro: " + str(e))
            finally:
                st.session_state.running = False

        # Quick Ask
        st.divider()
        st.subheader("Quick Ask")
        qa_input = st.text_input("Pergunta rapida a um agente (/ para skills)")
        qa_agent = st.selectbox(
            "Agente", ["worker", "planner", "reader", "orchestrator", "reporter"])
        bc1, bc2 = st.columns([2, 1])
        with bc1:
            run_qa = st.button("Perguntar")
        with bc2:
            if st.session_state.running:
                stop_button("stop_qa")
        if run_qa and qa_input:
            with st.spinner("Consultando..."):
                st.session_state.running = True
                try:
                    from lilo import handle_tool_call
                    result = handle_tool_call("villa_quick_ask", {
                        "query": qa_input, "agent": qa_agent})
                    st.markdown(result)
                except Exception as e:
                    st.error("Erro: " + str(e))
                finally:
                    st.session_state.running = False



        # ── Card 3D: LLMs default por estagio (rodape da pagina) ─────────────
        try:
            from agents.villa_lobos.agent import VILLA_MODELS as _VM
            _vm_orchestrator = _VM.get("orchestrator", "?")
            _vm_planner      = _VM.get("planner", "?")
            _vm_reader       = _VM.get("reader", "?")
            _vm_worker       = _VM.get("worker", "?")
            _vm_reporter     = _VM.get("reporter", "?")
        except Exception:
            from shared.models import MODELS as _M
            _vm_orchestrator = _vm_reporter = _M["chat"]
            _vm_planner      = _M["plan"]
            _vm_reader = _vm_worker = _M["code"]

        st.markdown(
            f"""
<style>
.villa-3d-card {{
    background: var(--lilo-bg-card, #FFFFFF);
    border-radius: 14px;
    padding: 18px 22px;
    margin: 14px 0 22px 0;
    color: var(--lilo-text, #3D3929);
    box-shadow: 0 2px 10px rgba(61,57,41,0.08);
    transition: box-shadow 0.2s ease;
    border: 1px solid var(--lilo-border, #E3E1D7);
}}
.villa-3d-card:hover {{
    box-shadow: 0 6px 18px rgba(61,57,41,0.12);
}}
.villa-3d-card .vc-title {{
    font-family: var(--lilo-serif, Georgia, serif);
    font-size: 1.05rem; font-weight: 600; letter-spacing: 0.2px;
    margin: 0 0 10px 0;
    border-bottom: 1px solid var(--lilo-border, #E3E1D7);
    padding-bottom: 6px;
}}
.villa-3d-card .vc-row {{
    display: flex; align-items: baseline;
    margin: 4px 0; font-size: 0.92rem; line-height: 1.45;
}}
.villa-3d-card .vc-stage {{
    min-width: 120px; font-weight: 600; color: var(--lilo-text-dim, #73705F);
    text-transform: uppercase; letter-spacing: 1px; font-size: 0.78rem;
}}
.villa-3d-card .vc-model {{
    font-family: 'Consolas','Courier New', monospace;
    background: var(--lilo-bg-soft, #F0EEE6); color: var(--lilo-accent-dark, #C96442);
    padding: 2px 8px; border-radius: 5px;
    font-size: 0.86rem;
}}
.villa-3d-card .vc-foot {{
    margin-top: 10px; font-size: 0.78rem;
    color: var(--lilo-text-dim, #73705F); font-style: italic;
}}
</style>
<div class="villa-3d-card">
  <div class="vc-title">LLMs default do pipeline (por estagio)</div>
  <div class="vc-row"><span class="vc-stage">Orchestrator</span> <span class="vc-model">{_vm_orchestrator}</span></div>
  <div class="vc-row"><span class="vc-stage">Planner</span> <span class="vc-model">{_vm_planner}</span></div>
  <div class="vc-row"><span class="vc-stage">Reader</span> <span class="vc-model">{_vm_reader}</span></div>
  <div class="vc-row"><span class="vc-stage">Worker</span> <span class="vc-model">{_vm_worker}</span></div>
  <div class="vc-row"><span class="vc-stage">Reporter</span> <span class="vc-model">{_vm_reporter}</span></div>
  <div class="vc-foot">Configuravel em agents/villa_lobos/agent.py (VILLA_MODELS) ou via .env (OLLAMA_MODEL_*).</div>
</div>
""",
            unsafe_allow_html=True,
        )

    # == Desktop =============================================================
    # Aba visual para os subagente Desktop (fs_*, run_shell, run_python).
    # Reusa lilo.handle_tool_call para nao duplicar a logica do agente.
    elif page == "Desktop":
        st.header("Desktop -- Filesystem & Shell")
        st.caption(
            "Formulario visual para fs_read/fs_write/fs_list/fs_search/"
            "run_shell/run_python. Restrito a allow-list "
            "(LILO_DESKTOP_ALLOW)."
        )

        # Mostra a allow-list atual para o usuario saber onde pode operar.
        try:
            from agents.desktop.agent import ALLOWLIST as _DESK_ALLOWLIST
            with st.expander("Allow-list ativa", expanded=False):
                for _p in _DESK_ALLOWLIST:
                    st.code(str(_p), language=None)
                st.caption(
                    "Configuravel em .env via LILO_DESKTOP_ALLOW "
                    "(separador ';' no Windows, ':' no Unix)."
                )
        except Exception as _eal:
            st.warning("Nao foi possivel carregar allow-list: " + str(_eal))

        from lilo import handle_tool_call as _desk_call

        _tab_read, _tab_write, _tab_list, _tab_search, _tab_shell, _tab_py = st.tabs([
            "fs_read", "fs_write", "fs_list", "fs_search",
            "run_shell", "run_python",
        ])

        # ---- fs_read ----
        with _tab_read:
            _path_r = st.text_input(
                "Caminho do arquivo",
                value=str(_ROOT / "README.md"),
                key="desk_read_path",
            )
            _maxb = st.number_input(
                "max_bytes", min_value=1024, max_value=2_000_000,
                value=200_000, step=10_000, key="desk_read_maxb",
            )
            if st.button("Ler arquivo", key="desk_read_btn", type="primary"):
                with st.spinner("Lendo..."):
                    try:
                        out = _desk_call("fs_read", {
                            "path": _path_r, "max_bytes": int(_maxb)})
                        st.code(out, language=None)
                    except Exception as e:
                        st.error("Erro: " + str(e))

        # ---- fs_write ----
        with _tab_write:
            _path_w = st.text_input(
                "Caminho de destino",
                value=str(_ROOT / "outputs" / "exemplo.txt"),
                key="desk_write_path",
            )
            _content = st.text_area(
                "Conteudo", height=200, key="desk_write_content",
                placeholder="texto a escrever...",
            )
            _append = st.checkbox(
                "Append (anexar em vez de sobrescrever)",
                value=False, key="desk_write_append",
            )
            if st.button("Escrever arquivo", key="desk_write_btn",
                         type="primary"):
                with st.spinner("Escrevendo..."):
                    try:
                        out = _desk_call("fs_write", {
                            "path": _path_w,
                            "content": _content,
                            "append": _append,
                        })
                        st.code(out, language=None)
                    except Exception as e:
                        st.error("Erro: " + str(e))

        # ---- fs_list ----
        with _tab_list:
            _path_l = st.text_input(
                "Diretorio", value=str(_ROOT), key="desk_list_path")
            _glob = st.text_input(
                "Glob pattern", value="*", key="desk_list_glob",
                help="Ex: *.py, **/*.md, data/*.csv")
            _rec = st.checkbox(
                "Recursivo", value=False, key="desk_list_rec")
            _lim = st.number_input(
                "Limite de itens", min_value=10, max_value=2000,
                value=200, step=50, key="desk_list_limit")
            if st.button("Listar diretorio", key="desk_list_btn",
                         type="primary"):
                with st.spinner("Listando..."):
                    try:
                        out = _desk_call("fs_list", {
                            "path": _path_l,
                            "glob": _glob,
                            "recursive": _rec,
                            "limit": int(_lim),
                        })
                        st.code(out, language=None)
                    except Exception as e:
                        st.error("Erro: " + str(e))

        # ---- fs_search ----
        with _tab_search:
            _root_s = st.text_input(
                "Raiz da busca", value=str(_ROOT), key="desk_search_root")
            _pat = st.text_input(
                "Padrao", value="", key="desk_search_pat",
                placeholder="texto literal ou regex")
            _re = st.checkbox("Regex", value=False, key="desk_search_re")
            _lim_s = st.number_input(
                "Limite de matches", min_value=10, max_value=500,
                value=50, step=10, key="desk_search_lim")
            if st.button("Buscar", key="desk_search_btn", type="primary"):
                if not _pat.strip():
                    st.warning("Informe o padrao a buscar.")
                else:
                    with st.spinner("Buscando..."):
                        try:
                            out = _desk_call("fs_search", {
                                "root": _root_s,
                                "pattern": _pat,
                                "regex": _re,
                                "limit": int(_lim_s),
                            })
                            st.code(out, language=None)
                        except Exception as e:
                            st.error("Erro: " + str(e))

        # ---- run_shell ----
        with _tab_shell:
            st.warning(
                "Comandos perigosos (rm -rf /, format, fork-bomb, "
                "shutdown...) sao bloqueados pelo agente.",
                icon=None,
            )
            _cmd = st.text_area(
                "Comando", value="", height=80, key="desk_shell_cmd",
                placeholder="ex: dir /b   ou   ls -la")
            _cwd = st.text_input(
                "cwd (opcional)", value="", key="desk_shell_cwd")
            _to = st.number_input(
                "timeout (s)", min_value=5, max_value=600,
                value=60, step=5, key="desk_shell_to")
            if st.button("Executar shell", key="desk_shell_btn",
                         type="primary"):
                if not _cmd.strip():
                    st.warning("Informe o comando.")
                else:
                    with st.spinner("Executando..."):
                        try:
                            args = {"cmd": _cmd, "timeout": int(_to)}
                            if _cwd.strip():
                                args["cwd"] = _cwd
                            out = _desk_call("run_shell", args)
                            st.code(out, language="bash")
                        except Exception as e:
                            st.error("Erro: " + str(e))

        # ---- run_python ----
        with _tab_py:
            st.caption(
                "Snippet Python executado em subprocess isolado. "
                "Use print() para ver saida."
            )
            _code = st.text_area(
                "Codigo Python", height=220, key="desk_py_code",
                value='print("ola, LILO Desktop!")')
            _to_py = st.number_input(
                "timeout (s)", min_value=5, max_value=600,
                value=60, step=5, key="desk_py_to")
            if st.button("Executar Python", key="desk_py_btn",
                         type="primary"):
                if not _code.strip():
                    st.warning("Informe o codigo.")
                else:
                    with st.spinner("Executando..."):
                        try:
                            out = _desk_call("run_python", {
                                "code": _code, "timeout": int(_to_py)})
                            st.code(out, language="python")
                        except Exception as e:
                            st.error("Erro: " + str(e))


    # == Skills ===============================================================
    elif page == "SciStudio":
        st.header("🎨 SciStudio — Produção de Divulgação Científica")
        st.caption("Figuras didáticas · **ilustração científica a partir de biblioteca SVG** "
                   "(bioicons + fontes CC-BY) · graphical abstracts · vídeos didáticos · pôster. "
                   "Container `scistudio` na porta 8505.")
        c1, c2 = st.columns([1, 3])
        with c1:
            st.link_button("↗ Abrir em nova aba", "http://localhost:8505",
                           use_container_width=True)
            try:
                import json as _json
                _cat = (_ROOT / "conteudo_digital" / "studio" / "static" / "icons"
                        / "_catalog" / "icons_catalog.json")
                if _cat.exists():
                    _d = _json.loads(_cat.read_text(encoding="utf-8"))
                    st.metric("Ícones SVG", _d.get("total", 0))
                    st.caption("Biblioteca por grupo:")
                    for _k, _v in list(_d.get("by_group", {}).items()):
                        st.caption(f"• {_k}: {_v}")
                else:
                    st.info("Catálogo SVG ausente — rode "
                            "`conteudo_digital/studio/tools/build_svg_library.py`.")
            except Exception as _e:
                log.debug("catalogo svg indisponivel: %s", _e)
        with c2:
            try:
                st.components.v1.iframe("http://localhost:8505/?embed=true",
                                        height=820, scrolling=True)
            except Exception:
                st.warning("Não foi possível embutir o SciStudio. Use o botão "
                           "'Abrir em nova aba'.")
        st.info("Se o quadro não carregar, suba o container: `docker compose up -d scistudio` "
                "na raiz do LILO (ou `docker compose up -d --build` para tudo).")

    elif page == "Tarefas":
        if cowork:
            cowork.render_tasks_page(st)
        else:
            st.error("Modulo dashboard_cowork indisponivel.")

    elif page == "Memoria":
        if cowork:
            cowork.render_memory_page(st)
        else:
            st.error("Modulo dashboard_cowork indisponivel.")

    elif page == "Conectores":
        if cowork:
            cowork.render_connectors_page(st)
        else:
            st.error("Modulo dashboard_cowork indisponivel.")

    elif page == "Skills":
        st.header("Skills Geradas")
        st.caption("Funcoes do Conda como tools MCP -- use / no chat para invocar")
        registry = load_skills_list()
        skills_dir = _ROOT / "lilo_skills"
        if registry.get("total_skills", 0) > 0:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total", registry.get("total_skills", 0))
            with c2:
                st.metric("Simples", registry.get("by_complexity", {}).get("simple", 0))
            with c3:
                st.metric("Media", registry.get("by_complexity", {}).get("medium", 0))
            all_skills = registry.get("skills", [])
            all_pkgs = sorted(set(s.get("source_package", "") for s in all_skills))
            all_tags = sorted(set(t for s in all_skills for t in s.get("tags", [])))
            fc1, fc2 = st.columns(2)
            with fc1:
                sel_pkg = st.selectbox("Pacote", ["Todos"] + all_pkgs)
            with fc2:
                sel_tag = st.selectbox("Tag", ["Todos"] + all_tags)
            filtered = all_skills
            if sel_pkg != "Todos":
                filtered = [s for s in filtered if s.get("source_package") == sel_pkg]
            if sel_tag != "Todos":
                filtered = [s for s in filtered if sel_tag in s.get("tags", [])]
            st.markdown("**" + str(len(filtered)) + " skills**")
            if filtered:
                df_sk = pd.DataFrame([{
                    "Slash Cmd": "/" + s["name"],
                    "Pacote": s.get("source_package", ""),
                    "Tags": ", ".join(s.get("tags", [])),
                    "Params": s.get("n_params", 0),
                } for s in filtered])
                st.dataframe(df_sk, use_container_width=True, hide_index=True)
            st.divider()
            st.subheader("Testar Skill")
            sel_skill = st.selectbox("Skill", [s["name"] for s in all_skills])
            if sel_skill:
                sp = skills_dir / "schemas" / (sel_skill + ".json")
                if sp.exists():
                    with open(sp) as fh:
                        schema = json.load(fh)
                    params = schema.get("parameters", {}).get("properties", {})
                    st.json(schema, expanded=False)
                    skill_args = {}
                    if params:
                        for pn, pd_ in params.items():
                            skill_args[pn] = st.text_input(
                                pn + " (" + pd_.get("type", "str") + ")",
                                value=str(pd_.get("default", "")),
                                key="skp_" + pn)
                    bc1, bc2 = st.columns([2, 1])
                    with bc1:
                        run_skill = st.button("Executar", type="primary")
                    with bc2:
                        if st.session_state.running:
                            stop_button("stop_skill")
                    if run_skill:
                        with st.spinner("Executando..."):
                            try:
                                from lilo_skills import call_skill
                                r = call_skill(sel_skill, skill_args if params else {})
                                st.code(r, language="json")
                            except Exception as e:
                                st.error("Erro: " + str(e))
            st.divider()
            st.code(
                "python lilo_skills/scan_conda_env.py\n"
                "python lilo_skills/generate_skills.py --validate",
                language="bash")
        else:
            st.warning("Nenhuma skill gerada. Execute scan_conda_env.py primeiro.")


    # == Custos ===============================================================
    elif page == "Custos":
        st.header("Monitoramento de Custos")
        try:
            from shared.cost_tracker import get_tracker
            tracker = get_tracker()
            summary = tracker.daily_summary()
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Requests", summary["total_requests"])
            with c2:
                st.metric("Custo", "$%.4f" % summary["total_cost_usd"])
            with c3:
                st.metric("Tokens IN", summary["total_tokens_in"])
            with c4:
                st.metric("Tokens OUT", summary["total_tokens_out"])
            st.divider()
            cb, cs = st.columns(2)
            with cb:
                st.subheader("Por Backend")
                if summary["by_backend"]:
                    st.dataframe(pd.DataFrame([
                        {"Backend": k, "Requests": v["count"],
                         "Custo": "$%.4f" % v["cost"]}
                        for k, v in summary["by_backend"].items()
                    ]), use_container_width=True, hide_index=True)
            with cs:
                st.subheader("Por Subagente")
                if summary["by_subagent"]:
                    st.dataframe(pd.DataFrame([
                        {"Subagente": k, "Requests": v["count"],
                         "Custo": "$%.4f" % v["cost"]}
                        for k, v in summary["by_subagent"].items()
                    ]), use_container_width=True, hide_index=True)
            st.divider()
            st.subheader("Recentes")
            recent = tracker.recent_requests(20)
            if recent:
                rdf = pd.DataFrame(recent)
                cols = [c for c in ["timestamp", "subagent", "tier",
                                    "model", "cost_usd", "duration_ms",
                                    "query_preview"] if c in rdf.columns]
                st.dataframe(rdf[cols], use_container_width=True, hide_index=True)
        except Exception as e:
            st.error("Erro: " + str(e))


    # == Saude ================================================================
    elif page == "Saude":
        st.header("Diagnostico LILO")
        if st.button("Health Check", type="primary"):
            with st.spinner("Verificando..."):
                ollama_ok, models = check_ollama()
                gpu_models = check_ollama_gpu()
                status_data = []
                status_data.append({
                    "Componente": "Ollama",
                    "Status": "Online" if ollama_ok else "Offline",
                    "Detalhes": str(len(models)) + " modelos" if ollama_ok else "Offline",
                })
                from shared.models import MODELS as _M
                expected = {
                    "chat": _M["chat"], "code": _M["code"],
                    "plan": _M["plan"], "fast": _M["autocomplete"],
                }
                for role, mn in expected.items():
                    ok = mn in models if ollama_ok else False
                    status_data.append({
                        "Componente": "Modelo (" + role + ")",
                        "Status": "Instalado" if ok else "Faltando",
                        "Detalhes": mn,
                    })
                # Detecta hardware NVIDIA primeiro
                nv = check_nvidia_smi()
                if nv:
                    status_data.append({
                        "Componente": "GPU (driver)",
                        "Status": "OK",
                        "Detalhes": f"{nv['name']} | driver {nv['driver']} | "
                                    f"VRAM {nv['vram_used_mb']}/{nv['vram_total_mb']} MB | "
                                    f"util {nv['util_pct']}%",
                    })
                else:
                    status_data.append({
                        "Componente": "GPU (driver)", "Status": "Nao detectado",
                        "Detalhes": "nvidia-smi nao encontrado. Instale driver NVIDIA + CUDA."})

                # Modelos atualmente em VRAM (Ollama)
                if gpu_models:
                    for gm in gpu_models:
                        vram = gm.get("size_vram", 0) / 1e9
                        status_data.append({
                            "Componente": "Ollama VRAM",
                            "Status": "Ativo",
                            "Detalhes": gm.get("name", "?") + " - %.1f GB carregado" % vram,
                        })
                else:
                    note = ("Nenhum modelo carregado AGORA. Normal apos 5 min de "
                            "ociosidade (OLLAMA_KEEP_ALIVE). Use 'Aquecer GPU' "
                            "abaixo ou rode uma query.")
                    status_data.append({
                        "Componente": "Ollama VRAM",
                        "Status": "Idle",
                        "Detalhes": note})

                for key, label in agent_labels.items():
                    status_data.append({
                        "Componente": "Agent: " + label,
                        "Status": "OK" if key in agents else "Erro",
                        "Detalhes": "" if key in agents
                                    else agent_errors.get(key, "?")[:60],
                    })
                # Web search
                try:
                    from shared.web_search import web_search as _ws
                    status_data.append({
                        "Componente": "Web Search",
                        "Status": "OK",
                        "Detalhes": "DuckDuckGo + requests"})
                except Exception:
                    status_data.append({
                        "Componente": "Web Search",
                        "Status": "Indisponivel",
                        "Detalhes": "pip install duckduckgo-search"})
                # Chat Memory
                try:
                    from shared.chat_memory import get_memory as _gm
                    _gm()
                    status_data.append({
                        "Componente": "Chat Memory",
                        "Status": "OK",
                        "Detalhes": "SQLite ativo"})
                except Exception as e:
                    status_data.append({
                        "Componente": "Chat Memory",
                        "Status": "Indisponivel",
                        "Detalhes": str(e)[:60]})

                df_status = pd.DataFrame(status_data)
                st.dataframe(df_status, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("Acoes")

        col_warm1, col_warm2 = st.columns([2, 3])
        with col_warm1:
            from shared.models import MODELS as _M
            warm_model = st.selectbox(
                "Modelo a aquecer",
                [_M["chat"], _M["code"], _M["plan"], _M["autocomplete"]],
                key="warm_model_sel",
            )
        with col_warm2:
            st.markdown("&nbsp;")
            if st.button("Aquecer GPU (carregar modelo na VRAM)",
                         type="primary", use_container_width=True):
                with st.spinner(f"Carregando {warm_model} na VRAM..."):
                    ok, msg = warm_up_gpu(warm_model)
                if ok:
                    st.success(msg)
                    nv2 = check_nvidia_smi()
                    if nv2:
                        st.info(f"VRAM apos warm-up: {nv2['vram_used_mb']}/"
                                f"{nv2['vram_total_mb']} MB | util {nv2['util_pct']}%")
                else:
                    st.error(msg)

        st.caption(
            "Dica: para o modelo nao descarregar da VRAM apos 5 min, "
            "OLLAMA_KEEP_ALIVE=2h ja esta no .env. Para sempre, use -1."
        )


    # == AJUDA & TUTORIAIS ====================================================
    # Layout estilo GenOmics localhost:3838 — header azul + tabs horizontais
    # com cards de conteudo em fundo branco.
    elif page == "Ajuda":
        # Header azul (Bootstrap info color)
        st.markdown(
            '''
            <div class="help-header">
                <h2>Ajuda &amp; Tutoriais</h2>
            </div>
            <div class="help-subtitle">
                Documentacao completa da plataforma LILO. Selecione um documento abaixo:
            </div>
            ''',
            unsafe_allow_html=True,
        )

        def _render_md(filepath):
            """Renderiza arquivo .md dentro de card branco."""
            try:
                content_md = Path(filepath).read_text(encoding="utf-8")
                st.markdown('<div class="help-content">', unsafe_allow_html=True)
                st.markdown(content_md, unsafe_allow_html=False)
                st.markdown('</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Nao foi possivel carregar {filepath}: {e}")

        def _list_md(folder):
            pf = Path(folder)
            if not pf.exists():
                return []
            return sorted(pf.glob("*.md"))

        # 6 abas como no GenOmics (README + Manual + Tecnica + Avancos + Versoes + Subagentes)
        tab_readme, tab_uso, tab_tecnico, tab_avancos, tab_versoes, tab_agentes = st.tabs([
            "README", "Manual do Usuario", "Documentacao Tecnica",
            "Avancos da Plataforma", "Versionamento", "Subagentes",
        ])

        with tab_readme:
            readme_path = _ROOT / "README.md"
            if readme_path.exists():
                _render_md(readme_path)
            else:
                st.warning("README.md nao encontrado.")

        with tab_uso:
            files = _list_md(_ROOT / "docs" / "uso")
            if not files:
                st.info("Nenhum documento em docs/uso/")
            else:
                names = [f.stem.replace("_", " ") for f in files]
                choice = st.radio("Documento:", names, horizontal=True, key="help_uso_radio")
                _render_md(files[names.index(choice)])

        with tab_tecnico:
            files = _list_md(_ROOT / "docs" / "tecnico")
            if not files:
                st.info("Nenhum documento em docs/tecnico/")
            else:
                names = [f.stem.replace("_", " ") for f in files]
                choice = st.radio("Documento:", names, horizontal=True, key="help_tec_radio")
                _render_md(files[names.index(choice)])

        with tab_avancos:
            # Avancos = historico ordenado pelo mais recente
            files = sorted(_list_md(_ROOT / "docs" / "historico"), reverse=True)
            if not files:
                st.info("Nenhum registro de avancos em docs/historico/.")
            else:
                names = [f.stem for f in files]
                choice = st.selectbox(
                    "Selecione um marco/registro (mais recentes primeiro):",
                    names, key="help_av_sel",
                )
                _render_md(files[names.index(choice)])

        with tab_versoes:
            files = _list_md(_ROOT / "docs" / "versoes")
            if not files:
                st.info("Nenhum documento em docs/versoes/")
            else:
                for f in files:
                    with st.expander(f.stem, expanded=(f == files[0])):
                        _render_md(f)

        with tab_agentes:
            files = _list_md(_ROOT / "docs" / "agentes")
            if not files:
                st.info("Nenhum README de subagente em docs/agentes/")
            else:
                names = [f.stem for f in files]
                choice = st.radio("Subagente:", names, horizontal=True, key="help_ag_radio")
                _render_md(files[names.index(choice)])

    # == GLOSSARIO ============================================================
    # Layout estilo GenOmics — header azul + busca + tabela 2 colunas
    elif page == "Glossario":
        st.markdown(
            """
            <div class="help-header glossario-header">
                <h2>Glossario de Termos</h2>
            </div>
            <div class="help-subtitle">
                Termos tecnicos usados na plataforma LILO. Use a busca abaixo para filtrar.
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Parse do GLOSSARIO.md em pares (termo, definicao) das tabelas markdown
        glossario_path = _ROOT / "docs" / "tecnico" / "GLOSSARIO.md"
        terms = []
        if glossario_path.exists():
            md = glossario_path.read_text(encoding="utf-8")
            current_section = "Geral"
            for line in md.splitlines():
                line = line.strip()
                if line.startswith("## "):
                    current_section = line[3:].strip()
                    continue
                if line.startswith("|") and "|" in line[1:]:
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if len(parts) >= 2:
                        termo, definicao = parts[0], parts[1]
                        if termo in ("Termo", "**Termo**", "") or set(termo) <= set("- :"):
                            continue
                        termo_clean = termo.replace("**", "").strip()
                        if termo_clean and definicao:
                            terms.append({
                                "Secao": current_section,
                                "Termo": termo_clean,
                                "Definicao": definicao,
                            })

        col_search, col_secao = st.columns([3, 2])
        with col_search:
            search_q = st.text_input(
                "Buscar termo...",
                key="glossario_search",
                placeholder="Ex: NVT, Ollama, Policy Engine, allow-list",
            )
        with col_secao:
            if terms:
                sections = sorted({t["Secao"] for t in terms})
                sel_secao = st.selectbox(
                    "Filtrar por secao:",
                    ["Todas"] + sections,
                    key="glossario_secao",
                )
            else:
                sel_secao = "Todas"

        filtered = terms
        if search_q:
            q = search_q.lower()
            filtered = [t for t in filtered
                        if q in t["Termo"].lower() or q in t["Definicao"].lower()]
        if sel_secao != "Todas":
            filtered = [t for t in filtered if t["Secao"] == sel_secao]

        st.markdown(
            f"<p style='color:#455A64;font-family:Inter,sans-serif;'>"
            f"<strong>{len(filtered)}</strong> termo(s) encontrados de "
            f"<strong>{len(terms)}</strong> total.</p>",
            unsafe_allow_html=True,
        )

        if filtered:
            df_terms = pd.DataFrame(filtered)
            st.dataframe(
                df_terms,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Secao": st.column_config.TextColumn("Secao", width="small"),
                    "Termo": st.column_config.TextColumn("Termo", width="medium"),
                    "Definicao": st.column_config.TextColumn("Definicao", width="large"),
                },
                height=600,
            )
        else:
            st.warning("Nenhum termo encontrado com os filtros aplicados.")

        st.caption(
            "Fonte: docs/tecnico/GLOSSARIO.md - "
            "para adicionar termos, edite o arquivo e recarregue a pagina (R)."
        )
