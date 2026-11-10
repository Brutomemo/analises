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
    'C00000': 'causador',
    'FF5050': 'causador',
    # Fundos rosa/vermelho claros (marcação de fala do causador)
    'FFC7CE': 'causador',
    'FFC0CB': 'causador',
    'F4CCCC': 'causador',
    'F8CBAD': 'causador',
    'FCE4D6': 'causador',
    'FFD6D6': 'causador',
    'FFCCCC': 'causador',
    # Azuis/cianos → negociador principal
    '00B0F0': 'negociador_principal',
    '4472C4': 'negociador_principal',
    '2E75B6': 'negociador_principal',
    '0070C0': 'negociador_principal',
    '00B8FF': 'negociador_principal',
    '17375E': 'negociador_principal',
    # Fundos azul/ciano claros (marcação de fala do negociador)
    'BDD7EE': 'negociador_principal',
    'DDEBF7': 'negociador_principal',
    'D6EAF8': 'negociador_principal',
    'CFE2F3': 'negociador_principal',
    'DEEAF6': 'negociador_principal',
    '9DC3E6': 'negociador_principal',
    '5B9BD5': 'negociador_principal',
    # Verdes → negociador secundário
    '00B050': 'negociador_secundario',
    '70AD47': 'negociador_secundario',
    '375623': 'negociador_secundario',
    '00FF00': 'negociador_secundario',
    'C6EFCE': 'negociador_secundario',
    'E2EFDA': 'negociador_secundario',
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
    # Fallback por componente RGB (fonte forte OU fundo claro rosa/azul)
    try:
        r = int(hex_upper[0:2], 16)
        g = int(hex_upper[2:4], 16)
        b = int(hex_upper[4:6], 16)
        # Vermelho / rosa (fonte ou fundo de destaque)
        if r > 180 and g < 80 and b < 80:
            return 'causador'
        if r > 200 and r >= g + 15 and r >= b + 15:
            return 'causador'
        # Azul/ciano (fonte ou fundo de destaque)
        if b > 150 and r < 80:
            return 'negociador_principal'
        if b > 100 and g > 100 and r < 60:
            return 'negociador_principal'
        if b > 180 and b >= r and b >= g - 10 and r < 220:
            return 'negociador_principal'
        # Verde dominante
        if g > 150 and r < 80 and b < 80:
            return 'negociador_secundario'
        if g > 180 and g >= r + 15 and g >= b + 15:
            return 'negociador_secundario'
    except (ValueError, IndexError):
        pass
    return None


_HIGHLIGHT_PAPEL = {
    'red': 'causador',
    'darkred': 'causador',
    'cyan': 'negociador_principal',
    'blue': 'negociador_principal',
    'darkblue': 'negociador_principal',
    'turquoise': 'negociador_principal',
    'green': 'negociador_secundario',
    'darkgreen': 'negociador_secundario',
    'yellow': None,
    'white': None,
    'black': None,
    'none': None,
}


def _hex_de_elemento_cor(el: ET.Element | None) -> str | None:
    """Lê w:val de w:color / w:shd (fill), ignorando auto."""
    if el is None:
        return None
    for k, v in el.attrib.items():
        if k.endswith('val') or k.endswith('fill'):
            if not v:
                continue
            hx = str(v).upper().strip()
            if hx in {'AUTO', 'NONE', 'WINDOWTEXT', 'CLEAR'}:
                continue
            if re.fullmatch(r'[0-9A-F]{6}', hx):
                return hx
    return None


def _papel_de_rpr(rpr: ET.Element | None) -> str | None:
    """Classifica papel a partir de rPr (cor de fonte, sombreamento ou highlight)."""
    if rpr is None:
        return None
    hx = _hex_de_elemento_cor(rpr.find('w:color', NS))
    papel = _classificar_cor(hx) if hx else None
    if papel:
        return papel
    hx = _hex_de_elemento_cor(rpr.find('w:shd', NS))
    papel = _classificar_cor(hx) if hx else None
    if papel:
        return papel
    # Marcador de destaque do Word (fundo azul/vermelho nas falas)
    hl = rpr.find('w:highlight', NS)
    if hl is not None:
        for k, v in hl.attrib.items():
            if 'val' in k and v:
                return _HIGHLIGHT_PAPEL.get(str(v).lower().strip())
    return None


def _papel_do_run(run: ET.Element) -> str | None:
    return _papel_de_rpr(run.find('w:rPr', NS))


def _papel_do_paragrafo(para: ET.Element) -> str | None:
    """Fallback: sombreamento no parágrafo (fundo rosa/azul da fala)."""
    ppr = para.find('w:pPr', NS)
    if ppr is None:
        return None
    return _papel_de_rpr(ppr) or _classificar_cor(_hex_de_elemento_cor(ppr.find('w:shd', NS)))


