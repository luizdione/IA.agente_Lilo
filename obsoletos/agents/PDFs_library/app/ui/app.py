# app/ui/app.py

import streamlit as st
from app.pipeline.executor import run

st.title("🧠 SciVault AI")

q = st.text_input("Pergunta científica:")

if q:
    result = run(q)
    for r in result:
        st.write(r)