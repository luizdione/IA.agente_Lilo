# app/ui/streamlit_app.py

import streamlit as st

st.title("SciVault")

query = st.text_input("Pergunte algo:")

if query:
    st.write("Buscando...")