def _cor_do_run(run: ET.Element) -> str | None:
    """Compat: retorna hex quando houver; preferir _papel_do_run na extração."""
    rpr = run.find('w:rPr', NS)
    if rpr is None:
        return None
    hx = _hex_de_elemento_cor(rpr.find('w:color', NS))
    if hx:
        return hx
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
            # Sombreamento da célula (alguns templates pintam a célula inteira)
            tc_pr = cell.find('w:tcPr', NS)
            papel_celula = None
            if tc_pr is not None:
                papel_celula = _classificar_cor(_hex_de_elemento_cor(tc_pr.find('w:shd', NS)))

            for para in cell.findall('.//w:p', NS):
                # Fonte / highlight / sombreamento: herda no parágrafo se o run não trouxer cor
                papel_atual = _papel_do_paragrafo(para) or papel_celula
                for run in para.findall('.//w:r', NS):
                    texto = ''.join(t.text or '' for t in run.findall('w:t', NS))
                    if not texto.strip():
                        continue

                    papel = _papel_do_run(run)
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


def _score_tabela_tecnicas(tbl: ET.Element) -> int:
    """Pontua tabela candidata a técnicas (evita wrapper com tabela aninhada)."""
    score = 0
    for linha in _linhas_cabecalho(tbl, max_linhas=8):
        if 'ANALISE DAS TECNICAS' in linha or 'TECNICAS DE NEGOCIACAO' in linha:
            score += 3
        if 'TECNICAS' in linha and ('TEMPO' in linha or 'VIDEO' in linha):
            score += 5
        if 'TECNICAS' in linha and 'TRECHO' in linha:
            score += 4
        if 'TECNICAS' in linha and 'ATITUDE' in linha:
            score += 3
        if 'EXPLICACAO SOBRE A UTILIZACAO' in linha:
            score += 2
    # Preferir tabela com várias linhas de dados (não só o título wrapper)
    n_rows = len(tbl.findall('./w:tr', NS))
    if n_rows >= 3:
        score += 2
    elif n_rows <= 1:
        score -= 2
    return score


def _encontrar_tabela_tecnicas(tabelas: list) -> ET.Element | None:
    """
    Localiza a tabela de técnicas em versões diferentes da APA
    (ex.: '34 - ANÁLISE DAS TÉCNICAS DE NEGOCIAÇÃO EMPREGADAS').
    Prefere a tabela cujo cabeçalho tem colunas Técnicas/Tempo/Trecho.
    """
    melhores = []
    for idx, tbl in enumerate(tabelas):
        sc = _score_tabela_tecnicas(tbl)
        if sc > 0:
            melhores.append((sc, -idx, tbl))
    if melhores:
        melhores.sort(reverse=True)
        return melhores[0][2]

    for chave in (
        'ANALISE DAS TECNICAS',
        'TECNICAS DE NEGOCIACAO',
        'TECNICAS EMPREGADAS',
    ):
        tbl = _encontrar_tabela_por_titulo(tabelas, chave)
        if tbl is not None:
            return tbl
    return None


def _eh_cabecalho_tecnicas(textos: list[str]) -> bool:
    juntos = _normalizar_texto(' '.join(textos))
    if 'TECNICAS' in juntos and ('TEMPO' in juntos or 'TRECHO' in juntos or 'ATITUDE' in juntos):
        return True
    prim = _normalizar_texto(textos[0] if textos else '')
    return prim in {'TECNICAS', 'TECNICA'}


def _texto_celula(cell: ET.Element) -> str:
    """Texto da célula, inclusive valor visível de content control (dropdown)."""
    partes = []
    for t in cell.findall('.//w:t', NS):
        if t.text:
            partes.append(t.text)
    return re.sub(r'\s+', ' ', ''.join(partes)).strip()


