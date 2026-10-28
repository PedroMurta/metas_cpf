import base64
from html import escape
from pathlib import Path

import streamlit as st


PASTA = Path(__file__).resolve().parent


def aplicar_tema():
    fontes = """
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@900&family=Inter:wght@300;400;500;600;700&display=swap');
@import url('https://use.typekit.net/lfm6vcy.css');
"""
    tokens = (PASTA / "assets/variaveis-claro.css").read_text(encoding="utf-8")
    estilos = (PASTA / "style.css").read_text(encoding="utf-8")
    st.html(f"<style>{fontes}\n{tokens}\n{estilos}</style>")


def cabecalho(titulo, etapa, gerencia):
    logo = base64.b64encode((PASTA / "assets/logo-light.png").read_bytes()).decode("ascii")
    st.html(
        f'''<header class="streamlit-header" aria-label="SEST SENAT">
            <div class="streamlit-header-left">
                <img class="streamlit-header-logo" src="data:image/png;base64,{logo}" alt="SEST SENAT">
                <span class="streamlit-header-divider" aria-hidden="true"></span>
                <span class="streamlit-header-area">{escape(gerencia.upper())}</span>
            </div>
            <div class="streamlit-header-title">{escape(titulo)}</div>
            <div class="streamlit-header-right">DADOS &amp; DECISÕES</div>
        </header>'''
    )
    if etapa:
        st.html(f'<div class="streamlit-section-tag">{escape(etapa)}</div>')
        st.title(titulo)


def rodape():
    st.html('<footer class="streamlit-footer">SEST SENAT · GEPLANE · Núcleo de Dados</footer>')