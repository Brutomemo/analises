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

import utils

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


def _hex_de_elemento_cor(el: ET.Element | None) -> str | None:
    """Lê w:val de w:color / w:shd (fill), ignorando auto."""
    if el is None:
        return None
    for k, v in el.attrib.items():
        if k.endswith('val') or k.endswith('fill'):
            if not v:
                continue
            hx = str(v).upper().strip()
            if hx in {'AUTO', 'NONE', 'WINDOWTEXT'}:
                continue
            if re.fullmatch(r'[0-9A-F]{6}', hx):
                return hx
    return None


def _cor_do_run(run: ET.Element) -> str | None:
    rpr = run.find('w:rPr', NS)
    if rpr is None:
        return None
    # Cor de fonte (padrão APA)
    hx = _hex_de_elemento_cor(rpr.find('w:color', NS))
    if hx:
        return hx
    # Alguns templates usam sombreamento colorido no run
    return _hex_de_elemento_cor(rpr.find('w:shd', NS))


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


def _normalizar_texto(texto: str) -> str:
    """Uppercase sem acentos — compara versões diferentes da APA com o mesmo critério."""
    mapa = str.maketrans({
        'Á': 'A', 'À': 'A', 'Â': 'A', 'Ã': 'A',
        'É': 'E', 'Ê': 'E',
        'Í': 'I',
        'Ó': 'O', 'Ô': 'O', 'Õ': 'O',
        'Ú': 'U',
        'Ç': 'C',
    })
    return (texto or '').upper().translate(mapa)


def _linhas_cabecalho(tbl: ET.Element, max_linhas: int = 5) -> list[str]:
    rows = tbl.findall('.//w:tr', NS)
    linhas = []
    for row in rows[:max_linhas]:
        linhas.append(_normalizar_texto(
            ''.join(t.text or '' for t in row.findall('.//w:t', NS))
        ))
    return linhas


def _encontrar_tabela_por_titulo(tabelas: list, palavra_chave: str) -> ET.Element | None:
    """
    Localiza tabela cujo cabeçalho contenha a palavra-chave.

    Não depende do número do item (28, 33, …). Em APAs reais o título pode
    estar na 2ª/3ª linha (ex.: linha 0 = "PARTE 2").
    """
    chave = _normalizar_texto(palavra_chave)
    for tbl in tabelas:
        for linha in _linhas_cabecalho(tbl):
            if chave in linha:
                return tbl
    return None


def _encontrar_tabela_transcricao(tabelas: list) -> ET.Element | None:
    """
    Localiza a seção de transcrição integral pela palavra TRANSCRICAO.

    Independente do número do item na APA. Evita falso positivo da coluna
    "TRECHO DA TRANSCRIÇÃO" na tabela de técnicas.
    """
    # Título de seção: opcional "NN - " + TRANSCRICAO (+ INTEGRAL...)
    re_titulo = re.compile(
        r'(?:^|\b)\d{0,3}\s*[-–.]?\s*TRANSCRICAO(?:\s+INTEGRAL)?'
    )
    candidatos = []

    for idx, tbl in enumerate(tabelas):
        linhas = _linhas_cabecalho(tbl)
        if not linhas:
            continue

        # Descarta tabela de técnicas mesmo que mencione "trecho da transcrição"
        cabecalho_junto = ' | '.join(linhas)
        if 'ANALISE DAS TECNICAS' in cabecalho_junto or (
            'TECNICAS' in linhas[0] and 'TRECHO' in cabecalho_junto
        ):
            continue

        melhor_score = 0
        for linha in linhas:
            if 'TRANSCRICAO' not in linha:
                continue
            # Coluna auxiliar de técnicas, não a seção de falas
            if 'TRECHO DA TRANSCRICAO' in linha and 'INTEGRAL' not in linha:
                continue

            score = 0
            if re_titulo.search(linha):
                score += 3
            if 'INTEGRAL' in linha:
                score += 2
            if 'TRANSCRICAO' in linha:
                score += 1
            # Títulos de seção costumam ser curtos
            if len(linha) < 80:
                score += 1
            melhor_score = max(melhor_score, score)

        if melhor_score > 0:
            candidatos.append((melhor_score, idx, tbl))

    if not candidatos:
        # Fallback: TRANSCRICAO de seção, nunca coluna "TRECHO DA TRANSCRICAO"
        for tbl in tabelas:
            linhas = _linhas_cabecalho(tbl)
            cabecalho_junto = ' | '.join(linhas)
            if 'ANALISE DAS TECNICAS' in cabecalho_junto:
                continue
            for linha in linhas:
                if 'TRANSCRICAO' not in linha:
                    continue
                if 'TRECHO DA TRANSCRICAO' in linha and 'INTEGRAL' not in linha:
                    continue
                return tbl
        return None

    candidatos.sort(key=lambda x: (-x[0], x[1]))
    return candidatos[0][2]


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
        # Pula a linha de cabeçalho (título da seção — número do item irrelevante)
        linha_texto = _normalizar_texto(
            ''.join(t.text or '' for t in row.findall('.//w:t', NS))
        )
        if 'TRANSCRICAO' in linha_texto and len(linha_texto) < 80:
            continue

        for cell in row.findall('.//w:tc', NS):
            for para in cell.findall('.//w:p', NS):
                # No Word, só o 1º run do parágrafo costuma trazer w:color;
                # os seguintes herdam visualmente — repetimos o último papel válido.
                papel_atual = None
                for run in para.findall('.//w:r', NS):
                    texto = ''.join(t.text or '' for t in run.findall('w:t', NS))
                    if not texto.strip():
                        continue

                    cor_hex = _cor_do_run(run)
                    papel = _classificar_cor(cor_hex) if cor_hex else None
                    if papel:
                        papel_atual = papel

                    if papel_atual and papel_atual in falas:
                        texto_limpo = _limpar(texto)
                        if texto_limpo:
                            falas[papel_atual].append(texto_limpo)

    return {papel: ' '.join(linhas) for papel, linhas in falas.items()}


