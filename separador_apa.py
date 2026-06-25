"""
separador_apa.py
Extrai transcrições e tabela de técnicas diretamente do arquivo .docx/.docm da APA.

Cores mapeadas:
  FF0000 → Causador
  00B0F0 → Negociador Principal (azul ciano)
  Variações azul/ciano → Negociador Principal
  00B050 → Negociador Secundário (verde)
  7030A0 → 1º Interventor (roxo) — incluído como opção
  000000 → Técnicas/marcadores em preto — REMOVIDOS
  FFC000 → Terceiro (amarelo) — ignorado por padrão
"""

import re
import io
import zipfile
import pandas as pd
import streamlit as st
from xml.etree import ElementTree as ET

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

# ============================================================
# MAPA DE CORES
# ============================================================

CORES = {
    'FF0000': 'causador',
    # Azuis/cianos → negociador principal
    '00B0F0': 'negociador_principal',
    '4472C4': 'negociador_principal',
    '2E75B6': 'negociador_principal',
    '0070C0': 'negociador_principal',
    '00B8FF': 'negociador_principal',
    '17375E': 'negociador_principal',
    # Verdes → negociador secundário
    '00B050': 'negociador_secundario',
    '70AD47': 'negociador_secundario',
    '375623': 'negociador_secundario',
    '00FF00': 'negociador_secundario',
    # Roxo → 1º interventor
    '7030A0': 'primeiro_interventor',
    # Preto e sem cor → remover
    '000000': None,
    'AUTO':   None,
}


def _classificar_cor(hex_color: str) -> str | None:
    if not hex_color:
        return None
    hex_upper = hex_color.upper().strip()
    if hex_upper in CORES:
        return CORES[hex_upper]
    # Fallback por componente RGB
    try:
        r = int(hex_upper[0:2], 16)
        g = int(hex_upper[2:4], 16)
        b = int(hex_upper[4:6], 16)
        # Vermelho dominante
        if r > 180 and g < 80 and b < 80:
            return 'causador'
        # Azul/ciano dominante
        if b > 150 and r < 80:
            return 'negociador_principal'
        if b > 100 and g > 100 and r < 60:
            return 'negociador_principal'
        # Verde dominante
        if g > 150 and r < 80 and b < 80:
            return 'negociador_secundario'
    except (ValueError, IndexError):
        pass
    return None


def _cor_do_run(run: ET.Element) -> str | None:
    rpr = run.find('w:rPr', NS)
    if rpr is None:
        return None
    cel = rpr.find('w:color', NS)
    if cel is None:
        return None
    for k, v in cel.attrib.items():
        if 'val' in k:
            return v
    return None


# ============================================================
# LIMPEZA
# ============================================================

_RE_TIMESTAMP = re.compile(r'\b\d{1,2}:\d{2}(?::\d{2})?\b')
_RE_ESPACOS   = re.compile(r'[ \t]{2,}')
_RE_LEGENDA   = re.compile(
    r'^(CAUSADOR|NEGOCIADOR PRINCIPAL|NEGOCIADOR SECUND[AÁ]RIO|1[°º]\s*INTERVENTOR)\s*:\s*\S+\s*',
    re.IGNORECASE
)

_FRAGMENTOS = {'verde', 'azul', 'vermelho', 'roxo', 'amarelo', ',', '–', '-'}

_RE_LEGENDA_COMPLETA = re.compile(
    r'^(CAUSADOR|NEGOCIADOR PRINCIPAL|NEGOCIADOR SECUND[AÁ]RIO|1[°º]\s*INTERVENTOR|GERENTE|TERCEIRO)\s*[:\-–]\s*\w*\s*$',
    re.IGNORECASE
)

def _limpar(texto: str) -> str:
    texto = _RE_TIMESTAMP.sub('', texto)
    texto = _RE_LEGENDA.sub('', texto)
    texto = _RE_ESPACOS.sub(' ', texto)
    texto = texto.strip()
    if texto.lower() in _FRAGMENTOS:
        return ''
    # Remove linhas que são apenas legenda de cor
    if _RE_LEGENDA_COMPLETA.match(texto):
        return ''
    # Remove separadores (linhas de travessão contínuo)
    if re.match(r'^[–\-_]{3,}$', texto):
        return ''
    return texto


