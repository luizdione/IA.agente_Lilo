"""
dashboard.py — Dashboard LILO (Streamlit)
==========================================
Interface web local que integra os 4 subagentes via shared/.

Uso:
    pip install streamlit pandas requests
    streamlit run dashboard.py --server.port 8501

Acesso: http://localhost:8501
"""

import streamlit as st
import sys
import os
import json
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

# Garante path do projeto
_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT))

from shared.utils import load_env, get_env
from shared.logger import get_logger

load_env()
log = get_logger("Dashboard")

# ── Configuração da página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="LILO — Dashboard",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Estado da sessão ─────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agents_loaded" not in st.session_state:
    st.session_state.agents_loaded = False
if "agents" not in st.session_state:
    st.session_state.agents = {}


# ── Carregar agentes (lazy, uma vez) ─────────────────────────────────────────
@st.cache_resource
def load_agents():
    """Carrega os subagentes LILO."""
    agents = {}
    errors = {}

    try:
        from Analise_SQL.agent import SQLAgent
        agents["sql"] = SQLAgent()
    except Exception as e:
        errors["sql"] = str(e)

    try:
        from PDFs_library.agent import PDFAgent
        agents["pdf"] = PDFAgent()
    except Exception as e:
        errors["pdf"] = str(e)

    try:
        from scholaragent.agent import ScholarAgent
        agents["scholar"] = ScholarAgent()
    except Exception as e:
        errors["scholar"] = str(e)

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gateway_agent", _ROOT / "llm-gateway" / "agent.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        agents["gateway"] = mod.GatewayAgent()
    except Exception as e:
        errors["gateway"] = str(e)

    return agents, errors


# ── Health check ─────────────────────────────────────────────────────────────
def check_ollama():
    """Verifica status do Ollama."""
    try:
        r = requests.get(f"{get_env('OLLAMA_HOST', 'http://localhost:11434')}/api/tags", timeout=3)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            return True, models
    except Exception:
        pass
    return False, []


def check_ollama_gpu():
    """Verifica modelos carregados na GPU."""
    try:
        r = requests.get(f"{get_env('OLLAMA_HOST', 'http://localhost:11434')}/api/ps", timeout=3)
        if r.status_code == 200:
            return r.json().get("models", [])
    except Exception:
        pass
    return []


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Dna/3D/dna_3d.png", width=60)
    st.title("LILO")
    st.caption("Agente Pessoal Integrado")

    # Carregar agentes
    agents, agent_errors = load_agents()

    # Status
    st.markdown("### Status")
    ollama_ok, ollama_models = check_ollama()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Ollama", "Online" if ollama_ok else "Offline")
    with col2:
        st.metric("Modelos", len(ollama_models) if ollama_ok else 0)

    st.markdown("**Subagentes:**")
    agent_labels = {"sql": "SQL", "pdf": "PDFs", "scholar": "Scholar", "gateway": "Gateway"}
    for key, label in agent_labels.items():
        if key in agents:
            st.success(f"{label}")
        else:
            st.error(f"{label}: {agent_errors.get(key, 'erro')[:40]}")

    st.divider()

    # Navegação
    page = st.radio(
        "Navegação",
        ["Chat", "SQL", "PDFs", "Scholar", "Custos", "Health"],
        label_visibility="collapsed",
    )

    st.divider()

    # Modo do chat
    if page == "Chat":
        mode = st.selectbox("Modo", ["chat", "code", "bioinfo", "sql"])
    else:
        mode = "chat"


# ── Página: Chat ─────────────────────────────────────────────────────────────
if page == "Chat":
    st.header("Chat LILO")

    # Histórico
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    if prompt := st.chat_input("Digite sua pergunta..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    # Roteamento automático via lilo.py
                    from lilo import route
                    response = route(prompt, context={"mode": mode})
                except Exception as e:
                    response = f"Erro: {e}"

            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})