# ============================================================
# EXTRAÇÃO DAS TÉCNICAS
# ============================================================

_RE_PLACEHOLDER_TECNICA = re.compile(
    r'^escolher\s+um\s+item\.?$',
    re.IGNORECASE,
)


def _tecnica_valida(tecnica: str) -> bool:
    """Ignora placeholders de dropdown do Word ('Escolher um item.')."""
    t = (tecnica or '').strip()
    if not t:
        return False
    if _RE_PLACEHOLDER_TECNICA.match(t):
        return False
    if _normalizar_texto(t) in {'ESCOLHER UM ITEM', 'ESCOLHER UM ITEM.'}:
        return False
    return True


def _extrair_tecnicas(tbl: ET.Element) -> pd.DataFrame:
    """
    Extrai colunas da tabela de técnicas do .docx.
    Tolerante a variações de layout (colunas mescladas / ordem diferente).
    Ignora linhas com placeholder "Escolher um item." (técnica não preenchida).
    """
    registros = []
    rows = tbl.findall('.//w:tr', NS)
    atitude_map = {
        '1': 1, '0': 0, '-1': -1,
        'positivo': 1, 'negativo': -1, 'neutro': 0,
        'positiva': 1, 'negativa': -1,
        '🟢 reação positiva': 1,
        '⚪ reação neutra': 0,
        '🔴 reação negativa': -1,
    }

    for i, row in enumerate(rows):
        if i < 2:
            continue

        cells = row.findall('.//w:tc', NS)
        if len(cells) < 2:
            continue

        textos = [
            ''.join(t.text or '' for t in cell.findall('.//w:t', NS)).strip()
            for cell in cells
        ]
        tecnica = re.sub(r'^\d+[\.\)]\s*', '', textos[0]).strip()
        if not _tecnica_valida(tecnica):
            continue

        atitude_raw = textos[5].strip() if len(textos) > 5 else textos[-1].strip()
        if _RE_PLACEHOLDER_TECNICA.match(atitude_raw or ''):
            atitude_raw = ''
        atitude = atitude_map.get(atitude_raw.lower()) if atitude_raw else None

        trecho = ''
        indices_trecho = range(1, 5) if len(textos) > 5 else range(1, len(textos))
        for idx in indices_trecho:
            candidato = textos[idx].strip()
            if not candidato or candidato == atitude_raw:
                continue
            if _RE_PLACEHOLDER_TECNICA.match(candidato):
                continue
            if len(candidato) > len(trecho):
                trecho = candidato

        if not trecho and len(textos) > 5:
            candidato = textos[4].strip()
            if _tecnica_valida(candidato) or (
                candidato and not _RE_PLACEHOLDER_TECNICA.match(candidato)
            ):
                trecho = candidato

        tecnica = utils.normalizar_nome_tecnica(tecnica) or tecnica

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

        # Âncora = "Transcrição" (qualquer número de item). Técnicas = título próprio.
        tbl_trans = _encontrar_tabela_transcricao(tabelas)
        tbl_tec   = _encontrar_tabela_por_titulo(tabelas, 'ANALISE DAS TECNICAS')

        transcricoes = _extrair_transcricoes(tbl_trans) if tbl_trans else {}
        # Fallback: se a seção foi achada mas saiu vazia, tenta demais tabelas
        # (versões com tabela aninhada / título em célula separada).
        if not any(transcricoes.get(k) for k in (
            'causador', 'negociador_principal', 'negociador_secundario'
        )):
            for tbl in tabelas:
                if tbl is tbl_trans:
                    continue
                candidato = _extrair_transcricoes(tbl)
                if any(candidato.get(k) for k in (
                    'causador', 'negociador_principal', 'negociador_secundario'
                )):
                    transcricoes = candidato
                    break

        tecnicas = _extrair_tecnicas(tbl_tec) if tbl_tec else pd.DataFrame()

        return {'transcricoes': transcricoes, 'tecnicas': tecnicas, 'erro': None}

    except Exception as e:
        return {'transcricoes': {}, 'tecnicas': pd.DataFrame(), 'erro': str(e)}


# ============================================================
# WIDGET STREAMLIT
# ============================================================

def _separador_keys():
    """Chaves versionadas do extrator (sincronizadas com _criar_apa_form_rev em form_apa)."""
    rev = st.session_state.get("_criar_apa_form_rev", 0)
    return lambda nome: f"{nome}__{rev}"


def render_separador():
    """
    Widget completo de extração da APA.
    Exibe transcrições separadas e tabela de técnicas prontas para usar.
    """
    sk = _separador_keys()
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
        key=sk("uploader_apa")
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
        st.text_area("Transcrição do Causador", value=trans.get('causador', ''), height=300, key=sk("ext_causador"))

    with tab_np:
        st.text_area("Transcrição do Negociador Principal", value=trans.get('negociador_principal', ''), height=300, key=sk("ext_neg_principal"))

    with tab_ns:
        st.text_area("Transcrição do Negociador Secundário", value=trans.get('negociador_secundario', ''), height=300, key=sk("ext_neg_secundario"))

    with tab_pi:
        st.text_area("Transcrição do 1º Interventor", value=trans.get('primeiro_interventor', ''), height=300, key=sk("ext_primeiro_interventor"))

    # ── TÉCNICAS ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Técnicas Extraídas")

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
