import streamlit as st
import requests
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance
import os
import io
import base64

# 1. CONFIGURAÇÃO DA PÁGINA (Fundamental para Layout Wide)
st.set_page_config(
    page_title="GATE - Analisador de APAs",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. FUNÇÕES AUXILIARES ---
def aplicar_opacidade_e_brilho(image_path, opacity=1.0, brightness=1.0):
    """Abre uma imagem e aplica níveis de opacidade e brilho (usado na imagem de fundo)."""
    try:
        img = Image.open(image_path)
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        if opacity < 1.0:
            alpha = img.getchannel('A')
            new_alpha = alpha.point(lambda i: i * opacity)
            img.putalpha(new_alpha)
        return img
    except FileNotFoundError:
        return None

def get_image_base64(image_path):
    """Converte a imagem para Base64 para permitir sobreposição de degradê em HTML."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return None

# --- RESOLUÇÃO DE CAMINHOS: ESTRATÉGIA DUAL (PC PESSOAL + TRABALHO) ---
script_dir = os.path.dirname(os.path.abspath(__file__))
path_assets_relativo = os.path.join(script_dir, "Assets")
path_assets_absoluto = r"C:\Users\marco\Desktop\Analises\streamlit_app\Assets"

if os.path.exists(path_assets_relativo):
    path_assets = path_assets_relativo
elif os.path.exists(path_assets_absoluto):
    path_assets = path_assets_absoluto
else:
    path_assets = path_assets_absoluto

path_teste_gate = os.path.join(path_assets, "teste-gate.PNG")
path_brasao_gate = os.path.join(path_assets, "BRASÃO GATE.PNG")
path_novo_prata = os.path.join(path_assets, "negociacao-novo-prata.PNG")


# --- 3. INJEÇÃO DE CSS (Vibe Premium/Electric Orange) ---
st.markdown("""
<style>
    /* REDUZIR MARGEM SUPERIOR DO STREAMLIT */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }
    
    /* ESCONDER O HEADER PADRÃO (A faixa do topo do Streamlit) */
    header {visibility: hidden;}

    /* FUNDO PRINCIPAL - Preto profundo */
    .stApp {
        background-color: #050505;
        color: #FFFFFF;
    }

    /* TÍTULO PRINCIPAL - Com gradiente */
    .main-title {
        font-family: 'Inter', sans-serif;
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(180deg, #FFFFFF 0%, #BBBBBB 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1.1;
    }

    /* SUBTÍTULO */
    .sub-title {
        color: #f97316; /* Laranja principal da referência */
        font-weight: 600;
        font-size: 1.1rem;
        margin-top: 5px;
        margin-bottom: 0;
    }

    /* CARD DE INFO - Glassmorphism sutil */
    .info-card {
        background: rgba(15, 15, 15, 0.7);
        border: 1px solid rgba(249, 115, 22, 0.15);
        border-radius: 12px;
        padding: 15px;
        margin-top: 25px;
        margin-bottom: 25px;
    }

    /* AJUSTE DE IMAGENS - Força arredondamento e bordas para o tema */
    [data-testid="stImage"] img {
        border-radius: 8px;
    }

    /* BOTÃO - Gradiente e Efeito Glow */
    div.stButton > button {
        background: linear-gradient(90deg, #f97316 0%, #fb923c 100%);
        color: white;
        border: none;
        padding: 0.7rem 2rem;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s ease;
        width: 100%;
    }
    div.stButton > button:hover {
        box-shadow: 0 0 15px rgba(249, 115, 22, 0.6);
        transform: translateY(-2px);
    }

    /* ESCONDER ELEMENTOS PADRÃO */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# =========================================================
# --- ESTRUTURA VISUAL DA PÁGINA ---
# =========================================================

# 1. IMAGEM DO TOPO COM DEGRADÊ LARANJA (HTML/CSS)
img_topo_b64 = get_image_base64(path_teste_gate)
if img_topo_b64:
    st.markdown(f"""
    <div style="
        position: relative;
        width: 100%;
        height: 250px;
        border-radius: 8px;
        overflow: hidden;
        background-image: url('data:image/png;base64,{img_topo_b64}');
        background-size: cover;
        background-position: center 20%;
        margin-bottom: 1rem;
    ">
        <div style="
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(180deg, rgba(5,5,5,0.1) 0%, rgba(249, 115, 22, 0.6) 100%);
        "></div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.error(f"Erro: Imagem do topo não localizada em {path_teste_gate}")


# 2. CABEÇALHO (Brasão | Título | Imagem de Fundo Novo Prata)
col_logo, col_titulo, col_img_fundo = st.columns([1, 4, 3])

with col_logo:
    try:
        img_brasao_original = Image.open(path_brasao_gate)
        st.image(img_brasao_original, use_container_width=True)
    except FileNotFoundError:
        st.error(f"Brasão não localizado em {path_brasao_gate}")

with col_titulo:
    st.markdown('<h1 class="main-title">Sistema de Análise Qualitativa</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Delta Negociação - GATE / PMESP</p>', unsafe_allow_html=True)

with col_img_fundo:
    img_op_processada = aplicar_opacidade_e_brilho(path_novo_prata, opacity=0.4, brightness=0.6)
    if img_op_processada:
        st.image(img_op_processada, use_container_width=True)
    else:
        st.warning(f"Imagem operacional não localizada em {path_novo_prata}")


# 3. ÁREA DE INFO (Card)
st.markdown(f"""
<div class="info-card">
    <p><strong>Desenvolvido por Marcos Batista.</strong> Este sistema processa as Análises Pós-Ação (APAs) com rigor metodológico e estatístico.</p>
    <p style="font-size: 0.9rem; color: #888;">A extração e os cálculos matemáticos são realizados localmente utilizando <strong>PyMuPDF</strong>, 
    <strong>SciPy</strong> (Correlação de Spearman) e <strong>Scikit-Learn</strong> (Modelagem de Tópicos LDA). A IA atua exclusivamente como estruturadora de metadados qualitativos, garantindo a reprodutibilidade dos dados.</p>
</div>
""", unsafe_allow_html=True)


# 4. ÁREA DE UPLOAD E INÍCIO DA ANÁLISE
st.markdown("### 🛠️ Preparação da Análise")
col_upload, col_espaco = st.columns([2, 1])

with col_upload:
    uploaded_file = st.file_uploader("Selecione a APA (PDF)", type=['pdf'])
    st.markdown("<br>", unsafe_allow_html=True)


# =========================================================
# --- LÓGICA E RENDERIZAÇÃO ORIGINAL (Preservada) ---
# =========================================================

def extrair_dados_pdf(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    dados = {"causador": [], "negociador_p": [], "negociador_s": [], "texto_completo": ""}
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if "lines" in b:
                for l in b["lines"]:
                    for s in l["spans"]:
                        texto = s["text"].strip()
                        if not texto: continue
                        color = s["color"]
                        if color == 16711680 or color == 13500416: dados["causador"].append(texto)
                        elif color == 255 or color == 128: dados["negociador_p"].append(texto)
                        elif color == 32768 or color == 65280: dados["negociador_s"].append(texto)
                        dados["texto_completo"] += texto + " "
    return {k: " ".join(v) if isinstance(v, list) else v for k, v in dados.items()}

def renderizar_relatorio_autoridade(dados_ia):
    st.markdown("<hr style='border: 0.5px solid rgba(249,115,22,0.15)'>", unsafe_allow_html=True)
    st.markdown('<h2 style="color: #f97316; margin-bottom: 20px;">📑 Relatório de Inteligência Pós-Ação</h2>', unsafe_allow_html=True)
    
    with st.expander("🔬 Metodologia Estatística Aplicada"):
        st.markdown("""
        <div style="color: #999; font-size: 0.9rem; line-height: 1.6;">
        • <b>Modelagem de Tópicos (LDA):</b> Decomposição semântica para identificar convergência temática.<br>
        • <b>Coeficiente de Spearman:</b> Validação de correlação técnica/comportamental.<br>
        • <b>Diferença de Médias (Delta):</b> Comprovação matemática do desarme emocional.
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<h3 style="font-size: 1.2rem; color: #FFFFFF; margin-top:15px;">📝 Parecer Técnico</h3>', unsafe_allow_html=True)
    parecer = dados_ia.get("parecer_tecnico", "Aguardando processamento...")
    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.03); border-left: 4px solid #f97316; padding: 15px; border-radius: 4px; color: #DDD; font-style: italic; font-size:0.95rem;">
        {parecer}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    chart_color = ["#f97316"] 

    with col1:
        st.markdown('<p style="color: #f97316; font-weight: bold; text-align:center;">Frequência de Técnicas</p>', unsafe_allow_html=True)
        if "grafico_frequencia" in dados_ia:
            st.bar_chart(dados_ia["grafico_frequencia"], color=chart_color)
    
    with col2:
        st.markdown('<p style="color: #f97316; font-weight: bold; text-align:center;">Evolução de Receptividade</p>', unsafe_allow_html=True)
        if "delta_emocional" in dados_ia:
            st.line_chart(dados_ia["delta_emocional"], color=chart_color)

    st.markdown("<br>", unsafe_allow_html=True)
    col_btn, _ = st.columns([1, 2])
    with col_btn:
        st.button("🖨️ Exportar Relatório (PDF)")

# --- PROCESSAMENTO ---
if uploaded_file is not None:
    if st.button("🚀 INICIAR ANÁLISE"):
        with st.spinner('Executando algoritmos de extração e IA...'):
            conteudo_extraido = extrair_dados_pdf(uploaded_file.getvalue())
            n8n_url = "http://n8n:5678/webhook-test/analise-doc"
            
            try:
                response = requests.post(n8n_url, json=conteudo_extraido) 
                if response.status_code == 200:
                    st.success("✅ Análise concluída com sucesso!")
                    renderizar_relatorio_autoridade(response.json())
                else:
                    st.error(f"Erro no n8n: {response.status_code}")
            except Exception as e:
                st.error(f"Erro na comunicação com o servidor: {e}")