def _extrair_tecnicas_de_rows(rows: list) -> list[dict]:
    atitude_map = {
        '1': 1, '0': 0, '-1': -1,
        'positivo': 1, 'negativo': -1, 'neutro': 0,
        'positiva': 1, 'negativa': -1,
        '🟢 reação positiva': 1,
        '⚪ reação neutra': 0,
        '🔴 reação negativa': -1,
    }
    registros = []
    for row in rows:
        # Apenas células diretas da linha (evita bagunça com tabelas aninhadas)
        cells = row.findall('./w:tc', NS) or row.findall('w:tc', NS)
        if len(cells) < 2:
            continue

        textos = [_texto_celula(cell) for cell in cells]
        if _eh_cabecalho_tecnicas(textos):
            continue
        # Título da seção (ex.: "34 - ANÁLISE DAS TÉCNICAS...")
        linha_norm = _normalizar_texto(' '.join(textos))
        if 'ANALISE DAS TECNICAS' in linha_norm or 'TECNICAS DE NEGOCIACAO' in linha_norm:
            continue

        tecnica = re.sub(r'^\d+[\.\)]\s*', '', textos[0]).strip()
        # Nome longo demais = provavelmente célula wrapper, não uma técnica
        if len(tecnica) > 120:
            continue
        if not _tecnica_valida(tecnica):
            continue

        # Preferir coluna "Trecho da Transcrição" quando o layout tem 6 colunas
        atitude_raw = textos[5].strip() if len(textos) > 5 else textos[-1].strip()
        if _RE_PLACEHOLDER_TECNICA.match(atitude_raw or ''):
            atitude_raw = ''
        atitude = atitude_map.get(atitude_raw.lower()) if atitude_raw else None

        trecho = ''
        if len(textos) > 5:
            # Layout padrão: Técnicas | Tempo | Vídeo | Explicação | Trecho | Atitude
            trecho = textos[4].strip()
            if _RE_PLACEHOLDER_TECNICA.match(trecho or '') or trecho == atitude_raw:
                trecho = ''
            if not trecho:
                for idx in range(1, 5):
                    candidato = textos[idx].strip()
                    if not candidato or candidato == atitude_raw:
                        continue
                    if _RE_PLACEHOLDER_TECNICA.match(candidato):
                        continue
                    if re.fullmatch(r'\d{1,2}:\d{2}(?::\d{2})?', candidato):
                        continue
                    if re.fullmatch(r'\d{1,3}', candidato):
                        continue
                    if len(candidato) > len(trecho):
                        trecho = candidato
        else:
            for idx in range(1, len(textos)):
                candidato = textos[idx].strip()
                if not candidato or candidato == atitude_raw:
                    continue
                if _RE_PLACEHOLDER_TECNICA.match(candidato):
                    continue
                if len(candidato) > len(trecho):
                    trecho = candidato

        tecnica = utils.normalizar_nome_tecnica(tecnica) or tecnica
        if not tecnica:
            continue

        registros.append({
            'TÉCNICAS': tecnica,
            'TRECHO DA TRANSCRIÇÃO': trecho,
            'ATITUDE DO CAUSADOR': atitude,
        })
    return registros


def _extrair_tecnicas(tbl: ET.Element) -> pd.DataFrame:
    """
    Extrai colunas da tabela de técnicas do .docx.
    Tolerante a variações de layout (colunas mescladas / ordem diferente).
    Ignora linhas com placeholder "Escolher um item." (técnica não preenchida).
    """
    rows = tbl.findall('./w:tr', NS) or tbl.findall('.//w:tr', NS)
    registros = _extrair_tecnicas_de_rows(rows)

    # Wrapper com tabela aninhada: tenta as tabelas internas
    if len(registros) < 2:
        for nested in tbl.findall('.//w:tbl', NS):
            nested_rows = nested.findall('./w:tr', NS) or nested.findall('.//w:tr', NS)
            candidato = _extrair_tecnicas_de_rows(nested_rows)
            if len(candidato) > len(registros):
                registros = candidato

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

        # Âncora = "Transcrição" / "Análise das Técnicas" (qualquer número de item).
        tbl_trans = _encontrar_tabela_transcricao(tabelas)
        tbl_tec = _encontrar_tabela_tecnicas(tabelas)

        transcricoes = _extrair_transcricoes(tbl_trans) if tbl_trans else {}
        # Fallback: se a seção foi achada mas saiu vazia, tenta demais tabelas
        # (versões com tabela aninhada / título em célula separada).
        if not any(transcricoes.get(k) for k in (
            'causador', 'negociador_principal', 'negociador_secundario'
        )):
            for tbl in tabelas:
                if tbl is tbl_trans or tbl is tbl_tec:
                    continue
                candidato = _extrair_transcricoes(tbl)
                if any(candidato.get(k) for k in (
                    'causador', 'negociador_principal', 'negociador_secundario'
                )):
                    transcricoes = candidato
                    break

        tecnicas = _extrair_tecnicas(tbl_tec) if tbl_tec else pd.DataFrame()
        # Fallback: varrer tabelas até achar linhas válidas de técnicas
        if tecnicas is None or tecnicas.empty:
            for tbl in tabelas:
                if tbl is tbl_trans:
                    continue
                candidato = _extrair_tecnicas(tbl)
                if candidato is not None and not candidato.empty:
                    tecnicas = candidato
                    break

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
