# ====
# 0. VALIDAÇÃO DE LICENÇA (ANTES DE TUDO)
# ====
from license_manager import LicenseManager

try:
    LicenseManager.validate_license()
except PermissionError:
    import streamlit as st
    st.error("❌ Erro: LICENSE.txt não encontrado na raiz do projeto.")
    st.stop()

# 1. CONFIGURAÇÃO DA PÁGINA
import streamlit as st
import subprocess
import sys
import os

st.set_page_config(page_title="Analise Qualitativa - Negociação", layout="wide", initial_sidebar_state="collapsed")

import css_loader
css_loader.load_css()

# 2. IMPORTS ORIGINAIS
from PIL import Image
import base64
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
import tempfile
from fpdf import FPDF
import unicodedata
import re
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns

# 3. IMPORTS PARA REGRESSÃO LINEAR (NOVO)
import numpy as np
from scipy import stats as sp_stats
from sklearn.preprocessing import StandardScaler
import warnings
import importlib
warnings.filterwarnings('ignore')

# ====
# 2.1. IMPORTAÇÃO DOS MÓDULOS DE IA E DADOS
# ====
import airtable_link
import analise
import ia_link        # Cérebro da Aba 1 (Transcrições)
import ia_estatistica # Cérebro da Aba 2 (Série Histórica)
import serie_historica
import chat_delta
import form_apa
import css_loader
import utils
import apa



# ====
# 4. SISTEMA DE SEGURANÇA
# ====
import os

def check_password():
    """Retorna True se o usuário inseriu a senha correta."""
    
    # LER APENAS DE VARIÁVEIS DE AMBIENTE (Railway)
    try:
        correct_password = st.secrets["ACCESS_PASSWORD"]
    except:
        correct_password = os.getenv("ACCESS_PASSWORD")

    if not correct_password:
            st.error("❌ ACCESS_PASSWORD não configurada!")
            return False
    
    def password_entered():
        """Verifica se a senha coincide."""
        if st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("## ✔ Controle de Acesso")
        st.text_input("Insira a Senha de Acesso:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("## ✔ Controle de Acesso - GATE")
        st.text_input("Senha incorreta. Tente novamente:", type="password", on_change=password_entered, key="password")
        st.error("Acesso negado. Credenciais inválidas.")
        return False
    else:
        return True
# ====
# 5. CAMADA DE PROTEÇÃO (O "ENVELOPE")
# ====
if not check_password():
    st.stop()

# --- TUDO A PARTIR DAQUI ESTÁ PROTEGIDO PELA SENHA ---

st.sidebar.success("Autenticação validada.")
# =====================================================================
#  INSERIR O CÓDIGO DE CARREGAMENTO GERAL AQUI (O "PORTEIRO")
# =====================================================================
# 1. Tenta recuperar os dados do cofre (Session State)
if "df_quali" in st.session_state and "df_tec" in st.session_state:
    df_quali = st.session_state["df_quali"]
    df_tec = st.session_state["df_tec"]

# 2. Se não estiverem no cofre (ex: acabou de logar), busca no Airtable
else:
    with st.spinner("Carregando bases operacionais do Airtable..."):
        df_quali, status_q = airtable_link.buscar_dados_apa()
        df_tec, status_t = airtable_link.buscar_todas_tecnicas()

        if df_quali.empty:
            st.error("Falha ao carregar as APAs. Verifique a conexão com o Airtable.")
            st.stop()
        # df_tec pode ser vazio legitimamente (tabela de técnicas ainda não tem registros)

        # Persiste em session_state para evitar buscar de novo a cada rerun
        st.session_state["df_quali"] = df_quali
        st.session_state["df_tec"]   = df_tec
        st.session_state["status_q"] = status_q
        st.session_state["status_t"] = status_t
# =====================================================================


        
# ====
# 1. CONFIGURAÇÃO DA PÁGINA E CSS (UX e Design System)
# ====
# === FONTES OFICIAIS DO SISTEMA ===
# O seletor universal * forca a fonte em TODO elemento, com excecoes para Share Tech Mono.
st.markdown("""


<div class="liquid-blob blob1"></div>
<div class="liquid-blob blob2"></div>
<div class="liquid-blob blob3"></div>
""", unsafe_allow_html=True)


if 'stats_calculados' not in st.session_state: st.session_state['stats_calculados'] = None


# ====
# 2. CABEÇALHO VISUAL E FUNDO DO CABEÇALHO
# ====

import os
import base64
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components

# =========================================================
# CSS GLOBAL — ORBITRON FUNCIONANDO NO APP INTEIRO
# =========================================================
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>

<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">

<style>

/* =========================================================
FORÇA ORBITRON GLOBALMENTE
========================================================= */

html, body, .stApp {
    font-family: 'Orbitron', sans-serif !important;
}

/* TITULOS */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Orbitron', sans-serif !important;
    letter-spacing: 0.03em;
}

