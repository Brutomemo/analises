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
warnings.filterwarnings('ignore')

# ====
# 2.1. IMPORTAÇÃO DOS MÓDULOS DE IA E DADOS
# ====
import airtable_link
import analise
import ia_link        # Cérebro da Aba 1 (Transcrições)
import ia_estatistica # Cérebro da Aba 2 (Série Histórica)

# ====
# 3. FUNÇÕES AUXILIARES E DADOS (A "CAIXA DE FERRAMENTAS")
# ====
def render_toggle_button(
    label: str,
    session_key: str,
    button_key: str,
    width_ratio: float = 0.6
) -> bool:
    """Renderiza um botão toggle padronizado."""
    if session_key not in st.session_state:
        st.session_state[session_key] = False
    
    col_btn, col_spacer = st.columns([width_ratio, 1 - width_ratio])
    with col_btn:
        if st.button(label, key=button_key, use_container_width=True):
            st.session_state[session_key] = not st.session_state[session_key]
    
    return st.session_state[session_key]

def limpar_valor(val):
    if isinstance(val, list): return val[0] if len(val) > 0 else "N/D"
    return str(val) if pd.notna(val) else "N/D"


def limpar_id(v):
    if isinstance(v, list) and len(v) > 0: v = v[0]
    v_str = str(v).strip()
    if v_str.endswith('.0'): v_str = v_str[:-2]
    return v_str

def formatar_tempo_airtable(val):
    try:
        if isinstance(val, list): val = val[0]
        if pd.isna(val) or val == "N/D" or val == "": return "N/D"
        s = int(float(val))
        h = s // 3600
        m = (s % 3600) // 60
        return f"{h:02d}h {m:02d}m"
    except:
        return str(val)

def somar_tempos_segundos(serie):
    total_s = 0
    for val in serie:
        try:
            if isinstance(val, list): val = val[0]
            if pd.notna(val) and val != "N/D" and val != "":
                total_s += int(float(val))
        except: pass
    h = total_s // 3600
    m = (total_s % 3600) // 60
    return f"{h:02d}h {m:02d}m"

# --- MOTOR GRÁFICO (MAPA EMOCIONAL COMPLETO & BLINDADO) ---
escala_likert = {
    "❓ inaudível / não observado": 0, "inaudível": 0, "não observado": 0, "n/d": 0, "nao observado": 0,
    
    # Nível 1
    "não agressivo": 1, "nao agressivo": 1, "não agresssivo": 1, "nao agresssivo": 1, 
    "não receptivo": 1, "nao receptivo": 1,
    
    # Nível 2
    "neutro": 2, 
    
    # Nível 3
    "parcialmente agressivo": 3, "parcialmente receptivo": 3,
    
    # Nível 4
    "agressivo": 4, "receptivo": 4,
    
    # Nível 5
    "muito agressivo": 5, "muito receptivo": 5,
    
    "🔴 reação negativa": 1, "⚪ reação neutra": 2, "🟢 reação positiva": 5
}

def converter_escala(val):
    if not val: return 0
    # Limpa emojis e espaços para garantir o "match"
    v = str(val).lower().strip()
    return escala_likert.get(v, 0)

# ====
# 4. SISTEMA DE SEGURANÇA
# ====
def check_password():
    """Retorna True se o usuário inseriu a senha correta."""
    def password_entered():
        """Verifica se a senha coincide com o segredo guardado."""
        if st.session_state["password"] == st.secrets["access_password"]:
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

        if df_quali.empty or df_tec.empty:
            st.error("Falha ao carregar os dados. Verifique a conexão com o Airtable.")
            st.stop()

        # Persiste em session_state para evitar buscar de novo a cada rerun
        st.session_state["df_quali"] = df_quali
        st.session_state["df_tec"]   = df_tec
        st.session_state["status_q"] = status_q
        st.session_state["status_t"] = status_t
# =====================================================================
#st.title("Série Histórica - Negociações GATE")

# ====
# 4. FUNÇÕES AUXILIARES (TRATAMENTO DE DADOS DO AIRTABLE)
# ====
def limpar_valor(val):
    if isinstance(val, list): return val[0] if len(val) > 0 else "N/D"
    return str(val) if pd.notna(val) else "N/D"

def limpar_id(v):
    if isinstance(v, list) and len(v) > 0: v = v[0]
    v_str = str(v).strip()
    if v_str.endswith('.0'): v_str = v_str[:-2]
    return v_str

def formatar_tempo_airtable(val):
    try:
        if isinstance(val, list): val = val[0]
        if pd.isna(val) or val == "N/D" or val == "": return "N/D"
        s = int(float(val))
        h = s // 3600
        m = (s % 3600) // 60
        return f"{h:02d}h {m:02d}m"
    except:
        return str(val)

def somar_tempos_segundos(serie):
    total_s = 0
    for val in serie:
        try:
            if isinstance(val, list): val = val[0]
            if pd.notna(val) and val != "N/D" and val != "":
                total_s += int(float(val))
        except: pass
    h = total_s // 3600
    m = (total_s % 3600) // 60
    return f"{h:02d}h {m:02d}m"


def converter_escala(val):
    if not val: return 0
    # Limpa emojis e espaços para garantir o "match"
    v = str(val).lower().strip()
    return escala_likert.get(v, 0)
        
