"""
separador_transcricao.py
Separa transcrições de APA por cor do texto no arquivo .docm.

Cores:
- Tons vermelhos  → Causador
- Tons azul/ciano → Negociador Principal
- Tons verdes     → Negociador Secundário
- Sem cor / preto → ignorado (marcadores de tempo, cabeçalhos)
"""

import re
import io
import zipfile
from xml.etree import ElementTree as ET


# ============================================================
# MAPEAMENTO DE CORES → PAPEL
# ============================================================

def _classificar_cor(hex_color: str) -> str | None:
    """
    Recebe uma cor hex (ex: 'FF0000') e retorna o papel correspondente.
    Retorna None se a cor não mapeia para nenhum papel.
    """
    if not hex_color or len(hex_color) != 6:
        return None

    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except ValueError:
        return None

    # Tom vermelho: R dominante, G e B baixos
    if r > 150 and g < 100 and b < 100:
        return "causador"

    # Tom azul ou ciano: B dominante, ou B+G dominantes com R baixo
    if b > 100 and r < 100:
        return "negociador_principal"
    if b > 100 and g > 100 and r < 80:
        return "negociador_principal"

    # Tom verde: G dominante, R e B baixos
    if g > 120 and r < 100 and b < 100:
        return "negociador_secundario"

    return None


# ============================================================
# LIMPEZA DO TEXTO
# ============================================================

_PATTERN_TIMESTAMP = re.compile(r'\b\d{1,2}:\d{2}(?::\d{2})?\b')
_PATTERN_ESPACOS   = re.compile(r'\s{2,}')

def _limpar_texto(texto: str) -> str:
    """Remove timestamps (00:00) e espaços duplos."""
    texto = _PATTERN_TIMESTAMP.sub('', texto)
    texto = _PATTERN_ESPACOS.sub(' ', texto)
    return texto.strip()


# ============================================================
# EXTRAÇÃO DO XML DO DOCM
# ============================================================

_NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def _extrair_document_xml(file_bytes: bytes) -> ET.Element:
    """Abre o .docm (zip) e retorna o ElementTree do document.xml."""
    with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
        with z.open('word/document.xml') as f:
            return ET.parse(f).getroot()


def _cor_do_run(run: ET.Element) -> str | None:
    """Extrai a cor hex de um <w:r> (run de texto)."""
    rpr = run.find('w:rPr', _NS)
    if rpr is None:
        return None
    color_el = rpr.find('w:color', _NS)
    if color_el is None:
        return None
    val = color_el.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
    if not val:
        val = color_el.attrib.get(
            '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val',
            color_el.get('w:val', '')
        )
    # Tenta o namespace direto
    for attr_name, attr_val in color_el.attrib.items():
        if 'val' in attr_name:
            val = attr_val
            break
    return val if val and val.upper() != 'AUTO' else None


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def separar_transcricao(file_bytes: bytes) -> dict:
    """
    Processa um arquivo .docm e retorna as transcrições separadas por papel.

    Args:
        file_bytes: Bytes do arquivo .docm carregado via st.file_uploader

    Returns:
        dict com chaves:
            - 'causador': str
            - 'negociador_principal': str
            - 'negociador_secundario': str
            - 'nao_classificado': str  (texto sem cor identificada)
            - 'estatisticas': dict com contagens
    """
    root = _extrair_document_xml(file_bytes)

    falas = {
        "causador": [],
        "negociador_principal": [],
        "negociador_secundario": [],
        "nao_classificado": [],
    }

    body = root.find('w:body', _NS)
    if body is None:
        return {k: "" for k in falas} | {"estatisticas": {}}

    for paragrafo in body.findall('w:p', _NS):
        # Agrupa runs do parágrafo por cor
        runs_por_papel = {}

        for run in paragrafo.findall('w:r', _NS):
            texto_run = ''.join(
                t.text or ''
                for t in run.findall('w:t', _NS)
            )
            if not texto_run.strip():
                continue

            cor_hex = _cor_do_run(run)
            papel = _classificar_cor(cor_hex) if cor_hex else None

            if papel:
                runs_por_papel.setdefault(papel, []).append(texto_run)
            else:
                runs_por_papel.setdefault("nao_classificado", []).append(texto_run)

        # Adiciona as falas do parágrafo
        for papel, textos in runs_por_papel.items():
            texto_junto = ' '.join(textos)
            texto_limpo = _limpar_texto(texto_junto)
            if texto_limpo:
                falas[papel].append(texto_limpo)

    # Junta tudo em strings
    resultado = {
        papel: '\n'.join(linhas)
        for papel, linhas in falas.items()
    }

    resultado['estatisticas'] = {
        'linhas_causador':              len(falas['causador']),
        'linhas_negociador_principal':  len(falas['negociador_principal']),
        'linhas_negociador_secundario': len(falas['negociador_secundario']),
        'linhas_nao_classificado':      len(falas['nao_classificado']),
    }

    return resultado