# ── Página: SQL ──────────────────────────────────────────────────────────────
elif page == "SQL":
    st.header("Análise SQL")

    col1, col2 = st.columns([2, 1])

    with col2:
        # Listar bancos disponíveis
        db_files = list(_ROOT.rglob("*.db")) + list(_ROOT.rglob("*.sqlite"))
        db_names = [str(f.relative_to(_ROOT)) for f in db_files]
        selected_db = st.selectbox("Banco de dados", db_names if db_names else ["Nenhum encontrado"])

        if selected_db and selected_db != "Nenhum encontrado":
            import sqlite3
            db_path = _ROOT / selected_db
            try:
                conn = sqlite3.connect(str(db_path))
                tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
                st.dataframe(tables, use_container_width=True)

                if not tables.empty:
                    selected_table = st.selectbox("Tabela", tables["name"].tolist())
                    if selected_table:
                        schema = pd.read_sql(f"PRAGMA table_info({selected_table})", conn)
                        st.dataframe(schema[["name", "type"]], use_container_width=True)
                conn.close()
            except Exception as e:
                st.error(f"Erro: {e}")

    with col1:
        query_input = st.text_area(
            "Query SQL ou pergunta em linguagem natural",
            height=100,
            placeholder="Ex: SELECT * FROM tabela LIMIT 10\nOu: quais são as espécies com mais registros?",
        )

        col_run, col_ai = st.columns(2)

        with col_run:
            if st.button("Executar SQL", type="primary") and query_input:
                if selected_db and selected_db != "Nenhum encontrado":
                    try:
                        conn = sqlite3.connect(str(_ROOT / selected_db))
                        df = pd.read_sql(query_input, conn)
                        conn.close()
                        st.dataframe(df, use_container_width=True)
                        st.info(f"{len(df)} registros retornados")
                    except Exception as e:
                        st.error(f"Erro SQL: {e}")

        with col_ai:
            if st.button("Perguntar ao LILO") and query_input:
                with st.spinner("Processando..."):
                    if "sql" in agents:
                        ctx = {}
                        if selected_db and selected_db != "Nenhum encontrado":
                            ctx["db_path"] = str(_ROOT / selected_db)
                        response = agents["sql"].run(query_input, ctx)
                        st.markdown(response)
                    else:
                        st.error("SQLAgent não disponível")


# ── Página: PDFs ─────────────────────────────────────────────────────────────
elif page == "PDFs":
    st.header("Biblioteca de PDFs")

    pdf_dir = Path(get_env("PDF_DIR", str(_ROOT / "PDFs_library" / "data")))

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Arquivos")
        # Buscar em múltiplos diretórios
        pdf_files = list(pdf_dir.rglob("*.pdf")) if pdf_dir.exists() else []
        pdf_files += list((_ROOT / "PDFs_library").rglob("*.pdf"))
        pdf_files += list((_ROOT / "scholaragent" / "uploads").rglob("*.pdf"))
        # Remover duplicatas
        pdf_files = list({str(f): f for f in pdf_files}.values())

        if pdf_files:
            pdf_names = [f.name for f in pdf_files]
            selected_pdf = st.selectbox("Selecione um PDF", pdf_names)
            selected_path = next(f for f in pdf_files if f.name == selected_pdf)
            st.caption(f"Caminho: {selected_path}")
        else:
            st.warning(f"Nenhum PDF encontrado em {pdf_dir}")
            selected_pdf = None
            selected_path = None

        # Upload
        uploaded = st.file_uploader("Upload PDF", type=["pdf"])
        if uploaded:
            save_path = pdf_dir / uploaded.name
            pdf_dir.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(uploaded.getbuffer())
            st.success(f"Salvo em {save_path}")
            st.rerun()

    with col2:
        if selected_path:
            analysis_mode = st.radio(
                "Modo de análise",
                ["simple", "introduction", "methods"],
                horizontal=True,
            )

            if st.button("Analisar PDF", type="primary"):
                with st.spinner(f"Analisando {selected_pdf}..."):
                    if "pdf" in agents:
                        response = agents["pdf"].run(
                            f"Analisar {selected_pdf}",
                            {"file_path": str(selected_path), "mode": analysis_mode},
                        )
                        st.markdown(response)
                    else:
                        st.error("PDFAgent não disponível")


