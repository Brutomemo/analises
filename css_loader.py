"""
css_loader.py
Carrega o style.css externo no app Streamlit.
Substitui todos os blocos st.markdown(<style>...</style>) do app.py.
"""

import os
import streamlit as st


def load_css():
    """
    Lê o arquivo style.css e injeta no Streamlit via st.markdown.
    Deve ser chamado UMA única vez no app.py, logo após st.set_page_config().
    """
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css")

    try:
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        st.markdown(
            f"<style>{css}</style>",
            unsafe_allow_html=True
        )

    except FileNotFoundError:
        st.warning("⚠️ style.css não encontrado. Verifique se o arquivo está na raiz do projeto.")
