import streamlit as st
import subprocess
import sys
import os

# =========================================================
# 0. PROTEÇÃO E INSTALAÇÃO AUTOMÁTICA
# =========================================================
try:
    import statsmodels.api as sm
    import patsy
except ImportError:
    # Se falhar, tenta instalar silenciosamente no Python ativo
    subprocess.check_call([sys.executable, "-m", "pip", "install", "statsmodels", "patsy", "scipy"])
    st.rerun() 

# =========================================================
# 1. SEUS IMPORTS ORIGINAIS (MANTIDOS E COMPLETOS)
# =========================================================
from PIL import Image
import base64
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
import tempfile
from fpdf import FPDF
import unicodedata

# =========================================================
# 1.1. IMPORTAÇÃO DOS MÓDULOS DE IA E DADOS
# =========================================================
import airtable_link
import analise
import ia_link        # Cérebro da Aba 1 (Transcrições)
import ia_estatistica # Cérebro da Aba 2 (Série Histórica)

# LINHA DE DEBUG (Remova após resolver o erro):
# st.sidebar.write(f"DEBUG: ia_link vindo de: {ia_link.__file__}")

# =========================================================
# 2. FUNÇÕES AUXILIARES (TRATAMENTO DE DADOS DO AIRTABLE)
# =========================================================
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
    # 1. Opções de Sistema / Inaudíveis
    "❓ inaudível / não observado": 0, "inaudível": 0, "não observado": 0, "n/d": 0, "nao observado": 0,

    # 2. Novos Termos da sua Base (Blinda contra erros de digitação)
    "não agressivo": 1, "nao agressivo": 1, "não agresssivo": 1, "nao agresssivo": 1, "muito baixa": 1, "muito baixo": 1,
    "baixo": 2, "baixa": 2, "pouco receptivo": 2,
    "neutro": 3, "moderada": 3, "moderado": 3,
    "receptivo": 4, "alta": 4, "alto": 4,
    "muito receptivo": 5, "muito alta": 5, "muito alto": 5,

    # 3. Mapeamento das Fórmulas com Emojis 
    "🔴 reação negativa": 1, "⚪ reação neutra": 3, "🟢 reação positiva": 5
}

def converter_escala(val):
    if not val: return 0
    # Limpa emojis e espaços para garantir o "match"
    v = str(val).lower().strip()
    return escala_likert.get(v, 0)