# ============================================================
# LOCALIZAR TABELA POR TÍTULO
# ============================================================

def _texto_da_tabela(tbl: ET.Element) -> str:
    return ''.join(t.text or '' for t in tbl.findall('.//w:t', NS))


def _encontrar_tabela_por_titulo(tabelas: list, palavra_chave: str) -> ET.Element | None:
    for tbl in tabelas:
        rows = tbl.findall('.//w:tr', NS)
        if not rows:
            continue
        primeira_linha = ''.join(
            t.text or '' for t in rows[0].findall('.//w:t', NS)
        ).upper()
        if palavra_chave.upper() in primeira_linha:
            return tbl
    return None


# ============================================================
# EXTRAÇÃO DAS TRANSCRIÇÕES
# ============================================================

def _extrair_transcricoes(tbl: ET.Element) -> dict:
    falas = {
        'causador': [],
        'negociador_principal': [],
        'negociador_secundario': [],
        'primeiro_interventor': [],
    }

    for row in tbl.findall('.//w:tr', NS):
        # Pula a linha de cabeçalho (título da seção)
        linha_texto = ''.join(t.text or '' for t in row.findall('.//w:t', NS)).upper()
        if 'TRANSCRI' in linha_texto and len(linha_texto) < 60:
            continue

        for cell in row.findall('.//w:tc', NS):
            for para in cell.findall('.//w:p', NS):
                for run in para.findall('.//w:r', NS):
                    texto = ''.join(t.text or '' for t in run.findall('w:t', NS))
                    if not texto.strip():
                        continue

                    cor_hex = _cor_do_run(run)
                    papel = _classificar_cor(cor_hex) if cor_hex else None

                    if papel and papel in falas:
                        texto_limpo = _limpar(texto)
                        if texto_limpo:
                            falas[papel].append(texto_limpo)

    return {papel: ' '.join(linhas) for papel, linhas in falas.items()}


# ============================================================
# EXTRAÇÃO DAS TÉCNICAS
# ============================================================

def _extrair_tecnicas(tbl: ET.Element) -> pd.DataFrame:
    """
    Extrai colunas da tabela de técnicas:
    Col 0: Técnica
    Col 4: Trecho da Transcrição
    Col 5: Atitude do Causador
    """
    registros = []
    rows = tbl.findall('.//w:tr', NS)

    for i, row in enumerate(rows):
        if i < 2:  # Pula título e cabeçalho
            continue
        cells = row.findall('.//w:tc', NS)
        if len(cells) < 6:
            continue

        def cel_texto(idx):
            return ''.join(t.text or '' for t in cells[idx].findall('.//w:t', NS)).strip()

        tecnica  = cel_texto(0)
        trecho   = cel_texto(4)
        atitude_raw = cel_texto(5).strip()

        if not tecnica:
            continue

        # Normalizar atitude: 1=positivo, 0=neutro, -1=negativo, None=inaudível
        atitude_map = {
            '1': 1, '0': 0, '-1': -1,
            'positivo': 1, 'negativo': -1, 'neutro': 0,
            'positiva': 1, 'negativa': -1,
            '🟢 reação positiva': 1,
            '⚪ reação neutra': 0,
            '🔴 reação negativa': -1,
        }
        atitude = atitude_map.get(atitude_raw.lower(), None)

        registros.append({
            'TÉCNICAS': tecnica,
            'TRECHO DA TRANSCRIÇÃO': trecho,
            'ATITUDE DO CAUSADOR': atitude,
        })

    return pd.DataFrame(registros)


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def processar_apa(file_bytes: bytes) -> dict:
    """
    Processa o arquivo .docx/.docm da APA e retorna transcrições e técnicas.

    Returns:
        {
          'transcricoes': {causador, negociador_principal, negociador_secundario, primeiro_interventor},
          'tecnicas': DataFrame,
          'erro': str | None
        }
    """
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            root = ET.parse(z.open('word/document.xml')).getroot()

        body = root.find('w:body', NS)
        tabelas = body.findall('.//w:tbl', NS)

        tbl_trans = _encontrar_tabela_por_titulo(tabelas, 'TRANSCRI')
        tbl_tec   = _encontrar_tabela_por_titulo(tabelas, 'ANÁLISE DAS TÉCNICAS')

        transcricoes = _extrair_transcricoes(tbl_trans) if tbl_trans else {}
        tecnicas     = _extrair_tecnicas(tbl_tec)       if tbl_tec   else pd.DataFrame()

        return {'transcricoes': transcricoes, 'tecnicas': tecnicas, 'erro': None}

    except Exception as e:
        return {'transcricoes': {}, 'tecnicas': pd.DataFrame(), 'erro': str(e)}