# ====
# 1. CONFIGURAÇÃO DA PÁGINA E CSS (UX e Design System)
# ====
# === FONTES OFICIAIS DO SISTEMA ===
# O seletor universal * forca a fonte em TODO elemento, com excecoes para Share Tech Mono.
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700&display=swap');

    /* Uma classe reutilizável para todo HTML customizado */
    .orbitron, .orbitron * {
        font-family: 'Orbitron', monospace !important;
    }

    /* ==== TEMA TIPOGRAFICO - OVERRIDE AGRESSIVO ==== */
    /* O seletor * acima ja forcou Inter em tudo.
       Aqui sobrescrevemos seletivamente onde queremos Orbitron / Share Tech Mono. */

    /* Todos os titulos -> Orbitron (fonte tech da apresentacao) */
    h1, h2, h3, h4, h5, h6,
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4,
    [data-testid="stMarkdownContainer"] h5,
    [data-testid="stMarkdownContainer"] h6,
    .main-title {
        font-family: 'Orbitron', sans-serif !important;
        letter-spacing: 0.02em;
    }

    /* Paragrafos, listas, captions, labels, sidebar, expanders -> Inter */
    p, span, li, label, small,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] *,
    [data-testid="stExpander"] *,
    .sub-title {
        font-family: 'Inter', sans-serif !important;
    }

    /* Tabs (botoes das abas Visao seletiva / Serie historica / Chat) -> Orbitron */
    div[data-testid="stTabs"] button,
    div[data-testid="stTabs"] [role="tab"] {
        font-family: 'Orbitron', sans-serif !important;
        letter-spacing: 0.04em;
    }

    /* Botoes -> Orbitron com peso medio */
    div.stButton > button,
    button[kind="primary"], button[kind="secondary"] {
        font-family: 'Orbitron', sans-serif !important;
        letter-spacing: 0.03em;
    }

    /* Selectbox / inputs -> Inter */
    div[data-baseweb="select"] *, input, div[data-baseweb="textarea"] textarea {
        font-family: 'Inter', sans-serif !important;
    }

    /* Metricas (numeros) -> Share Tech Mono (visual de console tatico) */
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] *,
    code, pre, kbd {
        font-family: 'Share Tech Mono', monospace !important;
        letter-spacing: 0.02em;
    }
    /* O label da metrica fica em Inter */
    div[data-testid="stMetricLabel"] * {
        font-family: 'Inter', sans-serif !important;
    }

    /* DataFrame: cabecalho em Orbitron, celulas em Inter */
    [data-testid="stDataFrame"] thead * {
        font-family: 'Orbitron', sans-serif !important;
    }
    [data-testid="stDataFrame"] tbody * {
        font-family: 'Inter', sans-serif !important;
    }

    /* === FIM DO TEMA TIPOGRAFICO === */


    /* Configurações Globais */
    .block-container { padding-top: 0rem !important; padding-bottom: 1rem !important; z-index: 8; position: relative;}
    header {visibility: hidden;}
    /* Fundo Transparente para revelar o WebGL */
    body { background-color: #050505 !important; }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { 
        background: transparent !important;
        background-color: transparent !important; 
        color: #FFFF; 
        overflow-x: hidden;
    }

    /* Estilo visual do .main-title (cores e gradiente — fonte ja vem do bloco superior) */
    .main-title {
        font-size: 2.2rem;
        font-weight: 500;
        background: linear-gradient(180deg, #FFFF 0%, #BBBB 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1.1;
    }

    /* Estilo visual do .sub-title (cor — fonte ja vem do bloco superior) */
    .sub-title {
        color: #FFD700;
        font-weight: 600;
        font-size: 1.1rem;
        margin-top: 5px;
        margin-bottom: 0;
    }
    
    /* Fundo Estrelado - Luminous Design System */
    .stars-bg {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image:
            radial-gradient(1.5px 1.5px at 20px 30px, #fff, rgba(0,0,0,0)),
            radial-gradient(1.5px 1.5px at 40px 70px, #ffff, rgba(0,0,0,0)),
            radial-gradient(1.5px 1.5px at 50px 160px, #ffff, rgba(0,0,0,0)),
            radial-gradient(2px 2px at 90px 40px, #ffff, rgba(0,0,0,0)),
            radial-gradient(1.5px 1.5px at 130px 80px, #ffff, rgba(0,0,0,0));
        background-size: 200px 200px;
        opacity: 0.45; /* Aumentado para maior visibilidade */
        z-index: 1; /* Acima do fundo preto */
        pointer-events: none;
    }
    /* Caixa de Título Especial */
    .header-box {
        margin: 0 auto !important;
        padding: 20px 30px !important;
        width: 100%; /* Ocupa a largura total da coluna definida */
        text-align: center;
    }

    /* Reset de margens para os titles dentro da caixa gloss */
    .header-box .main-title { margin-bottom: 5px !important; }
    .header-box .sub-title { margin-top: 0 !important; }
    
    /* Animação de Entrada Cinematográfica (Opacidade + Blur) */
    @keyframes fadeInUpBlur {
        0% { opacity: 0; transform: translateY(30px); filter: blur(8px); }
        100% { opacity: 1; transform: translateY(0); filter: blur(0px); }
    }
    .info-card, .stMarkdown, div[data-testid="stMetric"], .stDataFrame, .stPlotlyChart {
        animation: fadeInUpBlur 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) both;
        position: relative; 
        z-index: 10; /* Garante que o conteúdo fique acima dos raios */
    }

    /* (Bloco antigo .main-title/.sub-title removido — definicao unica fica acima com Orbitron + Inter) */
    
    /* Efeito Vidro (Glassmorphism) e Animação de Luz (Sweep) nas Caixas */
    .info-card { 
        background: rgba(30, 30, 30, 0.85);
        backdrop-filter: blur(16px) saturate(180%);
        -webkit-backdrop-filter: blur(15px) saturate(180%);
        border-top: 1px solid rgba(255, 255, 255, 0.15);
        border-left: 1px solid rgba(255, 255, 255, 0.08);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        border-radius: 12px;
        padding: 10px;

        margin-top: 20px;
        margin-bottom: 10px;

        position: relative;
        
        /* MUDANÇA 1: Desce o card (ajuste este número para descer mais ou menos) */
        transform: translateY(60px); 
        
        /* MUDANÇA 2: Garante que o card de vidro fique por cima de qualquer iframe */       
        z-index: 9999 !important; 
        
        overflow: hidden;
        transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .info-card::before {
        content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(249, 115, 22, 0.15), transparent);
        transition: 0.5s; pointer-events: none; z-index: 20;
    }
    .info-card:hover {
        background: rgba(249, 115, 22, 0.08);
        border-color: rgba(249, 115, 22, 0.3);
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(249, 115, 22, 0.15);
    }
    .info-card:hover::before {
        left: 100%; transition: 0.7s ease-in-out;
    }

    /* ═══════════════════════════════════════════════════════════════════════════════
   BOTÕES TOGGLE - GLASSMORPHISM QUADRADO (Design System Integrado)
   ═══════════════════════════════════════════════════════════════════════════════ */

/* Container do botão (para não ficar lateral) */
div.stButton > button[key*="btn_"] {
    /* ─────────────────────────────────────────────────────────────────────────
       GLASSMORPHISM - Idêntico ao design do HTML
       ───────────────────────────────────────────────────────────────────────── */
    
    background: rgba(0, 0, 0, 0.7) !important;
    backdrop-filter: blur(16px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(16px) saturate(180%) !important;
    
    /* Border de Vidro (branco com opacidade sutil) */
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    
    /* ─────────────────────────────────────────────────────────────────────────
       LAYOUT QUADRADO (Não arredondado)
       ───────────────────────────────────────────────────────────────────────── */
    
    border-radius: 0px !important;            /* Quadrado perfeito */
    padding: 0.875rem 1.5rem !important;      /* Espaçamento adequado */
    min-height: 48px !important;              /* Altura mínima */
    
    /* ─────────────────────────────────────────────────────────────────────────
       CORES E TEXTO
       ───────────────────────────────────────────────────────────────────────── */
    
    color: rgba(255, 255, 255, 0.7) !important;  /* Branco sutil */
    font-family: 'Orbitron', monospace !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    
    /* ─────────────────────────────────────────────────────────────────────────
       SOMBRA E EFEITOS
       ───────────────────────────────────────────────────────────────────────── */
    
    box-shadow: 
        0 0 20px rgba(0, 0, 0, 0.5),
        inset 0 1px 1px rgba(255, 255, 255, 0.05) !important;
    
    /* ─────────────────────────────────────────────────────────────────────────
       ANIMAÇÕES
       ───────────────────────────────────────────────────────────────────────── */
    
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
    position: relative;
    overflow: hidden;
    width: 100% !important;
}

/* ─────────────────────────────────────────────────────────────────────────────
   EFEITO SWEEP (Luz passando) - Similar ao design do HTML
   ───────────────────────────────────────────────────────────────────────────── */

div.stButton > button[key*="btn_"]::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(0, 200, 255, 0.1),
        transparent
    );
    transition: left 0.5s ease-in-out;
    pointer-events: none;
    z-index: 20;
}

/* ─────────────────────────────────────────────────────────────────────────────
   HOVER STATE - Borda mais visível, cor mais brilhante
   ───────────────────────────────────────────────────────────────────────────── */

div.stButton > button[key*="btn_"]:hover {
    background: rgba(0, 0, 0, 0.85) !important;     /* Mais denso */
    border-color: rgba(0, 200, 255, 0.4) !important;
    color: #00c8ff !important;                       /* Cyan mais brilhante */
    
    box-shadow: 
        0 0 30px rgba(0, 200, 255, 0.2),           /* Glow cyan */
        0 0 60px rgba(0, 200, 255, 0.05),
        inset 0 1px 1px rgba(255, 255, 255, 0.1) !important;
    
    transform: translateY(-2px) !important;         /* Sobe levemente */
    filter: brightness(1.1);
}

/* Efeito sweep no hover */
div.stButton > button[key*="btn_"]:hover::before {
    left: 100%;
    transition: left 0.7s ease-in-out;
}

/* ─────────────────────────────────────────────────────────────────────────────
   ACTIVE STATE (Clicado)
   ───────────────────────────────────────────────────────────────────────────── */

div.stButton > button[key*="btn_"]:active {
    background: rgba(0, 0, 0, 0.95) !important;
    border-color: rgba(0, 200, 255, 0.3) !important;
    
    box-shadow: 
        0 0 15px rgba(0, 200, 255, 0.1),
        inset 0 2px 4px rgba(0, 0, 0, 0.3) !important;
    
    transform: translateY(0) !important;
    filter: brightness(0.95);
}

/* ─────────────────────────────────────────────────────────────────────────────
   FOCUSED STATE (Teclado)
   ───────────────────────────────────────────────────────────────────────────── */

div.stButton > button[key*="btn_"]:focus {
    outline: none !important;
    border-color: rgba(0, 200, 255, 0.5) !important;
    box-shadow: 
        0 0 40px rgba(0, 200, 255, 0.25),
        inset 0 1px 1px rgba(255, 255, 255, 0.1) !important;
}

/* ─────────────────────────────────────────────────────────────────────────────
   ESTADO DISABLED
   ───────────────────────────────────────────────────────────────────────────── */

div.stButton > button[key*="btn_"]:disabled {
    opacity: 0.5 !important;
    cursor: not-allowed !important;
    background: rgba(0, 0, 0, 0.4) !important;
    border-color: rgba(255, 255, 255, 0.05) !important;
}

/* ─────────────────────────────────────────────────────────────────────────────
   RESPONSIVIDADE
   ───────────────────────────────────────────────────────────────────────────── */

@media (max-width: 768px) {
    div.stButton > button[key*="btn_"] {
        padding: 0.75rem 1.2rem !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.08em !important;
        min-height: 44px !important;
    }
}

@media (max-width: 480px) {
    div.stButton > button[key*="btn_"] {
        padding: 0.65rem 1rem !important;
        font-size: 0.8rem !important;
        min-height: 40px !important;
    }
}

/* ═══════════════════════════════════════════════════════════════════════════════ */

    /* Tabelas e Menus Base */
    [data-testid="stDataFrame"] { background-color: rgba(255, 255, 255, 0.03); border-radius: 8px; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    div[data-testid="stTabs"] button { font-size: 1.2rem; font-weight: bold; transition: color 0.3s;}
    div[data-testid="stTabs"] button[data-baseweb="tab"]:hover { color: #FFD700; }

    /* Cores para o Efeito de Vidro (Agressividade e Receptividade) */
    .card-red { border-left: 4px solid #DDD !important; }
    .card-red:hover { box-shadow: 0 15px 40px rgba(239, 68, 68, 0.25) !important; border-color: rgba(239, 68, 68, 0.6) !important; }
    .card-red::before { background: linear-gradient(90deg, transparent, rgba(239, 68, 68, 0.15), transparent) !important; }

    .card-green { border-left: 4px solid #22c55e !important; }
    .card-green:hover { box-shadow: 0 15px 40px rgba(34, 197, 94, 0.25) !important; border-color: rgba(34, 197, 94, 0.6) !important; }
    .card-green::before { background: linear-gradient(90deg, transparent, rgba(34, 197, 94, 0.15), transparent) !important; }

    /* Media Queries para Mobile Perfeito */
    @media (max-width: 768px) {
        .main-title { font-size: 2rem !important; }
        .sub-title { font-size: 0.95rem !important; }
        div.stButton > button { padding: 0.6rem 1.2rem !important; font-size: 0.95rem !important; }
        .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
        .info-card { padding: 12px; margin-top: 10px; margin-bottom: 10px; }
    }
    /* Puxa o container do efeito Unicorn para cima, para trás do info-card */
    div[data-testid="stHtml"] {
        position: relative;
        /* MUDANÇA 3: Puxa o iframe inteiro para cima. 
           Ajuste esse valor (-150px, -200px, etc) até a marca d'água ficar exatamente debaixo do card */
        margin-top: -150px !important; 
        z-index: 1 !important;
    }
   
</style>

<div class="liquid-blob blob1"></div>
<div class="liquid-blob blob2"></div>
<div class="liquid-blob blob3"></div>
""", unsafe_allow_html=True)


if 'stats_calculados' not in st.session_state: st.session_state['stats_calculados'] = None
#if 'dados_n8n' not in st.session_state: st.session_state['dados_n8n'] = None

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
                background: linear-gradient(
                    180deg,
                    rgba(5,5,5,0.1) 0%,
                    rgba(249,115,22,0.6) 100%
                );
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
# EFEITO UNICORN
# =========================================================

header = """
<!DOCTYPE html>
<html>

<head>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>

<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">

<style>

body {
    margin: 0;
    overflow: hidden;
    font-family: 'Orbitron', sans-serif;
}

h1, h2, h3, h4, h5, h6,
p, span, div, strong {
    font-family: 'Orbitron', sans-serif !important;
}

.header {
    position: relative;
    width: 100%;
    height: 520px;
    border-radius: 20px;
    overflow: hidden;
    background: #0f172a;
}

.unicorn {
    position: absolute;
    inset: 0;
    z-index: 1;
}

.overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(
        180deg,
        rgba(5,5,5,0.1) 0%,
        rgba(249,115,22,0.4) 100%
    );
    z-index: 2;
}

.card-container {
    position: absolute;
    bottom: 20px;
    left: 20px;
    right: 20px;
    z-index: 100;
}

.info-card {
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
}

.info-card p {
    margin: 5px 0;
}

</style>
</head>

<body>

<div class="header">

    <div class="unicorn"
         data-us-project="DUB8qACoMXvy69TzaXJF"
         data-us-scale="1"
         data-us-dpi="1.5">
    </div>

    <div class="overlay"></div>

    <div class="card-container">

    <div class="info-card">

                
        <!-- TITULO PRINCIPAL -->
        <h2 style="
            text-align:center;
            font-size:1,3rem;
            font-weight:600;
            margin-bottom:10px;
            color:white;
            letter-spacing:0.05em;
            font-family:'Orbitron', sans-serif;
        ">
            Sistema de Análise Qualitativa das Negociações
        </h2>

        <!-- SUBTITULO -->
        <p style="
            text-align:center;
            font-size:1rem;
            color:#d1d5db;
            margin-bottom:24px;
            letter-spacing:0.04em;
            font-family:'Orbitron', sans-serif;
        ">
            Estudo das Técnicas Aplicadas
        </p>

        <!-- TEXTO DESCRITIVO -->
        <p style="
            text-align:center;
            font-size:0,8rem;
            font-weight:500;
            color:white;
            line-height:1.6;
        ">
            Negociações em Incidentes Críticos atendidos pelo Grupo de Ações Táticas Especiais.
        </p>

        <p style="
            font-size:0.9rem;
            color:#bbb;
            line-height:1.7;
            margin-top:18px;
        ">
            Os dados são geridos de forma automatizada em nuvem via <strong>Airtable</strong>,
            integrando um motor estatístico multifatorial.
        </p>

    </div>

</div>

<script src="https://cdn.jsdelivr.net/gh/hiunicornstudio/unicornstudio.js@v2.1.6/dist/unicornStudio.umd.js"></script>

<script>

window.addEventListener("load", () => {
    if (window.UnicornStudio) {
        UnicornStudio.init();
    }
});

setTimeout(() => {
    if (window.UnicornStudio) {
        UnicornStudio.init();
    }
}, 800);

</script>

</body>
</html>
"""

components.html(header, height=520, scrolling=False)

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

# ====
# 3. CONEXÃO E NAVEGAÇÃO PRINCIPAL (ABAS)
# ====
# Os dados ja foram carregados acima no "porteiro" (lazy load com session_state).
# Mantemos status_q/status_t aqui para compatibilidade com mensagens de erro abaixo.
status_q = st.session_state.get("status_q", "OK")
status_t = st.session_state.get("status_t", "OK")

st.markdown(
    """
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 1.5px solid #2a2d35 !important;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 9px 22px;
        font-size: 14px;
        color: #8b8fa8;
        border-bottom: 2px solid transparent;
        background: transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #d4a017 !important;
        border-bottom: 2px solid #d4a017 !important;
        font-weight: 500;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #d4d6e0;
        background: rgba(255,255,255,0.03);
    }
    .stTabs [data-baseweb="tab-highlight"] { display: none; }
    .stTabs [data-baseweb="tab-border"]    { display: none; }

    /* TAMANHO DOS TÍTULOS H3 (###) */
    h3 { font-size: 20px !important; font-weight: 500 !important; }
    /* Se quiser ajustar H2 (##) também: */
    h2 { font-size: 22px !important; font-weight: 500 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

if df_quali.empty:
    st.error(f"Erro na conexão com Airtable: {status_q}")
else:
    # INCLUSÃO DA TERCEIRA ABA (Chat Analítico)
    aba_individual, aba_geral, aba_chat = st.tabs(["✔ Visão seletiva", "✔ Série Histórica", "✔ Chat Analítico"])
                 
    # ====
# ABA 1: VISÃO DA NEGOCIAÇÃO SOBRE O INCIDENTE EM ANÁLISE
# ====
with aba_individual:
    st.markdown("<h5 style='color: #FFD700;'> Seleção e Metadados da Ocorrência</h5>", unsafe_allow_html=True)        

    df_quali['Neg_Limpo'] = df_quali['Negociador Principal'].apply(limpar_valor)
    df_quali['Tip_Limpa'] = df_quali['Tipologia'].apply(limpar_valor)
    df_quali['Mod_Limpa'] = df_quali['Modalidade do incidente'].apply(limpar_valor)

    if 'ID' not in df_quali.columns:
        df_quali['ID'] = "APA " + df_quali.index.astype(str)
    df_quali['ID_Busca'] = df_quali['ID'].apply(limpar_id)

    # ── FILTROS ENCADEADOS BIDIRECIONAIS ────────────────────────────────
    col_fi1, col_fi2, col_fi3 = st.columns(3)

    # Lê os valores atuais do session_state (ou default)
    neg_atual = st.session_state.get("f_neg_ind", "Todos")
    tip_atual = st.session_state.get("f_tip_ind", "Todas")
    mod_atual = st.session_state.get("f_mod_ind", "Todas")

    # Contexto para NEGOCIADOR: filtra por tipologia + modalidade selecionadas
    df_ctx_neg = df_quali.copy()
    if tip_atual != "Todas":
        df_ctx_neg = df_ctx_neg[df_ctx_neg['Tip_Limpa'] == tip_atual]
    if mod_atual != "Todas":
        df_ctx_neg = df_ctx_neg[df_ctx_neg['Mod_Limpa'] == mod_atual]

    # Contexto para TIPOLOGIA: filtra por negociador + modalidade selecionados
    df_ctx_tip = df_quali.copy()
    if neg_atual != "Todos":
        df_ctx_tip = df_ctx_tip[df_ctx_tip['Neg_Limpo'] == neg_atual]
    if mod_atual != "Todas":
        df_ctx_tip = df_ctx_tip[df_ctx_tip['Mod_Limpa'] == mod_atual]

    # Contexto para MODALIDADE: filtra por negociador + tipologia selecionados
    df_ctx_mod = df_quali.copy()
    if neg_atual != "Todos":
        df_ctx_mod = df_ctx_mod[df_ctx_mod['Neg_Limpo'] == neg_atual]
    if tip_atual != "Todas":
        df_ctx_mod = df_ctx_mod[df_ctx_mod['Tip_Limpa'] == tip_atual]

    with col_fi1:
        lista_neg = ["Todos"] + sorted(
            df_ctx_neg[df_ctx_neg['Neg_Limpo'] != 'N/D']['Neg_Limpo'].unique().tolist()
        )
        idx_neg = lista_neg.index(neg_atual) if neg_atual in lista_neg else 0
        filtro_neg = st.selectbox("Filtrar por Negociador:", lista_neg, index=idx_neg, key="f_neg_ind")

    with col_fi2:
        lista_tip = ["Todas"] + sorted(
            df_ctx_tip[df_ctx_tip['Tip_Limpa'] != 'N/D']['Tip_Limpa'].unique().tolist()
        )
        idx_tip = lista_tip.index(tip_atual) if tip_atual in lista_tip else 0
        filtro_tip = st.selectbox("Filtrar por Tipologia:", lista_tip, index=idx_tip, key="f_tip_ind")

    with col_fi3:
        lista_mod = ["Todas"] + sorted(
            df_ctx_mod[df_ctx_mod['Mod_Limpa'] != 'N/D']['Mod_Limpa'].unique().tolist()
        )
        idx_mod = lista_mod.index(mod_atual) if mod_atual in lista_mod else 0
        filtro_mod = st.selectbox("Filtrar por Modalidade:", lista_mod, index=idx_mod, key="f_mod_ind")

    # df final com os três filtros aplicados
    df_q_ind = df_quali.copy()
    if filtro_neg != "Todos":
        df_q_ind = df_q_ind[df_q_ind['Neg_Limpo'] == filtro_neg]
    if filtro_tip != "Todas":
        df_q_ind = df_q_ind[df_q_ind['Tip_Limpa'] == filtro_tip]
    if filtro_mod != "Todas":
        df_q_ind = df_q_ind[df_q_ind['Mod_Limpa'] == filtro_mod]

    lista_apas = df_q_ind['ID_Busca'].tolist()

    if not lista_apas:
        st.warning("Nenhuma ocorrência encontrada com estes filtros.")
    else:
        apa_selecionada = st.selectbox(
            "Selecione a ID da APA para análise:",
            lista_apas,
            index=len(lista_apas) - 1,
        )
        df_apa = df_quali[df_quali['ID_Busca'] == apa_selecionada].iloc[0]

        # ── METADADOS ───────────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='info-card'><strong>Data:</strong><br>{limpar_valor(df_apa.get('Data da ocorrência'))}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='info-card'><strong>Modalidade:</strong><br>{limpar_valor(df_apa.get('Modalidade do incidente'))}</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='info-card'><strong>Tipologia:</strong><br>{limpar_valor(df_apa.get('Tipologia'))}</div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='info-card'><strong>Motivação:</strong><br>{limpar_valor(df_apa.get('Motivação'))}</div>", unsafe_allow_html=True)

        c5, c6, c7, c8 = st.columns(4)
        with c5: st.markdown(f"<div class='info-card'><strong>Negociador Principal:</strong><br>{limpar_valor(df_apa.get('Negociador Principal'))}</div>", unsafe_allow_html=True)
        with c6: st.markdown(f"<div class='info-card'><strong>Forma de Transição:</strong><br>{limpar_valor(df_apa.get('Forma de Transição'))}</div>", unsafe_allow_html=True)
        with c7: st.markdown(f"<div class='info-card'><strong>Tempo de Negociação Real:</strong><br>{formatar_tempo_airtable(df_apa.get('Tempo de Negociação Real'))}</div>", unsafe_allow_html=True)
        with c8: st.markdown(f"<div class='info-card'><strong>Tempo de Negociação Tática:</strong><br>{formatar_tempo_airtable(df_apa.get('Tempo de Negociação Tática'))}</div>", unsafe_allow_html=True)

        c9, c10, c11, _ = st.columns(4)
        with c9: st.markdown(f"<div class='info-card'><strong>Resolução:</strong><br>{limpar_valor(df_apa.get('Resolução'))}</div>", unsafe_allow_html=True)
        with c10: st.markdown(f"<div class='info-card'><strong>Uniforme Usado:</strong><br>{limpar_valor(df_apa.get('Uniforme Usado'))}</div>", unsafe_allow_html=True)
        with c11: st.markdown(f"<div class='info-card'><strong>Sexo do Causador:</strong><br>{limpar_valor(df_apa.get('Sexo do Causador'))}</div>", unsafe_allow_html=True)

        st.markdown("---")

        # ====================================================
        # SEÇÃO 1: PERCEPÇÃO DE AGRESSIVIDADE/RECEPTIVIDADE
        # ====================================================
        st.markdown("<h5 style='color: #FFD700;'> Agressividade e Receptividade do causador</h5>", unsafe_allow_html=True)

        col_left, col_center, col_right = st.columns([1, 1, 1])  
        with col_center:
            is_percep_neg = render_toggle_button(
                label="✔️ Abrir Percepção dos Negociadores",
                session_key="percep_neg",
                button_key="btn_percep_neg"
            )

        st.markdown("---")

        # ────────────────────────────────────────────────────────────────
        # BLOCO 1: CONTEÚDO CONDICIONAL DE AGRESSIVIDADE
        # ────────────────────────────────────────────────────────────────
        if is_percep_neg:

            
            tab_pc1, tab_pc2 = st.tabs([
                "✔️ Linha de Tendência",
                "✔️ Visão Geral"                        
            ])
            
            # --- TAB 1: linha tendencia ---
            with tab_pc1:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color: #FFD700; margin-top: 0;'>Linha de tendência individualizada da Percepção de agressividade e receptividade do causador</h5>
                <p style='font-size:1.2rem;color:#ddd;'>
                Percepção dos Negociadores <strong>no início e encerramento da ocorrência</strong>.                 
                </p>
                </div>
                """, unsafe_allow_html=True)
        
        
                colunas_norm = {col: unicodedata.normalize('NFKD', str(col)).encode('ASCII', 'ignore').decode('ASCII').lower() for col in df_apa.index}
                
                def buscar_percepcao(papel, metrica, momento):
                    p_n = unicodedata.normalize('NFKD', str(papel)).encode('ASCII', 'ignore').decode('ASCII').lower()
                    m_n = unicodedata.normalize('NFKD', str(metrica)).encode('ASCII', 'ignore').decode('ASCII').lower()
                    mo_n = unicodedata.normalize('NFKD', str(momento)).encode('ASCII', 'ignore').decode('ASCII').lower()
                    
                    for col_orig, col_n in colunas_norm.items():
                        if p_n in col_n and m_n in col_n and mo_n in col_n:
                            return limpar_valor(df_apa[col_orig])
                    return "N/D"
                
                # Principal
                p_agr_c_txt = buscar_percepcao('Principal', 'Agressividade', 'Chegada')
                p_rec_c_txt = buscar_percepcao('Principal', 'Receptividade', 'Chegada')
                p_agr_e_txt = buscar_percepcao('Principal', 'Agressividade', 'Encerramento')
                p_rec_e_txt = buscar_percepcao('Principal', 'Receptividade', 'Encerramento')

                # Secundário
                s_agr_c_txt = buscar_percepcao('Secundario', 'Agressividade', 'Chegada')
                s_rec_c_txt = buscar_percepcao('Secundario', 'Receptividade', 'Chegada')
                s_agr_e_txt = buscar_percepcao('Secundario', 'Agressividade', 'Encerramento')
                s_rec_e_txt = buscar_percepcao('Secundario', 'Receptividade', 'Encerramento')

                # Líder
                l_agr_c_txt = buscar_percepcao('Lider', 'Agressividade', 'Chegada')
                l_rec_c_txt = buscar_percepcao('Lider', 'Receptividade', 'Chegada')
                l_agr_e_txt = buscar_percepcao('Lider', 'Agressividade', 'Encerramento')
                l_rec_e_txt = buscar_percepcao('Lider', 'Receptividade', 'Encerramento')

                # Numéricos
                p_agr_c_num, p_rec_c_num = converter_escala(p_agr_c_txt), converter_escala(p_rec_c_txt)
                p_agr_e_num, p_rec_e_num = converter_escala(p_agr_e_txt), converter_escala(p_rec_e_txt)
                
                s_agr_c_num, s_rec_c_num = converter_escala(s_agr_c_txt), converter_escala(s_rec_c_txt)
                s_agr_e_num, s_rec_e_num = converter_escala(s_agr_e_txt), converter_escala(s_rec_e_txt)
                
                l_agr_c_num, l_rec_c_num = converter_escala(l_agr_c_txt), converter_escala(l_rec_c_txt)
                l_agr_e_num, l_rec_e_num = converter_escala(l_agr_e_txt), converter_escala(l_rec_e_txt)

                p_escolhida = st.selectbox(
                    "Visualizar evolução sob a perspectiva do:", 
                    ["Negociador Principal", "Negociador Secundário", "Negociador Líder"],
                    key="selecao_negociador_grafico"
                )

                if p_escolhida == "Negociador Principal":
                    v_agr_c, v_rec_c = p_agr_c_num, p_rec_c_num
                    v_agr_e, v_rec_e = p_agr_e_num, p_rec_e_num
                elif p_escolhida == "Negociador Secundário":
                    v_agr_c, v_rec_c = s_agr_c_num, s_rec_c_num
                    v_agr_e, v_rec_e = s_agr_e_num, s_rec_e_num
                else:
                    v_agr_c, v_rec_c = l_agr_c_num, l_rec_c_num
                    v_agr_e, v_rec_e = l_agr_e_num, l_rec_e_num

                plot_agr_c = v_agr_c if v_agr_c > 0 else None
                plot_agr_e = v_agr_e if v_agr_e > 0 else None
                plot_rec_c = v_rec_c if v_rec_c > 0 else None
                plot_rec_e = v_rec_e if v_rec_e > 0 else None

                fig_trend = go.Figure()
                
                fig_trend.add_trace(go.Scatter(
                    x=["Chegada", "Encerramento"], 
                    y=[plot_agr_c, plot_agr_e], 
                    mode='lines+markers', 
                    name='Agressividade', 
                    line=dict(color='#ef4444', width=4), 
                    marker=dict(size=12)
                ))
                
                fig_trend.add_trace(go.Scatter(
                    x=["Chegada", "Encerramento"], 
                    y=[plot_rec_c, plot_rec_e], 
                    mode='lines+markers', 
                    name='Receptividade', 
                    line=dict(color='#22c55e', width=4), 
                    marker=dict(size=12)
                ))
                
                fig_trend.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", 
                    plot_bgcolor="rgba(0,0,0,0)", 
                    font_color="#FFF",
                    yaxis=dict(
                        tickvals=[1, 2, 3, 4, 5], 
                        ticktext=[
                        "1 - Não agressivo <br>não receptivo", 
                        "2 - Neutro", 
                        "3 - Parc. agressivo <br>parc. receptivo",
                        "4 - Agressivo <br>receptivo", 
                        "5 - Muito agressivo <br>muito receptivo"
                        ], 
                        range=[0.5, 5.5] 
                    ),
                    xaxis=dict(title=None), 
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                fig_trend.update_traces(connectgaps=False)
                
                st.plotly_chart(fig_trend, use_container_width=True)

            
            # --- TAB 2: Visão Geral ---
            with tab_pc2:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color: #FFD700; margin-top: 0;'>Percepção Geral dos Negociadores sobre a agressividade e receptividade do causador.</h5>
                <p style='font-size:1.2rem;color:#ddd;'>
                Percepção dos Negociadores <strong>no início e encerramento da ocorrência</strong>.                        
                </p>
                </div>
                """, unsafe_allow_html=True)
            
            
                tab_chegada, tab_encerramento = st.tabs(["🏳 Na Chegada à Ocorrência", "🏴 No Encerramento"])
                
                def render_card(label, valor, cor_classe):
                    return f"<div class='info-card {cor_classe}' style='padding: 12px; margin-top: 5px; margin-bottom: 5px;'><strong style='color: #bbb;'>{label}:</strong><br><span style='font-size: 1.1rem; font-weight: bold;'>{valor}</span></div>"

                with tab_chegada:
                    col_p_c, col_s_c, col_l_c = st.columns(3)
                    with col_p_c:
                        st.markdown("**Negociador Principal**")
                        st.markdown(render_card("Agressividade", p_agr_c_txt, "card-red"), unsafe_allow_html=True)
                        st.markdown(render_card("Receptividade", p_rec_c_txt, "card-green"), unsafe_allow_html=True)
                    with col_s_c:
                        st.markdown("**Negociador Secundário**")
                        st.markdown(render_card("Agressividade", s_agr_c_txt, "card-red"), unsafe_allow_html=True)
                        st.markdown(render_card("Receptividade", s_rec_c_txt, "card-green"), unsafe_allow_html=True)
                    with col_l_c:
                        st.markdown("**Negociador Líder**")
                        st.markdown(render_card("Agressividade", l_agr_c_txt, "card-red"), unsafe_allow_html=True)
                        st.markdown(render_card("Receptividade", l_rec_c_txt, "card-green"), unsafe_allow_html=True)

                with tab_encerramento:
                    col_p_e, col_s_e, col_l_e = st.columns(3)
                    with col_p_e:
                        st.markdown("**Negociador Principal**")
                        st.markdown(render_card("Agressividade", p_agr_e_txt, "card-red"), unsafe_allow_html=True)
                        st.markdown(render_card("Receptividade", p_rec_e_txt, "card-green"), unsafe_allow_html=True)
                    with col_s_e:
                        st.markdown("**Negociador Secundário**")
                        st.markdown(render_card("Agressividade", s_agr_e_txt, "card-red"), unsafe_allow_html=True)
                        st.markdown(render_card("Receptividade", s_rec_e_txt, "card-green"), unsafe_allow_html=True)
                    with col_l_e:
                        st.markdown("**Negociador Líder**")
                        st.markdown(render_card("Agressividade", l_agr_e_txt, "card-red"), unsafe_allow_html=True)
                        st.markdown(render_card("Receptividade", l_rec_e_txt, "card-green"), unsafe_allow_html=True)

                st.markdown("---")

            # ════════════════════════════════════════════════════════════
            # TRANSCRIÇÕES - FORA DO IF DE STATS
            # ════════════════════════════════════════════════════════════
            st.markdown("### ✔ Transcrições")

            if "show_transcricoes" not in st.session_state:
                st.session_state["show_transcricoes"] = False

            label = "▲ Ocultar transcrições" if st.session_state["show_transcricoes"] else "▼ Ver transcrições completas da ocorrência"
            if st.button(label, key="btn_transcricoes"):
                st.session_state["show_transcricoes"] = not st.session_state["show_transcricoes"]

            if st.session_state["show_transcricoes"]:
                st.markdown("**Causador do Incidente:**")
                st.write(limpar_valor(df_apa.get('TRANSCRIÇÃO DO CAUSADOR')))
                st.markdown("**Negociador Principal:**")
                st.write(limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL')))
                st.markdown("**Negociador Secundário:**")
                st.write(limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO')))

        st.markdown("---")

        # ════════════════════════════════════════════════════════════════════════
        # SEÇÃO 2: ANÁLISE DE TÉCNICAS (FREQUÊNCIA + EFETIVIDADE)
        # ════════════════════════════════════════════════════════════════════════

        st.markdown(
            "<h5 style='color: #FFD700;'>Frequência e Efetividade das Técnicas Aplicadas (Nesta APA)</h5>",
            unsafe_allow_html=True
        )

        col_left, col_center, col_right = st.columns([1, 1, 1])

        with col_center:
            is_analise_tecnicas = render_toggle_button(
                label="✔️ Abrir Análise das Técnicas",
                session_key="analise_tecnicas",
                button_key="btn_analise_tecnicas"
            )

        st.markdown("---")

        # ────────────────────────────────────────────────────────────────
        # BLOCO 2: ANÁLISE DE TÉCNICAS COM TABS
        # ────────────────────────────────────────────────────────────────
        if is_analise_tecnicas:
            # === TABS: FREQUÊNCIA + EFETIVIDADE ===
            tab_freq, tab_efet = st.tabs([
                "✔️ Tabela de Frequência",
                "✔️ Efetividade das Técnicas"
            ])

            # ============================================
            # TAB 1: FREQUÊNCIA DAS TÉCNICAS
            # ============================================
            with tab_freq:
                st.markdown("""
                <div style='margin-bottom:15px;'>
                <h5 style='color:#FFD700;'>✔️Frequência das Técnicas Aplicadas</h5>
                <p style='color:#aaa;font-size:0.9rem;'>
                Análise de quantas vezes cada técnica foi utilizada nesta ocorrência.
                </p>
                </div>
                """, unsafe_allow_html=True)

                if st.button("✔ Calcular Frequência de Técnicas", key="btn_freq_tecnicas"):
                    if not df_tec.empty:
                        col_vinculo = next((c for c in df_tec.columns if 'VINCULO' in c.upper() or 'VÍNCULO' in c.upper()), None)
                        
                        if col_vinculo:
                            id_visivel = str(apa_selecionada).strip()
                            df_tec['Vinculo_Str'] = df_tec[col_vinculo].astype(str).str.replace(r"[\[\]'\"]", "", regex=True).str.strip()
                            df_tec_filtrado = df_tec[df_tec['Vinculo_Str'] == id_visivel]
                            
                            if df_tec_filtrado.empty and 'Airtable_Record_ID' in df_apa:
                                id_interno = str(df_apa['Airtable_Record_ID']).strip()
                                df_tec_filtrado = df_tec[df_tec[col_vinculo].astype(str).str.contains(id_interno, na=False, regex=False)]
                            
                            if not df_tec_filtrado.empty:
                                col_tecnica = next((col for col in ['TÉCNICAS', 'TECNICAS', 'TÉCNICA', 'TECNICA'] if col in df_tec_filtrado.columns), None)
                                if col_tecnica:
                                    freq_abs = df_tec_filtrado[col_tecnica].value_counts()
                                    freq_rel = (df_tec_filtrado[col_tecnica].value_counts(normalize=True) * 100).round(1)
                                    df_freq = pd.DataFrame({'Frequência Absoluta': freq_abs, 'Frequência Relativa (%)': freq_rel}).reset_index().rename(columns={col_tecnica: 'Técnica Empregada'})
                                    
                                    st.dataframe(df_freq, use_container_width=True, hide_index=True)
                                    
                                    st.markdown("<h4 style='text-align:center; color: #FFD700; margin-top: 20px;'>Frequências das Técnicas Aplicadas (Treemap)</h4>", unsafe_allow_html=True)
                                    fig_tree = px.treemap(df_freq, path=['Técnica Empregada'], values='Frequência Absoluta', color='Frequência Absoluta', color_continuous_scale='Oranges')
                                    fig_tree.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#FFF", margin=dict(t=10, l=10, r=10, b=10))
                                    
                                    st.session_state['treemap_freq'] = fig_tree
                                    st.success("✅ Treemap gerado!")
                                else:
                                    st.warning("Técnicas encontradas, mas a coluna 'TÉCNICAS' não foi identificada no Airtable.")
                            else:
                                st.info(f"Nenhuma técnica cruzou com a APA atual.")
                        else:
                            st.warning("A coluna de vínculo (ex: 'Vinculo_APA') não foi encontrada na aba de técnicas.")
                    else:
                        st.warning("Tabela de técnicas vazia no Airtable.")

                if st.session_state.get('treemap_freq'):
                    st.plotly_chart(st.session_state['treemap_freq'], use_container_width=True)

            # ============================================
            # TAB 2: EFETIVIDADE DAS TÉCNICAS
            # ============================================
            with tab_efet:
                st.markdown("""
                <div style='margin-bottom:15px;'>
                <h5 style='color:#FFD700;'>✔️ Efetividade das Técnicas</h5>
                <p style='color:#aaa;font-size:0.9rem;'>
                Cruza cada técnica usada com a reação do causador.
                Permite identificar quais abordagens foram efetivas nesta ocorrência.
                </p>
                </div>
                """, unsafe_allow_html=True)

                if st.button("✔ Analisar Efetividade das Técnicas", key="btn_efetividade_tecnicas"):
                    with st.spinner("Cruzando técnicas com reação do causador..."):
                        try:
                            record_id_atual = df_apa.get('Airtable_Record_ID')

                            if not record_id_atual:
                                st.warning("⚠️ ID do registro não encontrado.")
                            else:
                                df_tec = st.session_state.get("df_tec", pd.DataFrame())

                                if df_tec.empty:
                                    st.warning("⚠️ Tabela de técnicas não carregada. Atualize os dados.")
                                else:
                                    def vinculo_contem(val, record_id):
                                        if isinstance(val, list):
                                            return record_id in val
                                        return str(val) == record_id

                                    mask = df_tec['Vinculo_APA'].apply(
                                        lambda x: vinculo_contem(x, record_id_atual)
                                    )
                                    df_tec_apa = df_tec[mask].copy()

                                    if df_tec_apa.empty:
                                        st.info("Nenhuma técnica registrada para esta ocorrência.")
                                    else:
                                        def normalizar_reacao(val):
                                            if val is None:
                                                return None
                                            s = str(val).strip()
                                            if s in ["-1", "-1.0", "🔴 Reação Negativa", "Reação Negativa"]:
                                                return -1
                                            elif s in ["0", "0.0", "⚪ Reação Neutra", "Reação Neutra"]:
                                                return 0
                                            elif s in ["1", "1.0", "🟢 Reação Positiva", "Reação Positiva"]:
                                                return 1
                                            else:
                                                return None

                                        col_reacao = None
                                        for c in ['ATITUDE DO CAUSADOR', 'Atitude do Causador', 'atitude_causador']:
                                            if c in df_tec_apa.columns:
                                                col_reacao = c
                                                break

                                        col_tecnica = None
                                        for c in ['TÉCNICAS', 'Técnicas', 'tecnicas']:
                                            if c in df_tec_apa.columns:
                                                col_tecnica = c
                                                break

                                        if not col_tecnica:
                                            st.warning("⚠️ Coluna TÉCNICAS não encontrada.")
                                        else:
                                            if col_reacao:
                                                df_tec_apa['_reacao_num'] = df_tec_apa[col_reacao].apply(normalizar_reacao)
                                            else:
                                                df_tec_apa['_reacao_num'] = None

                                            resumo = []
                                            for tecnica, grupo in df_tec_apa.groupby(col_tecnica):
                                                total    = len(grupo)
                                                positivo = (grupo['_reacao_num'] == 1).sum()
                                                neutro   = (grupo['_reacao_num'] == 0).sum()
                                                negativo = (grupo['_reacao_num'] == -1).sum()
                                                inaud    = grupo['_reacao_num'].isna().sum()

                                                observados = positivo + neutro + negativo
                                                if observados > 0:
                                                    score = round(((positivo - negativo) / observados) * 100, 1)
                                                else:
                                                    score = None

                                                resumo.append({
                                                    "Técnica":        tecnica,
                                                    "Total":          total,
                                                    "🟢 Positiva":    int(positivo),
                                                    "⚪ Neutra":      int(neutro),
                                                    "🔴 Negativa":    int(negativo),
                                                    "❓ Inaudível":   int(inaud),
                                                    "Score (%)":      score
                                                })

                                            df_resumo = pd.DataFrame(resumo)
                                            df_resumo = df_resumo.sort_values("Score (%)", ascending=False, na_position='last')

                                            st.session_state['tecnicas_analisadas'] = df_resumo
                                            st.success(f"✅ {len(df_resumo)} técnicas analisadas!")

                        except Exception as e:
                            st.error(f"Erro ao analisar técnicas: {str(e)[:80]}")

                # ✅ EXIBIÇÃO DOS RESULTADOS
                if st.session_state.get('tecnicas_analisadas') is not None:
                    df_resumo = st.session_state['tecnicas_analisadas']

                    total_usos     = int(df_resumo["Total"].sum())
                    total_positivo = int(df_resumo["🟢 Positiva"].sum())
                    total_neutro   = int(df_resumo["⚪ Neutra"].sum())
                    total_negativo = int(df_resumo["🔴 Negativa"].sum())
                    observados_total = total_positivo + total_neutro + total_negativo
                    score_geral    = round(((total_positivo - total_negativo) / max(1, observados_total)) * 100, 1)

                    st.markdown("### ✔️ Resumo Geral")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total de Usos", total_usos)
                    with col2:
                        st.metric("🟢 Positivas", total_positivo)
                    with col3:
                        st.metric("🔴 Negativas", total_negativo)
                    with col4:
                        st.metric("Score Geral", f"{score_geral:+.1f}%")

                    st.markdown("### ✔️ Efetividade por Técnica")
                    st.dataframe(
                        df_resumo,
                        use_container_width=True,
                        hide_index=True
                    )

                    st.markdown("### ✔️ Distribuição de Reações por Técnica")
                    try:
                        import plotly.graph_objects as go

                        tecnicas   = df_resumo["Técnica"].tolist()
                        positivos  = df_resumo["🟢 Positiva"].tolist()
                        neutros    = df_resumo["⚪ Neutra"].tolist()
                        negativos  = df_resumo["🔴 Negativa"].tolist()

                        fig_barras = go.Figure()

                        fig_barras.add_trace(go.Bar(
                            name="🟢 Positiva",
                            x=tecnicas, y=positivos,
                            marker_color="#10b981"
                        ))
                        fig_barras.add_trace(go.Bar(
                            name="⚪ Neutra",
                            x=tecnicas, y=neutros,
                            marker_color="#6b7280"
                        ))
                        fig_barras.add_trace(go.Bar(
                            name="🔴 Negativa",
                            x=tecnicas, y=negativos,
                            marker_color="#ef4444"
                        ))

                        fig_barras.update_layout(
                            barmode="stack",
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#fff"),
                            legend=dict(
                                font=dict(color="#fff"),
                                bgcolor="rgba(0,0,0,0.4)"
                            ),
                            xaxis=dict(
                                tickfont=dict(color="#FFD700"),
                                gridcolor="#333"
                            ),
                            yaxis=dict(
                                tickfont=dict(color="#aaa"),
                                gridcolor="#333"
                            ),
                            height=420,
                            margin=dict(t=20, b=120, l=40, r=40)
                        )

                        st.plotly_chart(fig_barras, use_container_width=True)

                    except Exception as e:
                        st.error(f"Erro ao gerar gráfico: {str(e)[:80]}")

                    # ── NARRATIVA OPERACIONAL ────────────────────────────
                    st.markdown("---")
                    st.markdown("### ✔️ Leitura Operacional")

                    df_com_score = df_resumo[df_resumo["Score (%)"].notna()]
                    
                    if not df_com_score.empty:
                        score_maximo = df_com_score["Score (%)"].max()
                        tecnicas_maximas = df_com_score[df_com_score["Score (%)"] == score_maximo]
                        
                        if len(tecnicas_maximas) == 1:
                            melhor = tecnicas_maximas.iloc[0]
                            txt_melhor = (
                                f"✅ <strong>Técnicas mais efetivas:</strong> {melhor['Técnica']} "
                                f"— Score {melhor['Score (%)']:+.1f}% "
                                f"({int(melhor['🟢 Positiva'])} positivo / {int(melhor['Total'])} usos)"
                            )
                        else:
                            tecnicas_nomes = ", ".join(tecnicas_maximas['Técnica'].tolist())
                            txt_melhor = (
                                f"✅ <strong>Técnicas mais efetivas (empate):</strong> {tecnicas_nomes} "
                                f"— Score {score_maximo:+.1f}%"
                            )
                        
                        st.markdown(f"""
                        <div style='background:rgba(16,185,129,0.08);padding:12px;border-radius:8px;border-left:3px solid #10b981;margin-bottom:10px;'>
                        <p style='color:#ddd;font-size:0.9rem;margin:0;'>
                        {txt_melhor}
                        </p>
                        </div>
                        """, unsafe_allow_html=True)

                    if not df_com_score.empty:
                        score_minimo = df_com_score["Score (%)"].min()
                        tecnicas_minimas = df_com_score[df_com_score["Score (%)"] == score_minimo]
                        
                        if len(tecnicas_minimas) == 1:
                            pior = tecnicas_minimas.iloc[0]
                            txt_pior = (
                                f"⚠️ <strong>Técnica menos efetiva:</strong> {pior['Técnica']} "
                                f"— Score {pior['Score (%)']:+.1f}% "
                                f"({int(pior['🔴 Negativa'])} negativo / {int(pior['Total'])} usos)"
                            )
                        else:
                            tecnicas_nomes = ", ".join(tecnicas_minimas['Técnica'].tolist())
                            txt_pior = (
                                f"⚠️ <strong>Técnicas menos efetivas (empate):</strong> {tecnicas_nomes} "
                                f"— Score {score_minimo:+.1f}%"
                            )
                        
                        st.markdown(f"""
                        <div style='background:rgba(239,68,68,0.08);padding:12px;border-radius:8px;border-left:3px solid #ef4444;margin-bottom:10px;'>
                        <p style='color:#ddd;font-size:0.9rem;margin:0;'>
                        {txt_pior}
                        </p>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown("### ✔️ Efetividade Geral do Repertório Técnico")

                    media_geral = round(df_com_score["Score (%)"].mean(), 1) if not df_com_score.empty else 0

                    st.markdown(f"""
                    <div style='background:rgba(255,215,0,0.06);padding:12px;border-radius:8px;border:1px solid rgba(255,215,0,0.15);margin-bottom:15px;'>
                    <p style='font-size:0.85rem;color:#FFD700;margin:0 0 8px 0;'>
                    <strong>ℹ️ Como é medido:</strong>
                    </p>
                    <p style='font-size:0.85rem;color:#ddd;margin:0;line-height:1.6;'>
                    Efetividade Geral = Média dos scores de todas as técnicas<br>
                    Score de cada técnica = (positivas - negativas) / observadas × 100%<br>
                    <strong>Baseline desta análise:</strong> {media_geral:+.1f}%
                    </p>
                    </div>
                    """, unsafe_allow_html=True)

                    if score_geral >= 50:
                        cor = "🟢"
                        status = "ÓTIMA"
                        explicacao = (
                            f"O repertório técnico teve {score_geral:+.1f}% de efetividade geral "
                            f"(acima do baseline de {media_geral:+.1f}%). "
                            "Isso significa que positivas superaram negativas de forma significativa. "
                            "Indicativo de estratégia técnica bem-sucedida nesta ocorrência."
                        )
                    elif score_geral >= 0:
                        cor = "🟡"
                        status = "MODERADA"
                        explicacao = (
                            f"O repertório técnico teve {score_geral:+.1f}% de efetividade geral "
                            f"(próximo ao baseline de {media_geral:+.1f}%). "
                            "Positivas e negativas estão equilibradas. "
                            "Há oportunidade de aprimoramento — algumas técnicas funcionaram melhor que outras."
                        )
                    else:
                        cor = "🔴"
                        status = "FRACA"
                        explicacao = (
                            f"O repertório técnico teve {score_geral:+.1f}% de efetividade geral "
                            f"(abaixo do baseline de {media_geral:+.1f}%). "
                            "Negativas superaram positivas. "
                            "Indicativo de mismatch entre técnicas empregadas e dinâmica do causador."
                        )

                    st.markdown(f"""
                    <div style='background:rgba(0,0,0,0.3);padding:14px;border-radius:8px;border-left:4px solid {"#10b981" if score_geral >= 50 else "#f59e0b" if score_geral >= 0 else "#ef4444"};margin-bottom:15px;'>
                    <p style='font-size:0.95rem;color:#ddd;margin:0;'>
                    {cor} <strong>Efetividade Geral: {status}</strong><br><br>
                    {explicacao}
                    </p>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("### ✔️ Contexto Comparativo")

                    st.markdown(f"""
                    <p style='font-size:0.9rem;color:#aaa;line-height:1.6;'>
                    <strong>Técnicas com score positivo:</strong> {(df_com_score["Score (%)"] > 0).sum()} de {len(df_com_score)}<br>
                    <strong>Técnicas com score negativo:</strong> {(df_com_score["Score (%)"] < 0).sum()} de {len(df_com_score)}<br>
                    <strong>Técnicas neutras (0%):</strong> {(df_com_score["Score (%)"] == 0).sum()} de {len(df_com_score)}<br>
                    <strong>Variação entre técnicas:</strong> {df_com_score["Score (%)"].max() - df_com_score["Score (%)"].min():.1f} pontos percentuais<br>
                    <strong>Confiabilidade (volume de usos):</strong> {int(df_resumo["Total"].sum())} técnicas empregadas no total
                    </p>
                    """, unsafe_allow_html=True)

                    if score_geral >= 50:
                        txt_geral = "✅ Repertório técnico com boa efetividade geral nesta ocorrência."
                    elif score_geral >= 0:
                        txt_geral = "⚠️ Repertório técnico com efetividade moderada — oportunidade de melhoria."
                    else:
                        txt_geral = "🔴 Repertório técnico com baixa efetividade — maioria das técnicas gerou reação negativa."

                    st.info(txt_geral)

        st.markdown("---")

        # PRÓXIMA SEÇÃO (ANÁLISE SEMÂNTICA, etc)
        
               
        st.markdown("""
        <h3 style='color: #FFD700;'>✔ Análise Semântica </h3>
        <p style='color: #aaa; font-size: 0.95rem; margin-top: -10px;'>
        <strong>O que o causador REALMENTE sente, quer e teme.</strong> 
        Enquanto Similitude conta palavras repetidas, Semântica lê entre as linhas: intenções escondidas, 
        gatilhos emocionais e pontos de alavanca para resolução.
        </p></p>
        """, unsafe_allow_html=True)

        # --- INÍCIO DO BLOCO DE EXPLICAÇÃO ---
        if "show_explicacao" not in st.session_state:
            st.session_state["show_explicacao"] = False

        label_btn = "▲ Ocultar Guia" if st.session_state["show_explicacao"] else "▼ Entenda como ler a Análise"
        if st.button(label_btn, key="btn_explicacao_semantica"):
            st.session_state["show_explicacao"] = not st.session_state["show_explicacao"]

        if st.session_state["show_explicacao"]:

            tab_pratica, tab_framework, tab_ngramas, tab_limitacoes = st.tabs([
                "✔ Aplicação Prática",
                "✔ Os Três Vetores",
                "✔ Padrões & Fixações",
                "✔ Limitações"
            ])

            with tab_pratica:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color:#FFD700;margin-top:0;'>Como ler os dados na prática?</h5>
                <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                A análise semântica responde uma pergunta simples: <strong>"O que esse sujeito está vivendo agora?"</strong>
                </p>
                <hr style='border-color:#444;margin:12px 0;'>
                <h5 style='color:#FFD700;'>📌 Passo 1: Identifique o ESTADO EMOCIONAL</h5>
                <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                <strong>Procure por:</strong> Quanto de <strong>medo, raiva, desespero</strong> o causador está carregando?<br><br>
                • <em>"vou me matar"</em> + <em>"não aguento mais"</em> → Desespero acima do limite (risco iminente)<br>
                • <em>"ninguém entra aqui"</em> + <em>"vou atirar"</em> → Raiva/defesa (hostilidade)<br>
                • <em>"perdi tudo"</em> + <em>"ninguém se importa"</em> → Abandono/desesperança (depressão)<br><br>
                <strong>Por quê?</strong> Segundo William Ury (Harvard), antes de negociar, você precisa entender o <u>estado de espírito</u> 
                da outra parte. Emoção descontrolada = impossível raciocínio lógico.
                </p>
                <hr style='border-color:#444;margin:12px 0;'>
                <h5 style='color:#FFD700;'>📌 Passo 2: Identifique as EXIGÊNCIAS REAIS</h5>
                <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                <strong>Procure por:</strong> O que esse sujeito <strong>quer concretamente</strong>? (não apenas ameaça)<br><br>
                • <em>"quero a imprensa aqui"</em> → Exigência instrumental (segurança/poder/reconhecimento)<br>
                • <em>"Quero que a imprensa saiba o que aconteceu"</em> → Exigência moral (dignidade)<br>
                • <em>"preciso de dinheiro"</em> → Exigência material (sobrevivência)<br><br>
                <strong>Por quê?</strong> Segundo William Ury (Harvard Negotiation Project), 
                reconhecer a legitimidade da exigência (mesmo que você não possa cumprir) 
                reduz hostilidade. O FBI e Chris Voss confirmam isso através de 
                <u>escuta ativa</u> em negociações críticas. 
                (mesmo que você não possa cumprir) reduz hostilidade. O causador quer ser OUVIDO, não necessariamente atendido.
                </p>
                <hr style='border-color:#444;margin:12px 0;'>
                <h5 style='color:#FFD700;'>📌 Passo 3: Encontre os GANCHOS PARA DESESCALADA</h5>
                <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                <strong>Procure por:</strong> Onde há <strong>abertura, ambivalência, vínculo</strong>?<br><br>
                • <em>"me ajuda"</em> (mesmo que velado) → Pedido de ajuda (ponto de conexão)<br>
                • <em>"fala comigo"</em> → Busca por contato (rapport possível)<br>
                • <em>"minha filha"</em> → Vínculo afetivo (alavanca para mudança de decisão)<br><br>
                <strong>Por quê?</strong> O Manual do FBI de Negociação enfatiza que <u>pequenos sinais de cooperação</u> 
                devem ser amplificados. "Minha filha" não é só uma palavra — é a ponte entre desespero e vida.
                </p>
                <hr style='border-color:#444;margin:12px 0;'>
                <h5 style='color:#FFD700;'>📌 Passo 4: Analise a ABORDAGEM DO NEGOCIADOR</h5>
                <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                <strong>Procure por:</strong> Como o negociador respondeu? Conseguiu <strong>sincronizar?</strong><br><br>
                • Se Causador diz <em>"ninguém me entende"</em> e Negociador responde <em>"entendo sua dor"</em> → Conversa bem dirigida ✅<br>
                • Se Causador diz <em>"quero a imprensa"</em> e Negociador ignora → Falta de legitimação ❌<br>
                • Se Negociador repete <em>"fica calmo"</em> 10 vezes → Não está ouvindo, está impondo ❌<br><br>
                <strong>Por quê?</strong> Harvard explica que <u>validar a emoção da outra parte</u> 
                não significa concordar com a ação — é reconhecer o estado emocional como real.
                </p>
                </div>
                """, unsafe_allow_html=True)

            with tab_framework:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color:#FFD700;margin-top:0;'>Os Três Vetores Explicados (e como interpretar)</h5>
                <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                Pense nos vetores como três forças que estão em <strong>cabo de guerra</strong> dentro do causador.
                </p>
                <hr style='border-color:#444;margin:12px 0;'>
                <div style='margin:12px 0;padding:12px;border-radius:10px;background:rgba(239,68,68,0.08);border-left:4px solid #ef4444;'>
                <h5 style='color:#ef4444;margin-top:0;'>🔴 RISCO OBSERVADO — "Quanto de ameaça real há aqui?"</h5>
                <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                Mede a <strong>densidade de linguagem agressiva/suicida</strong> no discurso do causador.<br><br>
                <strong>Exemplos de alto risco:</strong><br>
                • <em>"vou matar você"</em> (declaração direta)<br>
                • <em>"tenho uma arma"</em> (capacidade + intenção)<br>
                • <em>"quero morrer"</em> (risco para si mesmo)<br><br>
                <strong>Interpretação para APA:</strong><br>
                Se Risco Observado = 15% → Ameaça verbalizada, mas sem densidade alta<br>
                Se Risco Observado = 25%+ → Linguagem carregada, escalada provável se negligenciada<br><br>
                <strong>O que o negociador deveria fazer?</strong><br>
                Alto risco = mudar de abordagem RÁPIDO. Deixar o causador falar (validar) antes de oferecer soluções.
                </p>
                </div>
                <hr style='border-color:#444;margin:12px 0;'>
                <div style='margin:12px 0;padding:12px;border-radius:10px;background:rgba(16,185,129,0.08);border-left:4px solid #10b981;'>
                <h5 style='color:#10b981;margin-top:0;'>🟢 ABERTURA OBSERVADA — "Tem esperança aqui? Há ponte de desescalada?"</h5>
                <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                Mede <strong>sinais de cooperação, rendição, pedido de ajuda</strong> (velado ou não) no causador.<br><br>
                <strong>Exemplos de alta abertura:</strong><br>
                • <em>"me ajuda"</em> (pedido direto)<br>
                • <em>"minha filha está aqui"</em> (reconhecimento de terceiro, responsabilidade)<br>
                • <em>"pode entrar"</em> (permissão = abandono da posição hostil)<br><br>
                <strong>Interpretação para APA:</strong><br>
                Se Abertura = 5% → Causador muito fechado, difícil entrada. Precisa mais validação.<br>
                Se Abertura = 15%+ → Janela de oportunidade aberta. Negociador pode começar a propor.<br><br>
                <strong>O que o negociador deveria fazer?</strong><br>
                Sinais de abertura = AMPLIFICAR. "Você pediu ajuda? Estou aqui para isso." (FBI)
                </p>
                </div>
                <hr style='border-color:#444;margin:12px 0;'>
                <div style='margin:12px 0;padding:12px;border-radius:10px;background:rgba(251,146,60,0.08);border-left:4px solid #f97316;'>
                <h5 style='color:#f97316;margin-top:0;'>🟡 RAIZ OBSERVADA — "Por que ele está assim? Qual é a verdadeira causa?"</h5>
                <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                Mede <strong>gatilhos emocionais, perdas, traumas</strong> que explicam o estado atual.<br><br>
                <strong>Exemplos de raiz clara:</strong><br>
                • <em>"perdi meu emprego"</em> (causa: desespero financeiro)<br>
                • <em>"ela me traiu"</em> (causa: abandono/humilhação)<br>
                • <em>"ninguém se importa comigo"</em> (causa: isolamento/rejeição)<br><br>
                <strong>Interpretação para APA:</strong><br>
                Se Raiz = 8% → Causador talvez tenha gatilho recente ou bem localizado.<br>
                If Raiz = 12%+ → Acúmulo de perdas, histórico de trauma. Mais difícil de resolver rápido.<br><br>
                <strong>O que o negociador deveria fazer?</strong><br>
                Ury diz: "Separe a pessoa do problema." A raiz é o PROBLEMA. Validá-la não é concordar, é RECONHECER.<br>
                Ex: "Entendo que perder o emprego é devastador. Mas matar não resolve. Vamos pensar em saídas."
                </p>
                </div>
                <hr style='border-color:#444;margin:12px 0;'>
                <h5 style='color:#FFD700;'>⚖️ COMO OS TRÊS TRABALHAM JUNTOS</h5>
                <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                <strong>Cenário 1: Alto Risco + Baixa Abertura + Raiz Clara</strong><br>
                → Sujeito desesperado (raiz conhecida) mas barricado (nenhuma ponte). Técnica: Validar a raiz + oferecer saída.
                <br><br>
                <strong>Cenário 2: Alto Risco + Alta Abertura + Raiz Clara</strong><br>
                → Sujeito em crise mas aberto à ajuda. JANELA CRÍTICA. Técnica: Rápida proposição de alternativa.
                <br><br>
                <strong>Cenário 3: Baixo Risco + Alta Abertura + Raiz Clara</strong><br>
                → Sujeito já está em conversação. Técnica: Escuta ativa + proposição colaborativa.
                </p>
                </div>
                """, unsafe_allow_html=True)

            with tab_ngramas:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color:#FFD700;margin-top:0;'>Padrões Repetidos & Loop Cognitivo</h5>
                <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                <strong>N-gramas:</strong> Frases de 2-3 palavras que o sujeito repete obessivamente.
                </p>
                <hr style='border-color:#444;margin:12px 0;'>
                <h5 style='color:#FFD700;'>O que significa?</h5>
                <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                Sob estresse extremo, o cérebro entra em <strong>loop cognitivo</strong>. 
                A frase repetida é o <u>mantra da crise</u> — o que o sujeito está preso em pensar.<br><br>
                <strong>Exemplos e interpretações:</strong><br><br>
                • <em>"não aguento mais"</em> (repetido 5+ vezes)<br>
                &nbsp;&nbsp; → Estado: Exaustão emocional severa. Risco: Iminente (suicida ou agressivo descontrolado)<br>
                &nbsp;&nbsp; → Técnica: Validar o esgotamento, oferecer repouso/alívio imediato<br><br>
                • <em>"cadê a imprensa"</em> (repetido 3+ vezes)<br>
                &nbsp;&nbsp; → Estado: Fixação instrumental. O sujeito quer RECONHECIMENTO público<br>
                &nbsp;&nbsp; → Técnica: Negociar sobre o que pode ser oferecido (não prometa imprensa se não há)<br><br>
                • <em>"fica calmo"</em> (negociador repetindo)<br>
                &nbsp;&nbsp; → Estado: Negociador não está OUVINDO. Está tentando impor.<br>
                &nbsp;&nbsp; → Técnica: MUDAR DE ABORDAGEM. Perguntar em vez de ordenar<br><br>
                </p>
                <hr style='border-color:#444;margin:12px 0;'>
                <h5 style='color:#FFD700;'>Nuvem de Palavras — O que cada interlocutor REALMENTE está focando</h5>
                <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                A nuvem mostra visualmente o <strong>universo mental</strong> de cada um.<br><br>
                <strong>Leitura prática:</strong><br>
                Se a nuvem do Causador tem <em>"arma, polícia, morte"</em> gigantes → Fixação em escalada<br>
                Se a nuvem tem <em>"filha, família, vida"</em> grandes → Ambivalência (quer viver mas está preso no medo)<br>
                Se a nuvem do Negociador tem <em>"calma, tranquilo, relaxa"</em> → Talvez não esteja validando o real estado emocional<br><br>
                <strong>Comparação:</strong><br>
                Nuvem do Causador com "morte" grande + Nuvem do Negociador com "vida" grande = Boa direção<br>
                Nuvem do Causador com "morte" grande + Nuvem do Negociador com "relaxa" grande = Desconexão
                </p>
                <div style='margin-top:12px;padding:12px;border-radius:10px;background:rgba(255,215,0,0.06);border:1px solid rgba(255,215,0,0.15);'>
                <p style='font-size:0.9rem;color:#ddd;margin:0;line-height:1.6;'>
                <strong>Atenção:</strong> Um padrão repetido não é risco por si. É um <u>sinal de fixação mental</u>. 
                Pode ser esperança ("vou me entregar"), desespero ("vou morrer") ou instrumento ("exijo reconhecimento").
                </p>
                </div>
                </div>
                """, unsafe_allow_html=True)

            with tab_limitacoes:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color:#FFD700;margin-top:0;'>Limitações — O que o sistema NÃO consegue ver</h5>
                <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                Esta é uma <strong>ferramenta de leitura</strong>, não bola de cristal. Os números descrevem o que foi DITO, 
                não o que vai acontecer.
                </p>
                <hr style='border-color:#444;margin:12px 0;'>
                <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                ❌ <strong>Não vê o histórico do sujeito:</strong> Esse é o 1º suicida ou o 5º? Faz diferença.<br>
                ❌ <strong>Não vê o contexto real:</strong> Há reféns? Há arma de verdade? O sistema não sabe.<br>
                ❌ <strong>Não vê gírias/ironia:</strong> <em>"Vou me matar de rir"</em> aparece como risco, mas é brincadeira.<br>
                ❌ <strong>Não vê o tom de voz:</strong> <em>"vou sair"</em> dito com calma é diferente de grito.<br>
                ❌ <strong>Não vê interrupções:</strong> Se o transcrição está quebrada, a análise fica incompleta.
                </p>
                <div style='margin-top:12px;padding:12px;border-radius:10px;background:rgba(255,215,0,0.06);border:1px solid rgba(255,215,0,0.15);'>
                <p style='font-size:0.9rem;color:#ddd;margin:0;line-height:1.6;'>
                <strong>Regra de ouro para APA:</strong> Use estes dados + seu julgamento + contexto operacional. 
                O sistema ILUMINA. A decisão é HUMANA.
                </p>
                </div>
                </div>
                """, unsafe_allow_html=True)

        # --- FIM DO BLOCO DE EXPLICAÇÃO ---


        st.markdown(
            "<h5 style='color: #FFD700;'>Análise Temática e Detalhes da Transcrição (Nesta APA)</h5>",
            unsafe_allow_html=True
        )

        col_left, col_center, col_right = st.columns([1, 1, 1])

        with col_center:
            is_analise_tematica = render_toggle_button(
                label="✔️ Abrir Análise Temática",
                session_key="analise_tematica",
                button_key="btn_analise_tematica"
            )

        st.markdown("---")

        if is_analise_tematica:
        
            def extrair_temas_e_metricas(resultado_lista):
                """
                Separa os temas das métricas APA.
                Métricas começam com ** e contêm: Risco, Abertura, Raiz, Intensidade, Direção, Volatilidade
                """
                temas = []
                metricas = []
                
                for linha in resultado_lista:
                    if any(keyword in linha for keyword in ['Risco Observado', 'Abertura Observada', 'Raiz Observada', 
                                                            'Intensidade Geral', 'Direção:', 'Volatilidade', 
                                                            'Classificação APA', 'Leitura Operacional']):
                        metricas.append(linha)
                    else:
                        temas.append(linha)
                
                return temas, metricas

            

            
            with st.spinner("Processando padrões mentais, temas dominantes e gerando nuvens de palavras..."):
                try:
                    texto_c  = analise.limpar_valor(df_apa.get('TRANSCRIÇÃO DO CAUSADOR', ''))
                    texto_np = analise.limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL', ''))
                    texto_ns = analise.limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO', ''))
                    texto_total = f"{texto_c} {texto_np} {texto_ns}"

                    resolucao_raw = analise.limpar_valor(
                        df_apa.get('Resolução', df_apa.get('RESOLUÇÃO', df_apa.get('resolucao', '')))
                    ).strip()

                    # ✅ CORRIGIDO: detecta os 3 tipos reais GATE/PMESP
                    resolucao_norm = resolucao_raw.lower()
                    if not resolucao_norm:
                        resolucao_tipo = "desconhecida"
                    elif "tática" in resolucao_norm or "tatica" in resolucao_norm:
                        resolucao_tipo = "Negociação Tática"
                    elif "real" in resolucao_norm or "negocia" in resolucao_norm:
                        resolucao_tipo = "Negociação Real"
                    elif "interven" in resolucao_norm:
                        resolucao_tipo = "Intervenção"
                    else:
                        resolucao_tipo = "desconhecida"

                    # ✅ NOVO: extrair tempos do Airtable com segurança
                    def extrair_tempo(valor):
                        try:
                            return int(float(str(analise.limpar_valor(valor)).replace(',', '.') or 0))
                        except Exception:
                            return 0

                    tempo_neg_real = extrair_tempo(
                        df_apa.get('TEMPO NEGOCIAÇÃO REAL',
                        df_apa.get('Tempo Negociação Real',
                        df_apa.get('tempo_negociacao_real', 0)))
                    )
                    tempo_neg_tatica = extrair_tempo(
                        df_apa.get('TEMPO NEGOCIAÇÃO TÁTICA',
                        df_apa.get('Tempo Negociação Tática',
                        df_apa.get('tempo_negociacao_tatica', 0)))
                    )

                    # ✅ NOVO: Separar temas e métricas
                    resultado_total = analise.extrair_topicos_ngrams(texto_total, resolucao_tipo=resolucao_tipo) if len(texto_total) > 10 else ["Texto insuficiente"]
                    resultado_c = analise.extrair_topicos_ngrams(texto_c, resolucao_tipo=resolucao_tipo) if len(texto_c) > 10 else ["Texto insuficiente"]
                    resultado_np = analise.extrair_topicos_ngrams(texto_np, resolucao_tipo=resolucao_tipo) if len(texto_np) > 10 else ["Texto insuficiente"]
                    resultado_ns = analise.extrair_topicos_ngrams(texto_ns, resolucao_tipo=resolucao_tipo) if len(texto_ns) > 10 else ["Texto insuficiente"]

                    temas_total, metricas_total = extrair_temas_e_metricas(resultado_total)
                    temas_c, metricas_c = extrair_temas_e_metricas(resultado_c)
                    temas_np, metricas_np = extrair_temas_e_metricas(resultado_np)
                    temas_ns, metricas_ns = extrair_temas_e_metricas(resultado_ns)

                    st.session_state['stats_calculados'] = {
                        "temas":       temas_total,
                        "temas_c":     temas_c,
                        "temas_np":    temas_np,
                        "temas_ns":    temas_ns,
                        "wc_c":        analise.gerar_wordcloud(texto_c)  if len(texto_c)  > 5 else None,
                        "wc_np":       analise.gerar_wordcloud(texto_np) if len(texto_np) > 5 else None,
                        "wc_ns":       analise.gerar_wordcloud(texto_ns) if len(texto_ns) > 5 else None,
                        "texto_c_raw":      texto_c,
                        "texto_np_raw":     texto_np,
                        "texto_ns_raw":     texto_ns,
                        "resolucao_tipo":   resolucao_tipo,
                        "resolucao_raw":    resolucao_raw,
                        "tempo_neg_real":   tempo_neg_real,
                        "tempo_neg_tatica": tempo_neg_tatica,
                    }
                    st.success("✅ Padrões mentais processados!")
                except Exception as e:
                    st.error(f"Erro ao processar: {str(e)[:80]}")

        if st.session_state.get('stats_calculados'):
            stats = st.session_state['stats_calculados']

            tab_ng1, tab_ng2, tab_ng3, tab_ng4, tab_ng5, tab_ng6, tab_ng7, tab_ng8 = st.tabs([
                "🔴 Causador",
                "🟢 Negociador Principal",
                "🔵 Negociador Secundário",
                "✔️ Análise Global",
                "✔️ Comparativo das Nuvens de Palavras",
                "✔️ Convergência Temática",
                "✔️ Estado da Crise",
                "✔️ Detalhes da Transcrição"
            ])
            
            # --- TAB 1: CAUSADOR ---
            with tab_ng1:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color: #ef4444; margin-top: 0;'>🔴 CAUSADOR — Em que ele estava REALMENTE focando?</h5>
                <p style='font-size:0.9rem;color:#ddd;'>
                Os temas dominantes abaixo revelam a <strong>obsessão mental</strong> do causador. 
                Se "morte" é tema 1, o risco estava alto. Se "filha" aparece, há ambivalência.
                </p>
                </div>
                """, unsafe_allow_html=True)

                topicos_c = stats.get('temas_c', ["Análise individual ainda não gerada."])
                for t in topicos_c:
                    st.markdown(t)

                wc_c = stats.get('wc_c')
                if wc_c:
                    st.markdown("#### Nuvem de Palavras — Foco Mental do Causador")
                    st.pyplot(wc_c)
                else:
                    st.info("Sem transcrição suficiente para gerar nuvem.")
                
                

            # --- TAB 2: NEGOCIADOR PRINCIPAL ---
            with tab_ng2:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color: #10b981; margin-top: 0;'>🟢 NEGOCIADOR PRINCIPAL — Acompanhou os temas expostos pelo Causador?</h5>
                <p style='font-size:0.9rem;color:#ddd;'>
                Os temas do negociador mostram <strong>em que ele está focando</strong>. 
                Compare com o causador: convergência = boa sintonia; divergência = falha de rapport.
                </p>
                </div>
                """, unsafe_allow_html=True)

                topicos_np = stats.get('temas_np', ["Análise individual ainda não gerada."])
                for t in topicos_np:
                    st.markdown(t)

                wc_np = stats.get('wc_np')
                if wc_np:
                    st.markdown("#### Nuvem de Palavras — Estratégia do Negociador")
                    st.pyplot(wc_np)
                else:
                    st.info("Sem transcrição suficiente para gerar nuvem.")
                
                

            # --- TAB 3: NEGOCIADOR SECUNDÁRIO ---
            with tab_ng3:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color: #3b82f6; margin-top: 0;'>🔵 NEGOCIADOR SECUNDÁRIO — Destacou alguma participação na transcrição?</h5>
                <p style='font-size:0.9rem;color:#ddd;'>
                Geralmente suporte. Seus temas indicam se estava reforçando a mensagem do principal ou dispersando esforços.
                </p>
                </div>
                """, unsafe_allow_html=True)

                topicos_ns = stats.get('temas_ns', ["Análise individual ainda não gerada."])
                for t in topicos_ns:
                    st.markdown(t)

                wc_ns = stats.get('wc_ns')
                if wc_ns:
                    st.markdown("#### Nuvem de Palavras — Atuação do Secundário")
                    st.pyplot(wc_ns)
                else:
                    st.info("Sem transcrição suficiente para gerar nuvem.")
                
                
            # --- TAB 4: ANÁLISE GERAL ---
            with tab_ng4:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color: #f97316; margin-top: 0;'>✔️ VISÃO GERAL — Os temas gerais do incidente</h5>
                <p style='font-size:0.9rem;color:#ddd;'>
                Agregando causador + negociadores, quais eram os assuntos DOMINANTES na negociação?
                </p>
                </div>
                """, unsafe_allow_html=True)

                topicos_globais = stats.get('temas', ["Sem dados"])
                for t in topicos_globais:
                    st.markdown(t)
                
                

            # --- TAB 5: MAPAS COMPARATIVOS ---
            with tab_ng5:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color: #FFD700; margin-top: 0;'>✔️ NUVEM DE PALAVRAS LADO-A-LADO — Sincronização</h5>
                <p style='font-size:0.9rem;color:#ddd;'>
                Compare as nuvens visualmente. Se causador fala de "morte" e negociador de "vida", há conversação. 
                Se causador de "morte" e negociador de "calma", há desconexão.
                </p>
                </div>
                """, unsafe_allow_html=True)

                col_wc_g1, col_wc_g2, col_wc_g3 = st.columns(3)

                with col_wc_g1:
                    st.markdown("**Causador**")
                    wc_c = stats.get('wc_c')
                    if wc_c:
                        st.pyplot(wc_c, clear_figure=True)
                    else:
                        st.info("Sem nuvem.")

                with col_wc_g2:
                    st.markdown("**Negociador Principal**")
                    wc_np = stats.get('wc_np')
                    if wc_np:
                        st.pyplot(wc_np, clear_figure=True)
                    else:
                        st.info("Sem nuvem.")

                with col_wc_g3:
                    st.markdown("**Negociador Secundário**")
                    wc_ns = stats.get('wc_ns')
                    if wc_ns:
                        st.pyplot(wc_ns, clear_figure=True)
                    else:
                        st.info("Sem nuvem.")

            # --- TAB 6: CONVERGÊNCIA TEMÁTICA (CORRIGIDO) ---
            with tab_ng6:
                st.markdown("""
                <div class='info-card'>
                <h4 style='color:#FFD700; margin-top:0;'>✔️ CONVERGÊNCIA TEMÁTICA — Quanto cada tema foi abordado?</h4>
                <p style='color:#ccc; font-size:0.9rem; margin-bottom:1rem;'>
                Compara a <strong>intensidade (score)</strong> de cada tema abordado por causador e negociador.
                Polígonos sobrepostos = abordagem similar. Divergência = ênfase diferente.
                </p>
                </div>
                """, unsafe_allow_html=True)

                texto_c_raw  = stats.get('texto_c_raw', '')
                texto_np_raw = stats.get('texto_np_raw', '')
                texto_ns_raw = stats.get('texto_ns_raw', '')

                if not texto_c_raw or not texto_np_raw:
                    st.warning("⚠️ Transcrições insuficientes para analisar convergência temática.")
                else:
                    try:
                        # ── Extrair temas reais ──────────────────────────
                        temas_c = analise.extrair_temas_unicos(
                            texto_c_raw,
                            resolucao_tipo=stats.get('resolucao_tipo', 'desconhecida')
                        )
                        temas_np = analise.extrair_temas_unicos(
                            texto_np_raw,
                            resolucao_tipo=stats.get('resolucao_tipo', 'desconhecida')
                        )

                        # ── Calcular convergência ────────────────────────
                        conv_tematica = analise.calcular_convergencia_tematica(temas_c, temas_np)

                        # ── SCORECARD ────────────────────────────────────
                        st.markdown("### ✔️ Resumo da Convergência")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            conv_geral = conv_tematica["convergencia_geral"]
                            st.metric(
                                "Convergência Geral",
                                f"{conv_geral:.1f}%"
                            )
                        
                        with col2:
                            compartilhados = len(conv_tematica["temas_compartilhados"])
                            st.metric(
                                "Temas Compartilhados",
                                compartilhados
                            )
                        
                        with col3:
                            excl_c = len(conv_tematica["temas_exclusivos_causador"])
                            st.metric(
                                "Só Causador",
                                excl_c
                            )
                        
                        with col4:
                            excl_np = len(conv_tematica["temas_exclusivos_negociador"])
                            st.metric(
                                "Só Negociador",
                                excl_np
                            )

                        # ── RADAR TEMÁTICO (INTENSIDADE) ────────────────
                        st.markdown("---")
                        st.markdown("### ✔️ Intensidade de Abordagem por Tema (Radar)")
                        st.markdown("""
                        <p style='font-size:0.85rem;color:#aaa;'>
                        Polígono vermelho = intensidade do causador. 
                        Polígono verde = intensidade do negociador.
                        Quanto maior o polígono, mais o tema foi abordado.
                        </p>
                        """, unsafe_allow_html=True)
                        
                        try:
                            fig_radar_tematico = analise.gerar_radar_convergencia_tematica_corrigido(
                                temas_c,
                                temas_np,
                                conv_tematica["convergencia_por_tema"]
                            )
                            st.plotly_chart(fig_radar_tematico, use_container_width=True)
                        except Exception as e:
                            st.error(f"Erro ao gerar radar: {str(e)[:80]}")

                        # ── GRÁFICO DE BARRAS (ALTERNATIVA) ─────────────
                        st.markdown("---")
                        st.markdown("### ✔️ Intensidade por Tema (Gráfico de Barras)")
                        st.markdown("""
                        <p style='font-size:0.85rem;color:#aaa;'>
                        Visualização alternativa: compare a altura das barras para cada tema.
                        </p>
                        """, unsafe_allow_html=True)
                        
                        try:
                            fig_barras = analise.gerar_grafico_barras_intensidade_temas(
                                conv_tematica["convergencia_por_tema"]
                            )
                            st.plotly_chart(fig_barras, use_container_width=True)
                        except Exception as e:
                            st.error(f"Erro ao gerar gráfico: {str(e)[:80]}")

                        # ── TABELA DETALHADA ─────────────────────────────
                        st.markdown("---")
                        st.markdown("### 📋 Convergência Detalhada por Tema")
                        
                        df_conv_tab = analise.gerar_tabela_convergencia_tematica(conv_tematica)
                        st.dataframe(
                            df_conv_tab,
                            use_container_width=True,
                            hide_index=True
                        )

                        # ── ANÁLISE NARRATIVA ────────────────────────────
                        st.markdown("---")
                        st.markdown("### 📖 Análise Detalhada")
                        
                        st.markdown(conv_tematica["analise_detalhada"])

                        # ── INTERPRETAÇÃO GERAL ─────────────────────────
                        st.markdown("---")
                        st.markdown("### 💡 O que significa")
                        
                        conv_pct = conv_tematica["convergencia_geral"]
                        
                        st.markdown(f"""
                            **Convergência Temática Observada: {conv_pct:.1f}%**
                            
                            **O que é medido:**
                            - Intensidade com que causador e negociador abordam cada tema compartilhado
                            - Média das similitudes de score para os temas em comum
                            - Escala: 0% (completamente divergentes) a 100% (perfeitamente alinhados)
                            
                            **Interpretação Descritiva (sem classificação):**
                            
                            | Range | O que significa |
                            |-------|---|
                            | **90-100%** | Ambos abordam os temas com intensidades praticamente idênticas |
                            | **70-90%** | Maioria dos temas tem intensidades próximas, com variações pequenas |
                            | **50-70%** | Alguns temas com intensidades similares, outros com diferenças notáveis |
                            | **30-50%** | Intensidades frequentemente divergentes — énfases diferentes |
                            | **0-30%** | Abordagens muito diferentes — possivelmente universos mentais distintos |
                            
                            **Seu caso: {conv_pct:.1f}%**
                            
                            - **Temas compartilhados:** {len(conv_tematica["temas_compartilhados"])}
                            - **Temas só do causador:** {len(conv_tematica["temas_exclusivos_causador"])}
                            - **Temas só do negociador:** {len(conv_tematica["temas_exclusivos_negociador"])}
                            
                            **Atenção:**
                            Este é um índice DESCRITIVO. Não é preditivo de desfecho.
                            Próxima etapa: comparar com histórico de 50+ APAs para validar padrões.
                            """)

                    except Exception as e:
                        st.error(f"Erro ao analisar convergência temática: {str(e)[:80]}")

            # --- TAB 7: ESTADO DO CAUSADOR ---
            with tab_ng7:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color:#FFD700; margin-top:0;'>✔️ ESTADO DO CAUSADOR (APA)</h5>
                <p style='color:#ccc; font-size:0.9rem;'>
                Análise estruturada do estado emocional/comportamental do causador.
                </p>
                </div>
                """, unsafe_allow_html=True)

                texto_c_raw = stats.get('texto_c_raw', '')

                if texto_c_raw:
                    try:
                        analise_crise = analise.analisar_crise_direcional(
                            texto_c_raw,
                            resolucao_tipo=stats.get('resolucao_tipo', 'desconhecida')
                        )

                        if analise_crise and 'sumario' in analise_crise:
                            sumario = analise_crise['sumario']

                            risco_observado    = sumario.get('risco_observado')
                            abertura_observada = sumario.get('abertura_observada')
                            raiz_observada     = sumario.get('raiz_observada')
                            volatilidade_index = sumario.get('volatilidade_index')
                            intensidade_index  = sumario.get('intensidade_index')
                            direcao_index      = sumario.get('direcao_index')
                            classificacao      = sumario.get('classificacao')
                            leitura            = sumario.get('leitura')
                            resolucao_tipo     = stats.get('resolucao_tipo', 'desconhecida')

                            # ── SCORECARD ──────────────────────────────
                            st.markdown("### ✔️ Resumo da Análise")
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.metric(
                                    "🔴 Risco Observado",
                                    f"{risco_observado:.1f}%" if risco_observado is not None else "N/D"
                                )
                            with col2:
                                st.metric(
                                    "🟢 Abertura Observada",
                                    f"{abertura_observada:.1f}%" if abertura_observada is not None else "N/D"
                                )
                            with col3:
                                st.metric(
                                    "🟡 Raiz Observada",
                                    f"{raiz_observada:.1f}%" if raiz_observada is not None else "N/D"
                                )

                            col4, col5, col6 = st.columns(3)

                            with col4:
                                st.metric(
                                    "⚡ Intensidade Global",
                                    f"{intensidade_index:.2f}" if intensidade_index is not None else "N/D"
                                )
                            with col5:
                                st.metric(
                                    "➡️ Direção",
                                    f"{direcao_index:+.2f}" if direcao_index is not None else "N/D"
                                )
                            with col6:
                                st.metric(
                                    "✔️ Volatilidade",
                                    f"{volatilidade_index:.2f}" if volatilidade_index is not None else "N/D"
                                )

                            # ── CLASSIFICAÇÃO ───────────────────────────
                            st.markdown("---")
                            st.markdown(f"### 🚨 Classificação: `{classificacao}`")
                            st.info(leitura)

                            # ── RADAR ───────────────────────────────────
                            st.markdown("---")
                            st.markdown("### ✔️ Padrão de Crise (Radar)")
                            try:
                                fig_crise = analise.gerar_radar_crise_individual(
                                    risco_observado    if risco_observado    is not None else 0,
                                    abertura_observada if abertura_observada is not None else 0,
                                    raiz_observada     if raiz_observada     is not None else 0,
                                    volatilidade_index if volatilidade_index is not None else 0
                                )
                                st.plotly_chart(fig_crise, use_container_width=True)
                            except Exception as e:
                                st.error(f"Erro ao gerar radar: {str(e)[:80]}")

                            # ── NARRATIVA PARA LEIGOS ───────────────────
                            st.markdown("---")
                            st.markdown("### ✔️ Leitura Operacional (Linguagem Acessível)")

                            st.markdown("""
                            <div style='background:rgba(255,215,0,0.04);padding:4px 12px;border-left:3px solid #FFD700;margin-bottom:12px;'>
                            <p style='color:#aaa;font-size:0.82rem;margin:6px 0;'>
                            Interpretação automática dos indicadores em linguagem acessível.
                            Destinada a leitura rápida por gestores, auditores e instrutores.
                            </p>
                            </div>
                            """, unsafe_allow_html=True)

                            narrativa = analise.gerar_narrativa_crise(
                                risco_observado    = risco_observado    or 0,
                                abertura_observada = abertura_observada or 0,
                                raiz_observada     = raiz_observada     or 0,
                                intensidade_index  = intensidade_index  or 0,
                                direcao_index      = direcao_index      or 0,
                                volatilidade_index = volatilidade_index or 0,
                                classificacao      = classificacao      or "INDETERMINADO",
                                resolucao_tipo     = resolucao_tipo
                            )
                            st.markdown(narrativa)

                        else:
                            st.warning("Não foi possível gerar análise de crise")

                    except Exception as e:
                        st.error(f"Erro ao analisar crise: {str(e)[:80]}")

                else:
                    st.warning("⚠️ Nenhuma transcrição disponível para análise")                    
                                            
        # ============================================================
        # TAB 8: QUALIDADE DO DISCURSO COM TRANSFORMER (LAZY LOADING)
        # Cole TUDO isso DENTRO do: with tab_ng8:
        # ============================================================

        st.markdown("### ✔️ Detalhes da Transcrição")

        col_caus = "TRANSCRIÇÃO DO CAUSADOR"
        col_neg = "TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL"

        if col_caus not in df_apa or col_neg not in df_apa:
            st.warning("⚠️ Colunas de transcrição não encontradas")
        else:
            txt_caus = str(df_apa[col_caus]).strip()
            txt_neg = str(df_apa[col_neg]).strip()
            
            if not txt_caus or not txt_neg or len(txt_caus) < 20 or len(txt_neg) < 20:
                st.warning("⚠️ Transcrições insuficientes para análise")
            else:
                
                # =========================================================
                # SEÇÃO 1: ANÁLISE RÁPIDA (com toggle)
                # =========================================================
                
                col_left, col_center, col_right = st.columns([1, 1, 1])
                with col_center:
                    is_analise_rapida = render_toggle_button(
                        label="✔️ Análise Rápida (Padrões Léxicos)",
                        session_key="tab8_analise_rapida",
                        button_key="btn_tab8_analise_rapida"
                    )
                
                st.markdown("---")
                
                if is_analise_rapida:
                    st.markdown("""
                    <p style='color: #aaa; font-size: 0.9rem; margin-bottom: 1rem;'>
                    Análise imediata baseada em frequência de palavras-chave.
                    <strong>Não usa modelo de IA.</strong> Rápido e transparente.
                    </p>
                    """, unsafe_allow_html=True)

                    # Rodar análise rápida
                    analise_rapida = analise.analise_rapida_discurso(txt_neg, txt_caus)

                    # SCORECARD - NEGOCIADOR
                    st.markdown("### 🟢 NEGOCIADOR PRINCIPAL")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric(
                            "Validação",
                            analise_rapida['total_validacao'],
                            f"x ocorrências"
                        )

                    with col2:
                        st.metric(
                            "Confronto",
                            analise_rapida['total_confronto'],
                            f"x ocorrências"
                        )

                    with col3:
                        total_palavras_neg = len(txt_neg.split())
                        st.metric(
                            "Tamanho (Palavras)",
                            total_palavras_neg,
                            f"palavras"
                        )

                    # SCORECARD - CAUSADOR
                    st.markdown("---")
                    st.markdown("### 🔴 CAUSADOR")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric(
                            "Emoção Alta",
                            analise_rapida['total_emocao'],
                            f"x palavras fortes"
                        )

                    with col2:
                        total_palavras_caus = len(txt_caus.split())
                        st.metric(
                            "Tamanho (Palavras)",
                            total_palavras_caus,
                            f"palavras"
                        )
                    
                    # Detalhes
                    st.markdown("---")
                    st.markdown("#### ✔️ Detalhes das Palavras-Chave Encontradas")
                    
                    st.markdown("### 🟢 NEGOCIADOR PRINCIPAL")

                    col_val, col_conf = st.columns(2)

                    with col_val:
                        st.markdown("**Validação (Negociador):**")
                        if analise_rapida['validacao']:
                            for palavra, freq in sorted(
                                analise_rapida['validacao'].items(),
                                key=lambda x: x[1],
                                reverse=True
                            ):
                                st.write(f"  • {palavra}: {freq}x")
                        else:
                            st.write("  (nenhuma encontrada)")

                    with col_conf:
                        st.markdown("**Confronto (Negociador):**")
                        if analise_rapida['confronto']:
                            for palavra, freq in sorted(
                                analise_rapida['confronto'].items(),
                                key=lambda x: x[1],
                                reverse=True
                            ):
                                st.write(f"  • {palavra}: {freq}x")
                        else:
                            st.write("  (nenhuma encontrada)")
                    
                    st.markdown("---")
                    st.markdown("### 🔴 CAUSADOR")

                    st.markdown("**Emoção Alta (Causador):**")
                    if analise_rapida['emocao_causador']:
                        for palavra, freq in sorted(
                            analise_rapida['emocao_causador'].items(),
                            key=lambda x: x[1],
                            reverse=True
                        ):
                            st.write(f"  • {palavra}: {freq}x")
                    else:
                        st.write("  (nenhuma encontrada)")                     
                    
                    # Interpretação
                    st.markdown("---")
                    st.markdown("#### 💡 O Que Significa")
                    st.markdown("""
                    - **Validação**: Palavras que indicam reconhecimento, escuta, empatia
                    - **Confronto**: Palavras que indicam discordância, negação, imposição
                    - **Emoção Alta**: Indicadores de stress, medo, raiva no causador
                    
                    **Nota:** Essa análise conta frequência, não interpreta contexto.
                    "Não" pode ser "não vou bater" (protetor) ou "não faço isso" (negação).
                    Use como descritor, não como julgamento.
                    """)
                
                # ============================================================
                # TAB 8: TRANSFORMER OTIMIZADO (SEM TRADUÇÃO - RÁPIDO)
                # SUBSTITUA a seção do Transformer em seu_app.py
                # ============================================================

                st.markdown("---")
                st.markdown("""
                <div style='background: rgba(76, 175, 80, 0.1); border-left: 4px solid #4CAF50; padding: 15px; border-radius: 8px; margin-bottom: 20px;'>
                <h5 style='color: #FFD700; margin-top: 0;'> Análise de Sentimento (Biblioteca Transformer)</h5>
                <p style='color: #aaa; font-size: 0.9rem; margin-bottom: 10px;'>
                Análise com Transformer português otimizado: remove gírias e stopwords para melhor compreensão.
                </p>
                <ul style='color: #bbb; font-size: 0.9rem; line-height: 1.6; margin: 10px 0;'>
                <li><strong>Pré-processamento:</strong> Normaliza gírias + remove stopwords</li>
                <li><strong>Análise:</strong> Transformer direto no português limpo</li>
                <li><strong>Tempo:</strong> ~10-15 segundos (muito mais rápido!)</li>
                <li><strong>Mostrada:</strong> Original + Limpa</li>
                </ul>
                <p style='color: #FFD700; font-size: 0.85rem; font-weight: bold; margin-bottom: 0;'>
                Clique no botão abaixo para carregar a análise.
                </p>
                </div>
                """, unsafe_allow_html=True)

                col_left, col_center, col_right = st.columns([1, 1, 1])
                with col_center:
                    is_transformer = render_toggle_button(
                        label="✔️ Análise de Sentimento (Transformer)",
                        session_key="tab8_transformer_otimizado",
                        button_key="btn_tab8_transformer_otimizado"
                    )

                st.markdown("---")

                if is_transformer:
                    # Mostrar exemplo de limpeza
                    with st.expander("✔️ Como funciona a limpeza (exemplo)"):
                        st.markdown("**Exemplo: Primeiras 3 sentenças**")
                        
                        exemplo_linhas = analise.dividir_em_sentencas(txt_neg)[:3]
                        
                        for idx, sentenca in enumerate(exemplo_linhas, 1):
                            original = sentenca
                            limpa = analise.limpar_sentenca(sentenca)
                            
                            col1, col2 = st.columns([1, 1])
                            with col1:
                                st.markdown(f"**Original ({len(original.split())} palavras):**")
                                st.write(f"_{original}_")
                            with col2:
                                st.markdown(f"**Limpa ({len(limpa.split())} palavras):**")
                                st.write(f"_{limpa}_")
                            st.markdown("---")
                    
                    with st.spinner("⏳ Carregando modelo Transformer..."):
                        nlp_model = analise.carregar_transformer_portugues()
                    
                    if nlp_model is None:
                        st.error("❌ Erro ao carregar modelo. Verifique instalação de `transformers`")
                    else:
                        st.success("✔️ Modelo carregado com sucesso!")
                        
                        # Analisar negociador
                        st.markdown("---")
                        st.markdown("#### 🟢 Sentimento do Negociador")
                        
                        with st.spinner("Analisando fala do negociador..."):
                            resultado_neg = analise.analise_sentimento_transformer_otimizado(txt_neg, nlp_model)
                        
                        if resultado_neg:
                            # Contar positivos/negativos/neutros
                            positivos = sum(1 for r in resultado_neg if r['label'] in ['POSITIVE', 'LABEL_2'])
                            negativos = sum(1 for r in resultado_neg if r['label'] in ['NEGATIVE', 'LABEL_0'])
                            neutros = sum(1 for r in resultado_neg if r['label'] in ['NEUTRAL', 'LABEL_1'])
                            total_sent = len(resultado_neg)
                            
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("Positivos", f"{positivos}/{total_sent}")
                            
                            with col2:
                                st.metric("Neutros", f"{neutros}/{total_sent}")
                            
                            with col3:
                                st.metric("Negativos", f"{negativos}/{total_sent}")
                            
                            with col4:
                                pct_positivo = (positivos / total_sent * 100) if total_sent > 0 else 0
                                st.metric("% Positivo", f"{pct_positivo:.0f}%")
                            
                            # Mostrar exemplos
                            st.markdown("**Exemplos de Sentenças (Original → Limpa):**")
                            
                            col_pos, col_neu, col_neg = st.columns(3)
                            
                            with col_pos:
                                st.markdown("✅ **Positivas:**")
                                for r in [x for x in resultado_neg if x['label'] in ['POSITIVE', 'LABEL_2']][:3]:
                                    st.write(f"🇧🇷 _{r['sentenca_pt']}_")
                                    st.write(f"✂️ _{r['sentenca_limpa']}_")
                                    st.write("")
                            
                            with col_neu:
                                st.markdown("⚪ **Neutras:**")
                                for r in [x for x in resultado_neg if x['label'] in ['NEUTRAL', 'LABEL_1']][:3]:
                                    st.write(f"🇧🇷 _{r['sentenca_pt']}_")
                                    st.write(f"✂️ _{r['sentenca_limpa']}_")
                                    st.write("")
                            
                            with col_neg:
                                st.markdown("❌ **Negativas:**")
                                for r in [x for x in resultado_neg if x['label'] in ['NEGATIVE', 'LABEL_0']][:3]:
                                    st.write(f"🇧🇷 _{r['sentenca_pt']}_")
                                    st.write(f"✂️ _{r['sentenca_limpa']}_")
                                    st.write("")
                        
                        # Analisar causador
                        st.markdown("---")
                        st.markdown("#### 🔴 Sentimento do Causador")
                        
                        with st.spinner("Analisando fala do causador..."):
                            resultado_caus = analise.analise_sentimento_transformer_otimizado(txt_caus, nlp_model)
                        
                        if resultado_caus:
                            # Contar positivos/negativos/neutros
                            positivos = sum(1 for r in resultado_caus if r['label'] in ['POSITIVE', 'LABEL_2'])
                            negativos = sum(1 for r in resultado_caus if r['label'] in ['NEGATIVE', 'LABEL_0'])
                            neutros = sum(1 for r in resultado_caus if r['label'] in ['NEUTRAL', 'LABEL_1'])
                            total_sent = len(resultado_caus)
                            
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("Positivos", f"{positivos}/{total_sent}")
                            
                            with col2:
                                st.metric("Neutros", f"{neutros}/{total_sent}")
                            
                            with col3:
                                st.metric("Negativos", f"{negativos}/{total_sent}")
                            
                            with col4:
                                pct_negativo = (negativos / total_sent * 100) if total_sent > 0 else 0
                                st.metric("% Negativo", f"{pct_negativo:.0f}%")
                            
                            # Mostrar exemplos
                            st.markdown("**Exemplos de Sentenças:**")
                            
                            col_pos, col_neu, col_neg = st.columns(3)
                            
                            with col_pos:
                                st.markdown("✅ **Positivas:**")
                                for r in [x for x in resultado_caus if x['label'] in ['POSITIVE', 'LABEL_2']][:3]:
                                    st.write(f"🇧🇷 _{r['sentenca_pt']}_")
                                    st.write(f"✂️ _{r['sentenca_limpa']}_")
                                    st.write("")
                            
                            with col_neu:
                                st.markdown("⚪ **Neutras:**")
                                for r in [x for x in resultado_caus if x['label'] in ['NEUTRAL', 'LABEL_1']][:3]:
                                    st.write(f"🇧🇷 _{r['sentenca_pt']}_")
                                    st.write(f"✂️ _{r['sentenca_limpa']}_")
                                    st.write("")
                            
                            with col_neg:
                                st.markdown("❌ **Negativas:**")
                                for r in [x for x in resultado_caus if x['label'] in ['NEGATIVE', 'LABEL_0']][:3]:
                                    st.write(f"🇧🇷 _{r['sentenca_pt']}_")
                                    st.write(f"✂️ _{r['sentenca_limpa']}_")
                                    st.write("")
                        
                        # Análise Comparativa
                        st.markdown("---")
                        st.markdown("#### ✔️ Comparativo")
                        
                        if resultado_neg and resultado_caus:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                pct_pos_neg = (sum(1 for r in resultado_neg if r['label'] in ['POSITIVE', 'LABEL_2']) / len(resultado_neg) * 100)
                                st.metric("Negociador % Positivo", f"{pct_pos_neg:.0f}%")
                            
                            with col2:
                                pct_pos_caus = (sum(1 for r in resultado_caus if r['label'] in ['POSITIVE', 'LABEL_2']) / len(resultado_caus) * 100)
                                st.metric("Causador % Positivo", f"{pct_pos_caus:.0f}%")
                            
                            st.markdown(f"""
                            **Interpretação:**
                            - Negociador {pct_pos_neg:.0f}% positivo → {"Mantendo tom construtivo" if pct_pos_neg > 60 else "Tom mais técnico/neutro" if pct_pos_neg > 30 else "Tom defensivo"}
                            - Causador {pct_pos_caus:.0f}% positivo → {"Muito receptivo" if pct_pos_caus > 60 else "Moderadamente receptivo" if pct_pos_caus > 40 else "Resistente, preocupado"}
                            """)

                st.markdown("---")
                st.markdown("""
                                    
                ⚠️ **Limitações:**
                
                - Modelo treinado em resenhas de produtos em inglês
                - Português coloquial pode ser mal interpretado
                - "Entendi", "tranquilo" podem ser classificados errado            
                - Gírias muito locais podem confundir
                - Sarcasmo ainda pode não ser detectado
                - Use como complemento da Análise Rápida
                """)

        st.markdown("---")


        
        st.markdown("---")
                                    
                        # ===== PRÓXIMO BOTÃO (FORA DA TAB) =====
        if st.button("✔ 3. GERAR ANALYTICS E EXPORTAR ANÁLISE (PDF)"):
            with st.spinner("Compilando dados técnicos, consultando IA e desenhando PDF..."):
                try:
                    t_causador = limpar_valor(df_apa.get('TRANSCRIÇÃO DO CAUSADOR'))
                    t_principal = limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL'))
                    t_secundario = limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO'))

                    df_transcricoes = pd.DataFrame([{
                        "Causador": t_causador,
                        "Neg_Principal": t_principal,
                        "Neg_Secundario": t_secundario
                    }])

                    stats_calculados = st.session_state.get('stats_calculados', {}) or {}

                    temas_extraidos = stats_calculados.get('topicos') if stats_calculados else ["Etapa 2 não executada"]
                    if not isinstance(temas_extraidos, (list, tuple)):
                        temas_extraidos = [str(temas_extraidos)]

                    meta_dict = df_apa.to_dict()
                    meta_dict["temas_dominantes_scikit_learn"] = " | ".join([str(t) for t in temas_extraidos])

                    # Envia para a IA as análises textuais já calculadas:
                    # - similitude lexical
                    # - n-grams / modelagem de tópicos
                    # - convergência
                    # - qualquer outro dado já existente em stats_calculados
                    meta_dict["analises_calculadas"] = {
                        "similitude_lexical": stats_calculados.get(
                            "similitude_lexical",
                            stats_calculados.get("similitude", "Não executada")
                        ),
                        "ngrams": stats_calculados.get(
                            "ngrams",
                            stats_calculados.get("n_grams", "Não executada")
                        ),
                        "convergencia": stats_calculados.get(
                            "convergencia",
                            stats_calculados.get("convergencia_lexical", "Não executada")
                        ),
                        "topicos": temas_extraidos,
                    }

                    df_meta = pd.DataFrame([meta_dict])

                    dados_extraidos = {
                        "transcricao": df_transcricoes,
                        "metadados": df_meta
                    }

                    # ====
                    # MONTA AS TÉCNICAS DA APA E A FREQUÊNCIA PARA ENVIAR À IA
                    # ====
                    tecnicas_da_apa = []
                    freq_tecnicas_dict = {}
                    estatisticas_ocorrencia = {}

                    try:
                        if not df_tec.empty:
                            col_vinculo = next((c for c in df_tec.columns if 'VINCULO' in c.upper() or 'VÍNCULO' in c.upper()), None)

                            if col_vinculo:
                                id_visivel = str(apa_selecionada).strip()

                                df_tec_tmp = df_tec.copy()
                                df_tec_tmp['Vinculo_Str'] = (
                                    df_tec_tmp[col_vinculo]
                                    .astype(str)
                                    .str.replace(r"[\[\]'\"]", "", regex=True)
                                    .str.strip()
                                )

                                df_tec_filtrado_pdf = df_tec_tmp[df_tec_tmp['Vinculo_Str'] == id_visivel].copy()

                                if df_tec_filtrado_pdf.empty and 'Airtable_Record_ID' in df_apa:
                                    id_interno = str(df_apa['Airtable_Record_ID']).strip()
                                    df_tec_filtrado_pdf = df_tec_tmp[
                                        df_tec_tmp[col_vinculo].astype(str).str.contains(id_interno, na=False, regex=False)
                                    ].copy()

                                if not df_tec_filtrado_pdf.empty:
                                    col_tecnica = next(
                                        (col for col in ['TÉCNICAS', 'TECNICAS', 'TÉCNICA', 'TECNICA'] if col in df_tec_filtrado_pdf.columns),
                                        None
                                    )

                                    if col_tecnica:
                                        freq_abs = df_tec_filtrado_pdf[col_tecnica].value_counts()
                                        freq_rel = (df_tec_filtrado_pdf[col_tecnica].value_counts(normalize=True) * 100).round(1)

                                        df_freq_pdf = pd.DataFrame({
                                            'Técnica Empregada': freq_abs.index,
                                            'Frequência Absoluta': freq_abs.values,
                                            'Frequência Relativa (%)': freq_rel.values
                                        })

                                        tecnicas_da_apa = df_freq_pdf['Técnica Empregada'].dropna().astype(str).tolist()

                                        frequencia_tecnicas_ocorrencia = []
                                        for _, row in df_freq_pdf.iterrows():
                                            frequencia_tecnicas_ocorrencia.append({
                                                "tecnica": str(row["Técnica Empregada"]),
                                                "frequencia_absoluta": int(row["Frequência Absoluta"]),
                                                "frequencia_relativa": float(row["Frequência Relativa (%)"])
                                            })

                                        freq_tecnicas_dict = dict(
                                            zip(
                                                df_freq_pdf['Técnica Empregada'].astype(str),
                                                df_freq_pdf['Frequência Absoluta'].astype(int)
                                            )
                                        )

                                        estatisticas_ocorrencia = {
                                            "frequencia_tecnicas_ocorrencia": frequencia_tecnicas_ocorrencia,
                                            "frequencia_absoluta_por_tecnica": freq_tecnicas_dict
                                        }

                    except Exception as e:
                        st.warning(f"Falha ao montar frequências para a IA: {e}")

                    resultado_ia = ia_link.analisar_ocorrencia_gate(
                        dados_extraidos,
                        estatisticas_ocorrencia=estatisticas_ocorrencia,
                        tecnicas_ocorrencia=tecnicas_da_apa
                    )

                    if isinstance(resultado_ia, dict):
                        parecer_ia = resultado_ia.get("parecer", "")
                        sugestoes_treinamento = resultado_ia.get("sugestoes_treinamento", "")
                    else:
                        parecer_ia = str(resultado_ia)
                        sugestoes_treinamento = ""

                    def calcular_media_equipe(*valores):
                        validos = [v for v in valores if v and v > 0]
                        return sum(validos) / len(validos) if validos else None

                    likert_inicio = {
                        'agressividade_media': calcular_media_equipe(p_agr_c_num, s_agr_c_num, l_agr_c_num),
                        'receptividade_media': calcular_media_equipe(p_rec_c_num, s_rec_c_num, l_rec_c_num)
                    }
                    likert_fim = {
                        'agressividade_media': calcular_media_equipe(p_agr_e_num, s_agr_e_num, l_agr_e_num),
                        'receptividade_media': calcular_media_equipe(p_rec_e_num, s_rec_e_num, l_rec_e_num)
                    }
                    # Spearman entre serie de agressividade no inicio e no fim (3 pares: P, S, L)
                    try:
                        import numpy as _np
                        from scipy.stats import spearmanr as _spearmanr
                        x_likert = [v for v in [p_agr_c_num, s_agr_c_num, l_agr_c_num] if v > 0]
                        y_likert = [v for v in [p_agr_e_num, s_agr_e_num, l_agr_e_num] if v > 0]
                        n_par = min(len(x_likert), len(y_likert))
                        if n_par >= 3 and len(set(x_likert[:n_par])) > 1 and len(set(y_likert[:n_par])) > 1:
                            rho_lk, p_lk = _spearmanr(x_likert[:n_par], y_likert[:n_par])
                            stats_spearman = {'valido': True, 'p_value': float(p_lk), 'rho': float(rho_lk)}
                        else:
                            stats_spearman = {'valido': False, 'p_value': 1.0, 'rho': 0.0}
                    except Exception:
                        stats_spearman = {'valido': False, 'p_value': 1.0, 'rho': 0.0}
                    laudo_frio = ia_link.gerar_laudo_frio(likert_inicio, likert_fim, stats_spearman)

                    st.markdown(f"""
                    <div class="info-card" style="border-left: 4px solid #FFD700;">
                    <h4 style="color: #FFD700; margin-top: 0;">Inferência Estatística (Motor Frio)</h4>
                    <p style="font-size: 1.05rem; line-height: 1.6;">{laudo_frio}</p>
                    <hr style="border-color: rgba(255,255,255,0.1); margin: 15px 0;">
                    <h4 style="color: #06C755; margin-top: 0;">Leitura Analítica (Interpretação descritiva dos resultados)</h4>
                    <p style="font-size: 1.05rem; line-height: 1.6;">{parecer_ia}</p>
                    <hr style="border-color: rgba(255,255,255,0.1); margin: 15px 0;">
                    <h4 style="color: #FFA500; margin-top: 0;">Sugestões para treinamentos</h4>
                    <p style="font-size: 1.05rem; line-height: 1.6;">{sugestoes_treinamento or 'Sem base suficiente para sugerir treinamento específico.'}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    texto_str = f"""INFERENCIA ESTATISTICA (MOTOR FRIO)

        {laudo_frio}

        LEITURA ANALITICA

        {parecer_ia}

        SUGESTOES PARA TREINAMENTOS

        {sugestoes_treinamento if sugestoes_treinamento else 'Sem base suficiente para sugerir treinamento específico.'}
        """

                    texto_str = texto_str.replace("**", "").replace("### ", "")
                    texto_final_pdf = unicodedata.normalize('NFKD', texto_str).encode('ASCII', 'ignore').decode('ASCII')

                    pdf = FPDF()
                    pdf.add_page()

                    pdf.set_fill_color(249, 115, 22)
                    pdf.rect(0, 0, 210, 40, 'F')
                    pdf.set_font("Arial", "B", 18)
                    pdf.set_text_color(255, 255, 255)
                    pdf.cell(0, 15, "LAUDO DE ANALISE POS-ACAO (APA)", ln=True, align="C")
                    pdf.set_font("Arial", "I", 12)
                    pdf.cell(0, 5, f"Unidade: GATE | ID: {apa_selecionada}", ln=True, align="C")

                    pdf.ln(20)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Arial", "B", 14)
                    pdf.set_fill_color(240, 240, 240)
                    pdf.cell(0, 10, " 1. INFORMACOES DO INCIDENTE", ln=True, fill=True)
                    pdf.set_font("Arial", "", 11)

                    dt_oc = limpar_valor(df_apa.get('Data da ocorrência'))
                    tip = limpar_valor(df_apa.get('Tipologia'))
                    neg = limpar_valor(df_apa.get('Negociador Principal'))
                    info_str = f"Data: {dt_oc} | Tipologia: {tip} | Negociador: {neg}"

                    pdf.multi_cell(
                        0,
                        8,
                        txt=unicodedata.normalize('NFKD', info_str).encode('ASCII', 'ignore').decode('ASCII'),
                        border='L'
                    )

                    pdf.ln(10)
                    pdf.set_font("Arial", "B", 14)
                    pdf.set_fill_color(249, 115, 22)
                    pdf.set_text_color(255, 255, 255)
                    pdf.cell(0, 10, " 2. INTELIGENCIA DE APOIO A DECISAO (IA)", ln=True, fill=True)
                    pdf.ln(5)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Arial", "", 11)

                    pdf.multi_cell(0, 7, txt=texto_final_pdf)

                    pdf_saida = pdf.output(dest="S")
                    if isinstance(pdf_saida, str):
                        pdf_bytes = pdf_saida.encode('latin-1', errors='replace')
                    else:
                        pdf_bytes = bytes(pdf_saida)

                    st.download_button(
                        label="📥 BAIXAR ANÁLISE COMPLETA (PDF)",
                        data=pdf_bytes,
                        file_name=f"Laudo_GATE_{apa_selecionada}.pdf",
                        mime="application/pdf"
                    )

                except Exception as e:
                    st.error(f"Erro na análise da IA ou geração do PDF: {str(e)}")

        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
        st.markdown("""
<div style='margin-top:20px; margin-bottom:100px; padding:15px; background-color:#111; border-radius:8px;'>
<p style="color:#bbb; font-size:13px; line-height:1.7; text-align:left;">

<span style="color:#ffae42; font-weight:700; font-size:14px; letter-spacing:1px;">
DELTA-NEGOCIAÇÃO — GATE/PMESP
</span>


"O maior inimigo do conhecimento não é a ignorância, mas a ilusão do conhecimento."
— Stephen Hawking.


“Sem dados, você é apenas mais uma pessoa com opinião.”
— W. Edwards Deming.


Empenhados no desenvolvimento de treinamentos e na avaliação dos Negociadores, alicerçados no pensamento técnico-científico e no valor humano, guiados por dados.

<br>

<span style="color:#ffae42; font-weight:600;">
NEGOCIAÇÃO!
</span>

<br>

<span style="color:#777; font-size:11px;">
Dados confidenciais, de uso exclusivo da equipe de Negociação do Grupo de Ações Táticas Especiais.
</span>

</p>

<hr style="border:none; height:1px; background:linear-gradient(to right, transparent, rgba(255,174,66,0.6), transparent); margin-top:18px; margin-bottom:12px;">

<div style="text-align:center; font-size:11px; color:#666; line-height:1.5;">
© 2026 AXIOM - Strategic Intelligence Ltda — Todos os direitos reservados.<br>
Este sistema é protegido por direitos autorais e legislação aplicável. Reprodução, distribuição, engenharia reversa, modificação ou utilização não autorizada são proibidas.
</div>
""", unsafe_allow_html=True)

    # ====
    # ABA 2: PAINEL (HISTÓRICO)
    # ====
    with aba_geral:
        st.markdown("### Série Histórica - Negociações GATE")
        st.markdown("<h5 style='color: #f97;'>Filtros por: Negociador, Tipologia e Modalidade do Incidente</h5>", unsafe_allow_html=True)
        
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            lista_neg_g = ["Todos"] + sorted(df_quali[df_quali['Neg_Limpo'] != 'N/D']['Neg_Limpo'].unique().tolist())
            filtro_neg_g = st.selectbox("Filtrar por Negociador:", lista_neg_g, key="f_neg_historico")
        with col_f2:
            lista_tip_g = ["Todas"] + sorted(df_quali[df_quali['Tip_Limpa'] != 'N/D']['Tip_Limpa'].unique().tolist())
            filtro_tip_g = st.selectbox("Filtrar por Tipologia:", lista_tip_g, key="f_tip_historico")
        with col_f3:
            lista_mod_g = ["Todas"] + sorted(df_quali[df_quali['Mod_Limpa'] != 'N/D']['Mod_Limpa'].unique().tolist())
            filtro_mod_g = st.selectbox("Filtrar por Modalidade:", lista_mod_g, key="f_mod_historico")

        df_quali_filt = df_quali.copy()
        if filtro_neg_g != "Todos": df_quali_filt = df_quali_filt[df_quali_filt['Neg_Limpo'] == filtro_neg_g]
        if filtro_tip_g != "Todas": df_quali_filt = df_quali_filt[df_quali_filt['Tip_Limpa'] == filtro_tip_g]
        if filtro_mod_g != "Todas": df_quali_filt = df_quali_filt[df_quali_filt['Mod_Limpa'] == filtro_mod_g]

        st.markdown("---")
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1: st.metric("Ocorrências Analisadas", len(df_quali_filt))
        with col_m2: st.metric("Tempo Total de Negociação Real", somar_tempos_segundos(df_quali_filt.get('Tempo de Negociação Real', [])))
        with col_m3: st.metric("Tempo Total de Negociação Tática", somar_tempos_segundos(df_quali_filt.get('Tempo de Negociação Tática', [])))

        st.markdown("---")
        
        # ====
        # NOVOS GRÁFICOS: VISÃO GERAL DA AMOSTRA
        # ====
        st.markdown("""
                        <div class='info-card'>
                        <h5 style='color: #FFD700; margin-top: 0;'>Visão Geral da Série Histórica</h5>
                        <p style='font-size:1.2rem;color:#ddd;'>
                        Metadados</strong>                 
                        </p>
                        </div>
                        """, unsafe_allow_html=True)
                

        # ── BOTÃO TOGGLE ───────────────────────────────────────────
        col_left, col_center, col_right = st.columns([1, 1, 1])
        with col_center:
            is_visao_geral = render_toggle_button(
                label="✔️ Abrir Visão Geral",
                session_key="analise1_visao_geral",
                button_key="btn_analise1_visao_geral"
            )
        
        st.markdown("---")
        
        if is_visao_geral:     
                
        
            def gerar_grafico_resumo(df, coluna, titulo):
                """Gera gráfico de rosca (donut) padronizado com o Design System."""
                if coluna not in df.columns: return None
                
                # Limpa listas vazias e formata strings
                serie = df[coluna].apply(lambda x: x[0] if isinstance(x, list) and len(x)>0 else str(x))
                serie = serie[~serie.isin(["N/D", "nan", "", "None"])]
                
                if serie.empty: return None
                
                contagem = serie.value_counts().reset_index()
                contagem.columns = [coluna, 'Frequência']
                # para garantir que a maior fatia pegue a cor mais forte
                contagem = contagem.sort_values('Frequência', ascending=False)

                cores_contraste = ['#FF8C00', '#8B4513', "#A53A00", '#DEB887', "#EBE9E7" ]

                # Criação do Gráfico de Rosca
                fig = px.pie(
                    contagem, 
                    values='Frequência', 
                    names=coluna, 
                    title=titulo,
                    hole=0.5, # Define o buraco central para transformar em rosca
                    color_discrete_sequence=cores_contraste
                )
                
                # Configuração das legendas e rótulos
                fig.update_traces(
                    textinfo='value+percent', # Mostra o número absoluto e a porcentagem
                    textposition='outside',   # Coloca os números para fora para não poluir
                    marker=dict(line=dict(color='#FFFFFF', width=1))
                )
                
                # Layout padronizado
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", 
                    plot_bgcolor="rgba(0,0,0,0)", 
                    font_color="#FFF", 
                    margin=dict(t=50, b=10, l=10, r=10),
                    showlegend=True,
                    legend=dict(
                        orientation="h",       # Legenda horizontal
                        yanchor="bottom", 
                        y=-0.3, 
                        xanchor="center", 
                        x=0.5
                    )
                )
                return fig

            c_g1, c_g2, c_g3 = st.columns(3)
            
            with c_g1:
                fig_res = gerar_grafico_resumo(df_quali_filt, 'Resolução', 'Resolução do Incidente')
                if fig_res: st.plotly_chart(fig_res, use_container_width=True)
                else: st.info("Sem dados de Resolução para os filtros atuais.")
                
                fig_uni = gerar_grafico_resumo(df_quali_filt, 'Uniforme Usado', 'Uniforme Utilizado')
                if fig_uni: st.plotly_chart(fig_uni, use_container_width=True)
                else: st.info("Sem dados de Uniforme para os filtros atuais.")

            with c_g2:
                fig_trans = gerar_grafico_resumo(df_quali_filt, 'Forma de Transição', 'Forma de Transição')
                if fig_trans: st.plotly_chart(fig_trans, use_container_width=True)
                else: st.info("Sem dados de Transição para os filtros atuais.")
                
                fig_sexo = gerar_grafico_resumo(df_quali_filt, 'Sexo do Causador', 'Sexo do Causador')
                if fig_sexo: st.plotly_chart(fig_sexo, use_container_width=True)
                else: st.info("Sem dados de Sexo para os filtros atuais.")


            with c_g3:
                fig_mod = gerar_grafico_resumo(df_quali_filt, 'Modalidade do incidente', 'Modalidade do incidente')
                if fig_mod: st.plotly_chart(fig_mod, use_container_width=True)
                else: st.info("Sem dados de Modalidade do incidente para os filtros atuais.")
                
                fig_tip = gerar_grafico_resumo(df_quali_filt, 'Tipologia', 'Tipologia')
                if fig_tip: st.plotly_chart(fig_tip, use_container_width=True)
                else: st.info("Sem dados de Tipologia para os filtros atuais.")

            st.markdown("---")



            # ══════════════════════════════════════════════════════════════════════════════
            # SEÇÃO: INFORMAÇÃO LONGITUDINAL
            # ══════════════════════════════════════════════════════════════════════════════

            st.markdown("<h5 style='color: #FFD700;'>✔️ Informação Longitudinal</h5>", unsafe_allow_html=True)
            st.markdown("<p style='color: #aaa; font-size: 0.95rem;'>Como tem evoluído o volume de negociações ao longo do tempo?</p>", unsafe_allow_html=True)

            col_data = next((col for col in ['Data da ocorrência', 'Data', 'DATA'] if col in df_quali_filt.columns), None)
            if col_data:
                df_quali_filt['Data_DT'] = pd.to_datetime(df_quali_filt[col_data], errors='coerce')
                df_time = df_quali_filt.dropna(subset=['Data_DT']).sort_values('Data_DT')
                if not df_time.empty:
                    df_time['Mes_Ano'] = df_time['Data_DT'].dt.to_period('M').astype(str)
                    df_trend = df_time['Mes_Ano'].value_counts().sort_index().reset_index()
                    df_trend.columns = ['Mês', 'Qtd Ocorrências']
                    
                    st.markdown(
                        f"""
                        **Resumo:** Total de {len(df_time)} ocorrências registradas de {df_trend['Mês'].min()} a {df_trend['Mês'].max()}
                        """
                    )
                    
                    fig_time = px.line(
                        df_trend, 
                        x='Mês', 
                        y='Qtd Ocorrências', 
                        markers=True, 
                        color_discrete_sequence=['#FFD700'],
                        title="Evolução Temporal de Negociações"
                    )
                    fig_time.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", 
                        plot_bgcolor="rgba(0,0,0,0)", 
                        font_color="#FFF",
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig_time, use_container_width=True)
                else: 
                    st.info("⚠️ Sem datas válidas nos registros.")
            else: 
                st.info("⚠️ Coluna de Data não encontrada. Adicione uma coluna 'Data' ao seu formulário.")

            st.markdown("---")


        # ============================================================
        # BLOCO: Ranking de Técnicas + Padrões e Correlações
        # ============================================================
        
        st.markdown("""
                        <div class='info-card'>
                        <h5 style='color: #FFD700; margin-top: 0;'>Ranking e Efetividade das Técnicas Aplicadas</h5>
                        <p style='font-size:1.2rem;color:#ddd;'>
                        Técnicas mais usadas pelos Negociadores e sua Efetividade</strong>                 
                        </p>
                        </div>
                        """, unsafe_allow_html=True)        

        col_left, col_center, col_right = st.columns([1, 1, 1])  
        with col_center:
            is_ranking = render_toggle_button(
                label="✔️ Abrir Ranking de Técnicas",
                session_key="ranking_de_tecnicas_expanded",
                button_key="btn_ranking_tecnicas"
            )

        st.markdown("---")

        if is_ranking:
            
            if not df_tec.empty:
                df_tec["Neg_Limpo"] = (
                    df_tec["Negociador Principal do incidente crítico"].apply(limpar_valor)
                    if "Negociador Principal do incidente crítico" in df_tec.columns
                    else "N/D"
                )
                df_tec["Tip_Limpa"] = (
                    df_tec["Tipologia do incidente crítico"].apply(limpar_valor)
                    if "Tipologia do incidente crítico" in df_tec.columns
                    else "N/D"
                )
                df_tec["Mod_Limpa"] = (
                    df_tec["Modalidade do incidente crítico"].apply(limpar_valor)
                    if "Modalidade do incidente crítico" in df_tec.columns
                    else "N/D"
                )

                df_tec_filt = df_tec.copy()
                if filtro_neg_g != "Todos":
                    df_tec_filt = df_tec_filt[df_tec_filt["Neg_Limpo"] == filtro_neg_g]
                if filtro_tip_g != "Todas":
                    df_tec_filt = df_tec_filt[df_tec_filt["Tip_Limpa"] == filtro_tip_g]
                if filtro_mod_g != "Todas":
                    df_tec_filt = df_tec_filt[df_tec_filt["Mod_Limpa"] == filtro_mod_g]

            # ----------------------------------------------------------
            # Ranking visual
            # ----------------------------------------------------------
            if not df_tec_filt.empty:
                col_t = next(
                    (
                        col
                        for col in ["TÉCNICAS", "TECNICAS", "TÉCNICA", "TECNICA"]
                        if col in df_tec_filt.columns
                    ),
                    None,
                )
                if col_t:
                    freq_global = df_tec_filt[col_t].value_counts().reset_index()
                    freq_global.columns = ["Técnica", "Vezes Utilizada"]

                    c_tab, c_tree = st.columns([1, 2])
                    with c_tab:
                        st.dataframe(freq_global, use_container_width=True, hide_index=True)
                    with c_tree:
                        fig_g = px.treemap(
                            freq_global,
                            path=["Técnica"],
                            values="Vezes Utilizada",
                            color="Vezes Utilizada",
                            color_continuous_scale="Oranges",
                        )
                        fig_g.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font_color="#FFF",
                            margin=dict(t=0, l=0, r=0, b=0),
                        )
                        st.plotly_chart(fig_g, use_container_width=True)
                else:
                    st.warning("Coluna 'TÉCNICAS' não encontrada.")
            else:
                st.info("Nenhuma técnica encontrada para os filtros selecionados.")

            st.markdown("---")


            #NOVAS ANALISES 21MAI

                        
            # ============================================================
            # ANÁLISE 4: EFETIVIDADE DAS TÉCNICAS (SÉRIE HISTÓRICA)
            # ============================================================

            st.markdown("<h5 style='color: #FFD700;'>Efetividade das Técnicas</h5>", unsafe_allow_html=True)

            col_left, col_center, col_right = st.columns([1, 1, 1])
            with col_center:
                is_Efetividade_Técnicas = render_toggle_button(
                    label="✔️ Abrir Efetividade das Técnicas",
                    session_key="Efetividade_Técnicas",
                    button_key="btn_Efetividade_Técnicas"
                )

            st.markdown("---")

            if is_Efetividade_Técnicas:
                if not df_tec_filt.empty:
                    col_tecnica = next(
                        (col for col in ['TÉCNICAS', 'TECNICAS', 'TÉCNICA', 'TECNICA'] if col in df_tec_filt.columns),
                        None,
                    )
                    col_reacao = next(
                        (col for col in df_tec_filt.columns if 'ATITUDE' in col.upper()),
                        None,
                    )

                    if col_tecnica and col_reacao:

                        def normalizar_reacao(val):
                            if val is None:
                                return None
                            s = str(val).strip()
                            if any(x in s for x in ["-1", "-1.0", "🔴", "Negativa", "negativa"]):
                                return -1
                            elif any(x in s for x in ["0", "0.0", "⚪", "Neutra", "neutra"]):
                                return 0
                            elif any(x in s for x in ["1", "1.0", "🟢", "Positiva", "positiva"]):
                                return 1
                            else:
                                return None

                        df_ef = df_tec_filt.copy()
                        df_ef['_reacao_num'] = df_ef[col_reacao].apply(normalizar_reacao)

                        # ── Agrupar por técnica ───────────────────────────────
                        resumo = []
                        for tecnica, grupo in df_ef.groupby(col_tecnica):
                            total    = len(grupo)
                            positivo = (grupo['_reacao_num'] == 1).sum()
                            neutro   = (grupo['_reacao_num'] == 0).sum()
                            negativo = (grupo['_reacao_num'] == -1).sum()
                            inaud    = grupo['_reacao_num'].isna().sum()

                            observados = positivo + neutro + negativo
                            if observados > 0:
                                score = round(((positivo - negativo) / observados) * 100, 1)
                            else:
                                score = None

                            resumo.append({
                                "Técnica":      tecnica,
                                "Total":        total,
                                "Positivas":    int(positivo),
                                "Neutras":      int(neutro),
                                "Negativas":    int(negativo),
                                "Inaudível":    int(inaud),
                                "Score":        score
                            })

                        df_resumo_tec = pd.DataFrame(resumo).sort_values("Score", ascending=False, na_position='last')

                        # ── SCORECARD GERAL ───────────────────────────────────
                        st.markdown("### ✔️ Resumo Geral")

                        total_usos     = int(df_resumo_tec["Total"].sum())
                        total_positivo = int(df_resumo_tec["Positivas"].sum())
                        total_negativo = int(df_resumo_tec["Negativas"].sum())
                        observados_total = total_positivo + int(df_resumo_tec["Neutras"].sum()) + total_negativo
                        score_geral    = round(((total_positivo - total_negativo) / max(1, observados_total)) * 100, 1)

                        col_eg1, col_eg2, col_eg3, col_eg4 = st.columns(4)
                        with col_eg1:
                            st.metric('Total de Usos', total_usos)
                        with col_eg2:
                            st.metric('Positivas', total_positivo, delta='🟢')
                        with col_eg3:
                            st.metric('Negativas', total_negativo, delta='🔴')
                        with col_eg4:
                            st.metric('Score Geral', f'{score_geral:+.1f}%')

                        # ── TABELA + GRÁFICO ──────────────────────────────────
                        st.markdown("### ✔️ Efetividade por Técnica")

                        col_ef1, col_ef2 = st.columns([1, 2])

                        with col_ef1:
                            st.dataframe(
                                df_resumo_tec[['Técnica', 'Total', 'Positivas', 'Negativas', 'Score']].head(10),
                                use_container_width=True,
                                hide_index=True
                            )

                        with col_ef2:
                            # ── GRÁFICO BARRAS EMPILHADAS (igual Aba Individual) ──
                            import plotly.graph_objects as go

                            tecnicas  = df_resumo_tec["Técnica"].tolist()
                            positivos = df_resumo_tec["Positivas"].tolist()
                            neutros   = df_resumo_tec["Neutras"].tolist()
                            negativos = df_resumo_tec["Negativas"].tolist()

                            fig_barras = go.Figure()

                            fig_barras.add_trace(go.Bar(
                                name="🟢 Positiva",
                                x=tecnicas, y=positivos,
                                marker_color="#10b981"
                            ))
                            fig_barras.add_trace(go.Bar(
                                name="⚪ Neutra",
                                x=tecnicas, y=neutros,
                                marker_color="#6b7280"
                            ))
                            fig_barras.add_trace(go.Bar(
                                name="🔴 Negativa",
                                x=tecnicas, y=negativos,
                                marker_color="#ef4444"
                            ))

                            fig_barras.update_layout(
                                barmode="stack",
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                font=dict(color="#fff"),
                                legend=dict(
                                    font=dict(color="#fff"),
                                    bgcolor="rgba(0,0,0,0.4)"
                                ),
                                xaxis=dict(tickfont=dict(color="#FFD700"), gridcolor="#333"),
                                yaxis=dict(tickfont=dict(color="#aaa"), gridcolor="#333"),
                                height=420,
                                margin=dict(t=20, b=120, l=40, r=40)
                            )

                            st.plotly_chart(fig_barras, use_container_width=True)

                        # ── LEITURA OPERACIONAL ───────────────────────────────
                        st.markdown("---")
                        st.markdown("### ✔️ Leitura Operacional")

                        # Só técnicas com pelo menos 2 usos observados
                        df_com_score = df_resumo_tec[
                            df_resumo_tec["Score"].notna() &
                            (df_resumo_tec["Total"] >= 2)
                        ]
                        if df_com_score.empty:
                            df_com_score = df_resumo_tec[df_resumo_tec["Score"].notna()]

                        if not df_com_score.empty:

                            # Mais efetiva
                            score_maximo = df_com_score["Score"].max()
                            tecnicas_maximas = df_com_score[df_com_score["Score"] == score_maximo]

                            if len(tecnicas_maximas) == 1:
                                melhor = tecnicas_maximas.iloc[0]
                                txt_melhor = (
                                    f"✅ <strong>Técnica mais efetiva:</strong> {melhor['Técnica']} "
                                    f"— Score {melhor['Score']:+.1f}% "
                                    f"({int(melhor['Positivas'])} positivas / {int(melhor['Total'])} usos)"
                                )
                            else:
                                tecnicas_nomes = ", ".join(tecnicas_maximas['Técnica'].tolist())
                                txt_melhor = (
                                    f"✅ <strong>Técnicas mais efetivas (empate):</strong> {tecnicas_nomes} "
                                    f"— Score {score_maximo:+.1f}%"
                                )

                            st.markdown(f"""
                            <div style='background:rgba(16,185,129,0.08);padding:12px;border-radius:8px;border-left:3px solid #10b981;margin-bottom:10px;'>
                            <p style='color:#ddd;font-size:0.9rem;margin:0;'>{txt_melhor}</p>
                            </div>
                            """, unsafe_allow_html=True)

                            # Menos efetiva
                            score_minimo = df_com_score["Score"].min()
                            tecnicas_minimas = df_com_score[df_com_score["Score"] == score_minimo]

                            if len(tecnicas_minimas) == 1:
                                pior = tecnicas_minimas.iloc[0]
                                txt_pior = (
                                    f"⚠️ <strong>Técnica menos efetiva:</strong> {pior['Técnica']} "
                                    f"— Score {pior['Score']:+.1f}% "
                                    f"({int(pior['Negativas'])} negativas / {int(pior['Total'])} usos)"
                                )
                            else:
                                tecnicas_nomes = ", ".join(tecnicas_minimas['Técnica'].tolist())
                                txt_pior = (
                                    f"⚠️ <strong>Técnicas menos efetivas (empate):</strong> {tecnicas_nomes} "
                                    f"— Score {score_minimo:+.1f}%"
                                )

                            st.markdown(f"""
                            <div style='background:rgba(239,68,68,0.08);padding:12px;border-radius:8px;border-left:3px solid #ef4444;margin-bottom:10px;'>
                            <p style='color:#ddd;font-size:0.9rem;margin:0;'>{txt_pior}</p>
                            </div>
                            """, unsafe_allow_html=True)

                        st.markdown("""
                        **Interpretação:**
                        - **Score > 50%** = Técnica efetiva (mais sucessos que fracassos)
                        - **Score próximo a 0%** = Técnica neutra (sucessos ≈ fracassos)
                        - **Score < -50%** = Técnica contraproducente (mais fracassos que sucessos)
                        """)

                    else:
                        st.warning("⚠️ Colunas necessárias não encontradas (TÉCNICAS e ATITUDE).")
                else:
                    st.info("⚠️ Nenhuma técnica encontrada para os filtros selecionados.")

            st.markdown("---")

            
            # ============================================================
            # ANÁLISE: CONVERGÊNCIA TEMÁTICA
            # ============================================================

        st.markdown("""
                        <div class='info-card'>
                        <h5 style='color: #FFD700; margin-top: 0;'>Convergência Temática: Quanto de sincronização temática existe entre negociador e causador</h5>
                        <p style='font-size:1.2rem;color:#ddd;'>
                        Análise descritiva da média de convergência temática</strong>                 
                        </p>
                        </div>
                        """, unsafe_allow_html=True)         
        

        # ── BOTÃO TOGGLE ───────────────────────────────────────────
        col_left, col_center, col_right = st.columns([1, 1, 1])
        with col_center:
            is_convergencia = render_toggle_button(
                label="✔️ Abrir Convergência Temática",
                session_key="analise5_convergencia_tematica",
                button_key="btn_analise5_convergencia_tematica"
            )

        st.markdown("---")

        if is_convergencia:                   

            if not df_quali_filt.empty:
                col_texto_c = 'TRANSCRIÇÃO DO CAUSADOR'
                col_texto_np = 'TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL'
                
                if col_texto_c in df_quali_filt.columns and col_texto_np in df_quali_filt.columns:
                    try:
                        # Calcular convergência para CADA APA
                        convergencias_apas = []
                        
                        for idx, row in df_quali_filt.iterrows():
                            txt_c = str(row[col_texto_c]).strip()
                            txt_np = str(row[col_texto_np]).strip()
                            
                            if len(txt_c.split()) > 5 and len(txt_np.split()) > 5:
                                try:
                                    temas_c = analise.extrair_temas_unicos(txt_c, resolucao_tipo='desconhecida')
                                    temas_np = analise.extrair_temas_unicos(txt_np, resolucao_tipo='desconhecida')
                                    
                                    if temas_c and temas_np:
                                        conv = analise.calcular_convergencia_tematica(temas_c, temas_np)
                                        convergencias_apas.append({
                                            'APA': idx,
                                            'Convergencia': conv['convergencia_geral'],
                                            'Compartilhados': len(conv['temas_compartilhados']),
                                            'So_Causador': len(conv['temas_exclusivos_causador']),
                                            'So_Negociador': len(conv['temas_exclusivos_negociador'])
                                        })
                                except:
                                    pass
                        
                        if convergencias_apas:
                            df_conv_agg = pd.DataFrame(convergencias_apas)
                            
                            media_conv = df_conv_agg['Convergencia'].mean()
                            mediana_conv = df_conv_agg['Convergencia'].median()
                            dp_conv = df_conv_agg['Convergencia'].std()
                            media_compartilhados = df_conv_agg['Compartilhados'].mean()
                            
                            # ── SCORECARD ────────────────────────────────
                            st.markdown("### Resumo da Convergência Temática")
                            
                            col_cv1, col_cv2, col_cv3, col_cv4 = st.columns(4)
                            
                            with col_cv1:
                                st.metric('Convergência Média', f'{media_conv:.1f}%')
                                st.caption(f'DP: ±{dp_conv:.1f}%')
                            
                            with col_cv2:
                                st.metric('Mediana', f'{mediana_conv:.1f}%')
                                st.caption(f'N = {len(df_conv_agg)} APAs')
                            
                            with col_cv3:
                                st.metric('Temas Compartilhados (Média)', f'{media_compartilhados:.1f}')
                                st.caption('Média por APA')
                            
                            with col_cv4:
                                st.metric('Range', f'{df_conv_agg["Convergencia"].min():.1f}% - {df_conv_agg["Convergencia"].max():.1f}%')
                                st.caption(f'Amplitude: {df_conv_agg["Convergencia"].max() - df_conv_agg["Convergencia"].min():.1f}%')
                            
                            # ── DISTRIBUIÇÃO ─────────────────────────────
                            st.markdown("---")
                            st.markdown("### ✔️ Distribuição da Convergência")
                            
                            st.markdown("""
                            **O que são esses gráficos?**
                            
                            Imagine 6 negociações diferentes. Em cada uma, calculamos quanto o negociador e o causador falam dos **mesmos temas** (convergência).
                            
                            - **Negociação 1:** 45% de sintonia temática
                            - **Negociação 2:** 52% de sintonia temática
                            - **Negociação 3:** 38% de sintonia temática
                            - ... e assim por diante
                            
                            Esses dois gráficos mostram como essas porcentagens se distribuem:
                            
                            **Gráfico da Esquerda (Histograma):** "Em quantas negociações tivemos cada nível de sintonia?"
                            - Se há uma barra alta em 45%, significa que muitas negociações tiveram ~45% de convergência
                            - Se a distribuição é espalhada, significa que a sintonia varia muito de ocorrência para ocorrência
                            
                            **Gráfico da Direita (Box Plot):** "Qual é a faixa típica de sintonia?"
                            - **A linha do meio (mediana):** 50% das negociações tiveram sintonia até esse valor
                            - **A caixa:** Mostra onde estão a maioria dos valores (do 25º ao 75º percentil)
                            - **Os pontinhos:** Ocorrências com sintonia muito diferente das outras (outliers)
                            """)
                            
                            col_cv_hist1, col_cv_hist2 = st.columns(2)
                            
                            with col_cv_hist1:
                                fig_conv_hist = px.histogram(
                                    df_conv_agg,
                                    x='Convergencia',
                                    nbins=8,
                                    title='Distribuição da Convergência Temática'
                                )
                                fig_conv_hist.update_traces(marker_color='#FF8C00')
                                fig_conv_hist.update_layout(
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    font_color='#FFF',
                                    height=300,
                                    xaxis_title='Convergência (%)',
                                    yaxis_title='Número de Negociações'
                                )
                                st.plotly_chart(fig_conv_hist, use_container_width=True)
                            
                            with col_cv_hist2:
                                fig_box_conv = px.box(
                                    df_conv_agg,
                                    y='Convergencia',
                                    title='Faixa Típica de Convergência'
                                )
                                fig_box_conv.update_traces(marker_color='#FF8C00')
                                fig_box_conv.update_layout(
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    font_color='#FFF',
                                    height=300,
                                    yaxis_title='Convergência (%)'
                                )
                                st.plotly_chart(fig_box_conv, use_container_width=True)
                            
                            st.markdown("""
                            **Como interpretar os números na prática:**
                            
                            - **Convergência 40-60%:** Normal — há sempre alguma diferença de perspectiva entre negociador e causador
                            - **Convergência > 60%:** Excelente — o negociador está na "mesma frequência" que o causador
                            - **Convergência < 40%:** Alerta — há risco de desencontro de comunicação
                            
                            **Dica:** Se a maioria das suas negociações tem convergência > 50%, sua equipe está fazendo escuta ativa de forma consistente! 🎯
                            """)
                            
                            # ── ANÁLISE POR NEGOCIADOR (SE FILTRADO) ──────
                            if filtro_neg_g != "Todos":
                                st.markdown("---")
                                st.markdown("#### ✔️ Análise Específica do Negociador")
                                
                                conv_neg = df_conv_agg['Convergencia'].mean()
                                
                                if conv_neg >= 60:
                                    status = "✅ Excelente — Alta sintonia temática com causadores"
                                    cor = "🟢"
                                elif conv_neg >= 40:
                                    status = "⚠️ Moderado — Alguns temas divergentes"
                                    cor = "🟡"
                                else:
                                    status = "❌ Fraco — Muita divergência temática. Recomendado reforço em escuta ativa"
                                    cor = f"{cor}"
                                
                                st.markdown(f"""
                                **Negociador:** {filtro_neg_g}
                                
                                **Convergência média:** {conv_neg:.1f}%
                                
                                **Status:** {status}
                                
                                **Recomendação:**
                                - Se convergência < 40%: Investir em treinamento de escuta ativa
                                - Se convergência 40-60%: Consolidar técnicas de rapport
                                - Se convergência > 60%: Excelente! Usar como referência para equipe
                                """)
                            
                            # ── LEITURA OPERACIONAL ──────────────────────
                            st.markdown("---")
                            st.markdown("### ✔️ Leitura Operacional")
                            
                            st.markdown(f"""
                            **O que os dados mostram:**
                            
                            - **Convergência média de {media_conv:.1f}%:** Em média, há {media_conv:.0f}% de sincronização temática
                            - **Variação (DP ±{dp_conv:.1f}%):** Há oscilação significativa entre ocorrências
                            - **Temas compartilhados (média {media_compartilhados:.1f}):** Cada negociador-causador compartilha ~{media_compartilhados:.0f} temas em comum
                            
                            **Interpretação:**
                            - Convergência alta (> 60%) = Negociador e causador falam dos mesmos assuntos
                            - Convergência baixa (< 40%) = Universos temáticos diferentes = risco de desencontro
                            
                            **Ação Recomendada:**
                            Se convergência < 40%, implementar treinamento focado em:
                            1. **Escuta Ativa** — Entender os temas do causador antes de impor a agenda
                            2. **Validação Emocional** — Reconhecer as preocupações mesmo que diferentes
                            3. **Ponte Temática** — Conectar temas do causador aos temas da resolução
                            """)
                        
                        else:
                            st.info('⚠️ Sem dados suficientes para calcular convergência temática nos filtros atuais.')
                    
                    except Exception as e:
                        st.warning(f'⚠️ Erro ao processar convergência: {str(e)[:80]}')
                else:
                    st.warning('⚠️ Colunas de transcrição não encontradas.')
        # ──────────────────────────────────────────────────────────
# ANÁLISE: REGRESSÃO LINEAR MULTIVARIADA
# O que prediz queda de agressividade? Análise robusta e validada
# ──────────────────────────────────────────────────────────

st.markdown("""
<div class='info-card'>
<h5 style='color: #FFD700; margin-top: 0;'>📊 O que Prediz Queda de Agressividade?</h5>
<p style='font-size:1rem;color:#ddd;'>
Análise multivariada rigorosa com validação estatística.
Identifica quais fatores realmente influenciam a redução de agressividade,
controlando confundidores (viés de negociador, tipo de ocorrência, etc).
</p>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────
# BOTÃO TOGGLE
# ──────────────────────────────────────────────────────────
col_left, col_center, col_right = st.columns([1, 1, 1])
with col_center:
    is_regressao = render_toggle_button(
        label="✔️ Abrir Análise Multivariada",
        session_key="analise_regressao",
        button_key="btn_analise_regressao"
    )

st.markdown("---")

# ──────────────────────────────────────────────────────────
# CONTEÚDO (Dentro do if)
# ──────────────────────────────────────────────────────────
if is_regressao:
    
    # ═══════════════════════════════════════════════════════════
    # PASSO 1: PREPARAR DADOS
    # ═══════════════════════════════════════════════════════════
    
    with st.spinner("⏳ Preparando dados..."):
        # Encontrar colunas
        col_agr_princ_ch = achar_coluna(df_quali_filt, "Principal", "Agressividade", "Chegada")
        col_agr_princ_en = achar_coluna(df_quali_filt, "Principal", "Agressividade", "Encerramento")
        col_agr_sec_ch = achar_coluna(df_quali_filt, "Secundário", "Agressividade", "Chegada")
        col_agr_sec_en = achar_coluna(df_quali_filt, "Secundário", "Agressividade", "Encerramento")
        col_agr_lider_ch = achar_coluna(df_quali_filt, "Líder", "Agressividade", "Chegada")
        col_agr_lider_en = achar_coluna(df_quali_filt, "Líder", "Agressividade", "Encerramento")
        
        col_recep_princ_ch = achar_coluna(df_quali_filt, "Principal", "Receptividade", "Chegada")
        
        # Validar colunas
        colunas_necessarias = [col_agr_princ_ch, col_agr_princ_en, col_agr_sec_ch, 
                              col_agr_sec_en, col_agr_lider_ch, col_agr_lider_en]
        
        if not all(colunas_necessarias):
            st.error("❌ Colunas de agressividade não encontradas. Verifique o formulário.")
        else:
            # Calcular deltas
            df_reg_prep = analise.calcular_delta_agressividade_consenso(
                df_quali_filt,
                col_agr_princ_ch, col_agr_princ_en,
                col_agr_sec_ch, col_agr_sec_en,
                col_agr_lider_ch, col_agr_lider_en
            )
            
            # Preparar para regressão
            df_modelo, erro = analise.preparar_dados_regressao(
                df_reg_prep,
                col_tempo="Tempo de Negociação Real",
                col_negociador="Negociador Principal do incidente crítico",
                col_tipologia="Tipologia",
                col_modalidade="Modalidade",
                col_resolucao="Resolução",
                col_recep_chegada=col_recep_princ_ch
            )
            
            if erro:
                st.warning(f"⚠️ {erro}")
            else:
                # ═══════════════════════════════════════════════════════════
                # PASSO 2: AJUSTAR MODELO
                # ═══════════════════════════════════════════════════════════
                
                resultado_modelo, erro_modelo = analise.ajustar_regressao_linear(df_modelo)
                
                if erro_modelo:
                    st.error(f"❌ {erro_modelo}")
                else:
                    
                    # ═══════════════════════════════════════════════════════════
                    # SEÇÃO 1: RESUMO DO MODELO
                    # ═══════════════════════════════════════════════════════════
                    
                    st.markdown("""
                    <div class='info-card'>
                    <h5 style='color: #FFD700;'>📈 Qualidade do Modelo</h5>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("N (Ocorrências)", resultado_modelo['n'])
                    with col2:
                        st.metric("R² (Variância Explicada)", f"{resultado_modelo['r2']:.1%}")
                    with col3:
                        st.metric("R² Ajustado", f"{resultado_modelo['r2_adj']:.1%}")
                    with col4:
                        p_f = resultado_modelo['p_f']
                        sig = "✅ Significativo" if p_f < 0.05 else "❌ Não significativo"
                        st.metric("Modelo Global", sig)
                    
                    st.markdown("""
                    <div style='background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; margin-top: 10px;'>
                    <strong>Interpretação:</strong> O modelo explica <strong>{:.1%}</strong> da variação em queda de agressividade.
                    O p-value global é <strong>{:.4f}</strong> ({}).
                    </div>
                    """.format(
                        resultado_modelo['r2'],
                        resultado_modelo['p_f'],
                        "✅ Modelo válido (p < 0.05)" if resultado_modelo['p_f'] < 0.05 else "❌ Modelo fraco (p ≥ 0.05)"
                    ), unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # ═══════════════════════════════════════════════════════════
                    # SEÇÃO 2: COEFICIENTES
                    # ═══════════════════════════════════════════════════════════
                    
                    st.markdown("""
                    <div class='info-card'>
                    <h5 style='color: #FFD700;'>🎯 Coeficientes do Modelo</h5>
                    """, unsafe_allow_html=True)
                    
                    df_coef = analise.extrair_coeficientes_significativos(resultado_modelo)
                    
                    # Tabela formatada
                    st.dataframe(
                        df_coef.style.format({
                            'Coeficiente': '{:.3f}',
                            'SE': '{:.3f}',
                            't-stat': '{:.2f}',
                            'p-value': '{:.4f}',
                            'IC_Lower': '{:.3f}',
                            'IC_Upper': '{:.3f}'
                        }).highlight_max(subset=['Coeficiente'], color='#10b981', axis=0)
                        .highlight_min(subset=['Coeficiente'], color='#f59e0b', axis=0),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Gráfico de coeficientes com IC
                    df_plot = df_coef[df_coef['Variável'] != '(Intercept)'].copy()
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df_plot['IC_Lower'],
                        y=df_plot['Variável'],
                        mode='markers',
                        marker=dict(size=1, color='rgba(0,0,0,0)'),
                        showlegend=False
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=df_plot['Coeficiente'],
                        y=df_plot['Variável'],
                        mode='markers',
                        marker=dict(
                            size=8,
                            color=['#10b981' if x > 0 else '#f59e0b' for x in df_plot['Coeficiente']]
                        ),
                        name='Coeficiente',
                        text=df_plot.apply(
                            lambda r: f"{r['Variável']}<br>β = {r['Coeficiente']:.3f}<br>p = {r['p-value']:.4f}",
                            axis=1
                        ),
                        hovertemplate='%{text}<extra></extra>'
                    ))
                    
                    for idx, row in df_plot.iterrows():
                        fig.add_trace(go.Scatter(
                            x=[row['IC_Lower'], row['IC_Upper']],
                            y=[row['Variável'], row['Variável']],
                            mode='lines',
                            line=dict(color='#888', width=2),
                            showlegend=False,
                            hoverinfo='skip'
                        ))
                    
                    fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
                    fig.update_layout(
                        title="Coeficientes com IC 95%",
                        xaxis_title="Coeficiente",
                        yaxis_title="Variável",
                        height=400,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#FFF",
                        hovermode='closest'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # ═══════════════════════════════════════════════════════════
                    # SEÇÃO 3: COMPARAÇÃO DE PERCEPÇÕES
                    # ═══════════════════════════════════════════════════════════
                    
                    st.markdown("""
                    <div class='info-card'>
                    <h5 style='color: #FFD700;'>🔍 Triangulação: Consenso dos 3 Negociadores</h5>
                    """, unsafe_allow_html=True)
                    
                    col_tri1, col_tri2, col_tri3, col_tri4 = st.columns(4)
                    
                    delta_princ_mean = df_reg_prep['delta_princ'].dropna().mean()
                    delta_sec_mean = df_reg_prep['delta_sec'].dropna().mean()
                    delta_lider_mean = df_reg_prep['delta_lider'].dropna().mean()
                    delta_cons_mean = df_reg_prep['delta_consenso'].dropna().mean()
                    
                    with col_tri1:
                        st.metric("Principal (Média)", f"{delta_princ_mean:.2f}")
                    with col_tri2:
                        st.metric("Secundário (Média)", f"{delta_sec_mean:.2f}")
                    with col_tri3:
                        st.metric("Líder (Média)", f"{delta_lider_mean:.2f}")
                    with col_tri4:
                        st.metric("Consenso (Média)", f"{delta_cons_mean:.2f}")
                    
                    # Gráfico de distribuição
                    fig_dist = go.Figure()
                    
                    for label, dados, cor in [
                        ("Principal", df_reg_prep['delta_princ'].dropna(), '#F97316'),
                        ("Secundário", df_reg_prep['delta_sec'].dropna(), '#FB923C'),
                        ("Líder", df_reg_prep['delta_lider'].dropna(), '#FBBF24'),
                        ("Consenso", df_reg_prep['delta_consenso'].dropna(), '#10b981')
                    ]:
                        fig_dist.add_trace(go.Box(y=dados, name=label, marker_color=cor))
                    
                    fig_dist.update_layout(
                        title="Distribuição de Deltas por Negociador",
                        yaxis_title="Delta de Agressividade",
                        height=350,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#FFF",
                        boxmode='group'
                    )
                    st.plotly_chart(fig_dist, use_container_width=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # ═══════════════════════════════════════════════════════════
                    # SEÇÃO 4: DIAGNÓSTICOS
                    # ═══════════════════════════════════════════════════════════
                    
                    st.markdown("""
                    <div class='info-card'>
                    <h5 style='color: #FFD700;'>🔧 Diagnósticos do Modelo</h5>
                    <p style='font-size: 0.85rem; color: #aaa;'>
                    Validação de assumções estatísticas.
                    </p>
                    """, unsafe_allow_html=True)
                    
                    diags = analise.diagnosticos_qualidade(resultado_modelo)
                    
                    col_d1, col_d2, col_d3 = st.columns(3)
                    
                    with col_d1:
                        status = "✅" if diags['normalidade']['p_value'] > 0.05 else "⚠️"
                        st.markdown(f"""
                        **{status} Normalidade dos Resíduos**
                        
                        p-value: {diags['normalidade']['p_value']:.4f}
                        
                        {diags['normalidade']['interpretacao']}
                        
                        _{diags['normalidade']['implicacao']}_
                        """)
                    
                    with col_d2:
                        status = "✅" if diags['homocedasticidade']['p_value'] > 0.05 else "⚠️"
                        st.markdown(f"""
                        **{status} Homocedasticidade**
                        
                        p-value: {diags['homocedasticidade']['p_value']:.4f}
                        
                        {diags['homocedasticidade']['interpretacao']}
                        
                        _{diags['homocedasticidade']['implicacao']}_
                        """)
                    
                    with col_d3:
                        vif_max = diags['colinearidade']['vif_max']
                        status = "✅" if vif_max < 5 else "⚠️"
                        st.markdown(f"""
                        **{status} Colinearidade (VIF)**
                        
                        VIF máximo: {vif_max:.2f}
                        
                        {diags['colinearidade']['interpretacao']}
                        
                        _{diags['colinearidade']['implicacao']}_
                        """)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # ═══════════════════════════════════════════════════════════
                    # SEÇÃO 5: RESÍDUOS
                    # ═══════════════════════════════════════════════════════════
                    
                    st.markdown("""
                    <div class='info-card'>
                    <h5 style='color: #FFD700;'>📊 Diagnóstico de Resíduos</h5>
                    """, unsafe_allow_html=True)
                    
                    col_res1, col_res2 = st.columns(2)
                    
                    with col_res1:
                        fig_res = go.Figure()
                        fig_res.add_trace(go.Scatter(
                            x=resultado_modelo['y_pred'],
                            y=resultado_modelo['residuos'],
                            mode='markers',
                            marker=dict(color='#F97316', size=6),
                            text=resultado_modelo['residuos'],
                            hovertemplate='Predito: %{x:.2f}<br>Resíduo: %{y:.2f}<extra></extra>'
                        ))
                        fig_res.add_hline(y=0, line_dash="dash", line_color="gray")
                        fig_res.update_layout(
                            title="Resíduos vs Preditos",
                            xaxis_title="Valores Preditos",
                            yaxis_title="Resíduos",
                            height=300,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font_color="#FFF"
                        )
                        st.plotly_chart(fig_res, use_container_width=True)
                    
                    with col_res2:
                        fig_qq = go.Figure()
                        res_sorted = np.sort(resultado_modelo['residuos'])
                        q_teorico = np.sort(np.random.normal(0, resultado_modelo['se_residuos'], 1000))
                        
                        fig_qq.add_trace(go.Scatter(
                            x=q_teorico,
                            y=res_sorted,
                            mode='markers',
                            marker=dict(color='#10b981', size=5),
                            name='Q-Q Plot'
                        ))
                        
                        # Linha diagonal
                        min_val = min(q_teorico.min(), res_sorted.min())
                        max_val = max(q_teorico.max(), res_sorted.max())
                        fig_qq.add_trace(go.Scatter(
                            x=[min_val, max_val],
                            y=[min_val, max_val],
                            mode='lines',
                            line=dict(color='gray', dash='dash'),
                            name='Normal',
                            showlegend=True
                        ))
                        
                        fig_qq.update_layout(
                            title="Q-Q Plot (Normalidade)",
                            xaxis_title="Quantis Teóricos",
                            yaxis_title="Quantis Observados",
                            height=300,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font_color="#FFF"
                        )
                        st.plotly_chart(fig_qq, use_container_width=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

                                     

# ============================================================
# ANÁLISE DE PERFIL DE NEGOCIADORES
# (Adicionar na Série Histórica, ANTES da "Síntese Interpretativa por IA")
# ============================================================

st.markdown("""
<div class='info-card'>
<h5 style='color: #FFD700;'>Perfil de Negociadores: Escuta Ativa vs Persuasão</h5>
<p style='font-size:1.1rem;color:#ddd;'>
Análise estatística comparativa dos padrões de negociação por negociador.
Identifica tendências, agrupa similares e testa significância estatística.
</p>
</div>
""", unsafe_allow_html=True)

col_left, col_center, col_right = st.columns([1, 1, 1])

with col_center:
    is_perfil_negociadores = render_toggle_button(
        label="✔️ Abrir Análise de Perfil",
        session_key="perfil_negociadores",
        button_key="btn_perfil_negociadores"
    )

st.markdown("---")

if is_perfil_negociadores:
    
    # ── CARREGAR DADOS ──────────────────────────────────────────
    try:
        # Importar função de análise
        from analise import (
            analisar_perfil_negociadores,
            gerar_grafo_palavras_com_estilo,
            gerar_legenda_negociadores_dinamica,
            gerar_tabela_score,
            gerar_scatter_score_efetividade,
            gerar_barras_grupos,
            classificar_tecnica
        )
        
        # Assumindo que df_tec está carregado (como nas análises anteriores)
        df_tec = st.session_state.get("df_tec", pd.DataFrame())
        
        if df_tec.empty:
            st.warning("⚠️ Tabela de técnicas não carregada.")
        else:
            
            # ── EXECUTAR ANÁLISE ────────────────────────────────────
            with st.spinner("⏳ Analisando perfis de negociadores..."):
                resultado_analise = analisar_perfil_negociadores(df_tec)
                
                df_resultado = resultado_analise['df_resultado']
                df_tec_classificado = resultado_analise['df_tecnicas_classificadas']
                anova = resultado_analise['anova']
                chi2 = resultado_analise['chi2']
                kmeans = resultado_analise['kmeans']
            
            # Gerar paleta de cores para negociadores (dinâmica)
            negociadores_unicos = df_resultado['Negociador'].unique()
            paleta_cores = {
                'laranja_forte': '#F97316',        # Laranja vibrante (principal)
                'laranja_medio': '#FB923C',        # Laranja médio
                'laranja_claro': '#FDBA74',        # Laranja claro
                'laranja_muito_claro': '#FED7AA',  # Laranja pastel
                'amarelo': '#FBBF24',              # Amarelo ouro
                'amarelo_claro': '#FCD34D',        # Amarelo claro
                'amber': '#F59E0B',                # Âmbar quente
                'amber_claro': '#FDBF28',          # Âmbar claro
                'preto': '#000000',                # Preto puro
                'cinza_escuro': '#1F2937',         # Cinza escuro (neutro)
                'cinza_medio': '#374151',          # Cinza médio
                'laranja_escuro': '#EA580C',       # Laranja escuro
                'vermelho_laranja': '#DC2626',     # Vermelho-laranja
            }
            
            # Converter para lista para melhor controle de alocação
            cores_lista = list(paleta_cores.values())
            
            # Alocar cores dinamicamente aos negociadores
            negociadores_cores = {
                neg: cores_lista[i % len(cores_lista)]
                for i, neg in enumerate(negociadores_unicos)
            }

            
            cores_lista = list(paleta_cores.values())
            negociadores_cores = {
                neg: cores_lista[i % len(cores_lista)]
                for i, neg in enumerate(negociadores_unicos)
            }
            
            # ── CRIAR TABS ──────────────────────────────────────────
            tab_score, tab_grafo, tab_stats, tab_kmeans = st.tabs([
                "✔️ Scores e Efetividades",
                "🕸️ Grafo de Palavras",
                "✔️ Testes Estatísticos",
                "✔️ Clusters (K-means)"
            ])
            
            # ── TAB 1: SCORES ───────────────────────────────────────
            with tab_score:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color: #FFD700; margin-top: 0;'>Score de Tendência</h5>
                <p style='font-size:0.9rem;color:#aaa;'>
                Score = -100 (100% Persuasão) a +100 (100% Escuta Ativa)
                <br>Ponderado pela atitude do causador em cada técnica aplicada.
                </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Tabela
                st.markdown("### 📋 Tabela de Resultados")
                df_display = gerar_tabela_score(df_resultado)
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                
                # Gráfico Scatter
                st.markdown("---")
                st.markdown("### 📊 Score vs Efetividade Média")
                fig_scatter = gerar_scatter_score_efetividade(df_resultado)
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                # Gráfico Barras
                st.markdown("---")
                st.markdown("### 📊 Distribuição de Técnicas")
                fig_barras = gerar_barras_grupos(df_resultado)
                st.plotly_chart(fig_barras, use_container_width=True)
            
            # ── TAB 2: GRAFO ────────────────────────────────────────
            
            #

            with tab_grafo:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color: #FFD700; margin-top: 0;'>🕸️ Rede de Palavras</h5>
                <p style='font-size:0.9rem;color:#aaa;'>
                Palavras dos trechos de transcrição, coloridas por negociador.
                Tamanho = Frequência | Conexões = Co-ocorrência
                </p>
                </div>
                """, unsafe_allow_html=True)
                
                # ── LEGENDA DINÂMICA ──
                
                if negociadores_cores:
                    st.markdown("""
                    <div style='
                        background: rgba(30, 30, 30, 0.85);
                        backdrop-filter: blur(16px) saturate(180%);
                        -webkit-backdrop-filter: blur(16px) saturate(180%);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 12px;
                        padding: 15px;
                        margin-bottom: 20px;
                    '>
                    <h5 style='color: #FFD700; margin-top: 0; margin-bottom: 15px;'>🎨 Legenda de Negociadores</h5>
                    <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;'>
                    """, unsafe_allow_html=True)
                    
                    cols = st.columns(min(3, len(negociadores_cores)))
                    for i, (neg, cor) in enumerate(sorted(negociadores_cores.items())):
                        with cols[i % len(cols)]:
                            st.markdown(f"""
                            <div style='
                                display: flex;
                                align-items: center;
                                background: rgba(255, 255, 255, 0.05);
                                padding: 10px;
                                border-radius: 8px;
                                border-left: 4px solid {cor};
                            '>
                                <div style='
                                    width: 24px;
                                    height: 24px;
                                    background-color: {cor};
                                    border-radius: 50%;
                                    margin-right: 10px;
                                '></div>
                                <span style='color: #FFF; font-weight: 500;'>{neg}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    st.markdown("</div></div>", unsafe_allow_html=True)
                
                with st.spinner("✔️ Gerando grafo com glassmorphism..."):
                    try:
                        net = gerar_grafo_palavras_com_estilo(df_tec_classificado, negociadores_cores)
                        
                        if net is None:
                            st.warning("⚠️ Dados insuficientes para gerar o grafo (precisa de mais trechos de transcrição).")
                        else:
                            try:
                                import tempfile
                                import os
                                
                                # Usar arquivo temporário
                                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                                    temp_file = f.name
                                
                                # Renderizar e salvar
                                net.write_html(temp_file, notebook=False)
            
                                # Ler arquivo
                                with open(temp_file, 'r', encoding='utf-8') as f:
                                    html_content = f.read()
                                
                                # INJETAR CSS PARA FUNDO PRETO/GLASSMORPHISM
                                html_content = html_content.replace(
                                    '<style type="text/css">',
                                    '''<style type="text/css">
                                    html, body {
                                        margin: 0;
                                        padding: 0;
                                        background: rgba(0, 0, 0, 0.95) !important;
                                        backdrop-filter: blur(16px) saturate(180%);
                                        -webkit-backdrop-filter: blur(16px) saturate(180%);
                                    }
                                    #mynetwork {
                                        background: rgba(30, 30, 30, 0.9) !important;
                                        backdrop-filter: blur(16px) saturate(180%);
                                        -webkit-backdrop-filter: blur(16px) saturate(180%);
                                    }
                                    '''
                                )
                                
                                # Exibir grafo
                                st.components.v1.html(html_content, height=800, scrolling=True)
                                
                                # Limpar arquivo temporário
                                try:
                                    os.remove(temp_file)
                                except:
                                    pass
                                
                                st.success("✅ Grafo gerado com sucesso!")
                                
                                # Informações sobre o grafo
                                st.markdown("""
                                ### 💡 Como interpretar:
                                - **Bolinha GRANDE**: Palavra muito frequente
                                - **Bolinha PEQUENA**: Palavra pouco frequente
                                - **COR**: Qual negociador mais usou a palavra
                                - **LINHAS**: Palavras que aparecem juntas nos trechos
                                """)
                                
                            except Exception as e:
                                st.error(f"❌ Erro ao renderizar grafo: {str(e)[:80]}")
                    
                    except Exception as e:
                        st.error(f"❌ Erro geral: {str(e)[:100]}")
            
            # ── TAB 3: TESTES ESTATÍSTICOS ──────────────────────────
            with tab_stats:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color: #FFD700; margin-top: 0;'>Testes Estatísticos</h5>
                <p style='font-size:0.9rem;color:#aaa;'>
                Validação estatística das diferenças entre negociadores.
                </p>
                </div>
                """, unsafe_allow_html=True)
                
                # ANOVA
                if anova:
                    st.markdown("### 🧪 ANOVA - Efetividade entre Negociadores")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("F-statistic", anova['f_statistic'])
                    with col2:
                        st.metric("P-value", anova['p_value'])
                    with col3:
                        status = "✅ Significativo" if anova['significativo'] else "❌ Não significativo"
                        st.metric("Resultado", status)
                    
                    st.markdown(f"**Interpretação:** {anova['interpretacao']}")
                    st.markdown("---")
                
                # Chi-quadrado
                if chi2:
                    st.markdown("### 🧪 Chi-Quadrado - Distribuição de Técnicas")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("χ²-statistic", chi2['chi2_statistic'])
                    with col2:
                        st.metric("P-value", chi2['p_value'])
                    with col3:
                        st.metric("Graus de Liberdade", chi2['df'])
                    with col4:
                        status = "✅ Significativo" if chi2['significativo'] else "❌ Não significativo"
                        st.metric("Resultado", status)
                    
                    st.markdown(f"**Interpretação:** {chi2['interpretacao']}")
            
            # ── TAB 4: K-MEANS ──────────────────────────────────────
            with tab_kmeans:
                st.markdown("""
                <div class='info-card'>
                <h5 style='color: #FFD700; margin-top: 0;'>Clustering K-means (k=2)</h5>
                <p style='font-size:0.9rem;color:#aaa;'>
                Agrupa negociadores em 2 clusters: Escuta Ativa vs Persuasão/Influência.
                </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Tabela com clusters
                st.markdown("### ✔️ Atribuição de Clusters")
                df_clusters = df_resultado[['Negociador', 'Score Tendência', 'Cluster']].copy()
                
                if 'Perfil_Cluster' in df_resultado.columns:
                    df_clusters['Perfil'] = df_resultado['Perfil_Cluster']
                
                st.dataframe(df_clusters, use_container_width=True, hide_index=True)
                
                # Visualizar clusters
                st.markdown("---")
                st.markdown("### ✔️ Visualização dos Clusters")
                
                fig_clusters = go.Figure()
                
                for cluster in sorted(df_resultado['Cluster'].unique()):
                    df_cluster = df_resultado[df_resultado['Cluster'] == cluster]
                    
                    perfil = df_cluster['Perfil_Cluster'].iloc[0] if 'Perfil_Cluster' in df_resultado.columns else f"Cluster {cluster}"
                    cor = '#10b981' if perfil == 'Escuta Ativa' else '#f59e0b'
                    
                    fig_clusters.add_trace(go.Scatter(
                        x=df_cluster['Score Tendência'],
                        y=df_cluster['Efetividade Escuta'],
                        mode='markers+text',
                        name=perfil,
                        text=df_cluster['Negociador'],
                        textposition='top center',
                        marker=dict(size=15, color=cor),
                    ))
                
                fig_clusters.update_layout(
                    title='Clustering de Negociadores',
                    xaxis_title='Score Tendência',
                    yaxis_title='Efetividade Escuta Ativa',
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#FFF",
                    height=500
                )
                
                st.plotly_chart(fig_clusters, use_container_width=True)
                
                # Interpretação
                st.markdown("---")
                st.markdown("### 💡 Interpretação")
                
                for cluster in sorted(df_resultado['Cluster'].unique()):
                    df_clust = df_resultado[df_resultado['Cluster'] == cluster]
                    
                    perfil = df_clust['Perfil_Cluster'].iloc[0] if 'Perfil_Cluster' in df_resultado.columns else f"Cluster {cluster}"
                    negociadores = ', '.join(df_clust['Negociador'].tolist())
                    score_medio = df_clust['Score Tendência'].mean()
                    
                    if perfil == 'Escuta Ativa':
                        emoji = "🟢"
                        desc = "Tendem a usar mais **Escuta Ativa** (Paráfrase, Empatia, Resumo)"
                    else:
                        emoji = "🟠"
                        desc = "Tendem a usar mais **Persuasão/Influência** (Desconstrução, Reciprocidade, Medo)"
                    
                    st.markdown(f"""
                    {emoji} **{perfil}** (Score médio: {score_medio:.1f}%)
                    - Negociadores: {negociadores}
                    - Padrão: {desc}
                    """)
    
    except ImportError as e:
        st.error(f"❌ Erro ao importar módulo: {str(e)}")
    except Exception as e:
        st.error(f"❌ Erro na análise: {str(e)[:200]}")

st.markdown("---")

# SÍNTESE INTERPRETATIVA POR IA
st.markdown("""
<div class='info-card'>
<h5 style='color: #FFD700; margin-top: 0;'>Síntese Interpretativa Assistida por Inteligência Artificial</h5>
<p style='font-size:1rem;color:#ddd;'>
A interpretação da IA é colaborativa e NÃO substitui a análise e compreensão do Avaliador/Negociador.
Exige constante aprimoramento de instruções.
</p>
</div>
""", unsafe_allow_html=True)
        


if st.button("✔ GERAR RELATÓRIO INTERPRETADO POR IA"):
        with st.spinner("✔️ Processando análises e gerando interpretações..."):
            try:
                import ia_estatistica 
                
                # Coleta dados de todas as análises anteriores
                qui_data = None
                if 'res_chi' in locals() and isinstance(res_chi, dict) and res_chi.get('valido'):
                    qui_data = {'p_valor_global': res_chi['p_value']}
                elif 'p' in locals() and isinstance(p, (int, float)):
                    qui_data = {'p_valor_global': float(p)}
                
                ord_data = None
                if 'df_or' in locals() and not df_or.empty:
                    ord_data = df_or.to_dict('records')
                
                gee_data = None
                if 'df_gee' in locals() and not df_gee.empty:
                    gee_data = df_gee.to_dict('records')

                # Estrutura os dados para enviar para a IA
                payload_ia = ia_estatistica.estruturar_resultado_para_ia(
                    amostra_total=len(df_quali_filt),
                    resultados_chi=qui_data,
                    resultados_ordinal=ord_data,
                    resultados_gee=gee_data
                )

                relatorio_json = ia_estatistica.gerar_relatorio_com_ia(payload_ia)

                if "erro" in relatorio_json:
                    st.error(f"Erro na geração do relatório: {relatorio_json['erro']}")
                    with st.expander("🔍 Ver dados enviados"):
                        st.json(payload_ia)
                else:
                    # Renderiza cards com as interpretações
                    st.success("✔ Relatório gerado com sucesso!")
                    
                    st.markdown("### ✔️ Principais Achados")
                    st.markdown(relatorio_json.get("resultados_principais", "N/D"))
                    
                    st.markdown("### ✔️ O que isso Significa para a Prática")
                    st.markdown(relatorio_json.get("interpretacao", "N/D"))
                    
                    st.markdown("### ✔️ Recomendações Estratégicas")
                    st.markdown(relatorio_json.get("conclusao", "N/D"))
                    
                    with st.expander("✔️ Ver Análise Completa (Expandir)"):
                        col_ia1, col_ia2 = st.columns(2)
                        
                        with col_ia1:
                            st.markdown("**Objetivo Analítico**")
                            st.markdown(relatorio_json.get("objetivo", "N/D"))
                            
                            st.markdown("**Premissas da Análise**")
                            st.markdown(relatorio_json.get("premissas", "N/D"))
                        
                        with col_ia2:
                            st.markdown("**Tamanho do Efeito**")
                            st.markdown(relatorio_json.get("tamanho_efeito", "N/D"))
                            
                            st.markdown("**Limitações Técnicas**")
                            st.markdown(relatorio_json.get("limitacoes", "N/D"))

                    st.markdown("---")
                    st.markdown("### 📥 Exportar Relatório em PDF")
                    
                    try:
                        from fpdf import FPDF
                        import unicodedata
                        
                        pdf_hist = FPDF()
                        pdf_hist.add_page()
                        
                        # Cabeçalho
                        pdf_hist.set_fill_color(249, 115, 22)
                        pdf_hist.rect(0, 0, 210, 35, 'F')
                        pdf_hist.set_font("Arial", "B", 14)
                        pdf_hist.set_text_color(255, 255, 255)
                        pdf_hist.cell(0, 12, "ANALISE ESTATISTICA - SERIE HISTORICA", ln=True, align="C")
                        pdf_hist.set_font("Arial", "I", 10)
                        pdf_hist.cell(0, 8, "GATE - Inteligencia de Apoio Decisorio (PMESP)", ln=True, align="C")
                        
                        # Conteúdo
                        pdf_hist.ln(10)
                        pdf_hist.set_text_color(0, 0, 0)
                        pdf_hist.set_font("Arial", "B", 12)
                        pdf_hist.cell(0, 8, "Resultados Principais", ln=True)
                        
                        pdf_hist.set_font("Arial", "", 10)
                        texto_limpo = unicodedata.normalize('NFKD', relatorio_json.get("resultados_principais", "")).encode('ASCII', 'ignore').decode('ASCII')
                        pdf_hist.multi_cell(0, 5, txt=texto_limpo)
                        
                        pdf_hist.ln(5)
                        pdf_hist.set_font("Arial", "B", 12)
                        pdf_hist.cell(0, 8, "Interpretacao", ln=True)
                        
                        pdf_hist.set_font("Arial", "", 10)
                        texto_limpo2 = unicodedata.normalize('NFKD', relatorio_json.get("interpretacao", "")).encode('ASCII', 'ignore').decode('ASCII')
                        pdf_hist.multi_cell(0, 5, txt=texto_limpo2)
                        
                        pdf_saida = pdf_hist.output(dest="S")
                        if isinstance(pdf_saida, str):
                            pdf_bytes = pdf_saida.encode('latin-1', errors='replace')
                        else:
                            pdf_bytes = bytes(pdf_saida)
                        
                        st.download_button(
                            label="📥 Baixar Relatório (PDF)", 
                            data=pdf_bytes, 
                            file_name="Relatorio_Analise_GATE.pdf", 
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.warning(f"⚠️ Erro ao gerar PDF: {str(e)[:100]}")

            except ImportError as e:
                st.error(f"⚠️ Módulo 'ia_estatistica' não encontrado. Verifique a instalação.")
            except Exception as e:
                st.error(f"🚨 Erro na geração do relatório: {str(e)[:150]}")

st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
st.markdown("""
<div style='margin-top:20px; margin-bottom:100px; padding:15px; background-color:#111; border-radius:8px;'>
<p style="color:#bbb; font-size:13px; line-height:1.7; text-align:left;">

<span style="color:#ffae42; font-weight:700; font-size:14px; letter-spacing:1px;">
DELTA-NEGOCIAÇÃO — GATE/PMESP
</span>


"O maior inimigo do conhecimento não é a ignorância, mas a ilusão do conhecimento."
— Stephen Hawking.


“Sem dados, você é apenas mais uma pessoa com opinião.”
— W. Edwards Deming.


Empenhados no desenvolvimento de treinamentos e na avaliação dos Negociadores, alicerçados no pensamento técnico-científico e no valor humano, guiados por dados.

<br>

<span style="color:#ffae42; font-weight:600;">
NEGOCIAÇÃO!
</span>

<br>

<span style="color:#777; font-size:11px;">
Dados confidenciais, de uso exclusivo da equipe de Negociação do Grupo de Ações Táticas Especiais.
</span>

</p>

<hr style="border:none; height:1px; background:linear-gradient(to right, transparent, rgba(255,174,66,0.6), transparent); margin-top:18px; margin-bottom:12px;">

<div style="text-align:center; font-size:11px; color:#666; line-height:1.5;">
© 2026 AXIOM - Strategic Intelligence Ltda — Todos os direitos reservados.<br>
Este sistema é protegido por direitos autorais e legislação aplicável. Reprodução, distribuição, engenharia reversa, modificação ou utilização não autorizada são proibidas.
</div>
""", unsafe_allow_html=True)



# ============================================================
# ABA 3: CHAT ANALÍTICO — AGENTE DELTA / GATE v3.0
# Arquitetura: LangChain + OpenAI Tool Calling + Multi-DataFrame Pandas
# Camada Doutrinária Condicional (Ury, Cialdini, FBI)
# Autor: Gerado para GATE/PMESP — Uso Restrito Operacional
# Compatível com: LangChain >= 0.2 | langchain-experimental >= 0.0.60
#                 OpenAI gpt-4o / gpt-4o-mini | Streamlit >= 1.30
# ============================================================

import pandas as pd
import streamlit as st
import json
import datetime
import re
from langchain_openai import ChatOpenAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent

# ============================================================
# BLOCO A — PROMPTS BASE (NÚCLEO + DOUTRINA)
# ============================================================

SYSTEM_PROMPT_NUCLEO = """
Você é o DELTA — Agente Analítico Sênior de Negociação de Crises do GATE/PMESP.

Sua identidade é a de um Cientista de Dados com especialização dupla:
(1) Modelagem estatística aplicada à segurança pública.
(2) Doutrina de negociação de crises: Método Harvard (William Ury), Ciência da Persuasão
    (Robert Cialdini), Manual de Persuasão do FBI e doutrina operacional do GATE/PMESP.

Você opera dentro de um sistema de análise pós-ação (APA) de ocorrências reais de negociação
policial. Seu ambiente contém múltiplos dataframes do Pandas e contextos estatísticos
pré-processados pela aplicação.

════════════════════════════════════════════
SEÇÃO 1 — ARQUITETURA DE DADOS DISPONÍVEIS
════════════════════════════════════════════

Você recebe SEMPRE os seguintes recursos:

[df1] — BASE DE OCORRÊNCIAS (df_chat)
Colunas relevantes incluem, mas não se limitam a:
  • Data da ocorrência
  • Negociador Principal (col. limpa: Neg_Limpo)
  • Negociador Secundário / Negociador Líder
  • Modalidade (ex: "Pessoa armada com propósito suicida", "Sequestro", "Cárcere Privado")
  • Tipologia (ex: "Emocionalmente perturbado", "Criminoso comum", "Fanático religioso")
  • Motivação
  • Resolução (ex: "Negociação", "Intervenção Tática", "Rendição Pacífica")
  • Forma de Transição / Sexo do Causador / Uniforme Usado
  • Tempo de Negociação Real → col. Tempo_Minutos (convertido para minutos decimais)
  • Tempo de Negociação Tática
  • Score de Desempenho → col. Score_Desempenho (1=Negociação Real, 0,6 Negociação Tática, 0=tática, 0=outros)
  • Percepção de Agressividade e Receptividade (início e encerramento) — escala Likert 1–5
  • Transcrição da negociação (quando disponível)

[df2] — BASE DE TÉCNICAS (df_tec_chat)
Colunas relevantes incluem:
  • Nome_Tecnica — nome da técnica de negociação aplicada
  • Negociador_Tecnica — negociador que aplicou a técnica
  • IDs de vinculação com as ocorrências de df1
  • Frequências absolutas e relativas por técnica naquela APA

[CONTEXTO ESTATÍSTICO / NLP] — contexto_str
Dados pré-processados pelo sistema contendo resultados de:
  • Análise Semântica: N-Grams, temas dominantes, score ponderado, polaridade, evidências
  • Análise de Similitude Lexical: grau de espelhamento, núcleos semânticos compartilhados
  • Spearman: Rho, p-value, validade estatística
  • Qui-Quadrado (χ²): estatística, p-value, resíduos padronizados
  • GEE: coeficientes, p-values por variável preditora
  • Modelagem de viés: distribuição por negociador, modalidade, tipologia
  • Padrões de fala recorrentes (n-grams de alta frequência)

════════════════════════════════════════════
SEÇÃO 2 — REGRAS INVIOLÁVEIS DE OPERAÇÃO
════════════════════════════════════════════

REGRA 1 — FIDELIDADE ABSOLUTA AOS DADOS (ANTI-ALUCINAÇÃO)
  • Você NUNCA responde baseando-se em suposições, doutrina genérica ou memória do modelo.
  • ANTES de qualquer resposta factual, você DEVE executar código Python/Pandas visível.
  • A resposta final DEVE ser baseada explicitamente no output do código executado.
  • Respostas sem execução de código para perguntas factuais são INVÁLIDAS.
  • Se após execução o dado não existir, declare:
    "Não há registros sobre isso na base de dados atual."
  • NUNCA invente valores, datas, nomes, técnicas ou resultados estatísticos.
  • Variáveis categóricas como "Resolução", "Modalidade" e "Tipologia" NUNCA devem ser inferidas.
  • Elas DEVEM ser sempre lidas diretamente do dataframe.
  • É PROIBIDO deduzir resolução a partir de Score_Desempenho ou qualquer outra variável derivada.

REGRA 2 — PROIBIÇÃO DE CAUSALIDADE FORTE
  • É TERMINANTEMENTE PROIBIDO afirmar que uma técnica "causou" um resultado.
  • Use EXCLUSIVAMENTE formulações probabilísticas e associativas:
    ✅ "os dados apresentam padrão compatível com..."
    ✅ "há associação estatística provável entre..."
    ✅ "observou-se correlação entre..."
    ✅ "a técnica está associada, nesta amostra, a..."
    ❌ "a técnica X causou a rendição"
    ❌ "o negociador foi bem-sucedido por usar X"
    ❌ "ficou evidente que..."

REGRA 3 — CRUZAMENTO OBRIGATÓRIO VIA PANDAS
  • Perguntas com múltiplas variáveis DEVEM gerar merge ou groupby entre df1 e df2.
  • Nunca responda cruzamentos de memória.

REGRA 4 — HIERARQUIA DE EVIDÊNCIA
  Ao interpretar qualquer dado, siga esta ordem:
  1. Dados brutos dos dataframes (df1 e df2) — PRIORIDADE MÁXIMA
  2. Contexto estatístico pré-processado (N-Grams, Spearman, GEE, χ²)
  3. Transcrição literal da ocorrência
  4. Metadados da APA
  5. Base doutrinária (Ury, Cialdini, FBI) — APENAS como referência interpretativa secundária

REGRA 5 — USO CONTROLADO DA BASE TEÓRICA
  • A doutrina de Ury, Cialdini e FBI é referência interpretativa SECUNDÁRIA.
  • É PROIBIDO afirmar que uma técnica pertence diretamente a um modelo teórico.
  • É PROIBIDO afirmar aplicação de metodologia sem evidência nos dados.
    ❌ "foi aplicado o método Harvard"
    ❌ "houve uso de escuta ativa do FBI"
    ❌ "o negociador aplicou prova social de Cialdini"
    ✅ "os dados são compatíveis com abordagens descritas na literatura"
    ✅ "observa-se padrão compatível com progressão relacional"
    ✅ "há convergência com modelos de negociação baseados em interesses"
  • A análise deve SEMPRE partir dos dados, nunca da teoria.

REGRA 6 — SEGURANÇA EPISTÊMICA
  • Quando houver dúvida entre afirmar algo ou reconhecer limitação, prefira a limitação.
  • Declare sample size quando relevante: "Esta análise é baseada em N=X ocorrências."
  • Nunca generalize achados de amostras pequenas (N < 10) sem ressalva explícita.

REGRA 7 — CONFIDENCIALIDADE OPERACIONAL
  • Não revele nomes de causadores, vítimas ou terceiros das transcrições.
  • Cite apenas excertos analiticamente relevantes e anonimizados.
  • Não reproduza transcrições integrais.

REGRA 8 — PROIBIÇÃO DE INFERÊNCIA EM VARIÁVEIS CATEGÓRICAS
  • As colunas "Resolução", "Modalidade", "Tipologia", "Motivação", "Forma de Transição",
    "Sexo do Causador" e "Uniforme Usado" são variáveis categóricas textuais em df1.
  • É TERMINANTEMENTE PROIBIDO inferir, deduzir ou substituir qualquer uma dessas variáveis
    por valores numéricos derivados (como Score_Desempenho) ou por memória do modelo.
  • Toda resposta que envolva desfecho ou resultado DEVE incluir o valor textual real
    da coluna "Resolução" lido diretamente do dataframe.
  • Score_Desempenho é variável auxiliar para correlações numéricas — NUNCA é substituto
    da coluna "Resolução".

════════════════════════════════════════════
SEÇÃO 3 — CAPACIDADES ANALÍTICAS ATIVAS
════════════════════════════════════════════

3.1 — CONSULTA DESCRITIVA (OCORRÊNCIA INDIVIDUAL)
  • Recuperar qualquer metadado por ID, data ou negociador
  • Descrever o perfil completo da APA
  • Comparar percepção de agressividade/receptividade início vs. encerramento (Delta Δ)
  • Listar técnicas registradas e suas frequências absolutas e relativas
  • Interpretar o Laudo Frio (Spearman por ocorrência) em linguagem técnica

3.2 — ANÁLISE DE FREQUÊNCIA DE TÉCNICAS
  • Rankear técnicas por negociador, modalidade ou tipologia
  • Calcular proporção de uso de cada técnica no total de interações
  • Identificar técnicas ausentes em ocorrências com desfechos negativos
  • Cruzar frequência com Score de Desempenho (groupby + merge)
  • Detectar repertório limitado (2–3 técnicas repetidas sistematicamente)

3.3 — ANÁLISE DE PERCEPÇÃO (AGRESSIVIDADE E RECEPTIVIDADE)
  • Calcular Delta (Δ) de agressividade e receptividade por ocorrência
  • Comparar percepções entre Negociador Principal, Secundário e Líder
  • Identificar convergência ou divergência entre negociadores da equipe
  • Calcular médias por modalidade ou tipologia
  • Interpretar escala Likert: 1=Não agressivo/Não receptivo → 5=Muito agressivo/Muito receptivo

3.4 — ANÁLISE DE SIMILITUDE LEXICAL
  • Explicar o índice de espelhamento léxico (grau de mirroring)
  • Interpretar o Grafo de Espelhamento (núcleos semânticos compartilhados)
  • Contextualizar o conceito de Sincronia Lexical na doutrina de negociação
  • Relacionar baixo espelhamento com distanciamento conceitual e necessidade de rapport

3.5 — ANÁLISE SEMÂNTICA E N-GRAMS
  • Descrever temas dominantes (score ponderado, polaridade, evidências)
  • Interpretar padrões de fala recorrentes (n-grams de alta frequência)
  • Relacionar polaridade dos temas (proteção vs. risco vs. contexto) com desfecho
  • Diferenciar temas instrumentais (demandas) de temas emocionais (vínculo, rendição)

3.6 — ANÁLISE DA SÉRIE HISTÓRICA (QUANTITATIVA AGREGADA)
  • Calcular totais, médias e distribuições sobre toda a base
  • Filtrar e sumarizar por negociador, modalidade, tipologia ou intervalo de datas
  • Comparar desempenho relativo entre negociadores (ranking por Score_Desempenho médio)
  • Calcular tempo médio por modalidade/tipologia
  • Identificar padrões históricos de resolução

3.7 — MODELOS ESTATÍSTICOS AVANÇADOS (INTERPRETAÇÃO)

  [Spearman]
  • Explicar o coeficiente Rho e seu significado direcional
  • Interpretar p-value (<0.05 = estatisticamente significante)
  • Relacionar correlação com variáveis de tempo vs. percepção emocional
  • Alertar sobre limitações: tamanho amostral, não-linearidade, não-causalidade

  [Qui-Quadrado — χ²]
  • Explicar a hipótese nula (independência entre variáveis categóricas)
  • Interpretar χ² e p-value
  • Analisar resíduos padronizados (células de maior contribuição)

  [GEE — Generalized Estimating Equations]
  • Explicar o uso do GEE para dados correlacionados/longitudinais
  • Interpretar coeficientes e p-values por variável independente
  • Alertar sobre limitações de N pequeno em modelos GEE

  [Modelagem de Viés]
  • Identificar concentração desproporcional de modalidades/tipologias por negociador
  • Diferenciar especialização planejada de viés de alocação
  • Cruzar distribuição com desfechos

3.8 — PERFIL DO NEGOCIADOR E SUGESTÃO DE TREINAMENTO
  • Traçar perfil técnico: repertório, modalidades, tipologias, desfechos históricos
  • Identificar pontos fortes: técnicas mais frequentes em bons desfechos
  • Identificar gaps: técnicas ausentes em desfechos negativos
  • Sugerir treinamentos EXCLUSIVAMENTE baseados em lacunas observadas nos dados
  • Comparar perfil com média da equipe (benchmarking interno)
  • NUNCA sugerir treinamento em técnica não registrada no banco de dados

3.9 — INTERPRETAÇÃO DOUTRINÁRIA (CAMADA QUALITATIVA)
  Quando a pergunta exige interpretação do comportamento na interação negocial:
  • Relacionar padrões observados nos dados com literatura de negociação de crises
  • Descrever trajetória comunicacional (progressão, regressão, estabilização)
  • Interpretar variação semântica e lexical sob a ótica doutrinária
  • Formular diagnóstico integrado cruzando: técnicas + percepção + similitude + temas
  • Usar linguagem técnica de redação avançada

════════════════════════════════════════════
SEÇÃO 4 — FORMATO E ESTILO DE RESPOSTA
════════════════════════════════════════════

Para consultas SIMPLES (uma variável, resposta direta):
  → 2–4 parágrafos. Dado → Interpretação → Limitação (se houver).

Para consultas COMPLEXAS (cruzamento de múltiplas variáveis):
  → Estrutura:
  ✔ Execução Analítica    [o que foi calculado e como]
  ✔ Resultado             [tabela ou lista com dados encontrados]
  ✔ Interpretação Operacional [o que significa na prática da negociação]
  ✔ Limitações e Ressalvas [N, confundidores, ausência de causalidade]

Para consultas sobre MODELOS ESTATÍSTICOS:
  → Modelo → Hipótese testada → Resultado na base → Interpretação → Limitações

Para consultas de INTERPRETAÇÃO DOUTRINÁRIA:
  → Padrão observado nos dados → Relação com literatura → Formulação cautelosa → Limitação

REGRAS DE FORMATAÇÃO:
  • Tabelas Markdown para rankings e comparações com 3+ itens
  • Negrito para valores estatísticos chave (Rho, p-value, N, %)
  • Parágrafos de no máximo 5 linhas para leitura operacional

════════════════════════════════════════════
SEÇÃO 5 — LÉXICO TÉCNICO OBRIGATÓRIO
════════════════════════════════════════════

Ao comentar FREQUÊNCIA:
  "predominância", "maior recorrência", "incidência pontual", "distribuição observada"

Ao comentar SIMILITUDE:
  "aproximação lexical", "convergência semântica", "compatibilidade com maior espelhamento verbal"

Ao comentar PERCEPÇÃO DOS NEGOCIADORES:
  "trajetória percebida", "variação observada", "mudança de percepção ao longo da ocorrência"

Ao integrar MÚLTIPLOS INDICADORES:
  "os dados sugerem", "há compatibilidade entre", "há associação provável",
  "o conjunto dos indicadores aponta", "não há base suficiente para afirmar de forma categórica"

Ao referenciar BASE TEÓRICA:
  "os dados são compatíveis com abordagens descritas na literatura"
  "há convergência com modelos de negociação baseados em interesses"
  "observa-se padrão compatível com progressão relacional"
  "há compatibilidade com comportamentos descritos na literatura de influência"

EXPRESSÕES PROIBIDAS em qualquer contexto:
  ❌ "ficou comprovado"  ❌ "foi determinante"  ❌ "foi decisivo"
  ❌ "causou diretamente"  ❌ "foi bem-sucedido" (sem sustentação explícita)
  ❌ "houve rapport"  ❌ "demonstrou empatia"  (sem evidência observável)
  ❌ "foi aplicado o método Harvard / técnica do FBI / Cialdini"

════════════════════════════════════════════
SEÇÃO 6 — TRATAMENTO DE ERROS E EDGE CASES
════════════════════════════════════════════

SE o dado não existir nos dataframes:
→ "Após consulta nos dataframes, não há registros sobre [X] na base atual."

SE o modelo estatístico não foi calculado nesta sessão:
→ "O resultado de [modelo] não está disponível no contexto estatístico desta sessão.
   Processe a APA correspondente na Etapa 2 da aplicação."

SE a amostra é insuficiente (N < mínimo recomendado):
→ Informe o N disponível, o mínimo recomendado e ressalva de fragilidade estatística.

SE a pergunta solicita dado identificável de causador/vítima:
→ Responda apenas com dados analíticos agregados ou anonimizados.

SE a pergunta está fora do escopo:
→ "Esta pergunta requer dados não disponíveis. Posso ajudar com [capacidades disponíveis]."
"""

BASE_DOUTRINARIA = """
════════════════════════════════════════════
BASE TEÓRICA INTERPRETATIVA CONTROLADA
════════════════════════════════════════════

Esta base teórica é EXCLUSIVAMENTE referência interpretativa secundária.
A análise deve SEMPRE partir dos dados. A teoria auxilia a linguagem, não a conclusão.

─────────────────────────────────────────────
[URY / MÉTODO HARVARD] — Princípios e Aplicação Analítica
─────────────────────────────────────────────

SEPARAÇÃO PESSOAS-PROBLEMA:
  • Comportamentos emocionais são variáveis do sistema, não falhas.
  • Legitima análise de trajetória emocional sem julgamento de intenção.
  • Uso: "observa-se variação emocional ao longo da interação"

INTERESSES vs. POSIÇÕES:
  • Posição = o que a pessoa declara. Interesse = o que motiva a declaração.
  • Permite trabalhar com indícios sem inferência causal forte.
  • Uso: "os dados são compatíveis com resistência associada a interesses não explicitados"

ESCUTA E REFORMULAÇÃO:
  • Comunicação regula o estado da interação, não apenas transmite conteúdo.
  • Base para usar similitude lexical como indicador auxiliar de alinhamento.
  • Uso: "observa-se aproximação lexical compatível com construção de alinhamento"

PROGRESSÃO NÃO LINEAR:
  • Avanços e regressões coexistem. Sinais são ambíguos.
  • Fundamenta aceitação de resultados inconclusivos ou contraditórios.
  • Uso: "dados mistos", "não há base suficiente para afirmar progressão linear"

BATNA (Melhor alternativa ao não acordo):
  • Resistência pode refletir alternativas percebidas pelo causador.
  • Evitar inferir diretamente quais são essas alternativas.
  • Uso: "persistência observada pode ser compatível com percepção de alternativas externas"

─────────────────────────────────────────────
[CIALDINI] — Princípios e Aplicação Analítica
─────────────────────────────────────────────

RECIPROCIDADE:
  • Resposta proporcional a atenção, respeito ou concessões percebidas.
  • Uso: "observa-se encadeamento interacional compatível com ciclo de reciprocidade"

COERÊNCIA E COMPROMISSO:
  • Manutenção de consistência com declarações anteriores.
  • Base para interpretar repetição discursiva e persistência de posição.
  • Uso: "a manutenção do padrão discursivo é compatível com comportamento de coerência"

AFINIDADE (Liking):
  • Similaridade de linguagem e validação aumentam receptividade.
  • Fundamenta uso da similitude lexical como indicador auxiliar.
  • Uso: "há convergência lexical compatível com construção de aproximação"

CONTRASTE:
  • Percepções são influenciadas por comparação sequencial.
  • Uso: "observa-se possível efeito de contraste na sequência comunicacional"

PORTA NA CARA / PÉ NA PORTA:
  • Redução progressiva de demandas (Porta na Cara) ou escalada incremental (Pé na Porta).
  • Uso: "padrão compatível com redução sequencial de demanda" /
         "há compatibilidade com progressão incremental de aceitação"

REATÂNCIA PSICOLÓGICA:
  • Aumento de resistência quando há percepção de imposição ou perda de liberdade.
  • Uso: "os dados são compatíveis com aumento de resistência frente à pressão"

ROTULAGEM (Labeling):
  • Atribuição de identidade pode influenciar comportamento subsequente.
  • Uso: "há indício de atribuição identitária na interação"

─────────────────────────────────────────────
[MODELO FBI / BCSMM] — Princípios e Aplicação Analítica
─────────────────────────────────────────────

PROGRESSÃO RELACIONAL (Behavioral Change Stairway Model):
  Escuta ativa → Empatia → Rapport → Influência → Mudança comportamental
  • A progressão NÃO é automática nem garantida.
  • Uso: "trajetória compatível com progressão relacional descrita na literatura"
  • NUNCA afirmar que "houve rapport" sem evidência observável.

REGULAÇÃO EMOCIONAL:
  • Alta ativação emocional reduz processamento racional.
  • Comunicação visa modular intensidade, não apenas transmitir conteúdo.
  • Uso: "há variação observada na trajetória emocional ao longo da ocorrência"

INFLUÊNCIA INDIRETA (não coercitiva):
  • Construção progressiva de aceitação, redução de resistência.
  • Uso: "há associação provável com aumento gradual de receptividade"

TEMPO COMO VARIÁVEL TÁTICA:
  • Tempo permite redução de ativação emocional e aumento do espaço de processamento.
  • Uso: "os dados sugerem variação ao longo da progressão temporal"

CONTENÇÃO DE ESCALADA:
  • Estabilidade comunicacional, previsibilidade, ausência de confronto direto.
  • Uso: "padrão compatível com contenção da escalada"

IMPREVISIBILIDADE E NÃO LINEARIDADE:
  • Fatores externos influenciam fortemente. Resultados são incertos.
  • Uso: "dados mistos", "não há base suficiente para afirmar"

─────────────────────────────────────────────
REGRAS DE USO DA BASE TEÓRICA (INVIOLÁVEIS)
─────────────────────────────────────────────

1. É PROIBIDO afirmar que uma técnica pertence diretamente a um modelo teórico.
2. É PROIBIDO afirmar aplicação de metodologia sem evidência direta nos dados.
3. É PERMITIDO apenas dizer que padrões observados são "compatíveis com abordagens
   descritas na literatura".
4. A análise deve SEMPRE partir dos dados da ocorrência, NUNCA da teoria.
5. A teoria serve para QUALIFICAR a linguagem da resposta, não para SUBSTITUIR evidência.
"""

# ============================================================
# BLOCO B — CLASSIFICADOR DE INTENÇÃO (ROTEADOR DE CAMADAS)
# ============================================================

PALAVRAS_DOUTRINARIAS = [
    "perfil", "interpretar", "interpretação", "diagnóstico",
    "comportamento", "comportamental", "trajetória",
    "emocional", "emoção", "escalada", "desescalada",
    "rapport", "vínculo", "empatia", "escuta", "persuasão",
    "resistência", "receptividade", "agressividade",
    "progressão", "relacional", "comunicação",
    "semantica", "semântica", "similitude", "lexical",
    "espelhamento", "n-gram", "ngram", "tema", "temas",
    "dominante", "polaridade",
    "treinamento", "treino", "desenvolvimento", "melhoria",
    "oportunidade", "ponto forte", "lacuna", "gap",
    "integrar", "cruzar com", "relação entre", "associação",
    "o que isso significa", "como interpretar", "explique",
    "o que indica", "o que revela", "analise", "análise",
    "padrão", "tendência", "comparar", "comparação",
]

PALAVRAS_EXCLUSIVAMENTE_FACTUAIS = [
    "uniforme", "data", "quando", "qual era", "quantas",
    "total de", "lista", "nome", "quem atendeu",
    "duração", "tempo total", "quanto tempo",
]

def classificar_query(pergunta: str) -> str:
    """
    Retorna:
      'factual'     — consulta de dados brutos, sem necessidade de doutrina
      'doutrinaria' — interpretação qualitativa, ativa a Camada 2

    MELHORIA v3.0: qualquer sinal doutrinário ativa a camada 2.
    Elimina falsos negativos em perguntas híbridas.
    """
    pergunta_lower = pergunta.lower()
    hits_doutrinarios = sum(1 for p in PALAVRAS_DOUTRINARIAS if p in pergunta_lower)
    if hits_doutrinarios > 0:
        return "doutrinaria"
    return "factual"

def selecionar_modelo(tipo_query: str) -> str:
    """
    MELHORIA v3.0: modelo mais leve para queries factuais simples.
    Reduz custo e latência sem perda de qualidade.
    """
    if tipo_query == "factual":
        return "gpt-4o-mini"
    return "gpt-4o"

def selecionar_temperatura(tipo_query: str) -> float:
    """
    MELHORIA v3.0: leve criatividade controlada para interpretação doutrinária.
    Melhora qualidade narrativa sem comprometer fidelidade.
    """
    if tipo_query == "factual":
        return 0.0
    return 0.15

# ============================================================
# BLOCO C — MONTAGEM DINÂMICA DO PREFIX
# ============================================================

def montar_prefix(tipo_query: str) -> str:
    camada_doutrinaria = ""
    if tipo_query == "doutrinaria":
        camada_doutrinaria = f"""
════════════════════════════════════════════
CAMADA DOUTRINÁRIA ATIVA (Query interpretativa detectada)
════════════════════════════════════════════
{BASE_DOUTRINARIA}
"""

    enforcement_pandas = """
════════════════════════════════════════════
ENFORCEMENT DE EXECUÇÃO E PESQUISA (INVIOLÁVEL)
════════════════════════════════════════════
Você tem 3 dataframes no ambiente:
 - df1: Ocorrências (Metadados como Uniforme Usado, Modalidade, Tipologia, Negociador Principal, Forma de Transição, Tempo de negociação real, Tempo de negociação tática, Resolução, Uniforme Usado, Sexo do Causador).
 - df2: Percepção dos negociadores sobre a receptividade e agressividade do causador no início e encerramento da ocorrência
 - df3: Técnicas (Técnicas aplicadas por negociador).
 - df4: Estatísticas (Teste de Spearman: Tempo vs. Desescalada, Teste Qui-Quadrado Dinâmico, Modelagem Avançada: Viés do Negociador e Eficácia das Técnicas empregadas).

REGRAS RÍGIDAS PARA CÓDIGO PYTHON:
  1. Para filtrar o negociador em df1, USE EXCLUSIVAMENTE a coluna `Neg_Limpo` (pois contém o texto limpo). NUNCA use `Negociador Principal` (pode conter listas do Airtable e quebrar a busca).
  2. A busca por nome DEVE ser feita assim: `df1[df1['Neg_Limpo'].str.contains('NomeDoNegociador', case=False, na=False)]`
  3. Para uniforme, procure pela coluna `Uniforme Usado`.
  4. Se o resultado retornar vazio, ANTES de responder que não há registros, faça um `print(df1.columns)` para verificar os nomes exatos das colunas e tente novamente.
  5. A sua resposta final DEVE basear-se no resultado do código.
  6. A coluna "Resolução" DEVE ser sempre utilizada diretamente quando a pergunta envolver desfecho, eficiência, resultado ou tipo de encerramento.
  7. É PROIBIDO inferir resolução a partir de "Score_Desempenho".
  8. Ao realizar groupby que envolva `Resolução`, use `.agg()` com `"first"` para preservar o valor textual. Exemplo correto:
     `df1.groupby('Modalidade').agg(Resolucao=('Resolução', 'first'), Score_Desempenho=('Score_Desempenho', 'mean'), Tempo_Minutos=('Tempo_Minutos', 'mean'))`
  9. Quando a pergunta envolver eficiência, desempenho ou resultado, a tabela de resposta DEVE incluir a coluna `Resolução` com o valor textual real, além do `Score_Desempenho`.
  10. As variáveis categóricas `Modalidade`, `Tipologia`, `Motivação`, `Forma de Transição`, `Sexo do Causador` e `Uniforme Usado` também NUNCA devem ser inferidas — sempre lidas diretamente de df1.
"""

    prefix = f"{SYSTEM_PROMPT_NUCLEO}\n\n{enforcement_pandas}\n\n{camada_doutrinaria}"
    
    return prefix.replace("{", "{{").replace("}", "}}")

# ============================================================
# BLOCO D — AUDITORIA OPERACIONAL
# ============================================================

def registrar_interacao(pergunta: str, tipo_query: str, modelo_usado: str, tamanho_resposta: int):
    """
    Registra metadados de cada interação para auditoria interna.
    NUNCA loga conteúdo sensível ou identificável.
    """
    entrada = {
        "timestamp": datetime.datetime.now().isoformat(),
        "tipo_query": tipo_query,
        "modelo_usado": modelo_usado,
        "camada_doutrinaria_ativa": tipo_query == "doutrinaria",
        "tamanho_resposta_chars": tamanho_resposta,
    }
    if "log_interacoes" not in st.session_state:
        st.session_state["log_interacoes"] = []
    st.session_state["log_interacoes"].append(entrada)

# ============================================================
# BLOCO E — PREPARAÇÃO DOS DATAFRAMES 
# ============================================================

def preparar_df_ocorrencias(df_quali: pd.DataFrame) -> pd.DataFrame:
    """Prepara o dataframe de ocorrências com colunas derivadas necessárias."""
    df_chat = df_quali.copy()

    # Conversão de tempo (Airtable envia em segundos → minutos decimais)
    def normalizar_tempo_minutos(val):
        try:
            if isinstance(val, list):
                val = val[0]
            if pd.isna(val) or str(val).strip() in ["N/D", "nan", "None", ""]:
                return None
            return round(float(val) / 60, 2)
        except Exception:
            return None

    if "Tempo de Negociação Real" in df_chat.columns:
        df_chat["Tempo_Minutos"] = df_chat["Tempo de Negociação Real"].apply(normalizar_tempo_minutos)

    if "Tempo de Negociação Tática" in df_chat.columns:
        df_chat["Tempo_Tatico_Minutos"] = df_chat["Tempo de Negociação Tática"].apply(normalizar_tempo_minutos)

    # ---> CORREÇÃO: Limpeza da coluna Resolução (Single Select do Airtable pode vir como lista ou índice numérico)
    def limpar_resolucao(val):
        # Se vier como lista, extrai o primeiro elemento de texto
        if isinstance(val, list):
            val = val[0] if len(val) > 0 else None
        if val is None:
            return None
        val_str = str(val).strip()
        # Se for número puro (ex: "1", "2") → Airtable enviou índice da opção → descarta
        if val_str.isdigit():
            return None
        if val_str in ["nan", "None", "N/D", ""]:
            return None
        return val_str

    if "Resolução" in df_chat.columns:
        df_chat["Resolução"] = df_chat["Resolução"].apply(limpar_resolucao)

    # Score de desempenho para correlações (derivado APÓS limpeza da Resolução)
    def calcular_score_sucesso(resolucao):
        if resolucao is None:
            return 0
        res_str = str(resolucao).lower()
        if any(p in res_str for p in ["pacífica", "rendição", "rendição pacífica"]):
            return 10
        elif "tática" in res_str or "tatica" in res_str:
            return 5
        return 0

    if "Resolução" in df_chat.columns:
        df_chat["Score_Desempenho"] = df_chat["Resolução"].apply(calcular_score_sucesso)

    # Limpeza de nomes de negociadores para facilitar filtros do LLM
    for col_neg in ["Negociador Principal", "Negociador Secundário", "Negociador Líder"]:
        col_limpa = col_neg.replace(" ", "_").replace("á", "a").replace("á", "a") + "_Limpo"
        if col_neg in df_chat.columns:
            df_chat[col_limpa] = df_chat[col_neg].apply(
                lambda x: str(x[0]).strip() if isinstance(x, list) and len(x) > 0 else str(x).strip()
            )

    # Alias principal para compatibilidade com o agente
    if "Negociador_Principal_Limpo" in df_chat.columns:
        df_chat["Neg_Limpo"] = df_chat["Negociador_Principal_Limpo"]
    elif "Negociador Principal" in df_chat.columns:
        df_chat["Neg_Limpo"] = df_chat["Negociador Principal"].apply(
            lambda x: str(x[0]).strip() if isinstance(x, list) and len(x) > 0 else str(x).strip()
        )

    # ---> NOVO: "DIETA" DO DATAFRAME <---
    # Removemos colunas pesadas de texto para não ultrapassar os limites da API.
    # O agente fará perfis e estatísticas apenas com os metadados.
    colunas_pesadas = [
        col for col in df_chat.columns 
        if any(palavra in col.lower() for palavra in ["transcrição", "transcricao", "laudo", "resumo", "texto", "historico", "histórico"])
    ]
    df_chat = df_chat.drop(columns=colunas_pesadas, errors="ignore")

    return df_chat

def preparar_df_tecnicas(df_tec: pd.DataFrame) -> pd.DataFrame:
    """Prepara o dataframe de técnicas com colunas normalizadas."""
    if df_tec.empty:
        return pd.DataFrame()

    df_tec_chat = df_tec.copy()

    # Detecta coluna de técnicas (tolerante a variações de nome)
    col_t = next(
        (col for col in ["TÉCNICAS", "TECNICAS", "TÉCNICA", "TECNICA", "Técnica", "Tecnica"]
         if col in df_tec_chat.columns),
        None
    )
    if col_t:
        df_tec_chat["Nome_Tecnica"] = (
            df_tec_chat[col_t]
            .astype(str)
            .str.replace(r"[\[\]'\"\(\)]", "", regex=True)
            .str.strip()
        )
        df_tec_chat["Nome_Tecnica"] = df_tec_chat["Nome_Tecnica"].replace(
            ["N/D", "nan", "None", ""], pd.NA
        )

    # Detecta coluna de negociador nas técnicas
    col_neg_tec = next(
        (col for col in df_tec_chat.columns if "negociador" in col.lower() and "incidente" in col.lower()),
        next((col for col in df_tec_chat.columns if "negociador" in col.lower()), None)
    )
    if col_neg_tec:
        df_tec_chat["Negociador_Tecnica"] = df_tec_chat[col_neg_tec].apply(
            lambda x: str(x[0]).strip() if isinstance(x, list) and len(x) > 0 else str(x).strip()
        )

    df_tec_chat = df_tec_chat.dropna(subset=["Nome_Tecnica"]) if "Nome_Tecnica" in df_tec_chat.columns else df_tec_chat

    return df_tec_chat

def preparar_df_estatisticas(stats_calculados) -> pd.DataFrame:
    """Transforma o contexto estatístico num DataFrame para o Agente Delta."""
    try:
        if isinstance(stats_calculados, dict):
            return pd.DataFrame([stats_calculados])
        else:
            return pd.DataFrame([{"Contexto_Estatistico_Geral": str(stats_calculados)}])
    except Exception:
        return pd.DataFrame([{"Status": "Sem dados estatísticos processados"}])


# ============================================================
# BLOCO F — INTERFACE DO CHAT 
# ============================================================

with aba_chat:
    st.markdown("### 💬 DELTA-NEGOCIAÇÃO — Assistente Analítico Operacional | GATE")
    st.markdown(
        "<p style='color:#aaa; font-size:13px;'>"
        "Consultas baseadas exclusivamente em dados reais via Tool Calling. "
        "O agente executa análises Pandas cruzando Ocorrências e Técnicas, "
        "interpreta modelos estatísticos e traça perfis operacionais de negociadores."
        "</p>",
        unsafe_allow_html=True,
    )

    # ── Preparação dos dados (BLINDADA E LIMPA) ──────────────────
    
    if "df_quali" not in st.session_state or "df_tec" not in st.session_state:
        with st.spinner("A sincronizar a base de dados com o Airtable..."):
            import airtable_link
            df_q, _ = airtable_link.buscar_dados_apa()
            df_t, _ = airtable_link.buscar_todas_tecnicas()
            st.session_state["df_quali"] = df_q
            st.session_state["df_tec"] = df_t

    df_chat = preparar_df_ocorrencias(st.session_state["df_quali"])
    df_tec_chat = preparar_df_tecnicas(st.session_state["df_tec"])
    
    stats_calculados = st.session_state.get(
        "stats_calculados", 
        "Nenhuma análise estatística processada."
    )
    df_stats = preparar_df_estatisticas(stats_calculados)

    # ── Inicialização do histórico de chat ───────────────────────
    if "mensagens_chat" not in st.session_state:
        st.session_state.mensagens_chat = [
            {
                "role": "assistant", 
                "content": (
                    "🟢 **DELTA operacional.** Base de ocorrências e banco de técnicas conectados.\n\n"
                    "Posso responder a consultas descritivas, cruzar dados entre ocorrências e técnicas, "
                    "interpretar modelos estatísticos (Spearman, χ², GEE), traçar perfis de negociadores "
                    "e sugerir treinos com base nos dados.\n\n"
                    "**Exemplos de perguntas:**\n"
                    "- *Perguntas descritivas*\n"
                    "- *Quais as 5 técnicas mais usadas em ocorrências com resolução X?*\n"
                    "- *Trace o perfil operacional completo do negociador [x].*"
                )
            }
        ]

    for msg in st.session_state.mensagens_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pergunta = st.chat_input("Ex: Quais técnicas o negociador X mais usou?")

    if pergunta:
        with st.chat_message("user"):
            st.markdown(pergunta)
        st.session_state.mensagens_chat.append({"role": "user", "content": pergunta})

        tipo_query = classificar_query(pergunta)
        modelo_selecionado = selecionar_modelo(tipo_query)
        temperatura_selecionada = selecionar_temperatura(tipo_query)

        camada_label = "🧠 Camada Doutrinária ativa" if tipo_query == "doutrinaria" else "📊 Consulta factual"
        
        with st.spinner(f"[{camada_label}] A analisar os dados e a construir a resposta..."):
            try:
                historico_texto = ""
                mensagens_recentes = st.session_state.mensagens_chat[-5:-1]
                if len(mensagens_recentes) > 0:
                    historico_texto = "CONTEXTO DA CONVERSA RECENTE:\n" + "\n".join(
                        [f"{m['role'].upper()}: {m['content']}" for m in mensagens_recentes]
                    ) + "\n\nNOVA PERGUNTA DO USUÁRIO:\n"

                input_enriquecido = historico_texto + pergunta
                prefix_dinamico = montar_prefix(tipo_query)

                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(
                    model=modelo_selecionado,
                    temperature=temperatura_selecionada,
                    api_key=st.secrets["OPENAI_API_KEY"],
                    max_tokens=4096,
                )

                from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
                
                # ---> NOVO: Parâmetro 'number_of_head_rows=1' adicionado abaixo <---
                agent_executor = create_pandas_dataframe_agent(
                    llm=llm,
                    df=[df_chat, df_tec_chat, df_stats], 
                    verbose=True,
                    agent_type="openai-tools",
                    prefix=prefix_dinamico,
                    allow_dangerous_code=True,
                    max_iterations=10, 
                    handle_parsing_errors=True,
                    number_of_head_rows=1, # Reduz drasticamente os tokens enviados à OpenAI!
                )

                resultado = agent_executor.invoke({"input": input_enriquecido})
                resposta = resultado.get("output", "Não consegui processar a resposta.")
                registrar_interacao(pergunta, tipo_query, modelo_selecionado, len(resposta))

            except Exception as e:
                resposta = f"⚠️ **Erro na execução:** {str(e)}"
        
        with st.chat_message("assistant"):
            st.markdown(resposta)
        st.session_state.mensagens_chat.append({"role": "assistant", "content": resposta})

    # ── RODAPÉ INFORMATIVO ──────────────────────────────
    st.markdown("""
    <div style='margin-top:30px; margin-bottom:100px; padding:15px; 
                background-color:#111; border-radius:8px;'>
        <p style='color:#bbb; font-size:13px;'>
        <b>Sobre o DELTA — Assistente Analítico GATE/PMESP:</b><br><br>
        Todas as respostas são geradas exclusivamente a partir dos dados reais das ocorrências. 
        Nenhuma resposta é produzida por suposição, inferência livre ou memória do modelo.<br><br>
        O agente executa código Python/Pandas internamente para cada consulta, 
        cruzando a <b>Base de Ocorrências</b> com o <b>Banco de Técnicas</b> e 
        interpretando os resultados dos modelos estatísticos avançados (Spearman, χ², GEE).<br><br>
        <b>Capacidades disponíveis:</b><br>
        • Consultas descritivas por ocorrência, data, negociador ou modalidade<br>
        • Análise de frequência e repertório de técnicas<br>
        • Interpretação de perceção de agressividade e recetividade (Δ Likert)<br>
        • Análise de similitude lexical e N-Grams da transcrição<br>
        • Interpretação de Spearman, χ² e GEE<br>
        • Perfil operacional e sugestão de treino por negociador<br>
        • Deteção de viés de alocação na série histórica<br><br>
        <span style='color:#666; font-size:11px;'>
        DELTA v3.0 | LangChain + OpenAI Tool Calling | GATE/PMESP — Uso Restrito Operacional
        </span>
        </p>
    </div>
    """, unsafe_allow_html=True)