/* TEXTOS */
p, span, div, label {
    font-family: 'Orbitron', sans-serif !important;
}

/* STRONG */
strong {
    font-family: 'Orbitron', sans-serif !important;
    font-weight: 700;
}

/* STREAMLIT */
.stMarkdown,
.stText,
.stMetric,
.stDataFrame,
.stTable {
    font-family: 'Orbitron', sans-serif !important;
}

/* SUBTITLE */
.sub-title {
    font-family: 'Orbitron', sans-serif !important;
    letter-spacing: 0.04em;
}

/* MAIN TITLE */
.main-title {
    font-family: 'Orbitron', sans-serif !important;
    font-weight: 700;
    letter-spacing: 0.05em;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# PATHS
# =========================================================

script_dir = os.path.dirname(os.path.abspath(__file__))
path_assets = os.path.join(script_dir, "Assets")

path_brasao_gate = os.path.join(path_assets, "brasao_gate.webp")

# =========================================================
# IMAGEM TOPO
# =========================================================

img_topo_b64 = ""

try:
    with open(path_teste_gate, "rb") as img_file:
        img_topo_b64 = base64.b64encode(img_file.read()).decode()
except:
    pass

# =========================================================
# BANNER TOPO
# =========================================================

if img_topo_b64:
    st.markdown(f"""
        <div style="
            position: relative;
            width: 100%;
            height: 200px;
            border-radius: 0px;
            overflow: hidden;
            background-image: url('data:image/webp;base64,{img_topo_b64}');
            background-size: cover;
            background-position: center 40%;
            animation: fadeInUpBlur 1s cubic-bezier(0.2, 0.8, 0.2, 1) both;
        ">
            <div style="
                position: absolute;
                inset: 0;
                background: linear-gradient(180deg, rgba(5,5,5,0.6) 0%, 
                rgba(5,5,5,0.0) 40%, 
                rgba(249,115,22,0.4) 100%);
            "></div>
        </div>
    """, unsafe_allow_html=True)

# =========================================================
# CABEÇALHO
# =========================================================

col_logo, col_titulo, col_espaco = st.columns([1, 6, 1])

with col_logo:

    try:

        with open(path_brasao_gate, "rb") as f:
            brasao_b64 = base64.b64encode(f.read()).decode()

        st.markdown(f"""
            <div style="display:flex; justify-content:center; width:100%;">
                <img src="data:image/webp;base64,{brasao_b64}"
                     style="max-width:90px; height:auto; border:none;">
            </div>
        """, unsafe_allow_html=True)

    except Exception:
        pass

# =========================================================
# CABEÇALHO IMAGEM
# =========================================================

script_dir = os.path.dirname(os.path.abspath(__file__))
path_cab = os.path.join(script_dir, "Assets", "image cab.jpg")

try:
    with open(path_cab, "rb") as f:
        cab_b64 = base64.b64encode(f.read()).decode()

    st.markdown(f"""
        <div style="
            position: relative;
            width: 100%;
            height: 520px;
            border-radius: 20px;
            overflow: hidden;
            background-image: url('data:image/jpeg;base64,{cab_b64}');
            background-size: cover;
            background-position: center;
        ">
            <div style="
                position: absolute;
                inset: 0;
                background: linear-gradient(180deg, rgba(5,5,5,0.6) 0%, 
                rgba(5,5,5,0.0) 40%, 
                rgba(249,115,22,0.4) 100%);
            "></div>
            <div style="
                position: absolute;
                bottom: 20px; left: 20px; right: 20px;
            ">
                <div style="
                    background: rgba(10,10,10,0.72);
                    backdrop-filter: blur(16px) saturate(180%);
                    -webkit-backdrop-filter: blur(16px) saturate(180%);
                    border-top: 1px solid rgba(255,255,255,0.15);
                    border-left: 1px solid rgba(255,255,255,0.08);
                    border-right: 1px solid rgba(255,255,255,0.08);
                    border-bottom: 1px solid rgba(255,255,255,0.05);
                    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
                    border-radius: 12px;
                    padding: 15px 20px;
                    color: white;
                ">
                    <h2 style="text-align:center; font-size:1.3rem; font-weight:600; margin-bottom:10px; color:white; letter-spacing:0.05em; font-family:'Orbitron', sans-serif;">
                        Sistema de Análise Qualitativa das Negociações
                    </h2>
                    <p style="text-align:center; font-size:1rem; color:#d1d5db; margin-bottom:24px; letter-spacing:0.04em; font-family:'Orbitron', sans-serif;">
                        Estudo das Técnicas Aplicadas
                    </p>
                    <p style="text-align:center; font-size:0.8rem; font-weight:500; color:white; line-height:1.6;">
                        Negociações em Incidentes Críticos atendidos pelo Grupo de Ações Táticas Especiais.
                    </p>
                    <p style="font-size:0.9rem; color:#bbb; line-height:1.7; margin-top:18px;">
                        Os dados são geridos de forma automatizada em nuvem via <strong>Airtable</strong>, integrando um motor estatístico multifatorial.
                    </p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

except Exception:
    pass

# =========================================================
# RODAPÉ
# =========================================================

st.markdown(
    '<p class="sub-title">Delta-Negociação - GATE / PMESP</p>',
    unsafe_allow_html=True
)

st.markdown(
    '<p style="color:#999; margin-top:5px;">Desenvolvido por Cb PM Marcos - Supervisão: Cap PM Pavão</p>',
    unsafe_allow_html=True
)

# ============================================================
# 3. CONEXÃO E NAVEGAÇÃO PRINCIPAL
# ============================================================

# Os dados já foram carregados acima no "porteiro"
# (lazy load com session_state).

status_q = st.session_state.get("status_q", "OK")
status_t = st.session_state.get("status_t", "OK")


# ============================================================
# VALIDAÇÃO AIRTABLE
# ============================================================

if df_quali.empty:
    st.error(f"Erro na conexão com Airtable: {status_q}")

else:
    # ========================================================
    # NAVEGAÇÃO PRINCIPAL
    # ========================================================

    pagina = st.radio(
        label="",
        options=[
            "✔ Visão seletiva",
            "✔ Série Histórica",
            "✔ Chat Analítico",
            "✔ Entrada de Dados"
        ],
        horizontal=True,
        key="menu_principal_delta"
    )
            

    # ========================================================
    # ABA 1 — VISÃO SELETIVA
    # ========================================================


    # ====
    # ABA 1: VISÃO DA NEGOCIAÇÃO SOBRE O INCIDENTE EM ANÁLISE
    # ====
    if pagina == "✔ Visão seletiva":
        apa.render_apa(df_quali, df_tec)            

    elif pagina == "✔ Série Histórica":
        serie_historica.render_serie_historica(df_quali)

    elif pagina == "✔ Chat Analítico":
        chat_delta.render_chat_delta(df_quali, df_tec)  
  
    elif pagina == "✔ Entrada de Dados":
        form_apa.render(df_quali, df_tec)

    