# ============================================================
# WIDGET STREAMLIT
# ============================================================

def render_separador(prefill_callback=None):
    """
    Renderiza o widget de separação de transcrição no Streamlit.

    Args:
        prefill_callback: função opcional chamada com (causador, neg_principal, neg_secundario)
                          para preencher campos do formulário automaticamente.
    """
    import streamlit as st

    st.markdown("""
    <div class='info-card'>
    <h5 style='color: #FFD700; margin-top: 0;'>📄 Separador de Transcrições</h5>
    <p style='font-size:0.9rem; color:#bbb;'>
    Faça upload do arquivo <strong>.docm</strong> com a transcrição colorida.<br>
    🔴 Vermelho = Causador &nbsp;|&nbsp;
    🔵 Azul/Ciano = Neg. Principal &nbsp;|&nbsp;
    🟢 Verde = Neg. Secundário
    </p>
    </div>
    """, unsafe_allow_html=True)

    arquivo = st.file_uploader(
        "Selecione o arquivo .docm",
        type=["docm", "docx"],
        key="uploader_transcricao"
    )

    if arquivo is None:
        return

    if st.button("✔️ Separar Transcrições", key="btn_separar_transcricao"):
        with st.spinner("Processando arquivo..."):
            try:
                resultado = separar_transcricao(arquivo.read())
                stats = resultado.get('estatisticas', {})

                # Métricas
                col1, col2, col3 = st.columns(3)
                with col1: st.metric("🔴 Causador",         f"{stats.get('linhas_causador', 0)} falas")
                with col2: st.metric("🔵 Neg. Principal",   f"{stats.get('linhas_negociador_principal', 0)} falas")
                with col3: st.metric("🟢 Neg. Secundário",  f"{stats.get('linhas_negociador_secundario', 0)} falas")

                st.markdown("---")

                # Tabs de resultado
                tab_c, tab_np, tab_ns = st.tabs([
                    "🔴 Causador",
                    "🔵 Negociador Principal",
                    "🟢 Negociador Secundário"
                ])

                causador     = resultado.get('causador', '')
                neg_principal = resultado.get('negociador_principal', '')
                neg_secundario = resultado.get('negociador_secundario', '')

                with tab_c:
                    st.text_area(
                        "Transcrição do Causador",
                        value=causador,
                        height=300,
                        key="resultado_causador"
                    )

                with tab_np:
                    st.text_area(
                        "Transcrição do Negociador Principal",
                        value=neg_principal,
                        height=300,
                        key="resultado_neg_principal"
                    )

                with tab_ns:
                    st.text_area(
                        "Transcrição do Negociador Secundário",
                        value=neg_secundario,
                        height=300,
                        key="resultado_neg_secundario"
                    )

                # Callback para preencher formulário automaticamente
                if prefill_callback:
                    if st.button("✔️ Usar estas transcrições no formulário", key="btn_usar_transcricoes"):
                        prefill_callback(causador, neg_principal, neg_secundario)
                        st.success("✅ Transcrições inseridas no formulário!")

                # Aviso se nenhuma cor foi detectada
                total_classificado = (
                    stats.get('linhas_causador', 0) +
                    stats.get('linhas_negociador_principal', 0) +
                    stats.get('linhas_negociador_secundario', 0)
                )
                if total_classificado == 0:
                    st.warning(
                        "⚠️ Nenhuma fala foi classificada por cor. "
                        "Verifique se o arquivo tem texto colorido conforme o padrão."
                    )

            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {str(e)}")