# ============================================================
# WIDGET STREAMLIT
# ============================================================

def render_separador():
    """
    Widget completo de extração da APA.
    Exibe transcrições separadas e tabela de técnicas prontas para usar.
    """
    st.markdown("""
    <div class='info-card'>
    <h5 style='color: #FFD700; margin-top: 0;'>📄 Extrator de APA</h5>
    <p style='font-size:0.9rem; color:#bbb;'>
    Faça upload do arquivo <strong>.docx</strong> da APA.<br>
    O sistema extrai automaticamente as transcrições e a tabela de técnicas.
    </p>
    </div>
    """, unsafe_allow_html=True)

    arquivo = st.file_uploader(
        "Selecione o arquivo .docx da APA",
        type=["docx", "docm"],
        key="uploader_apa"
    )

    if arquivo is None:
        return

    with st.spinner("Processando arquivo..."):
        resultado = processar_apa(arquivo.read())

    if resultado['erro']:
        st.error(f"❌ Erro ao processar: {resultado['erro']}")
        return

    trans = resultado['transcricoes']
    df_tec = resultado['tecnicas']

    # ── TRANSCRIÇÕES ──────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📝 Transcrições Extraídas")

    tabs_nomes = ["🔴 Causador", "🔵 Neg. Principal", "🟢 Neg. Secundário", "🟣 1º Interventor"]
    tabs_chaves = ["causador", "negociador_principal", "negociador_secundario", "primeiro_interventor"]

    col1, col2, col3, col4 = st.columns(4)
    for col, chave, nome in zip(
        [col1, col2, col3, col4], tabs_chaves,
        ["Causador", "Neg. Principal", "Neg. Secundário", "1º Interventor"]
    ):
        palavras = len(trans.get(chave, '').split())
        col.metric(nome, f"{palavras} palavras")

    tab_c, tab_np, tab_ns, tab_pi = st.tabs(tabs_nomes)

    with tab_c:
        st.text_area("Transcrição do Causador", value=trans.get('causador', ''), height=300, key="ext_causador")

    with tab_np:
        st.text_area("Transcrição do Negociador Principal", value=trans.get('negociador_principal', ''), height=300, key="ext_neg_principal")

    with tab_ns:
        st.text_area("Transcrição do Negociador Secundário", value=trans.get('negociador_secundario', ''), height=300, key="ext_neg_secundario")

    with tab_pi:
        st.text_area("Transcrição do 1º Interventor", value=trans.get('primeiro_interventor', ''), height=300, key="ext_primeiro_interventor")

    # ── TÉCNICAS ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### ⚙️ Técnicas Extraídas")

    if df_tec.empty:
        st.warning("⚠️ Nenhuma técnica encontrada no documento.")
    else:
        st.metric("Total de técnicas", len(df_tec))
        st.dataframe(df_tec, use_container_width=True, hide_index=True)

        # Salvar no session_state para uso posterior
        st.session_state['tecnicas_extraidas_apa'] = df_tec

        st.info(
            "✅ Técnicas prontas. "
            "Use o botão abaixo para enviá-las ao Airtable vinculadas a uma APA."
        )

    # Aviso se nada foi extraído
    total_palavras = sum(len(trans.get(c, '').split()) for c in tabs_chaves)
    if total_palavras == 0:
        st.warning(
            "⚠️ Nenhuma transcrição foi extraída. "
            "Verifique se o arquivo contém texto colorido conforme o padrão da APA."
        )
