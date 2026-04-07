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
# 1. CONFIGURAÇÃO DA PÁGINA E CSS (Estilo Positiv+ & GATE)
# =========================================================
st.set_page_config(page_title="GATE - Analisador de APAs", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* Configurações Globais */
    .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; z-index: 10;}
    header {visibility: hidden;}
    .stApp { background-color: #050505; color: #FFFFFF; overflow-x: hidden; }
    
    /* Fontes e Títulos */
    .main-title {
        font-family: 'Inter', stencil-sans; font-size: 2.8rem; font-weight: 800;
        background: linear-gradient(180deg, #FFFFFF 0%, #BBBBBB 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; line-height: 1.1;
    }
    .sub-title { color: #f97316; font-weight: 600; font-size: 1.1rem; margin-top: 5px; margin-bottom: 0; }
    
    /* Efeito Vidro (Glassmorphism) e Animação de Luz (Sweep) nas Caixas */
    .info-card { 
        background: rgba(255, 255, 255, 0.03);
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
        background: rgba(249, 115, 22, 0.05);
        border-color: rgba(249, 115, 22, 0.3);
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(249, 115, 22, 0.15);
    }
    .info-card:hover::before {
        left: 100%; transition: 0.7s ease-in-out;
    }

    /* Efeito Expansivo nos Botões (Magnifying/Scale) */
    div.stButton > button { 
        background: linear-gradient(90deg, #f97316 0%, #fb923c 100%); 
        color: white; border: none; padding: 0.7rem 2rem; border-radius: 10px; font-weight: bold; 
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); width: 100%; position: relative;
    }
    div.stButton > button:hover { 
        box-shadow: 0 0 25px rgba(249, 115, 22, 0.6); 
        transform: scale(1.03) translateY(-2px); 
    }
    
    /* Efeito Ambient Blobs (Degradês Flutuantes no Fundo) */
    .liquid-blob {
        position: fixed; border-radius: 60%; filter: blur(80px); opacity: 0.15; z-index: -1;
        animation: float 10s infinite alternate cubic-bezier(0.4, 0, 0.2, 1); pointer-events: none;
    }
    .blob1 { background-color: #f97316; width: 500px; height: 500px; top: -100px; left: -100px; animation-duration: 15s; }
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
    div[data-testid="stTabs"] button[data-baseweb="tab"]:hover { color: #f97316; }

    /* Cores Táticas para o Efeito de Vidro (Agressividade e Receptividade) */
    .card-red { border-left: 4px solid #ef4444 !important; }
    .card-red:hover { box-shadow: 0 15px 40px rgba(239, 68, 68, 0.25) !important; border-color: rgba(239, 68, 68, 0.6) !important; }
    .card-red::before { background: linear-gradient(90deg, transparent, rgba(239, 68, 68, 0.15), transparent) !important; }

    .card-green { border-left: 4px solid #22c55e !important; }
    .card-green:hover { box-shadow: 0 15px 40px rgba(34, 197, 94, 0.25) !important; border-color: rgba(34, 197, 94, 0.6) !important; }
    .card-green::before { background: linear-gradient(90deg, transparent, rgba(34, 197, 94, 0.15), transparent) !important; }
</style>

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
            cursor.style.backgroundColor = '#f97316';
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
# 2. CABEÇALHO VISUAL
# =========================================================
script_dir = os.path.dirname(os.path.abspath(__file__))
path_assets = os.path.join(script_dir, "Assets")
path_teste_gate = os.path.join(path_assets, "teste-gate.PNG")
path_brasao_gate = os.path.join(path_assets, "BRASÃO GATE.PNG")

try:
    with open(path_teste_gate, "rb") as img_file: img_topo_b64 = base64.b64encode(img_file.read()).decode()
    st.markdown(f"""<div style="position: relative; width: 100%; height: 200px; border-radius: 2px; overflow: hidden; background-image: url('data:image/png;base64,{img_topo_b64}'); background-size: cover; background-position: center 40%; margin-bottom: 1rem;"><div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(180deg, rgba(5,5,5,0.1) 0%, rgba(249, 115, 22, 0.6) 100%);"></div></div>""", unsafe_allow_html=True)
except: pass

col_logo, col_titulo, col_espaco = st.columns([1, 6, 1])
with col_logo:
    try: st.image(Image.open(path_brasao_gate), use_container_width=True)
    except: pass
with col_titulo:
    st.markdown('<h1 class="main-title">Sistema de Análise Qualitativa das Negociações - Estudo das Técnicas aplicadas</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Delta Negociação - GATE / PMESP</p>', unsafe_allow_html=True)
    st.markdown('<p style="color: #888; margin-top: 5px;">Desenvolvido por Cb PM Marcos - Supervisão: Cap PM Pavão</p>', unsafe_allow_html=True)
    st.markdown(f"""
<div class="info-card">
    <p><strong>Sistema automatizado de análise qualitativa das Negociações em Incidentes Críticos atendidos pelo Grupo de Ações Táticas Especiais.</strong></p>
    <p style="font-size: 0.9rem; color: #888;">Os dados são geridos de forma automatizada em nuvem via <strong>Airtable</strong>. Cálculos matemáticos realizados localmente utilizando  
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

        # Filtros Locais (Agora com 3 colunas)
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
            apa_selecionada = st.selectbox("Selecione a ID da APA para análise:", lista_apas, index=len(lista_apas)-1)
            df_apa = df_quali[df_quali['ID_Busca'] == apa_selecionada].iloc[0]
            
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

            # --- BUSCA INTELIGENTE DE COLUNAS (Blinda contra mudanças de nome no Airtable) ---
            def buscar_percepcao(papel, metrica, momento):
                # Tira acentos e minúsculas para caçar a coluna independentemente de como foi digitada
                def norm(t): return unicodedata.normalize('NFKD', str(t)).encode('ASCII', 'ignore').decode('ASCII').lower()
                
                for col in df_apa.index:
                    col_norm = norm(col)
                    if norm(papel) in col_norm and norm(metrica) in col_norm and norm(momento) in col_norm:
                        return limpar_valor(df_apa[col])
                return "N/D"

            # VARIÁVEIS TEXTUAIS GLOBAIS DA APA (Extração Robusta dos 3 Observadores)
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

            # Valores Numéricos (MANTIDOS PARA O GRÁFICO FUNCIONAR)
            p_agr_c_num, p_rec_c_num = converter_escala(p_agr_c_txt), converter_escala(p_rec_c_txt)
            p_agr_e_num, p_rec_e_num = converter_escala(p_agr_e_txt), converter_escala(p_rec_e_txt)
            
            s_agr_c_num, s_rec_c_num = converter_escala(s_agr_c_txt), converter_escala(s_rec_c_txt)
            s_agr_e_num, s_rec_e_num = converter_escala(s_agr_e_txt), converter_escala(s_rec_e_txt)
            
            l_agr_c_num, l_rec_c_num = converter_escala(l_agr_c_txt), converter_escala(l_rec_c_txt)
            l_agr_e_num, l_rec_e_num = converter_escala(l_agr_e_txt), converter_escala(l_rec_e_txt)

            # =========================================================
            # GRÁFICO DE TENDÊNCIA E EVOLUÇÃO (Com Seletor de Perspectiva)
            # =========================================================
            st.markdown("### 📈 Evolução Emocional")
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

            # 2. BLOCO DE PERCEPÇÕES (COM EFEITO DE VIDRO E CORES TÁTICAS)
            st.markdown("### 🧠 Percepções da Equipe (Textual)")
            tab_chegada, tab_encerramento = st.tabs(["➡️ Na Chegada à Ocorrência", "🛑 No Encerramento"])
            
            # Função para desenhar o card de vidro com a cor tática escolhida
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

            # 3. TRANSCRIÇÕES
            st.markdown("### 🗣️ Transcrições Literal")
            with st.expander("Ver transcrições completas da ocorrência", expanded=False):
                st.markdown("**Causador do Incidente:**")
                st.write(limpar_valor(df_apa.get('TRANSCRIÇÃO DO CAUSADOR')))
                st.markdown("**Negociador Principal:**")
                st.write(limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL')))
                st.markdown("**Negociador Secundário:**")
                st.write(limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO')))

            st.markdown("---")

            # 4. TABELA DE FREQUÊNCIA (CRUZAMENTO DEFINITIVO)
            st.markdown("<h4 style='color: #f97316;'>📉 Frequência das Técnicas Aplicadas (Nesta APA)</h4>", unsafe_allow_html=True)
            
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
                            
                            st.markdown("<h5 style='text-align:center; color: #FFFFFF; margin-top: 20px;'>Frequencias de aplicações das Técnicas (Treemap)</h5>", unsafe_allow_html=True)
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

            # ETAPA 2 DA ABA INDIVIDUAL
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
                    st.markdown('<p style="color: #f97316; font-weight: bold; text-align:center;">Causador</p>', unsafe_allow_html=True)
                    if stats['wc_c']: st.pyplot(stats['wc_c'])
                with c_w2:
                    st.markdown('<p style="color: #f97316; font-weight: bold; text-align:center;">Negociador Principal</p>', unsafe_allow_html=True)
                    if stats['wc_np']: st.pyplot(stats['wc_np'])
                with c_w3:
                    st.markdown('<p style="color: #f97316; font-weight: bold; text-align:center;">Negociador Secundário</p>', unsafe_allow_html=True)
                    if stats['wc_ns']: st.pyplot(stats['wc_ns'])

            st.markdown("---")
            
            # =========================================================
            # ETAPA 3: INTELIGÊNCIA ARTIFICIAL E LAUDO TÉCNICO
            # =========================================================
            st.markdown("### 📄 Etapa 3: Inteligência de Apoio à Decisão e Exportação")
            
            # ATENÇÃO: Substitui pela tua URL real do n8n (usando host.docker.internal ou o IP)
            url_n8n = "http://host.docker.internal:5680/webhook/analise-doc"
            
            if st.button("📡 3. GERAR ANALYTICS E EXPORTAR ANÁLISE (PDF)"):
                with st.spinner("Compilando dados táticos, consultando IA e desenhando PDF..."):
                    try:
                        # 1. Captura direta para evitar campos "Não informados"
                        t_causador = limpar_valor(df_apa.get('TRANSCRIÇÃO DO CAUSADOR'))
                        t_principal = limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL'))
                        t_secundario = limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO'))

                        df_transcricoes = pd.DataFrame([{
                            "Causador": t_causador,
                            "Neg_Principal": t_principal,
                            "Neg_Secundario": t_secundario
                        }])

                        # 2. Recupera tópicos da Etapa 2
                        temas_extraidos = st.session_state['stats_calculados']['topicos'] if st.session_state.get('stats_calculados') else ["Etapa 2 não executada"]

                        # 3. Prepara Metadados para a IA "ler" os gráficos
                        meta_dict = df_apa.to_dict()
                        meta_dict["temas_dominantes_scikit_learn"] = " | ".join(temas_extraidos)
                        df_meta = pd.DataFrame([meta_dict])
                                                
                        dados_extraidos = {
                            "transcricao": df_transcricoes,
                            "metadados": df_meta
                        }

                        # 4. Envio para IA python
                        resultado_ia = ia_link.analisar_ocorrencia_gate(dados_extraidos)
                        
                        # Processamento do Parecer (Modo RAIO-X incluído)
                        if isinstance(resultado_ia, dict) and 'parecer' in resultado_ia:
                            parecer_ia = resultado_ia['parecer']
                        else:
                            parecer_ia = f"Sinal recebido, mas os dados estão incompletos ou a URL precisa de ajuste. Bruto: {resultado_ia}"

                        # 5. Laudo Frio (Estatístico) - Utilizando a Média Válida da Equipe!
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

                        # Exibição na Tela (Glassmorphism)
                        st.markdown(f"""
                        <div class="info-card" style="border-left: 4px solid #f97316;">
                            <h4 style="color: #f97316; margin-top: 0;">Inferência Estatística (Motor Frio)</h4>
                            <p style="font-size: 1.05rem; line-height: 1.6;">{laudo_frio}</p>
                            <hr style="border-color: rgba(255,255,255,0.1); margin: 15px 0;">
                            <h4 style="color: #06C755; margin-top: 0;">Leitura Analítica (IA)</h4>
                            <p style="font-size: 1.05rem; line-height: 1.6;">{parecer_ia}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        # 6. Geração de PDF Blindada
                        def limpar_texto_pdf(texto):
                            return unicodedata.normalize('NFKD', str(texto)).encode('ASCII', 'ignore').decode('ASCII')

                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_font("Arial", "B", 16)
                        pdf.cell(0, 10, "LAUDO DE ANALISE POS-ACAO (APA)", ln=True, align="C")
                        pdf.set_font("Arial", "B", 12)
                        pdf.cell(0, 10, "Delta Negociacao - GATE / PMESP", ln=True, align="C")
                        pdf.ln(10)
                        
                        pdf.set_font("Arial", "", 12)
                        pdf.cell(0, 8, f"ID da APA: {apa_selecionada}", ln=True)
                        pdf.cell(0, 8, limpar_texto_pdf(f"Tipologia: {limpar_valor(df_apa.get('Tipologia'))}"), ln=True)
                        pdf.ln(5)

                        pdf.set_font("Arial", "B", 14)
                        pdf.cell(0, 10, "1. Leitura Analitica", ln=True)
                        pdf.set_font("Arial", "", 12)
                        pdf.multi_cell(0, 8, txt=limpar_texto_pdf(parecer_ia))
                        
                        pdf_bytes = pdf.output(dest="S")
                        st.download_button(label="📥 BAIXAR ANÁLISE COMPLETA (PDF)", data=pdf_bytes, file_name=f"Laudo_GATE_{apa_selecionada}.pdf", mime="application/pdf")

                    except Exception as e:
                        st.error(f"Erro no processamento: {e}")

    # =========================================================
    # ABA 2: PAINEL ESTRATÉGICO (HISTÓRICO)
    # =========================================================
    with aba_geral:
        st.markdown("### 🧠 Série Histórica - Negociações GATE")
        st.markdown("<h5 style='color: #f97316;'>Filtros de Cenário</h5>", unsafe_allow_html=True)
        
        # Filtros Globais (Com 3 colunas e chaves blindadas contra duplicação)
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
        with col_m2: st.metric("Tempo Total Real", somar_tempos_segundos(df_quali_filt.get('Tempo de Negociação Real', [])))
        with col_m3: st.metric("Tempo Total Tático", somar_tempos_segundos(df_quali_filt.get('Tempo de Negociação Tática', [])))

        st.markdown("---")
        st.markdown("#### Ranking de Técnicas (Filtrado)")
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
            
        # =========================================================
        # MOTOR ESTATÍSTICO BÁSICO (SPEARMAN & QUI-QUADRADO)
        # =========================================================
        st.markdown("---")
        st.markdown("<h4 style='color: #f97316;'>🔬 Análise Inferencial Básica</h4>", unsafe_allow_html=True)
        
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
        
        df_sp = df_quali_filt.copy()
        c_sp1, c_sp2 = st.columns(2)
        
        with c_sp1:
            st.markdown("<div class='info-card'><strong>Teste de Spearman: Tempo vs. Desescalada</strong>", unsafe_allow_html=True)
            if col_agr_c and col_agr_e and 'Tempo de Negociação Real' in df_sp.columns:
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
            else: st.warning("Colunas insuficientes para Spearman.")
            st.markdown("</div>", unsafe_allow_html=True)

        with c_sp2:
            st.markdown("<div class='info-card'><strong>Teste Qui-Quadrado: Tipologia vs. Técnicas</strong>", unsafe_allow_html=True)
            if not df_tec.empty and not df_tec_filt.empty and 'col_t' in locals() and col_t:
                if 'Tip_Limpa' in df_tec_filt.columns:
                    res_chi = analise.calcular_qui_quadrado(df_tec_filt, 'Tip_Limpa', col_t)
                    if res_chi.get('valido', False):
                        st.write(f"Qui-Quadrado: `{res_chi['chi2']:.2f}`")
                        st.write(f"P-Value: `{res_chi['p_value']:.4f}`")
                        dependencia = "Existe dependência doutrinária" if res_chi['p_value'] < 0.05 else "Distribuição aleatória"
                        st.success(f"Resultado: **{dependencia}**.")
                    else: st.warning(res_chi.get('msg', 'Variância insuficiente.'))
            else: st.warning("Sem dados de técnicas carregados.")
            st.markdown("</div>", unsafe_allow_html=True)

        # =========================================================
        # MOTOR ESTATÍSTICO AVANÇADO (VIÉS, REGRESSÃO ORDINAL E GEE)
        # =========================================================
        st.markdown("---")
        st.markdown("<h4 style='color: #f97316;'>📐 Modelagem Avançada: Viés e Eficácia Real das Técnicas</h4>", unsafe_allow_html=True)
        
        # Caça a coluna independentemente se for a de números ou a de texto com emojis
        col_resposta = next((col for col in df_tec_filt.columns if 'ATITUDE' in col.upper()), None)
        
        if not col_resposta:
            st.warning("⚠️ **Ativação Necessária:** Para desbloquear os motores de Regressão e GEE, crie uma coluna chamada **'Resposta da Técnica'** na aba de Técnicas no seu Airtable, contendo os valores: `-1` (Negativa), `0` (Neutra), `1` (Positiva) ou `N/D`.")
        else:
            try:
                import statsmodels.api as sm
                import statsmodels.formula.api as smf
                from statsmodels.miscmodels.ordinal_model import OrderedModel
                from scipy.stats import chi2_contingency
                import numpy as np

                # 1. Preparação dos Dados
                df_adv = df_tec_filt.copy()
                mapa_resp = {'-1': 'Negativa', '-1.0': 'Negativa', -1: 'Negativa', '🔴 reação negativa': 'Negativa',
                             '0': 'Neutra', '0.0': 'Neutra', 0: 'Neutra', '⚪ reação neutra': 'Neutra',
                             '1': 'Positiva', '1.0': 'Positiva', 1: 'Positiva', '🟢 reação positiva': 'Positiva'}
                
                # Aplica a limpeza transformando tudo em minúsculo na hora de ler para não dar erro de maiúscula
                df_adv['Resposta_Cat'] = df_adv[col_resposta].astype(str).str.lower().str.strip().map(mapa_resp).fillna('Nao_Observado')
                df_adv_clean = df_adv[df_adv['Resposta_Cat'] != 'Nao_Observado'].copy()
                
                df_adv_clean['Resposta_Ord'] = pd.Categorical(df_adv_clean['Resposta_Cat'], categories=['Negativa', 'Neutra', 'Positiva'], ordered=True)
                
                st.markdown("<div class='info-card'>", unsafe_allow_html=True)
                st.markdown("##### 1. Teste de Viés por Negociador (Qui-Quadrado de Resíduos)")
                st.write("Verifica se há padrão sistemático de autovalidação nas equipes.")
                
                # Tabela de Contingência e Resíduos
                tab_vies = pd.crosstab(df_adv_clean['Neg_Limpo'], df_adv_clean['Resposta_Cat'])
                if tab_vies.shape[0] > 1 and tab_vies.shape[1] > 1:
                    chi2, p, dof, exp = chi2_contingency(tab_vies)
                    residuos = (tab_vies - exp) / np.sqrt(exp)
                    
                    st.write(f"**P-Valor global:** `{p:.4e}` *(Se < 0.05, a percepção de sucesso depende de quem é o negociador)*")
                    
                    # Gráfico de Heatmap de Resíduos
                    fig_heat = px.imshow(residuos, text_auto=".2f", color_continuous_scale="RdBu",
                                         title="Mapa de Calor do Viés (Resíduos Padronizados)",
                                         labels=dict(color="Resíduo"))
                    fig_heat.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#FFF")
                    st.plotly_chart(fig_heat, use_container_width=True)
                    
                    st.info("💡 **Como interpretar:** Valores > **+1.96** (Azul escuro) indicam que o negociador relata essa categoria muito *acima* do normal. Valores < **-1.96** (Vermelho escuro) indicam relato muito *abaixo* do padrão. Isso evidencia viés.")
                else:
                    st.write("Dados insuficientes para calcular viés entre múltiplos negociadores.")
                st.markdown("</div>", unsafe_allow_html=True)
                
                # 2. Regressão Logística Ordinal
                st.markdown("<div class='info-card'>", unsafe_allow_html=True)
                st.markdown("##### 2. Eficácia Isolada da Técnica (Regressão Ordinal)")
                st.write("Avalia o peso da técnica expurgando os efeitos do negociador e tipologia.")
                
                # Renomeia colunas para o Patsy não quebrar
                if 'col_t' in locals() and col_t:
                    df_adv_clean['Tecnica_Patsy'] = df_adv_clean[col_t].str.replace(' ', '_').str.replace('-', '_')
                    df_adv_clean['Neg_Patsy'] = df_adv_clean['Neg_Limpo'].str.replace(' ', '_')
                    df_adv_clean['Tip_Patsy'] = df_adv_clean['Tip_Limpa'].str.replace(' ', '_')

                    try:
                        mod_ord = OrderedModel.from_formula("Resposta_Ord ~ C(Tecnica_Patsy) + C(Neg_Patsy) + C(Tip_Patsy)", data=df_adv_clean, distr='logit')
                        res_ord = mod_ord.fit(method='bfgs', disp=False)
                        
                        # Filtra apenas os coeficientes das técnicas
                        coefs = res_ord.params[res_ord.params.index.str.contains('Tecnica')]
                        pvals = res_ord.pvalues[res_ord.params.index.str.contains('Tecnica')]
                        
                        # Cria DataFrame de Odds Ratios
                        df_or = pd.DataFrame({'Técnica': coefs.index.str.extract(r'\[T\.(.*?)\]')[0], 'Odds_Ratio': np.exp(coefs), 'P_Valor': pvals})
                        df_or = df_or[df_or['P_Valor'] < 0.05].sort_values('Odds_Ratio', ascending=False)
                        
                        if not df_or.empty:
                            st.dataframe(df_or.style.format({'Odds_Ratio': '{:.2f}', 'P_Valor': '{:.4f}'}), use_container_width=True, hide_index=True)
                            
                            # TRAVA DE SEGURANÇA N < 10
                            if len(df_adv_clean) < 10:
                                st.warning(f"⚠️ **Amostra Reduzida (N={len(df_adv_clean)}):** Os Odds Ratios acima são instáveis. Com amostras pequenas, o modelo tende a superestimar o impacto (separação perfeita). Não use para validar doutrina ainda.")
                            else:
                                st.success("💡 **Como interpretar:** Um Odds Ratio (OR) de `2.0` significa que aplicar esta técnica *dobra* a chance de subir um nível na resposta do causador, controlando pelo viés do negociador.")
                        else:
                            st.write("Nenhuma técnica isolada apresentou significância estatística (P < 0.05).")
                    except Exception as e:
                        st.warning(f"O modelo Ordinal não convergiu. Geralmente ocorre por separação perfeita (técnicas com pouquíssimas amostras). Detalhe: {str(e)[:100]}")
                st.markdown("</div>", unsafe_allow_html=True)
                
                # 3. Modelo Multinível (GEE)
                st.markdown("<div class='info-card'>", unsafe_allow_html=True)
                st.markdown("##### 3. Robustez Hierárquica (Equações de Estimação Generalizadas - GEE)")
                st.write("Controla matematicamente o efeito de 'cluster' (várias técnicas aplicadas pelo mesmo negociador).")
                
                try:
                    # O modelo agora usa as colunas limpas
                    modelo_gee = smf.gee("Sucesso ~ C(Tecnica_Patsy)",
                        groups=df_adv_clean['Neg_Patsy'],
                        data=df_adv_clean,
                        family=sm.families.Binomial(),
                        cov_struct=sm.cov_struct.Exchangeable())
                    res_gee = modelo_gee.fit()
                        
                        # Extração de Coeficientes
                    gee_coefs = res_gee.params[res_gee.params.index.str.contains('Tecnica_Patsy')]
                    gee_pvals = res_gee.pvalues[res_gee.params.index.str.contains('Tecnica_Patsy')]
                    gee_coefs = res_gee.params[res_gee.params.index.str.contains('Tecnica')]

                        # Monta o DataFrame de resultados
                    df_gee = pd.DataFrame({
                            'Técnica': gee_coefs.index.str.extract(r'\[T\.(.*?)\]')[0],
                            'Coeficiente_GEE': gee_coefs,
                            'P_Valor': gee_pvals
                            })
                    
                        # Filtra apenas as significativas para o destaque, mas você pode mostrar todas
                    df_gee_sig = df_gee[df_gee['P_Valor'] < 0.05].sort_values('Coeficiente_GEE', ascending=False)
                    if not df_gee.empty:
                        st.dataframe(df_gee.style.format({'Coeficiente_GEE': '{:.2f}', 'P_Valor': '{:.4f}'}), 
                     use_container_width=True, hide_index=True)
                        
                        # --- A TRAVA DE SEGURANÇA CONTRA MAL-ENTENDIDOS ---
                        if len(df_adv_clean) < 10:
                            st.warning(f"⚠️ **Amostra Crítica (N={len(df_adv_clean)}):** Os coeficientes de 35.53 indicam 'separação perfeita'. A matemática 'viciou' porque há poucos casos. Não utilize esses dados para validar doutrina até atingir N > 30.")
                        else:
                            st.success("💡 **Prova Científica:** As técnicas acima demonstraram eficácia real, controlando o estilo individual dos negociadores.")
                    else:
                        st.write("Nenhuma técnica apresentou P < 0.05 após o controle hierárquico.")

                except Exception as e:
                    st.error(f"Erro no GEE: Amostra insuficiente ou sem variabilidade entre negociadores. Detalhe: {str(e)[:50]}")

                    st.markdown("</div>", unsafe_allow_html=True)

                except ImportError:
                    st.error("A biblioteca **statsmodels** não está instalada no servidor. Rode `pip install statsmodels` para ativar a modelagem preditiva.")

        # --- TENDÊNCIA TEMPORAL ---
        st.markdown("---")
        st.markdown("<h4 style='color: #f97316;'>📈 Volume e Tendência Temporal</h4>", unsafe_allow_html=True)
        
        col_data = next((col for col in ['Data da ocorrência', 'Data', 'DATA'] if col in df_quali_filt.columns), None)
        if col_data:
            df_quali_filt['Data_DT'] = pd.to_datetime(df_quali_filt[col_data], errors='coerce')
            df_time = df_quali_filt.dropna(subset=['Data_DT']).sort_values('Data_DT')
            
            if not df_time.empty:
                df_time['Mes_Ano'] = df_time['Data_DT'].dt.to_period('M').astype(str)
                df_trend = df_time['Mes_Ano'].value_counts().sort_index().reset_index()
                df_trend.columns = ['Mês', 'Qtd Ocorrências']
                
                fig_time = px.line(df_trend, x='Mês', y='Qtd Ocorrências', markers=True, line_shape='spline', color_discrete_sequence=['#f97316'])
                fig_time.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#FFF")
                st.plotly_chart(fig_time, use_container_width=True)
            else: st.info("Não há datas válidas suficientes no Airtable para desenhar o gráfico.")
        else: st.info("Coluna de Data não encontrada para a tendência.")
        # =========================================================
        # MÓDULO NOVO: RELATÓRIO INTERPRETATIVO COM IA
        # =========================================================
        st.markdown("---")
        st.markdown("<h4 style='color: #06C755;'>🧠 Síntese Interpretativa Avançada (Elaborado por Inteligência Artificial - modelo OpenAi 4o-mini)</h4>", unsafe_allow_html=True)
        st.markdown("<p style='color: #bbb;'>Este módulo traduz a matriz matemática gerada acima em um relatório estratégico doutrinário.</p>", unsafe_allow_html=True)

        if st.button("🤖 GERAR RELATÓRIO ESTATÍSTICO DESCRITIVO"):
            with st.spinner("Estruturando matrizes e consultando Cientista de Dados IA..."):
                try:
                    import ia_estatistica # Assegure-se de que as novas funções estão neste arquivo
                    
                    # 1. Coleta Segura das Variáveis do Motor Frio (evita NameError se a conta falhou acima)
                    # Verifica se as variáveis de resultado foram criadas na execução do bloco anterior
                    qui_data = {'p_valor_global': p} if 'p' in locals() else None
                    
                    ord_data = None
                    if 'df_or' in locals() and not df_or.empty:
                        ord_data = df_or.to_dict('records')
                        
                    gee_data = None
                    if 'df_gee' in locals() and not df_gee.empty:
                        gee_data = df_gee.to_dict('records')

                    # 2. Empacota os dados 
                    payload_ia = ia_estatistica.estruturar_resultado_para_ia(
                        amostra_total=len(df_quali_filt),
                        resultados_chi=qui_data,
                        resultados_ordinal=ord_data,
                        resultados_gee=gee_data
                    )

                    # 3. Executa a Invocação
                    # NOTA: Configure a API KEY dentro do ia_link.py
                    relatorio_json = ia_estatistica.gerar_relatorio_com_ia(payload_ia)

                    # 4. Tratamento de Fallback
                    if "erro" in relatorio_json:
                        st.error(relatorio_json["erro"])
                        with st.expander("Ver Payload Enviado"):
                            st.json(payload_ia)
                    else:
                        # 5. Formatação Visual usando seu padrão Glassmorphism
                        def render_ia_card(titulo, texto, icone="📌"):
                            return f"""
                            <div class="info-card" style="border-left: 3px solid #06C755; padding: 15px; margin-bottom: 15px;">
                                <h5 style="color: #06C755; margin-top: 0; font-size: 1.1rem;">{icone} {titulo}</h5>
                                <p style="font-size: 1.05rem; line-height: 1.6; color: #EEE;">{texto}</p>
                            </div>
                            """

                        # Layout em colunas
                        c_ia1, c_ia2 = st.columns(2)
                        with c_ia1:
                            st.markdown(render_ia_card("Objetivo Analítico", relatorio_json.get("objetivo", "N/D"), "🎯"), unsafe_allow_html=True)
                            st.markdown(render_ia_card("Premissas e Limitações", relatorio_json.get("premissas", "N/D") + "<br><br><strong>Limitações Técnicas:</strong> " + relatorio_json.get("limitacoes", "N/D"), "⚖️"), unsafe_allow_html=True)
                        with c_ia2:
                            st.markdown(render_ia_card("Resultados Principais", relatorio_json.get("resultados_principais", "N/D"), "📊"), unsafe_allow_html=True)
                            st.markdown(render_ia_card("Tamanho do Efeito", relatorio_json.get("tamanho_efeito", "N/D"), "📈"), unsafe_allow_html=True)

                        st.markdown(render_ia_card("Tradução Tática e Doutrinária", relatorio_json.get("interpretacao", "N/D"), "🧠"), unsafe_allow_html=True)
                        st.markdown(render_ia_card("Conclusão Estratégica (Veredito)", relatorio_json.get("conclusao", "N/D"), "🏆"), unsafe_allow_html=True)

                        # Exibição opcional do JSON bruto para conferência acadêmica
                        with st.expander("🕵️ Ver Matriz Bruta de Dados (JSON Payload e Retorno)"):
                            st.markdown("**Payload enviado para a IA (O que o Python calculou):**")
                            st.json(payload_ia)
                            st.markdown("**JSON Retornado pela IA:**")
                            st.json(relatorio_json)

                except Exception as e:
                    st.error(f"Erro na geração do relatório de IA: {str(e)}")