# ── Página: Scholar ──────────────────────────────────────────────────────────
elif page == "Scholar":
    st.header("Busca Acadêmica")

    search_query = st.text_input(
        "Termos de busca",
        placeholder="Ex: CRISPR-Cas9 Trypanosoma cruzi drug targets",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        source = st.selectbox("Fonte", ["auto", "pubmed", "arxiv"])
    with col2:
        max_results = st.slider("Max resultados", 1, 20, 5)
    with col3:
        synthesize = st.checkbox("Sintetizar com LLM", value=True)

    if st.button("Buscar", type="primary") and search_query:
        with st.spinner("Buscando artigos..."):
            if "scholar" in agents:
                response = agents["scholar"].run(
                    search_query,
                    {"source": source, "max_results": max_results, "synthesize": synthesize},
                )
                st.markdown(response)
            else:
                st.error("ScholarAgent não disponível")


# ── Página: Custos ──────────────────────────────────────────────────────────
elif page == "Custos":
    st.header("Monitoramento de Custos")

    try:
        from shared.cost_tracker import get_tracker
        tracker = get_tracker()
        summary = tracker.daily_summary()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Requests hoje", summary["total_requests"])
        with col2:
            st.metric("Custo total", f"${summary['total_cost_usd']:.4f}")
        with col3:
            st.metric("Tokens IN", summary["total_tokens_in"])
        with col4:
            st.metric("Tokens OUT", summary["total_tokens_out"])

        st.divider()

        col_be, col_sa = st.columns(2)
        with col_be:
            st.subheader("Por Backend")
            if summary["by_backend"]:
                be_df = pd.DataFrame([
                    {"Backend": k, "Requests": v["count"], "Custo": f"${v['cost']:.4f}"}
                    for k, v in summary["by_backend"].items()
                ])
                st.dataframe(be_df, use_container_width=True, hide_index=True)

        with col_sa:
            st.subheader("Por Subagente")
            if summary["by_subagent"]:
                sa_df = pd.DataFrame([
                    {"Subagente": k, "Requests": v["count"], "Custo": f"${v['cost']:.4f}"}
                    for k, v in summary["by_subagent"].items()
                ])
                st.dataframe(sa_df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Últimas Requests")
        recent = tracker.recent_requests(20)
        if recent:
            recent_df = pd.DataFrame(recent)
            cols_show = [c for c in ["timestamp", "subagent", "tier", "model", "cost_usd", "duration_ms", "query_preview"] if c in recent_df.columns]
            st.dataframe(recent_df[cols_show], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma request registrada ainda.")

    except Exception as e:
        st.error(f"Erro ao carregar custos: {e}")


# ── Página: Health ───────────────────────────────────────────────────────────
elif page == "Health":
    st.header("Diagnóstico LILO")

    if st.button("Executar Health Check", type="primary"):
        with st.spinner("Verificando backends..."):
            # Ollama
            ollama_ok, models = check_ollama()
            gpu_models = check_ollama_gpu()

            # Tabela de status
            status_data = []

            status_data.append({
                "Componente": "Ollama",
                "Status": "Online" if ollama_ok else "Offline",
                "Detalhes": f"{len(models)} modelos" if ollama_ok else "Não respondeu",
            })

            # Modelos LILO esperados
            expected = {
                "chat": get_env("OLLAMA_MODEL", "llama3.1:8b-instruct-q8_0"),
                "code": get_env("OLLAMA_MODEL_CODE", "qwen2.5-coder:14b"),
                "plan": get_env("OLLAMA_MODEL_PLAN", "phi3:14b-medium-128k-instruct-q4_K_M"),
                "fast": get_env("OLLAMA_MODEL_FAST", "qwen2.5-coder:7b-instruct"),
            }

            for role, model_name in expected.items():
                installed = model_name in models if ollama_ok else False
                status_data.append({
                    "Componente": f"Modelo ({role})",
                    "Status": "Instalado" if installed else "Faltando",
                    "Detalhes": model_name,
                })

            # GPU
            if gpu_models:
                for gm in gpu_models:
                    vram = gm.get("size_vram", 0) / 1e9
                    status_data.append({
                        "Componente": "GPU",
                        "Status": "Ativo",
                        "Detalhes": f"{gm.get('name', '?')} — {vram:.1f} GB VRAM",
                    })
            else:
                status_data.append({
                    "Componente": "GPU",
                    "Status": "N/A",
                    "Detalhes": "Nenhum modelo na GPU",
                })

            # Subagentes
            for key, label in agent_labels.items():
                status_data.append({
                    "Componente": f"Agent: {label}",
                    "Status": "OK" if key in agents else "Erro",
                    "Detalhes": "" if key in agents else agent_errors.get(key, "?")[:60],
                })

            # LiteLLM
            try:
                r = requests.get(f"{get_env('LITELLM_PROXY_URL', 'http://localhost:4000')}/health", timeout=2)
                litellm_ok = r.status_code == 200
            except Exception:
                litellm_ok = False

            status_data.append({
                "Componente": "LiteLLM Proxy",
                "Status": "Online" if litellm_ok else "Offline",
                "Detalhes": get_env("LITELLM_PROXY_URL", "http://localhost:4000"),
            })

            df = pd.DataFrame(status_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Lista completa de modelos
            if ollama_ok and models:
                with st.expander("Todos os modelos Ollama"):
                    for m in sorted(models):
                        st.code(m)


# ── Footer ───────────────────────────────────────────────────────────────────
st.sidebar.divider()
st.sidebar.caption(f"LILO v{get_env('LILO_VERSION', '1.0.0')} — {datetime.now().strftime('%H:%M:%S')}")
