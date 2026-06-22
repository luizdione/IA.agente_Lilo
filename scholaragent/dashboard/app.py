"""
dashboard/app.py — Interface de conversa com a biblioteca + gate de verificação.
Uso: streamlit run scholaragent/dashboard/app.py

Fluxo: pergunta -> RAG (Lilo 3.0) -> gate de verificação factual -> revisão humana
-> liberação para export. Nenhum conteúdo externo sai sem PASS + aprovação humana.
"""
from __future__ import annotations
import streamlit as st

from scholaragent.brain.embedder import Embedder
from scholaragent.brain.vector_store import BrainStore
from scholaragent.chat.rag_chain import ScholarRAG
from scholaragent.verify import (
    build_grounder, VerificationGate, evidence_from_rag, Decision,
)
from scholaragent.export.guard import can_export

st.set_page_config(page_title="ScholarAgent — Cérebro Científico", layout="wide")

_BADGE = {"pass": "🟢 PASS", "review": "🟡 REVIEW", "block": "🔴 BLOCK"}


@st.cache_resource
def load_resources():
    embedder = Embedder()
    store = BrainStore()
    rag = ScholarRAG(store, embedder)
    gate = VerificationGate(build_grounder(store, embedder))
    return rag, store, gate


rag, store, gate = load_resources()

st.title("🧠 ScholarAgent — Cérebro Científico")
st.caption(f"Chunks indexados: {store.count()}")

tab_chat, tab_verify, tab_gap, tab_intro = st.tabs(
    ["💬 Chat", "✅ Verificação", "🔍 Gaps", "📝 Rascunho de introdução"]
)

# --------------------------------- Chat ----------------------------------- #
with tab_chat:
    st.subheader("Converse com sua biblioteca")
    st.session_state.setdefault("history", [])
    question = st.chat_input("Ex.: Quais papers tenho sobre eQTL em músculo bovino?")
    if question:
        with st.spinner("Consultando biblioteca e verificando..."):
            res = rag.ask(question)
            report = None
            if res["chunks"]:
                used, ref_map = evidence_from_rag(res["chunks"], res["metas"])
                report = gate.verify(
                    content_id=f"chat-{len(st.session_state.history)}",
                    question=question, generated_text=res["answer"],
                    used_chunks=used, ref_to_evidence=ref_map,
                )
                st.session_state["last_report"] = report
        st.session_state.history.append({"q": question, "res": res, "report": report})

    for turn in st.session_state.history:
        with st.chat_message("user"):
            st.write(turn["q"])
        with st.chat_message("assistant"):
            rep = turn["report"]
            if rep is not None:
                st.markdown(f"**Gate:** {_BADGE.get(rep.decision.value, rep.decision.value)}")
            st.write(turn["res"]["answer"])
            if turn["res"]["refs"]:
                with st.expander("Referências usadas"):
                    for r in turn["res"]["refs"]:
                        st.caption(r)

# ----------------------------- Verificação -------------------------------- #
with tab_verify:
    st.subheader("Verificação factual antes de publicar")
    report = st.session_state.get("last_report")
    if report is None:
        st.info("Faça uma pergunta na aba Chat para gerar um relatório de verificação.")
    else:
        st.markdown(f"### Decisão do gate: **{_BADGE.get(report.decision.value)}**")
        st.caption(f"não-suportados: {report.unsupported_count} · "
                   f"contraditos: {report.contradicted_count}")
        for r in report.results:
            head = f"[{r.verdict.value}] {r.claim.text[:80]}"
            with st.expander(head):
                st.write("**Afirmação:**", r.claim.text)
                st.caption(f"tipo={r.claim.claim_type.value} · "
                           f"numérico_ok={r.numeric_ok} · citação_ok={r.citation_ok}")
                for e in r.evidence:
                    st.info(f"Fonte ({e.section}): {e.text[:400]}")
                if r.rationale:
                    st.caption(r.rationale)

        if report.decision == Decision.BLOCK:
            st.error("BLOCK: há afirmação não sustentada ou contradita. "
                     "Edite a fonte ou o texto antes de aprovar.")
        else:
            reviewer = st.text_input("Revisor", value="Luiz Dione (IFRJ)")
            if st.button("Aprovar para exportação"):
                report.human_approved = True
                report.reviewer = reviewer
                st.success("Aprovado. Conteúdo liberado para export/.")

        st.divider()
        st.write("**Liberado para export/?**",
                 "✅ sim" if can_export(report) else "❌ não")

# ------------------------------- Gaps ------------------------------------- #
with tab_gap:
    st.subheader("Detector de lacunas na literatura")
    theme = st.text_input("Tema de pesquisa", placeholder="ex: eQTL Nelore músculo")
    if st.button("Detectar gaps") and theme:
        with st.spinner("Analisando lacunas..."):
            res = rag.ask(
                f"Quais são as lacunas, contradições e perguntas não respondidas sobre: "
                f"{theme}? Seja específico sobre o que ainda não foi estudado.",
                n_chunks=12,
            )
        st.write(res["answer"])
        with st.expander("Papers consultados"):
            for r in res["refs"]:
                st.caption(r)

# ----------------------- Rascunho de introdução --------------------------- #
with tab_intro:
    st.subheader("Rascunho de introdução")
    topic = st.text_input("Tópico do paper", placeholder="ex: eQTL de Bos indicus em músculo")
    if st.button("Gerar rascunho") and topic:
        with st.spinner("Redigindo e verificando..."):
            res = rag.ask(
                f"Escreva uma introdução científica formal de 3 parágrafos sobre: {topic}. "
                "Use as referências disponíveis e cite pelo número.",
                n_chunks=10,
            )
            if res["chunks"]:
                used, ref_map = evidence_from_rag(res["chunks"], res["metas"])
                report = gate.verify("intro", topic, res["answer"], used, ref_map)
                st.session_state["last_report"] = report
                st.markdown(f"**Gate:** {_BADGE.get(report.decision.value)} "
                            f"(revise na aba Verificação antes de usar)")
        st.write(res["answer"])