# =========================================================
# 1. CONFIGURAÇÃO DA PÁGINA E CSS (UX e Design System)
# =========================================================
st.set_page_config(page_title="GATE - Analisador de APAs", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=Bricolage+Grotesque:opsz,wght@12..96,300;12..96,400;12..96,600&display=swap');

    /* Configurações Globais */
    .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; z-index: 10; position: relative;}
    header {visibility: hidden;}
    /* Fundo Transparente para revelar o WebGL */
    body { background-color: #050505 !important; }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { 
        background: transparent !important;
        background-color: transparent !important; 
        color: #FFFFFF; 
        overflow-x: hidden; 
        font-family: 'Inter', sans-serif;
    }
    
    /* Fundo Estrelado - Luminous Design System */
    .stars-bg {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image:
            radial-gradient(1.5px 1.5px at 20px 30px, #fff, rgba(0,0,0,0)),
            radial-gradient(1.5px 1.5px at 40px 70px, #ffffff, rgba(0,0,0,0)),
            radial-gradient(1.5px 1.5px at 50px 160px, #ffffff, rgba(0,0,0,0)),
            radial-gradient(2px 2px at 90px 40px, #ffffff, rgba(0,0,0,0)),
            radial-gradient(1.5px 1.5px at 130px 80px, #ffffff, rgba(0,0,0,0));
        background-size: 200px 200px;
        opacity: 0.45; /* Aumentado para maior visibilidade */
        z-index: 1; /* Acima do fundo preto */
        pointer-events: none;
    }

    /* Animação Efeito Raio Descendo do Céu */
    @keyframes rayFall {
        0% { transform: translateY(-100vh) rotate(15deg); opacity: 0; filter: blur(2px); }
        15% { opacity: 1; filter: blur(0px); } /* Opacidade máxima e foco nítido mais cedo */
        85% { opacity: 1; filter: blur(0px); } /* Mantém brilho máximo durante a queda */
        100% { transform: translateY(120vh) rotate(15deg); opacity: 0; filter: blur(2px); }
    }
    .dynamic-ray {
        position: fixed;
        top: 0;
        width: 3px; /* Raio mais espesso */
        height: 350px; /* Raio mais longo */
        /* Núcleo brilhante (branco) com bordas laranjas para simular energia */
        background: linear-gradient(to bottom, transparent, rgba(249, 115, 22, 0.9), rgba(255, 255, 255, 0.9), transparent);
        /* Efeito Glow / Neon ao redor do raio */
        box-shadow: 0 0 25px 5px rgba(249, 115, 22, 0.7); 
        z-index: 2; /* Traz para frente do fundo, mas atrás dos cards (z-index 10) */
        animation: rayFall linear infinite;
        pointer-events: none;
    }
    .ray1 { left: 15%; animation-duration: 5s; animation-delay: 0s; }
    .ray2 { left: 45%; animation-duration: 4.5s; animation-delay: 2s; }
    .ray3 { left: 75%; animation-duration: 6s; animation-delay: 1s; }
    .ray4 { left: 85%; animation-duration: 7s; animation-delay: 3s; }
    .ray5 { left: 5%; animation-duration: 5.5s; animation-delay: 4s; }

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

    /* Fontes e Títulos */
    .main-title {
        font-family: 'Bricolage Grotesque', sans-serif; font-size: 2.8rem; font-weight: 300; letter-spacing: -0.02em;
        background: linear-gradient(180deg, #FFFFFF 0%, #BBBBBB 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; line-height: 1.1;
    }
    .sub-title { color: #FFD700; font-weight: 600; font-size: 1.1rem; margin-top: 5px; margin-bottom: 0; }
    
    /* Efeito Vidro (Glassmorphism) e Animação de Luz (Sweep) nas Caixas */
    .info-card { 
        background: rgba(10, 10, 10, 0.6); /* Levemente mais opaco para dar contraste aos raios passando por trás */
        backdrop-filter: blur(16px) saturate(180%);
        -webkit-backdrop-filter: blur(16px) saturate(180%);
        border-top: 1px solid rgba(255, 255, 255, 0.15);
        border-left: 1px solid rgba(255, 255, 255, 0.08);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        border-radius: 12px; padding: 15px; margin-top: 15px; margin-bottom: 15px; 
        position: relative; overflow: hidden;
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

    /* Efeito Design System nos Botões (Gradiente + Glow) */
    div.stButton > button { 
        background: linear-gradient(to top, #fef08a 0%, #fb923c 50%, #f97316 100%) !important;
        color: #2c1306 !important; /* Cor escura para leitura perfeita sobre o laranja/amarelo */
        border: 1px inset rgba(255, 255, 255, 0.4) !important;
        padding: 0.7rem 2rem; border-radius: 9999px !important; font-weight: 600 !important; 
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important; width: 100%; position: relative;
        box-shadow: 0 0 40px -5px rgba(249, 115, 22, 0.6) !important;
        animation: fadeInUpBlur 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) both;
    }
    div.stButton > button:hover { 
        box-shadow: 0 0 60px -5px rgba(249, 115, 22, 0.8) !important; 
        transform: scale(1.05) translateY(-2px) !important; 
    }
    
    /* Efeito Ambient Blobs (Degradês Flutuantes no Fundo) */
    .liquid-blob {
        position: fixed; border-radius: 60%; filter: blur(80px); opacity: 0.20; z-index: 1;
        animation: float 10s infinite alternate cubic-bezier(0.4, 0, 0.2, 1); pointer-events: none;
    }
    .blob1 { background-color: #FFD700; width: 500px; height: 500px; top: -100px; left: -100px; animation-duration: 15s; }
    .blob2 { background-color: #fb923c; width: 400px; height: 400px; top: 40%; right: -100px; animation-duration: 20s; animation-delay: -10s; }
    .blob3 { background-color: #c2410c; width: 600px; height: 600px; bottom: -150px; left: 20%; animation-duration: 25s; animation-delay: -15s; }
    
    @keyframes float {
        0% { transform: translate(0, 0) scale(1); }
        100% { transform: translate(30px, 50px) scale(1.1); }
    }

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
</style>

<div class="stars-bg"></div>
<div class="dynamic-ray ray1"></div>
<div class="dynamic-ray ray2"></div>
<div class="dynamic-ray ray3"></div>
<div class="dynamic-ray ray4"></div>
<div class="dynamic-ray ray5"></div>

<div class="liquid-blob blob1"></div>
<div class="liquid-blob blob2"></div>
<div class="liquid-blob blob3"></div>
""", unsafe_allow_html=True)

# Cursor Customizado Global via JavaScript
components.html("""
<script>
    const doc = window.parent.document;
    if (!doc.getElementById('cursor-gate')) {
        const cursor = doc.createElement('div');
        cursor.id = 'cursor-gate';
        cursor.style.position = 'fixed';
        cursor.style.top = '0';
        cursor.style.left = '0';
        cursor.style.width = '20px';
        cursor.style.height = '20px';
        cursor.style.backgroundColor = 'rgba(255, 255, 255, 0.8)';
        cursor.style.borderRadius = '50%';
        cursor.style.pointerEvents = 'none';
        cursor.style.zIndex = '999999';
        cursor.style.transform = 'translate(-50%, -50%)';
        cursor.style.transition = 'width 0.2s, height 0.2s, background-color 0.2s';
        cursor.style.mixBlendMode = 'overlay';
        cursor.style.backdropFilter = 'blur(2px)';
        doc.body.appendChild(cursor);

        doc.addEventListener('mousemove', (e) => {
            cursor.style.left = e.clientX + 'px';
            cursor.style.top = e.clientY + 'px';
        });

        doc.addEventListener('mousedown', () => {
            cursor.style.width = '15px';
            cursor.style.height = '15px';
            cursor.style.backgroundColor = '#FFD700';
        });
        
        doc.addEventListener('mouseup', () => {
            cursor.style.width = '20px';
            cursor.style.height = '20px';
            cursor.style.backgroundColor = 'rgba(255, 255, 255, 0.8)';
        });
    }
</script>
""", height=0, width=0)

if 'stats_calculados' not in st.session_state: st.session_state['stats_calculados'] = None
if 'dados_n8n' not in st.session_state: st.session_state['dados_n8n'] = None

# =========================================================
# BACKGROUND DINÂMICO WEBGL (Unicorn Studio)
# =========================================================
components.html("""
<script>
    const parentDoc = window.parent.document;
    const parentWin = window.parent;

    // Verifica se o background já existe para não duplicar quando o Streamlit atualizar
    if (!parentDoc.getElementById('unicorn-bg-container')) {
        
        // Cria o container do background que vai ocupar a tela toda
        const bgContainer = parentDoc.createElement('div');
        bgContainer.id = 'unicorn-bg-container';
        bgContainer.style.position = 'fixed';
        bgContainer.style.top = '0';
        bgContainer.style.left = '0';
        bgContainer.style.width = '100vw';
        bgContainer.style.height = '100vh';
        bgContainer.style.zIndex = '-10'; // Garante que fique atrás de tudo
        bgContainer.style.pointerEvents = 'none'; // Impede que o fundo roube os cliques
        
        // Cria a div específica exigida pelo Unicorn Studio com o SEU PROJETO
        const usDiv = parentDoc.createElement('div');
        usDiv.id = 'hero-bg';
        usDiv.setAttribute('data-us-project', '0Air3YV0ySfVbTEkT2EW'); // <-- SEU EFEITO AQUI
        usDiv.style.width = '100%';
        usDiv.style.height = '100%';
        
        // Injeta as divs no corpo (body) do Streamlit
        bgContainer.appendChild(usDiv);
        parentDoc.body.appendChild(bgContainer);

        // Carrega o script do Unicorn Studio dinamicamente
        const script = parentDoc.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/gh/hiunicornstudio/unicornstudio.js@v1.4.34/dist/unicornStudio.umd.js';
        
        script.onload = function() {
            // Inicializa o WebGL assim que o script terminar de carregar
            if (!parentWin.UnicornStudio || !parentWin.UnicornStudio.isInitialized) {
                if(parentWin.UnicornStudio) {
                    parentWin.UnicornStudio.init();
                    parentWin.UnicornStudio.isInitialized = true;
                }
            }
        };
        
        parentDoc.head.appendChild(script);
    }
</script>
""", height=0, width=0)

# =========================================================
# 2. CABEÇALHO VISUAL E FUNDO DO CABEÇALHO
# =========================================================
import os
import base64
from PIL import Image

script_dir = os.path.dirname(os.path.abspath(__file__))
path_assets = os.path.join(script_dir, "Assets") 

# Padronizando os caminhos limpos (Apenas banner e logo em webp)
path_teste_gate = os.path.join(path_assets, "teste_gate.webp")
path_brasao_gate = os.path.join(path_assets, "brasao_gate.webp")

# --- 1. PREPARAR IMAGENS (Codificar para Base64) ---
img_topo_b64 = ""

# Topo (Banner principal)
try:
    with open(path_teste_gate, "rb") as img_file: 
        img_topo_b64 = base64.b64encode(img_file.read()).decode()
except: pass 

# --- 2. RENDERIZAR BANNER TOPO (Com animação e degradê) ---
if img_topo_b64:
    st.markdown(f"""<div style="position: relative; width: 100%; height: 200px; border-radius: 2px; overflow: hidden; background-image: url('data:image/webp;base64,{img_topo_b64}'); background-size: cover; background-position: center 40%; margin-bottom: 1rem; animation: fadeInUpBlur 1s cubic-bezier(0.2, 0.8, 0.2, 1) both;"><div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(180deg, rgba(5,5,5,0.1) 0%, rgba(249, 115, 22, 0.6) 100%);"></div></div>""", unsafe_allow_html=True)

# --- 3. CONTEÚDO DO CABEÇALHO (Logo e Textos) ---
col_logo, col_titulo, col_espaco = st.columns([1, 6, 1])

with col_logo:
    try: 
        st.image(Image.open(path_brasao_gate), use_container_width=True)
    except Exception as e: 
        st.error(f"Erro ao carregar logo: Verifique se o arquivo existe em {path_brasao_gate}")

with col_titulo:
    st.markdown('<h1 class="main-title">Sistema de Análise Qualitativa das Negociações - Estudo das Técnicas aplicadas</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Delta Negociação - GATE / PMESP</p>', unsafe_allow_html=True)
    st.markdown('<p style="color: #999; margin-top: 5px;">Desenvolvido por Cb PM Marcos - Supervisão: Cap PM Pavão</p>', unsafe_allow_html=True)
    
    st.markdown(f"""
<div class="info-card">
    <p><strong>Sistema automatizado de análise qualitativa das Negociações em Incidentes Críticos atendidos pelo Grupo de Ações Táticas Especiais.</strong></p>
    <p style="font-size: 0.9rem; color: #999;">Os dados são geridos de forma automatizada em nuvem via <strong>Airtable</strong>. Cálculos matemáticos realizados localmente utilizando  
    <strong>SciPy</strong> (Correlação de Spearman com Quartis) e <strong>Scikit-Learn</strong> (Modelagem N-Gramas). Modelo integra Inteligência Artificial atuando exclusivamente como estruturadora de metadados qualitativos da perspectiva tripla.</p>
</div>
""", unsafe_allow_html=True)
    

    
# =========================================================
# 3. CONEXÃO E NAVEGAÇÃO PRINCIPAL (ABAS)
# =========================================================
with st.spinner("Sincronizando com Banco de Dados Seguro (Airtable)..."):
    df_quali, status_q = airtable_link.buscar_dados_apa()
    df_tec, status_t = airtable_link.buscar_todas_tecnicas()

if df_quali.empty:
    st.error(f"Erro na conexão com Airtable: {status_q}")
else:
    aba_individual, aba_geral = st.tabs(["🎯 Visão seletiva", "📊 Série Histórica"])

    # =========================================================
    # ABA 1: VISÃO DA NEGOCIAÇÃO SOBRE O INCIDENTE EM ANÁLISE
    # =========================================================
    with aba_individual:
        st.markdown("### 🛠️ Etapa 1: Seleção e Metadados da Ocorrência")
        
        df_quali['Neg_Limpo'] = df_quali.get('Negociador Principal', '').apply(limpar_valor)
        df_quali['Tip_Limpa'] = df_quali.get('Tipologia', '').apply(limpar_valor)
        df_quali['Mod_Limpa'] = df_quali.get('Modalidade do incidente', '').apply(limpar_valor)
        
        if 'ID' not in df_quali.columns: df_quali['ID'] = "APA " + df_quali.index.astype(str)
        df_quali['ID_Busca'] = df_quali.get('ID', df_quali.index).apply(limpar_id)

        # Filtros Locais
        col_fi1, col_fi2, col_fi3 = st.columns(3)
        with col_fi1:
            lista_neg_ind = ["Todos"] + sorted(df_quali[df_quali['Neg_Limpo'] != 'N/D']['Neg_Limpo'].unique().tolist())
            filtro_neg_ind = st.selectbox("Filtrar por Negociador:", lista_neg_ind, key="f_neg_ind")
        with col_fi2:
            lista_tip_ind = ["Todas"] + sorted(df_quali[df_quali['Tip_Limpa'] != 'N/D']['Tip_Limpa'].unique().tolist())
            filtro_tip_ind = st.selectbox("Filtrar por Tipologia:", lista_tip_ind, key="f_tip_ind")
        with col_fi3:
            lista_mod_ind = ["Todas"] + sorted(df_quali[df_quali['Mod_Limpa'] != 'N/D']['Mod_Limpa'].unique().tolist())
            filtro_mod_ind = st.selectbox("Filtrar por Modalidade:", lista_mod_ind, key="f_mod_ind")

        df_q_ind = df_quali.copy()
        if filtro_neg_ind != "Todos": df_q_ind = df_q_ind[df_q_ind['Neg_Limpo'] == filtro_neg_ind]
        if filtro_tip_ind != "Todas": df_q_ind = df_q_ind[df_q_ind['Tip_Limpa'] == filtro_tip_ind]
        if filtro_mod_ind != "Todas": df_q_ind = df_q_ind[df_q_ind['Mod_Limpa'] == filtro_mod_ind]
        
        lista_apas = df_q_ind['ID_Busca'].tolist()
        
        if not lista_apas:
            st.warning("Nenhuma ocorrência encontrada com estes filtros.")
        else:
            # 1. Aqui termina o bloco de cima (Filtros e Seletor)
            apa_selecionada = st.selectbox("Selecione a ID da APA para análise:", lista_apas, index=len(lista_apas)-1)
            df_apa = df_quali[df_quali['ID_Busca'] == apa_selecionada].iloc[0]
            
            # ========================================================
            # 💡 HACK DE ESPAÇAMENTO PARA REVELAR A LUZ DO FUNDO
            # ========================================================
            st.markdown("<div style='height: 180px;'></div>", unsafe_allow_html=True)
            
            # 2. Aqui começa o bloco de baixo (Metadados)
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(f"<div class='info-card'><strong>Data:</strong><br>{limpar_valor(df_apa.get('Data da ocorrência'))}</div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='info-card'><strong>Modalidade:</strong><br>{limpar_valor(df_apa.get('Modalidade do incidente'))}</div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='info-card'><strong>Tipologia:</strong><br>{limpar_valor(df_apa.get('Tipologia'))}</div>", unsafe_allow_html=True)
            with c4: st.markdown(f"<div class='info-card'><strong>Motivação:</strong><br>{limpar_valor(df_apa.get('Motivação'))}</div>", unsafe_allow_html=True)

            c5, c6, c7, _ = st.columns(4)
            with c5: st.markdown(f"<div class='info-card'><strong>Negociador Principal:</strong><br>{limpar_valor(df_apa.get('Negociador Principal'))}</div>", unsafe_allow_html=True)
            with c6: st.markdown(f"<div class='info-card'><strong>Tempo de Negociação Real:</strong><br>{formatar_tempo_airtable(df_apa.get('Tempo de Negociação Real'))}</div>", unsafe_allow_html=True)
            with c7: st.markdown(f"<div class='info-card'><strong>Tempo de Negociação Tática:</strong><br>{formatar_tempo_airtable(df_apa.get('Tempo de Negociação Tática'))}</div>", unsafe_allow_html=True)

            st.markdown("---")

            def buscar_percepcao(papel, metrica, momento):
                def norm(t): return unicodedata.normalize('NFKD', str(t)).encode('ASCII', 'ignore').decode('ASCII').lower()
                for col in df_apa.index:
                    col_norm = norm(col)
                    if norm(papel) in col_norm and norm(metrica) in col_norm and norm(momento) in col_norm:
                        return limpar_valor(df_apa[col])
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

            st.markdown("### 📈 Percepção do Negociador sobre a escala de agressividade e receptividade do causador frente ao Negociador Principal")
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

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=["Chegada", "Encerramento"], y=[v_agr_c, v_agr_e], mode='lines+markers', name='Agressividade', line=dict(color='#ef4444', width=4), marker=dict(size=12)))
            fig_trend.add_trace(go.Scatter(x=["Chegada", "Encerramento"], y=[v_rec_c, v_rec_e], mode='lines+markers', name='Receptividade', line=dict(color='#22c55e', width=4), marker=dict(size=12)))
            fig_trend.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#FFF",
                yaxis=dict(title="Nível Qualitativo", tickvals=[0,1,2,3,4,5], ticktext=["Não obs.", "Muito Baixa", "Baixa", "Moderada", "Alta", "Muito Alta"], range=[-0.5, 5.5]),
                xaxis=dict(title="Momento da Ocorrência"), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_trend, use_container_width=True)

            st.markdown("---")

            st.markdown("### 🧠 Percepção dos Negociadores sobre a escala de agressividade e receptividade do causador (Textual)")
            tab_chegada, tab_encerramento = st.tabs(["➡️ Na Chegada à Ocorrência", "🛑 No Encerramento"])
            
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

            st.markdown("### 🗣️ Transcrições Literal")
            with st.expander("Ver transcrições completas da ocorrência", expanded=False):
                st.markdown("**Causador do Incidente:**")
                st.write(limpar_valor(df_apa.get('TRANSCRIÇÃO DO CAUSADOR')))
                st.markdown("**Negociador Principal:**")
                st.write(limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL')))
                st.markdown("**Negociador Secundário:**")
                st.write(limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO')))

            st.markdown("---")

            st.markdown("### 🗣️ Índice de Similitude e Grafo de Espelhamento Léxico")
            st.markdown("<div class='info-card'>", unsafe_allow_html=True)
            st.markdown("<span style='font-size: 0.85rem; color: #aaa;'><strong>O que significa:</strong> Compara matematicamente as palavras utilizadas pelo Negociador Principal e pelo Causador, mensurando o espelhamento. Índices mais altos indicam 'espelhamento' na estrutura da linguagem (mirroring). Em negociações bem-sucedidas, o negociador e o causador passam a apresentar núcleos semânticos em comum, criando uma 'Sincronia Lexical'. O grafo ilustra os núcleos semânticos que conectaram as duas partes.</span><br><br>", unsafe_allow_html=True)

            col_causador = "TRANSCRIÇÃO DO CAUSADOR"
            col_negociador = "TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL"

            if col_causador in df_apa and col_negociador in df_apa:
                txt_caus = str(df_apa[col_causador]).strip()
                txt_neg = str(df_apa[col_negociador]).strip()
                
                if txt_caus.lower() in ['nan', 'none', '', 'inaudível', 'n/d'] or txt_neg.lower() in ['nan', 'none', '', 'inaudível', 'n/d']:
                    st.warning("⚠️ **Diálogo unilateral ou ausente.** Não foi possível mensurar o espelhamento pois uma das partes não produziu volume verbal audível/registrado. Isso geralmente indica ausência de rapport verbal estruturado na fase registrada.")
                elif len(txt_caus.split()) < 5 or len(txt_neg.split()) < 5:
                    st.warning("⚠️ **Volume Verbal Insuficiente:** O diálogo registrado possui menos de 5 palavras válidas por parte, impossibilitando a análise matemática de similitude.")
                else:
                    try:
                        from sklearn.feature_extraction.text import TfidfVectorizer
                        from sklearn.metrics.pairwise import cosine_similarity
                        import re

                        def limpar_texto(t):
                            return re.sub(r'[^\w\s]', '', t.lower())

                        txt_caus_limpo = limpar_texto(txt_caus)
                        txt_neg_limpo = limpar_texto(txt_neg)

                        stopwords_pt = [
                            'o', 'a', 'os', 'as', 'um', 'uma', 'de', 'do', 'da', 'em', 'no', 'na', 'para', 'com', 
                            'que', 'é', 'e', 'se', 'por', 'como', 'pra', 'ta', 'tá', 'eu', 'vc', 'você', 'me', 
                            'meu', 'minha', 'aqui', 'vou', 'isso', 'mas', 'não', 'nao', 'sim', 'só', 'ele', 'ela', 
                            'eles', 'elas', 'vai', 'foi', 'fui', 'tudo', 'bem', 'tem', 'têm', 'bom', 'pode', 'então', 
                            'gente', 'muito', 'mais', 'já', 'agora', 'quando', 'onde', 'quem', 'qual', 'ser', 'fazer', 
                            'ter', 'estar', 'dizer', 'falar', 'quer', 'quero', 'sei', 'sabe', 'ver', 'lá', 'aí', 
                            'pro', 'pra', 'dos', 'das', 'nas', 'nos', 'ou', 'nem', 'até', 'mesmo', 'porque', 'pq', 'mim', 'assim', 'falou', 'dele', 'comigo', 'faz', 'ficar'
                        ]
                        vectorizer = TfidfVectorizer(stop_words=stopwords_pt)
                        
                        tfidf_matrix = vectorizer.fit_transform([txt_neg_limpo, txt_caus_limpo])
                        similaridade = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                        sintonia_pct = similaridade * 100

                        col_sin1, col_sin2 = st.columns([1, 3])
                        
                        with col_sin1:
                            st.metric(label="Grau de Espelhamento", value=f"{sintonia_pct:.1f}%")
                        
                        with col_sin2:
                            cor_barra = "#28a745" if sintonia_pct > 25 else "#ffc107" if sintonia_pct > 10 else "#dc3545"
                            st.markdown(f"""
                            <div style='background-color: #333; border-radius: 5px; width: 100%; height: 25px; margin-top: 15px;'>
                                <div style='background-color: {cor_barra}; width: {sintonia_pct}%; height: 100%; border-radius: 5px;'></div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if sintonia_pct >= 25:
                                st.success("✅ **Forte Vínculo (Espelhamento Tático):** Alto nível de ancoragem. O negociador adequou-se ao código linguístico do causador (espelhamento) e validou seus pontos de interesse.")
                            elif sintonia_pct >= 10:
                                st.info("ℹ️ **Vínculo Moderado:** Há pontos de ancoragem semântica, mas os discursos ainda guardam distanciamento conceitual.")
                            else:
                                st.error("🚨 **Divergência de Discurso:** Vocabulários quase completamente distintos. Indica ruptura ou negociação puramente transacional.")

                        if sintonia_pct > 0:
                            st.markdown("##### 🕸️ Grafo de Espelhamento Léxico (Núcleos Semânticos Compartilhados)")
                            st.write("<span style='font-size: 0.85rem; color: #aaa;'>Visualização interativa dos termos que serviram de ponte para o estabelecimento do Rapport.</span>", unsafe_allow_html=True)
                            
                            try:
                                import plotly.graph_objects as go
                                from collections import Counter

                                palavras_neg = [w for w in txt_neg_limpo.split() if w not in stopwords_pt and len(w) > 2]
                                palavras_caus = [w for w in txt_caus_limpo.split() if w not in stopwords_pt and len(w) > 2]
                                
                                set_comuns = set(palavras_neg).intersection(set(palavras_caus))
                                
                                if set_comuns:
                                    contagem_comuns = Counter({w: palavras_neg.count(w) + palavras_caus.count(w) for w in set_comuns})
                                    top_comuns = dict(contagem_comuns.most_common(12))
                                    
                                    node_x = []
                                    node_y = []
                                    node_text = []
                                    node_color = []
                                    node_size = []

                                    node_x.append(-2)
                                    node_y.append(0)
                                    node_text.append("<b>NEGOCIADOR</b>")
                                    node_color.append("#2196F3") 
                                    node_size.append(40)

                                    node_x.append(2)
                                    node_y.append(0)
                                    node_text.append("<b>CAUSADOR</b>")
                                    node_color.append("#F44336") 
                                    node_size.append(40)

                                    edge_x = []
                                    edge_y = []
                                    
                                    y_pos = 1.5 
                                    passo_y = 3 / max(len(top_comuns), 1) 
                                    
                                    for palavra, peso in top_comuns.items():
                                        node_x.append(0)
                                        node_y.append(y_pos)
                                        node_text.append(palavra)
                                        node_color.append("#FFC107") 
                                        tamanho_calc = min(max(peso * 3, 15), 35) 
                                        node_size.append(tamanho_calc)
                                        
                                        edge_x.extend([-2, 0, None])
                                        edge_y.extend([0, y_pos, None])
                                        
                                        edge_x.extend([0, 2, None])
                                        edge_y.extend([y_pos, 0, None])
                                        
                                        y_pos -= passo_y

                                    edge_trace = go.Scatter(
                                        x=edge_x, y=edge_y,
                                        line=dict(width=1, color='#555'),
                                        hoverinfo='none',
                                        mode='lines')

                                    node_trace = go.Scatter(
                                        x=node_x, y=node_y,
                                        mode='markers+text',
                                        text=node_text,
                                        textposition="bottom center",
                                        hoverinfo='text',
                                        marker=dict(
                                            color=node_color,
                                            size=node_size,
                                            line=dict(width=2, color='white')
                                        ),
                                        textfont=dict(color='white', size=12)
                                    )

                                    fig_grafo = go.Figure(data=[edge_trace, node_trace],
                                                 layout=go.Layout(
                                                    showlegend=False,
                                                    hovermode='closest',
                                                    margin=dict(b=20,l=5,r=5,t=40),
                                                    paper_bgcolor="rgba(0,0,0,0)", 
                                                    plot_bgcolor="rgba(0,0,0,0)",
                                                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                                                ))
                                    
                                    fig_grafo.update_layout(height=400)
                                    
                                    st.plotly_chart(fig_grafo, use_container_width=True)
                                
                                else:
                                    st.info("ℹ️ Não há intersecção semântica suficiente para gerar um grafo estrutural (Discursos completamente isolados).")

                            except Exception as e:
                                st.error(f"Erro ao desenhar o grafo estrutural: {e}")
                                
                    except Exception as e:
                        st.error(f"Erro no cálculo base de similaridade: {e}")
            else:
                st.info("Colunas de transcrição não encontradas para o cálculo de Sintonia Léxica.")
                
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<h4 style='color: #FFD700;'>📉 Frequência das Técnicas Aplicadas (Nesta APA)</h4>", unsafe_allow_html=True)
            
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
                            
                            st.markdown("<h4 style='text-align:center; color: #FFFFFF; margin-top: 20px;'>Frequencias das Técnicas Aplicadas (Treemap)</h5>", unsafe_allow_html=True)
                            fig_tree = px.treemap(df_freq, path=['Técnica Empregada'], values='Frequência Absoluta', color='Frequência Absoluta', color_continuous_scale='Oranges')
                            fig_tree.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#FFF", margin=dict(t=10, l=10, r=10, b=10))
                            st.plotly_chart(fig_tree, use_container_width=True)
                        else:
                            st.warning("Técnicas encontradas, mas a coluna 'TÉCNICAS' não foi identificada no Airtable.")
                    else:
                        st.info(f"Nenhuma técnica cruzou com a APA atual.")
                else:
                    st.warning("A coluna de vínculo (ex: 'Vinculo_APA') não foi encontrada na aba de técnicas.")
            else:
                st.warning("Tabela de técnicas vazia no Airtable.")
            
            st.markdown("---")

            st.markdown("### 📊 Etapa 2: Análise Semântica (Scikit-learn: Machine Learning in Python)")
            if st.button("⚙️ 2. GERAR NUVEM DE PALAVRAS E N-GRAMS"):
                with st.spinner("Processando N-Grams e plotando gráficos..."):
                    texto_c = limpar_valor(df_apa.get('TRANSCRIÇÃO DO CAUSADOR'))
                    texto_np = limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL'))
                    texto_ns = limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO'))
                    texto_total = f"{texto_c} {texto_np} {texto_ns}"
                    st.session_state['stats_calculados'] = {
                        "topicos": analise.extrair_topicos_ngrams(texto_total) if len(texto_total) > 10 else ["Texto insuficiente"],
                        "wc_c": analise.gerar_wordcloud(texto_c) if len(texto_c) > 5 else None,
                        "wc_np": analise.gerar_wordcloud(texto_np) if len(texto_np) > 5 else None,
                        "wc_ns": analise.gerar_wordcloud(texto_ns) if len(texto_ns) > 5 else None
                    }

            if st.session_state['stats_calculados']:
                stats = st.session_state['stats_calculados']
                st.markdown('<div class="info-card"><h4 style="color: #f97316; margin-top: 0;">🧠 Temas Dominantes Globais (N-Gramas)</h4>', unsafe_allow_html=True)
                for t in stats['topicos']: st.markdown(t)
                st.markdown('</div>', unsafe_allow_html=True)
                
                c_w1, c_w2, c_w3 = st.columns(3)
                with c_w1:
                    st.markdown('<p style="color: #FFD700; font-weight: bold; text-align:center;">Causador</p>', unsafe_allow_html=True)
                    if stats['wc_c']: st.pyplot(stats['wc_c'])
                with c_w2:
                    st.markdown('<p style="color: #FFD700; font-weight: bold; text-align:center;">Negociador Principal</p>', unsafe_allow_html=True)
                    if stats['wc_np']: st.pyplot(stats['wc_np'])
                with c_w3:
                    st.markdown('<p style="color: #FFD700; font-weight: bold; text-align:center;">Negociador Secundário</p>', unsafe_allow_html=True)
                    if stats['wc_ns']: st.pyplot(stats['wc_ns'])

            st.markdown("---")
            
            st.markdown("### 📄 Etapa 3: Inteligência de Apoio à Decisão e Exportação")
            
            url_n8n = "http://host.docker.internal:5680/webhook/analise-doc"
            
            if st.button("📡 3. GERAR ANALYTICS E EXPORTAR ANÁLISE (PDF)"):
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

                        temas_extraidos = st.session_state['stats_calculados']['topicos'] if st.session_state.get('stats_calculados') else ["Etapa 2 não executada"]

                        meta_dict = df_apa.to_dict()
                        meta_dict["temas_dominantes_scikit_learn"] = " | ".join(temas_extraidos)
                        df_meta = pd.DataFrame([meta_dict])
                                                
                        dados_extraidos = {
                            "transcricao": df_transcricoes,
                            "metadados": df_meta
                        }

                        resultado_ia = ia_link.analisar_ocorrencia_gate(dados_extraidos)
                        
                        if isinstance(resultado_ia, dict) and 'parecer' in resultado_ia:
                            parecer_ia = resultado_ia['parecer']
                        else:
                            parecer_ia = f"Sinal recebido, mas os dados estão incompletos ou a URL precisa de ajuste. Bruto: {resultado_ia}"

                        def calcular_media_equipe(*valores):
                            validos = [v for v in valores if v > 0]
                            return sum(validos) / len(validos) if validos else 0

                        likert_inicio = {
                            'agressividade_media': calcular_media_equipe(p_agr_c_num, s_agr_c_num, l_agr_c_num), 
                            'receptividade_media': calcular_media_equipe(p_rec_c_num, s_rec_c_num, l_rec_c_num)
                        }
                        likert_fim = {
                            'agressividade_media': calcular_media_equipe(p_agr_e_num, s_agr_e_num, l_agr_e_num), 
                            'receptividade_media': calcular_media_equipe(p_rec_e_num, s_rec_e_num, l_rec_e_num)
                        }
                        stats_spearman = {'valido': False, 'p_value': 0.0, 'rho': 0.0} 
                        laudo_frio = ia_link.gerar_laudo_frio(likert_inicio, likert_fim, stats_spearman)

                        st.markdown(f"""
                        <div class="info-card" style="border-left: 4px solid #FFD700;">
                            <h4 style="color: #FFD700; margin-top: 0;">Inferência Estatística (Motor Frio)</h4>
                            <p style="font-size: 1.05rem; line-height: 1.6;">{laudo_frio}</p>
                            <hr style="border-color: rgba(255,255,255,0.1); margin: 15px 0;">
                            <h4 style="color: #06C755; margin-top: 0;">Leitura Analítica (Interpretação descritiva dos resultados)</h4>
                            <p style="font-size: 1.05rem; line-height: 1.6;">{parecer_ia}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        if isinstance(parecer_ia, dict):
                            partes = [f"{k.upper()}:\n{v}" for k, v in parecer_ia.items()]
                            texto_str = "\n\n".join(partes)
                        else:
                            texto_str = str(parecer_ia)
                        
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
                        
                        pdf.multi_cell(0, 8, txt=unicodedata.normalize('NFKD', info_str).encode('ASCII', 'ignore').decode('ASCII'), border='L')
                        
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

    # =========================================================
    # ABA 2: PAINEL (HISTÓRICO)
    # =========================================================
    with aba_geral:
        st.markdown("### 🧠 Série Histórica - Negociações GATE")
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
        st.markdown("#### Ranking de Técnicas Aplicadas")
        if not df_tec.empty:
            df_tec['Neg_Limpo'] = df_tec['Negociador Principal do incidente crítico'].apply(limpar_valor) if 'Negociador Principal do incidente crítico' in df_tec.columns else 'N/D'
            df_tec['Tip_Limpa'] = df_tec['Tipologia do incidente crítico'].apply(limpar_valor) if 'Tipologia do incidente crítico' in df_tec.columns else 'N/D'
            df_tec['Mod_Limpa'] = df_tec['Modalidade do incidente crítico'].apply(limpar_valor) if 'Modalidade do incidente crítico' in df_tec.columns else 'N/D'
            
            df_tec_filt = df_tec.copy()
            if filtro_neg_g != "Todos": df_tec_filt = df_tec_filt[df_tec_filt['Neg_Limpo'] == filtro_neg_g]
            if filtro_tip_g != "Todas": df_tec_filt = df_tec_filt[df_tec_filt['Tip_Limpa'] == filtro_tip_g]
            if filtro_mod_g != "Todas": df_tec_filt = df_tec_filt[df_tec_filt['Mod_Limpa'] == filtro_mod_g]
            
            if not df_tec_filt.empty:
                col_t = next((col for col in ['TÉCNICAS', 'TECNICAS', 'TÉCNICA', 'TECNICA'] if col in df_tec_filt.columns), None)
                if col_t:
                    freq_global = df_tec_filt[col_t].value_counts().reset_index()
                    freq_global.columns = ['Técnica', 'Vezes Utilizada']
                    
                    c_tab, c_tree = st.columns([1, 2])
                    with c_tab: st.dataframe(freq_global, use_container_width=True, hide_index=True)
                    with c_tree:
                        fig_g = px.treemap(freq_global, path=['Técnica'], values='Vezes Utilizada', color='Vezes Utilizada', color_continuous_scale='Oranges')
                        fig_g.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#FFF", margin=dict(t=0, l=0, r=0, b=0))
                        st.plotly_chart(fig_g, use_container_width=True)
                else: st.warning("Coluna 'TÉCNICAS' não encontrada.")
            else: st.info("Nenhuma técnica encontrada para os filtros selecionados.")
            
        st.markdown("---")
        st.markdown("<h4 style='color: #FFD700;'>🔬 Análise Inferencial Básica</h4>", unsafe_allow_html=True)
        
        def achar_coluna(df, papel, metrica, momento):
            import unicodedata
            def norm(t): return unicodedata.normalize('NFKD', str(t)).encode('ASCII', 'ignore').decode('ASCII').lower()
            for col in df.columns:
                col_norm = norm(col)
                if norm(papel) in col_norm and norm(metrica) in col_norm and norm(momento) in col_norm:
                    return col
            return None

        col_agr_c = achar_coluna(df_quali_filt, 'Principal', 'Agressividade', 'Chegada')
        col_agr_e = achar_coluna(df_quali_filt, 'Principal', 'Agressividade', 'Encerramento')
        
        id_col = next((c for c in df_tec_filt.columns if 'ID' in c.upper() or 'VINCULO' in c.upper()), None)
        lixo = ['none', 'nan', 'n/d', '', 'null', '[]']
        
        if 'col_t' in locals() and col_t:
            df_tec_limpo = df_tec_filt[~df_tec_filt[col_t].astype(str).str.strip().str.lower().isin(lixo)].copy()
        else:
            df_tec_limpo = df_tec_filt.copy()

        total_apas_reais = df_tec_limpo[id_col].astype(str).nunique() if id_col else 0

        df_sp = df_quali_filt.copy()
        c_sp1, c_sp2 = st.columns(2)
        
        with c_sp1:
            st.markdown("<div class='info-card'><strong>Teste de Spearman: Tempo vs. Desescalada</strong><br><span style='font-size: 0.85rem; color: #aaa;'>O que mede: Verifica se ocorrências mais longas resultam matematicamente em uma maior queda de agressividade do causador.</span>", unsafe_allow_html=True)
            
            if len(df_sp) < 5:
                st.warning(f"⚠️ **Aguardando dados (N={len(df_sp)}):** São necessárias mais ocorrências encerradas para calcular a correlação de tempo de forma confiável.")
            elif col_agr_c and col_agr_e and 'Tempo de Negociação Real' in df_sp.columns:
                df_sp['Agr_Inicio'] = df_sp[col_agr_c].apply(converter_escala)
                df_sp['Agr_Fim'] = df_sp[col_agr_e].apply(converter_escala)
                df_sp['Delta_Agressividade'] = df_sp['Agr_Inicio'] - df_sp['Agr_Fim']
                
                def tempo_para_minutos(val):
                    try:
                        if isinstance(val, list): val = val[0]
                        if pd.isna(val) or val == "N/D" or val == "": return 0
                        return int(float(val)) / 60
                    except: return 0
                
                df_sp['Tempo_Minutos'] = df_sp['Tempo de Negociação Real'].apply(tempo_para_minutos)
                res_sp = analise.calcular_spearman(df_sp, 'Tempo_Minutos', 'Delta_Agressividade')
                
                if res_sp.get('valido', False):
                    st.write(f"Coeficiente Rho: `{res_sp['rho']:.2f}`")
                    st.write(f"P-Value: `{res_sp['p_value']:.4f}`")
                    interprete = "Significativa" if res_sp['p_value'] < 0.05 else "Não Significativa"
                    st.info(f"A correlação é estatisticamente **{interprete}**.")
                else:
                    st.warning(res_sp.get('msg', 'Dados insuficientes para cálculo estatístico (N < 3).'))
            else: 
                st.warning("Colunas de Agressividade ou Tempo ausentes.")
            st.markdown("</div>", unsafe_allow_html=True)

        with c_sp2:
            st.markdown("<div class='info-card'><strong>Teste Qui-Quadrado Dinâmico</strong><br><span style='font-size: 0.85rem; color: #aaa;'>Analisa a dependência entre duas variáveis com o objetivo de identificar padrões de associação entre elas.</span>", unsafe_allow_html=True)
            
            opcoes_variaveis = {
                "Tipologia": "Tip_Limpa",
                "Negociador": "Neg_Limpo",
                "Modalidade": "Modalidade", 
                "Atitude do Causador": "Resposta_Cat" 
            }
            
            var_analise = st.selectbox("Selecione a Variável 1:", list(opcoes_variaveis.keys()), index=0)
            col_v1 = opcoes_variaveis[var_analise]
            
            col_v2 = col_t 

            if total_apas_reais < 10:
                st.warning(f"⚠️ **Análise em Maturação (N={total_apas_reais}):** O cruzamento de padrões exige no mínimo 10 APAs distintas para evitar que o talento (ou erro) de um único caso seja lido como regra.")
            else:
                df_qui_clean = df_tec_filt.dropna(subset=[col_v1, col_v2]).copy()
                
                if not df_qui_clean.empty:
                    res_chi = analise.calcular_qui_quadrado(df_qui_clean, col_v1, col_v2)
                    
                    if res_chi.get('valido', False):
                        st.write(f"Estatística Qui-Quadrado: `{res_chi['chi2']:.2f}`")
                        st.write(f"P-Valor: `{res_chi['p_value']:.4f}`")
                        
                        if res_chi['p_value'] < 0.05:
                            st.success(f"✅ **Existe Padrão:** O uso de técnicas **depende** do(a) {var_analise}. Isso indica uma atuação padronizada/doutrinária.")
                        else:
                            st.info(f"ℹ️ **Sem Padrão:** O uso de técnicas é independente do(a) {var_analise}. A aplicação parece ser situacional ou improvisada.")
                    else:
                        st.warning("Variância insuficiente para este cruzamento específico.")
                else:
                    st.warning("Sem dados suficientes após filtragem.")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("<h4 style='color: #FFD700;'>📐 Modelagem Avançada: Viés do Negociador e Eficácia das Técnicas empregadas</h4>", unsafe_allow_html=True)
        st.markdown("""
        <p style='color: #bbb; font-size: 1rem; line-height: 1.6; margin-bottom: 20px;'>
            Este módulo amplia a análise estatística ao empregar modelos inferenciais avançados, como Regressão Ordinal e Equações de Estimação Generalizadas (GEE), com o objetivo de avaliar a eficácia das técnicas aplicadas em diferentes contextos operacionais. A abordagem busca controlar variáveis de confusão — como diferenças individuais entre negociadores e características específicas dos cenários — permitindo uma análise mais precisa das associações observadas. O propósito é identificar padrões consistentes nos dados e subsidiar a construção de <strong>protocolos táticos orientados por evidências</strong>, reduzindo a influência de vieses e fortalecendo a avaliação da doutrina da Equipe de Negociação.
        </p>
        """, unsafe_allow_html=True)
        
        if total_apas_reais < 15:
            st.info(f"""
            💡 **Por que estas estatísticas estão ocultas? (Modo de Segurança)**
            
            Modelos matemáticos avançados (Regressão e GEE) exigem um volume histórico de ocorrências distintas para não gerarem resultados distorcidos. Atualmente, o sistema detectou dados de apenas **{total_apas_reais} ocorrências**.
            
            * **Meta para desbloqueio:** 15 ocorrências únicas.
            """)
        else:
            col_resposta = next((col for col in df_tec_filt.columns if 'ATITUDE' in col.upper()), None)
            
            if not col_resposta:
                st.warning("⚠️ **Ativação Necessária:** Crie a coluna 'Resposta da Técnica' no Airtable.")
            else:
                try: 
                    import statsmodels.api as sm
                    import statsmodels.formula.api as smf
                    from statsmodels.miscmodels.ordinal_model import OrderedModel
                    from scipy.stats import chi2_contingency
                    import numpy as np

                    df_adv = df_tec_limpo.copy()
                    mapa_resp = {'-1': 'Negativa', '-1.0': 'Negativa', -1: 'Negativa', '🔴 reação negativa': 'Negativa',
                                 '0': 'Neutra', '0.0': 'Neutra', 0: 'Neutra', '⚪ reação neutra': 'Neutra',
                                 '1': 'Positiva', '1.0': 'Positiva', 1: 'Positiva', '🟢 reação positiva': 'Positiva'}
                    
                    df_adv['Resposta_Cat'] = df_adv[col_resposta].astype(str).str.lower().str.strip().map(mapa_resp).fillna('Nao_Observado')
                    df_adv_clean = df_adv[df_adv['Resposta_Cat'] != 'Nao_Observado'].copy()
                    df_adv_clean = df_adv_clean.dropna(subset=['TÉCNICAS'])
                    df_adv_clean['Resposta_Ord'] = pd.Categorical(df_adv_clean['Resposta_Cat'], categories=['Negativa', 'Neutra', 'Positiva'], ordered=True)
                    
                    st.markdown("<div class='info-card'>", unsafe_allow_html=True)
                    st.markdown("##### 1. Teste de Viés por Negociador (Qui-Quadrado de Resíduos)")
                    st.markdown("<span style='font-size: 0.85rem; color: #aaa;'><strong>O que significa:</strong> Verifica se os relatos de 'sucesso' estão concentrados em apenas alguns negociadores ou se são homogêneos.</span>", unsafe_allow_html=True)
                    
                    tab_vies = pd.crosstab(df_adv_clean['Neg_Limpo'], df_adv_clean['Resposta_Cat'])
                    if tab_vies.shape[0] > 1 and tab_vies.shape[1] > 1:
                        chi2, p, dof, exp = chi2_contingency(tab_vies)
                        residuos = (tab_vies - exp) / np.sqrt(exp)
                        st.write(f"**P-Valor global:** `{p:.4e}`")
                        fig_heat = px.imshow(residuos, text_auto=".2f", color_continuous_scale="RdBu", title="Mapa de Calor do Viés")
                        fig_heat.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#FFF")
                        st.plotly_chart(fig_heat, use_container_width=True)
                    else:
                        st.write("Dados insuficientes para comparar múltiplos negociadores.")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.markdown("<div class='info-card'>", unsafe_allow_html=True)
                    st.markdown("##### 2. Eficácia Isolada da Técnica (Regressão Ordinal)")
                    st.markdown("<span style='font-size: 0.85rem; color: #aaa;'><strong>O que significa:</strong> Isola o peso da técnica, removendo a influência do negociador e da tipologia da crise.</span>", unsafe_allow_html=True)
                    
                    if 'col_t' in locals() and col_t:
                        df_adv_clean['Tecnica_Patsy'] = df_adv_clean[col_t].astype(str).str.replace(' ', '_').str.replace('-', '_')
                        df_adv_clean['Neg_Patsy'] = df_adv_clean['Neg_Limpo'].astype(str).str.replace(' ', '_')
                        df_adv_clean['Tip_Patsy'] = df_adv_clean['Tip_Limpa'].astype(str).str.replace(' ', '_')

                        try:
                            mod_ord = OrderedModel.from_formula("Resposta_Ord ~ C(Tecnica_Patsy) + C(Neg_Patsy) + C(Tip_Patsy)", data=df_adv_clean, distr='logit')
                            res_ord = mod_ord.fit(method='bfgs', disp=False)
                            coefs = res_ord.params[res_ord.params.index.str.contains('Tecnica')]
                            pvals = res_ord.pvalues[res_ord.params.index.str.contains('Tecnica')]
                            df_or = pd.DataFrame({'Técnica': coefs.index.str.extract(r'\[T\.(.*?)\]')[0], 'Odds_Ratio': np.exp(coefs), 'P_Valor': pvals})
                            df_or = df_or[df_or['P_Valor'] < 0.05].sort_values('Odds_Ratio', ascending=False)
                            
                            if not df_or.empty:
                                st.dataframe(df_or.style.format({'Odds_Ratio': '{:.2f}', 'P_Valor': '{:.4f}'}), use_container_width=True, hide_index=True)
                                st.success("💡 Um Odds Ratio de 2.0 indica que a técnica dobra a chance de uma resposta positiva.")
                            else:
                                st.info("ℹ️ Nenhuma técnica isolada apresentou significância estatística neste cenário.")
                        except:
                            st.warning("O modelo Ordinal não convergiu para este subconjunto.")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.markdown("<div class='info-card'>", unsafe_allow_html=True)
                    st.markdown("##### 3. Robustez Hierárquica (Equações de Estimação Generalizadas - GEE)")
                    st.markdown("<span style='font-size: 0.85rem; color: #aaa;'><strong>O que significa:</strong> Valida se a técnica é eficaz para a Tropa inteira ou apenas resultado do talento individual.</span>", unsafe_allow_html=True)
                    
                    df_gee_real = df_adv_clean.copy()
                    df_gee_real['Sucesso'] = np.where(df_gee_real['Resposta_Cat'] == 'Positiva', 1, 0)
                    try:
                        if 'Tecnica_Patsy' in df_gee_real.columns:
                            modelo_gee = smf.gee("Sucesso ~ C(Tecnica_Patsy)", groups=df_gee_real['Neg_Patsy'], data=df_gee_real, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable())
                            res_gee = modelo_gee.fit()
                            gee_coefs = res_gee.params[res_gee.params.index.str.contains('Tecnica')]
                            gee_pvals = res_gee.pvalues[res_gee.params.index.str.contains('Tecnica')]
                            df_gee = pd.DataFrame({'Técnica': gee_coefs.index.str.extract(r'\[T\.(.*?)\]')[0], 'Coeficiente_GEE': gee_coefs, 'P_Valor': gee_pvals})
                            
                            if not df_gee.empty:
                                st.dataframe(df_gee.style.format({'Coeficiente_GEE': '{:.2f}', 'P_Valor': '{:.4f}'}), use_container_width=True, hide_index=True)
                                if (gee_pvals < 0.05).any(): st.success("✅ **Doutrina Validada:** Técnica sobreviveu ao controle de viés.")
                                else: st.info("ℹ️ Nenhuma técnica atingiu significância.")
                    except:
                        st.error("Erro no processamento GEE.")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                except ImportError:
                    st.error("🚨 Biblioteca statsmodels não instalada.")
                except Exception as e:
                    st.error(f"🚨 Erro geral: {str(e)}")

        st.markdown("---")
        st.markdown("<h4 style='color: #FFD700;'>📈 Volume e Tendência Temporal</h4>", unsafe_allow_html=True)
        
        col_data = next((col for col in ['Data da ocorrência', 'Data', 'DATA'] if col in df_quali_filt.columns), None)
        if col_data:
            df_quali_filt['Data_DT'] = pd.to_datetime(df_quali_filt[col_data], errors='coerce')
            df_time = df_quali_filt.dropna(subset=['Data_DT']).sort_values('Data_DT')
            if not df_time.empty:
                df_time['Mes_Ano'] = df_time['Data_DT'].dt.to_period('M').astype(str)
                df_trend = df_time['Mes_Ano'].value_counts().sort_index().reset_index()
                df_trend.columns = ['Mês', 'Qtd Ocorrências']
                fig_time = px.line(df_trend, x='Mês', y='Qtd Ocorrências', markers=True, color_discrete_sequence=['#FFD700'])
                fig_time.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#FFF")
                st.plotly_chart(fig_time, use_container_width=True)
            else: st.info("Sem datas válidas.")
        else: st.info("Coluna de Data não encontrada.")

        st.markdown("---")
        st.markdown("<h4 style='color: #06C755;'>🧠 Síntese Interpretativa Avançada (Interpretação descritiva dos resultados estatísticos assistida por modelo de linguagem (LLM – OpenAI GPT-4o-mini), com base em dados previamente processados por métodos estatísticos.)</h4>", unsafe_allow_html=True)
        st.markdown("<p style='color: #bbb;'>Este módulo traduz a matriz matemática gerada acima em um relatório estratégico que visa o aperfeiçoamento técnico contínuo do Negociador.</p>", unsafe_allow_html=True)

        if st.button("🤖 GERAR RELATÓRIO ESTATÍSTICO DESCRITIVO"):
            with st.spinner("Estruturando matrizes e consultando Cientista de Dados IA..."):
                try:
                    import ia_estatistica 
                    
                    qui_data = {'p_valor_global': p} if 'p' in locals() else None
                    
                    ord_data = None
                    if 'df_or' in locals() and not df_or.empty:
                        ord_data = df_or.to_dict('records')
                        
                    gee_data = None
                    if 'df_gee' in locals() and not df_gee.empty:
                        gee_data = df_gee.to_dict('records')

                    payload_ia = ia_estatistica.estruturar_resultado_para_ia(
                        amostra_total=len(df_quali_filt),
                        resultados_chi=qui_data,
                        resultados_ordinal=ord_data,
                        resultados_gee=gee_data
                    )

                    relatorio_json = ia_estatistica.gerar_relatorio_com_ia(payload_ia)

                    if "erro" in relatorio_json:
                        st.error(relatorio_json["erro"])
                        with st.expander("Ver Payload Enviado"):
                            st.json(payload_ia)
                    else:
                        def render_ia_card(titulo, texto, icone="📌"):
                            return f"""
                            <div class="info-card" style="border-left: 3px solid #06C755; padding: 15px; margin-bottom: 15px;">
                                <h5 style="color: #06C755; margin-top: 0; font-size: 1.1rem;">{icone} {titulo}</h5>
                                <p style="font-size: 1.05rem; line-height: 1.6; color: #FFF;">{texto}</p>
                            </div>
                            """

                        c_ia1, c_ia2 = st.columns(2)
                        with c_ia1:
                            st.markdown(render_ia_card("Objetivo Analítico", relatorio_json.get("objetivo", "N/D"), "🎯"), unsafe_allow_html=True)
                            st.markdown(render_ia_card("Premissas e Limitações da Análise", relatorio_json.get("premissas", "N/D") + "<br><br><strong>Limitações Técnicas:</strong> " + relatorio_json.get("limitacoes", "N/D"), "⚖️"), unsafe_allow_html=True)
                        with c_ia2:
                            st.markdown(render_ia_card("Resultados Principais", relatorio_json.get("resultados_principais", "N/D"), "📊"), unsafe_allow_html=True)
                            st.markdown(render_ia_card("Tamanho do Efeito", relatorio_json.get("tamanho_efeito", "N/D"), "📈"), unsafe_allow_html=True)

                        st.markdown(render_ia_card("Implicações Analíticas para a Tomada de Decisão", relatorio_json.get("interpretacao", "N/D"), "🧠"), unsafe_allow_html=True)
                        st.markdown(render_ia_card("Direcionamento Estratégico Baseado em Evidências", relatorio_json.get("conclusao", "N/D"), "🏆"), unsafe_allow_html=True)

                        with st.expander("🕵️ Ver Matriz Bruta de Dados (JSON Payload e Retorno)"):
                            st.markdown("**Payload enviado para a IA (O que o Python calculou):**")
                            st.json(payload_ia)
                            st.markdown("**JSON Retornado pela IA:**")
                            st.json(relatorio_json)

                        st.markdown("---")
                        st.markdown("### 🖨️ Exportar Relatório")
                        
                        try:
                            pdf_hist = FPDF()
                            pdf_hist.add_page()
                            
                            pdf_hist.set_fill_color(249, 115, 22)
                            pdf_hist.rect(0, 0, 210, 40, 'F')
                            pdf_hist.set_font("Arial", "B", 16)
                            pdf_hist.set_text_color(255, 255, 255)
                            pdf_hist.cell(0, 15, "RELATORIO DA ANÁLISE - SÉRIE HISTÓRICA", ln=True, align="C")
                            pdf_hist.set_font("Arial", "I", 12)
                            pdf_hist.cell(0, 5, "GATE - Inteligencia de Apoio ao Processo Decisório", ln=True, align="C")
                            
                            pdf_hist.ln(20)
                            pdf_hist.set_text_color(0, 0, 0)
                            pdf_hist.set_font("Arial", "B", 14)
                            pdf_hist.set_fill_color(240, 240, 240)
                            pdf_hist.cell(0, 10, " 1. SINTESE DAS TECNICAS APLICADAS", ln=True, fill=True)
                            pdf_hist.ln(5)
                            
                            pdf_hist.set_font("Arial", "", 12)
                            
                            partes_hist = [f"{k.upper()}:\n{v}" for k, v in relatorio_json.items() if isinstance(v, str)]
                            texto_hist_str = "\n\n".join(partes_hist).replace("**", "").replace("### ", "")
                            texto_pdf_limpo_hist = unicodedata.normalize('NFKD', texto_hist_str).encode('ASCII', 'ignore').decode('ASCII')
                            
                            pdf_hist.multi_cell(0, 8, txt=texto_pdf_limpo_hist)
                            
                            pdf_saida_hist = pdf_hist.output(dest="S")
                            if isinstance(pdf_saida_hist, str):
                                pdf_bytes_hist = pdf_saida_hist.encode('latin-1', errors='replace')
                            else:
                                pdf_bytes_hist = bytes(pdf_saida_hist)
                                
                            st.download_button(
                                label="📥 BAIXAR RELATÓRIO (PDF)", 
                                data=pdf_bytes_hist, 
                                file_name="Relatorio_de_análise_GATE.pdf", 
                                mime="application/pdf"
                            )
                        except Exception as e:
                            st.error(f"Erro na geração do PDF Série Histórica: {str(e)}")

                except Exception as e:
                    st.error(f"Erro na geração do relatório de IA: {str(e)}")