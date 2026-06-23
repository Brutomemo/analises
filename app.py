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
import serie_historica
import chat_delta
import form_apa

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
import os

def check_password():
    """Retorna True se o usuário inseriu a senha correta."""
    
    # LER APENAS DE VARIÁVEIS DE AMBIENTE (Railway)
    correct_password = os.getenv("ACCESS_PASSWORD")
    
    # Validação
    if not correct_password:
        st.error("❌ ACCESS_PASSWORD não configurada no Railway!")
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
         data-us-project="XPl2w0YzOvf5kT7pPLLc"
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

window.addEventListener("load", () => {
    if (window.UnicornStudio) {
        UnicornStudio.init();
    }
});

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

# ============================================================
# 3. CONEXÃO E NAVEGAÇÃO PRINCIPAL
# ============================================================

# Os dados já foram carregados acima no "porteiro"
# (lazy load com session_state).

status_q = st.session_state.get("status_q", "OK")
status_t = st.session_state.get("status_t", "OK")

# ============================================================
# CSS GLOBAL
# ============================================================

st.markdown(
    """
    <style>

    /* =====================================================
       MENU HORIZONTAL
    ===================================================== */

    div[role="radiogroup"] {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1.5rem;
        border-bottom: 1.5px solid #2a2d35;
        padding-bottom: 8px;
    }

    div[role="radiogroup"] label {
        background: transparent !important;
        border: none !important;
        padding: 10px 18px !important;
        border-radius: 6px;
        color: #8b8fa8 !important;
        font-size: 14px !important;
        transition: all 0.2s ease;
    }

    div[role="radiogroup"] label:hover {
        background: rgba(255,255,255,0.03) !important;
        color: #d4d6e0 !important;
    }

    div[role="radiogroup"] label[data-checked="true"] {
        color: #d4a017 !important;
        border-bottom: 2px solid #d4a017 !important;
        font-weight: 600 !important;
    }

    /* =====================================================
       ESCONDE CÍRCULO DO RADIO
    ===================================================== */

    div[role="radiogroup"] input {
        display: none;
    }

    /* =====================================================
       TÍTULOS
    ===================================================== */

    h3 {
        font-size: 20px !important;
        font-weight: 500 !important;
    }

    h2 {
        font-size: 22px !important;
        font-weight: 500 !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

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
                    # ===== SALVAR EM SESSION_STATE PARA USAR NO PDF =====
                    st.session_state.p_agr_c_num = p_agr_c_num
                    st.session_state.p_rec_c_num = p_rec_c_num
                    st.session_state.s_agr_c_num = s_agr_c_num
                    st.session_state.s_rec_c_num = s_rec_c_num
                    st.session_state.l_agr_c_num = l_agr_c_num
                    st.session_state.l_rec_c_num = l_rec_c_num
                    st.session_state.p_agr_e_num = p_agr_e_num
                    st.session_state.p_rec_e_num = p_rec_e_num
                    st.session_state.s_agr_e_num = s_agr_e_num
                    st.session_state.s_rec_e_num = s_rec_e_num
                    st.session_state.l_agr_e_num = l_agr_e_num
                    st.session_state.l_rec_e_num = l_rec_e_num

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

                        # Limiar mínimo de confiança (n de observações)
                        N_MIN_CONFIANCA = 3

                        df_com_score = df_resumo[df_resumo["Score (%)"].notna()].copy()

                        # Coluna de observados (positiva+neutra+negativa) por técnica
                        df_com_score["_observados"] = (
                            df_com_score["🟢 Positiva"]
                            + df_com_score["⚪ Neutra"]
                            + df_com_score["🔴 Negativa"]
                        )

                        # Subconjunto com amostra estatisticamente confiável
                        df_confiavel = df_com_score[df_com_score["_observados"] >= N_MIN_CONFIANCA]
                        df_baixa_confianca = df_com_score[df_com_score["_observados"] < N_MIN_CONFIANCA]

                        if not df_confiavel.empty:
                            score_maximo = df_confiavel["Score (%)"].max()
                            tecnicas_maximas = df_confiavel[df_confiavel["Score (%)"] == score_maximo]

                            if len(tecnicas_maximas) == 1:
                                melhor = tecnicas_maximas.iloc[0]
                                txt_melhor = (
                                    f"✅ <strong>Técnica mais efetiva:</strong> {melhor['Técnica']} "
                                    f"— Score {melhor['Score (%)']:+.1f}% "
                                    f"({int(melhor['🟢 Positiva'])} positivo / {int(melhor['_observados'])} observados)"
                                )
                            else:
                                tecnicas_nomes = ", ".join(tecnicas_maximas['Técnica'].tolist())
                                txt_melhor = (
                                    f"✅ <strong>Técnicas mais efetivas (empate):</strong> {tecnicas_nomes} "
                                    f"— Score {score_maximo:+.1f}% (n≥{N_MIN_CONFIANCA})"
                                )
                        else:
                            txt_melhor = (
                                f"⚠️ Nenhuma técnica atingiu o mínimo de {N_MIN_CONFIANCA} observações "
                                "para análise de efetividade confiável."
                            )

                        st.markdown(f"""
                        <div style='background:rgba(16,185,129,0.08);padding:12px;border-radius:8px;border-left:3px solid #10b981;margin-bottom:10px;'>
                        <p style='color:#ddd;font-size:0.9rem;margin:0;'>
                        {txt_melhor}
                        </p>
                        </div>
                        """, unsafe_allow_html=True)

                        if not df_resumo.empty:
                            max_negativas = df_resumo["🔴 Negativa"].max()
                            tecnicas_minimas = df_resumo[df_resumo["🔴 Negativa"] == max_negativas]

                            if max_negativas == 0:
                                txt_pior = "ℹ️ Nenhuma técnica registrou reação negativa nesta ocorrência."
                            elif len(tecnicas_minimas) == 1:
                                pior = tecnicas_minimas.iloc[0]
                                txt_pior = (
                                    f"⚠️ <strong>Técnica menos efetiva:</strong> {pior['Técnica']} "
                                    f"— Score {pior['Score (%)']:+.1f}% "
                                    f"({int(pior['🔴 Negativa'])} negativo / {int(pior['Total'])} usos)"
                                )
                            else:
                                tecnicas_nomes = ", ".join(tecnicas_minimas['Técnica'].tolist())
                                score_medio_piores = round(tecnicas_minimas["Score (%)"].mean(), 1)
                                txt_pior = (
                                    f"⚠️ <strong>Técnicas menos efetivas (empate):</strong> {tecnicas_nomes} "
                                    f"— {int(max_negativas)} validações negativas | Score médio {score_medio_piores:+.1f}%"
                                )

                            st.markdown(f"""
                            <div style='background:rgba(239,68,68,0.08);padding:12px;border-radius:8px;border-left:3px solid #ef4444;margin-bottom:10px;'>
                            <p style='color:#ddd;font-size:0.9rem;margin:0;'>
                            {txt_pior}
                            </p>
                            </div>
                            """, unsafe_allow_html=True)

                            if not df_baixa_confianca.empty:
                                tecnicas_baixa = ", ".join(df_baixa_confianca['Técnica'].tolist())
                                st.markdown(f"""
                                <div style='background:rgba(255,255,255,0.04);padding:10px;border-radius:8px;border-left:3px solid #6b7280;margin-bottom:10px;'>
                                <p style='color:#999;font-size:0.8rem;margin:0;'>
                                ℹ️ <strong>Baixa confiança estatística (n&lt;{N_MIN_CONFIANCA}):</strong> {tecnicas_baixa} —
                                excluídas do ranking de "mais efetiva" por amostra insuficiente.
                                </p>
                                </div>
                                """, unsafe_allow_html=True)

                        st.markdown("---")
                        st.markdown("### ✔️ Efetividade Geral do Repertório Técnico")

                        # Mediana ponderada por volume — mais robusta que média simples
                        # como referência de dispersão (NÃO é "baseline" para o score_geral,
                        # que é uma métrica diferente: ponderada pelo total observado)
                        mediana_scores = round(df_com_score["Score (%)"].median(), 1) if not df_com_score.empty else 0

                        st.markdown(f"""
                        <div style='background:rgba(255,215,0,0.06);padding:12px;border-radius:8px;border:1px solid rgba(255,215,0,0.15);margin-bottom:15px;'>
                        <p style='font-size:0.85rem;color:#FFD700;margin:0 0 8px 0;'>
                        <strong>ℹ️ Como é medido:</strong>
                        </p>
                        <p style='font-size:0.85rem;color:#ddd;margin:0;line-height:1.6;'>
                        <strong>Score Geral</strong> = (Σ positivas − Σ negativas) / Σ observadas × 100% — métrica ponderada pelo volume de uso.<br>
                        <strong>Score por técnica</strong> = (positivas − negativas) / observadas × 100%.<br>
                        <strong>Mediana das técnicas:</strong> {mediana_scores:+.1f}% (referência de dispersão; técnicas com n&lt;{N_MIN_CONFIANCA} têm baixa confiança estatística).
                        </p>
                        </div>
                        """, unsafe_allow_html=True)

                        if score_geral >= 50:
                            cor = "🟢"
                            status = "ÓTIMA"
                            explicacao = (
                                f"O repertório técnico teve {score_geral:+.1f}% de efetividade geral, "
                                f"considerando {observados_total} reações observadas de {total_usos} usos totais. "
                                "Positivas superaram negativas de forma significativa nesta ocorrência."
                            )
                        elif score_geral >= 0:
                            cor = "🟡"
                            status = "MODERADA"
                            explicacao = (
                                f"O repertório técnico teve {score_geral:+.1f}% de efetividade geral, "
                                f"considerando {observados_total} reações observadas de {total_usos} usos totais. "
                                "Positivas e negativas estão relativamente equilibradas — "
                                "há oportunidade de aprimoramento."
                            )
                        else:
                            cor = "🔴"
                            status = "FRACA"
                            explicacao = (
                                f"O repertório técnico teve {score_geral:+.1f}% de efetividade geral, "
                                f"considerando {observados_total} reações observadas de {total_usos} usos totais. "
                                "Negativas superaram positivas — possível mismatch entre técnicas "
                                "empregadas e dinâmica do causador."
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

                        n_positivas_tec = (df_com_score["Score (%)"] > 0).sum()
                        n_negativas_tec = (df_com_score["Score (%)"] < 0).sum()
                        n_neutras_tec   = (df_com_score["Score (%)"] == 0).sum()
                        n_total_tec     = len(df_com_score)
                        n_baixa_conf    = len(df_baixa_confianca)
                        variacao        = df_com_score["Score (%)"].max() - df_com_score["Score (%)"].min()

                        st.markdown(f"""
                        <p style='font-size:0.9rem;color:#aaa;line-height:1.6;'>
                        <strong>Técnicas com score positivo:</strong> {n_positivas_tec} de {n_total_tec}<br>
                        <strong>Técnicas com score negativo:</strong> {n_negativas_tec} de {n_total_tec}<br>
                        <strong>Técnicas neutras (0%):</strong> {n_neutras_tec} de {n_total_tec}<br>
                        <strong>Técnicas com baixa confiança (n&lt;{N_MIN_CONFIANCA}):</strong> {n_baixa_conf} de {n_total_tec}<br>
                        <strong>Variação entre técnicas:</strong> {variacao:.1f} pontos percentuais<br>
                        <strong>Total de reações observadas:</strong> {observados_total} (de {total_usos} usos registrados)
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

            #  (ANÁLISE SEMÂNTICA, etc)
        
               
            st.markdown("""
            <h3 style='color: #FFD700;'>Análise Semântica </h3>
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
                    Esta é uma <strong>ferramenta de leitura</strong>. Os números descrevem o que foi DITO, 
                    não o que vai acontecer.
                    </p>
                    <hr style='border-color:#444;margin:12px 0;'>
                    <p style='font-size:0.92rem;color:#ddd;line-height:1.6;'>
                    ❌ <strong>Não vê o histórico do sujeito:</strong> Quantas tentativas de suicidio.<br>
                    ❌ <strong>Não vê o contexto real:</strong> Há reféns? O sistema não sabe.<br>
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

                # --- TAB 6: CONVERGÊNCIA TEMÁTICA  ---
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

            st.markdown("### Detalhes da Transcrição")

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
                            label="✔️ Análise dos Padrões Léxicos",
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
                                             


        
            st.markdown("---")
                                    
                            # ===== PRÓXIMO BOTÃO (FORA DA TAB) =====
            if st.button("✔ 3. GERAR ANALYTICS E EXPORTAR ANÁLISE (PDF)"):
                with st.spinner("Compilando dados técnicos, consultando IA e desenhando PDF..."):
                    try:
                        # ===== RECUPERAR DO SESSION_STATE =====
                        p_agr_c_num = st.session_state.get('p_agr_c_num', 0)
                        p_rec_c_num = st.session_state.get('p_rec_c_num', 0)
                        s_agr_c_num = st.session_state.get('s_agr_c_num', 0)
                        s_rec_c_num = st.session_state.get('s_rec_c_num', 0)
                        l_agr_c_num = st.session_state.get('l_agr_c_num', 0)
                        l_rec_c_num = st.session_state.get('l_rec_c_num', 0)
                        p_agr_e_num = st.session_state.get('p_agr_e_num', 0)
                        p_rec_e_num = st.session_state.get('p_rec_e_num', 0)
                        s_agr_e_num = st.session_state.get('s_agr_e_num', 0)
                        s_rec_e_num = st.session_state.get('s_rec_e_num', 0)
                        l_agr_e_num = st.session_state.get('l_agr_e_num', 0)
                        l_rec_e_num = st.session_state.get('l_rec_e_num', 0)

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
                        # - n-grams / modelagem de tópicos
                        # - convergência
                       
                        meta_dict["analises_calculadas"] = {                            
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
                        pdf.cell(0, 15, "RELATÓRIO DE ANALISE POS-ACAO (APA), ASSISTIDO POR INTELIGENCIA ARTIFICIAL PARA APOIO DECISORIO", ln=True, align="C")
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
            © 2026 Delta-Negociação — Todos os direitos reservados.<br>
            Este sistema é protegido por direitos autorais e legislação aplicável. Reprodução, distribuição, engenharia reversa, modificação ou utilização não autorizada são proibidas.
            </div>
            """, unsafe_allow_html=True)

    elif pagina == "✔ Série Histórica":
        serie_historica.render_serie_historica(df_quali)

    elif pagina == "✔ Chat Analítico":
        chat_delta.render_chat_delta(df_quali, df_tec)  
  
    elif pagina == "✔ Entrada de Dados":
        form_apa.render(df_quali, df_tec)

    