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
    # Vermelhos → causador
    'FF0000': 'causador',
    'EE0000': 'causador',
    'C00000': 'causador',
    'FF5050': 'causador',
    'FF6666': 'causador',
    # Azuis/cianos → negociador principal
    '00B0F0': 'negociador_principal',
    '4472C4': 'negociador_principal',
    '2E75B6': 'negociador_principal',
    '0070C0': 'negociador_principal',
    '00B8FF': 'negociador_principal',
    '17375E': 'negociador_principal',
    '5B9BD5': 'negociador_principal',
    '215E99': 'negociador_principal',
    # Verdes → negociador secundário
    '00B050': 'negociador_secundario',
    '70AD47': 'negociador_secundario',
    '375623': 'negociador_secundario',
    '00FF00': 'negociador_secundario',
    '196B24': 'negociador_secundario',
    # Roxo → 1º interventor
    '7030A0': 'primeiro_interventor',
    '77206D': 'primeiro_interventor',
    # Amarelo/laranja (terceiro) e preto → ignorar
    'FFC000': None,
    'ED7D31': None,
    '000000': None,
    '1A1C1E': None,
    'AUTO': None,
}


def _classificar_cor(hex_color: str) -> str | None:
    """Classifica papel pela cor de fonte do diálogo (não texto de template)."""
    if not hex_color:
        return None
    hex_upper = hex_color.upper().strip()
    if hex_upper in CORES:
        return CORES[hex_upper]
    try:
        r = int(hex_upper[0:2], 16)
        g = int(hex_upper[2:4], 16)
        b = int(hex_upper[4:6], 16)
        # Amarelo / laranja (terceiro) — nunca causador
        if r > 180 and g > 90 and b < 100:
            return None
        # Tons de vermelho → causador
        if r >= 180 and r > g + 40 and r > b + 40 and g < 120:
            return 'causador'
        # Tons de azul / ciano → negociador principal
        if b >= 140 and b >= r + 30 and g < 220:
            return 'negociador_principal'
        if b > 100 and g > 100 and r < 80:
            return 'negociador_principal'
        # Tons de verde → negociador secundário
        if g >= 140 and g > r + 30 and g > b + 20:
            return 'negociador_secundario'
        # Roxo
        if r > 80 and b > 80 and g < 80 and abs(r - b) < 60:
            return 'primeiro_interventor'
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
            if hx in {'AUTO', 'NONE', 'WINDOWTEXT', 'CLEAR'}:
                continue
            if re.fullmatch(r'[0-9A-F]{6}', hx):
                return hx
    return None


def _papel_do_run(run: ET.Element) -> str | None:
    """Papel pela cor de fonte do run (diálogo APA)."""
    rpr = run.find('w:rPr', NS)
    if rpr is None:
        return None
    hx = _hex_de_elemento_cor(rpr.find('w:color', NS))
    return _classificar_cor(hx) if hx else None


def _cor_do_run(run: ET.Element) -> str | None:
    rpr = run.find('w:rPr', NS)
    if rpr is None:
        return None
    return _hex_de_elemento_cor(rpr.find('w:color', NS))


# ============================================================
# LIMPEZA
# ============================================================

_RE_TIMESTAMP = re.compile(r'(?:(?<=^)|(?<=\s))\d{1,2}:\d{2}(?::\d{2})?(?=[\s,]|$)')
_RE_ESPACOS = re.compile(r'[ \t]{2,}')
_RE_PAPEL_LEGENDA = (
    r'(?:CAUSADOR|NEGOCIADOR\s+PRINCIPAL|NEGOCIADOR\s+SECUND[AÁ]RIO|'
    r'(?:1[°º]?|PRIMEIRO)\s*INTERVENTOR|GERENTE|TERCEIRO|V[IÍ]TIMA|'
    r'COMANDANTE(?:\s+DO\s+INCIDENTE)?)'
)
_RE_LEGENDA = re.compile(
    rf'^{_RE_PAPEL_LEGENDA}\s*[=:\-–]\s*.+$',
    re.IGNORECASE,
)
_RE_LEGENDA_INLINE = re.compile(
    rf'{_RE_PAPEL_LEGENDA}\s*[=:\-–]\s*'
    r'(?:AZUL|VERMELHO|VERDE|ROXO|PRETO|LARANJA|AMARELO|CINZA)\b',
    re.IGNORECASE,
)
_RE_LEGENDA_COR_PRIMEIRO = re.compile(
    r'^(?:AZUL|VERMELHO|VERDE|ROXO|PRETO|LARANJA|AMARELO|CINZA)\s*[=:\-–]\s*'
    rf'{_RE_PAPEL_LEGENDA}\b.*$',
    re.IGNORECASE,
)
_RE_INSTRUCAO = re.compile(
    r'(descrever de forma clara|este campo tem como objetivo|'
    r'justificando a classifica[cç][aã]o|modalidade identificada|'
    r'inserir registros fotogr[aá]ficos|a equipe dever[aá] transcrever|'
    r'orienta[cç][oõ]es obrigat[oó]rias|legendas de cores para os interlocutores|'
    r'destaque de t[eé]cnicas|numera[cç][aã]o sequencial|'
    r'autorizado pelo cmt a n[aã]o fazer transcri[cç][aã]o|'
    r'preservar a integridade do conte[uú]do verbalizado|'
    r'identifica[cç][aã]o do equipamento|informar de qual equipamento|'
    r'identificar e nomear os arquivos|utilizar realce de texto|'
    r'trechos inaud[ií]veis devem ser indicados|'
    r'an[aá]lise d\s*as t[eé]cnicas|item\s*34)',
    re.IGNORECASE,
)
_FRAGMENTOS = {
    'verde', 'azul', 'vermelho', 'roxo', 'amarelo', 'laranja', 'preto', 'cinza',
    'verde:', 'azul:', 'vermelho:', 'roxo:', 'amarelo:', 'laranja:', 'preto:', 'cinza:',
    ',', '–', '-', 'vídeo', 'video', 'áudio', 'audio', 'descrição', 'descricao',
    'negociador principal', 'negociador secundário', 'negociador secundario',
    'causador', 'primeiro interventor', '1º interventor', '1° interventor',
    'gerente', 'terceiro', 'terceiros', 'vítima', 'vitima',
    'comandante', 'comandante do incidente',
    'obs', 'obs.', 'la ranja', 'laranja vítima', 'laranja vitima',
}


def _limpar(texto: str) -> str:
    """Remove timestamps, legendas de cor e fragmentos que não são diálogo."""
    texto = _RE_TIMESTAMP.sub('', texto or '')
    texto = _RE_LEGENDA_INLINE.sub('', texto)
    texto = _RE_ESPACOS.sub(' ', texto).strip(' \t-–_|:')
    if not texto:
        return ''
    low = texto.lower().strip()
    if low in _FRAGMENTOS:
        return ''
    if _RE_LEGENDA.match(texto):
        return ''
    if _RE_LEGENDA_COR_PRIMEIRO.match(texto):
        return ''
    if _RE_INSTRUCAO.search(texto):
        return ''
    if re.match(r'^[–\-_]{3,}$', texto):
        return ''
    if re.match(r'^(?:v[ií]deo|áudio|audio)\s*\d+\s*$', low):
        return ''
    # Só underscore / placeholder de seção vazia
    if re.fullmatch(r'[_.\s]+', texto):
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


def _linhas_diretas(tbl: ET.Element) -> list:
    """Linhas diretas da tabela (ignora tabelas aninhadas)."""
    rows = tbl.findall('./w:tr', NS)
    return rows if rows else tbl.findall('w:tr', NS)


def _texto_celula_sem_aninhada(cell: ET.Element) -> str:
    """Texto da célula excluindo conteúdo de tabelas aninhadas."""
    nested_t = set()
    for nested in cell.findall('.//w:tbl', NS):
        for t in nested.findall('.//w:t', NS):
            nested_t.add(t)
    partes = []
    for t in cell.findall('.//w:t', NS):
        if t not in nested_t and t.text:
            partes.append(t.text)
    return ''.join(partes)


def _texto_linha_direta(row: ET.Element) -> str:
    """Texto da linha sem descer em tabelas aninhadas."""
    cells = row.findall('./w:tc', NS) or row.findall('w:tc', NS)
    return ''.join(_texto_celula_sem_aninhada(c) for c in cells)


def _linhas_cabecalho(tbl: ET.Element, max_linhas: int = 5) -> list[str]:
    """Cabeçalho só com linhas diretas — evita misturar Transcrição com Técnicas aninhadas."""
    linhas = []
    for row in _linhas_diretas(tbl)[:max_linhas]:
        linhas.append(_normalizar_texto(_texto_linha_direta(row)))
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
    Localiza a seção de diálogo: 'NN - TRANSCRIÇÃO' / 'TRANSCRIÇÃO INTEGRAL'.

    Usa só linhas diretas (não mistura com tabela de Técnicas aninhada).
    Nunca retorna a tabela de análise de técnicas.
    """
    re_titulo = re.compile(
        r'(?:^|\b)\d{0,3}\s*[-–.]?\s*TRANSCRICAO(?:\s+INTEGRAL)?'
    )
    candidatos = []

    for idx, tbl in enumerate(tabelas):
        # Só as primeiras linhas curtas = título (o corpo do diálogo é enorme e
        # pode citar "análise das técnicas" no rodapé de instruções).
        linhas_brutas = _linhas_cabecalho(tbl, max_linhas=4)
        titulos = [l for l in linhas_brutas if len(l) <= 160]
        if not titulos:
            continue

        cab_titulo = ' | '.join(titulos)
        if 'ANALISE DAS TECNICAS' in cab_titulo:
            continue
        if 'TECNICAS' in cab_titulo and 'TEMPO' in cab_titulo and 'ATITUDE' in cab_titulo:
            continue

        melhor_score = 0
        for linha in titulos:
            if 'TRANSCRICAO' not in linha:
                continue
            if 'TRECHO DA TRANSCRICAO' in linha and 'INTEGRAL' not in linha:
                continue

            score = 0
            if re_titulo.search(linha):
                score += 5
            if 'INTEGRAL' in linha:
                score += 3
            if 'VIDEOS' in linha or 'AUDIOS' in linha:
                score += 1
            if len(linha) < 100:
                score += 1
            melhor_score = max(melhor_score, score)

        if melhor_score > 0:
            candidatos.append((melhor_score, idx, tbl))

    if not candidatos:
        return None
    candidatos.sort(key=lambda x: (-x[0], x[1]))
    return candidatos[0][2]


# ============================================================
# EXTRAÇÃO DAS TRANSCRIÇÕES
# ============================================================

def _paragrafos_sem_tabela_aninhada(cell: ET.Element) -> list:
    """Parágrafos da célula que não estão dentro de tabela aninhada."""
    nested_paras = set()
    for nested in cell.findall('.//w:tbl', NS):
        for p in nested.findall('.//w:p', NS):
            nested_paras.add(p)
    return [p for p in cell.findall('.//w:p', NS) if p not in nested_paras]


def _extrair_transcricoes(tbl: ET.Element) -> dict:
    """
    Extrai só o diálogo colorido da seção Transcrição.
    Vermelho=causador, azul/ciano=negociador principal, verde=secundário.
    Remove timestamps (00:00) e legendas; ignora tabelas aninhadas (técnicas).
    """
    falas = {
        'causador': [],
        'negociador_principal': [],
        'negociador_secundario': [],
        'primeiro_interventor': [],
    }

    for row in _linhas_diretas(tbl):
        linha_bruta = _texto_linha_direta(row)
        linha_texto = _normalizar_texto(linha_bruta)
        # Pula só linhas de título curtas (o corpo do diálogo é longo e pode
        # mencionar "análise das técnicas" no rodapé de instruções).
        if len(linha_texto) <= 160:
            if 'TRANSCRICAO' in linha_texto or linha_texto.strip() in {'PARTE 2', 'PARTE2'}:
                continue
            if 'ANALISE DAS TECNICAS' in linha_texto:
                continue
            if 'TECNICAS' in linha_texto and 'TEMPO' in linha_texto:
                continue

        for cell in row.findall('./w:tc', NS) or row.findall('w:tc', NS):
            papel_atual = None
            for para in _paragrafos_sem_tabela_aninhada(cell):
                for run in para.findall('./w:r', NS) or para.findall('.//w:r', NS):
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
    """Pontua só se o cabeçalho direto indicar a tabela de técnicas."""
    score = 0
    for linha in _linhas_cabecalho(tbl, max_linhas=6):
        if 'ANALISE DAS TECNICAS' in linha or 'TECNICAS DE NEGOCIACAO' in linha:
            score += 8
        if 'TECNICAS' in linha and ('TEMPO' in linha or 'VIDEO' in linha):
            score += 6
        if 'TECNICAS' in linha and 'TRECHO' in linha:
            score += 4
        if 'TECNICAS' in linha and 'ATITUDE' in linha:
            score += 3
        if 'EXPLICACAO SOBRE A UTILIZACAO' in linha:
            score += 2
        # Evita tabela de Transcrição / outras seções
        if 'TRANSCRICAO INTEGRAL' in linha:
            score -= 20
        if 'MODALIDADE DO INCIDENTE' in linha:
            score -= 20
    return score


def _encontrar_tabela_tecnicas(tabelas: list) -> ET.Element | None:
    """
    Localiza a tabela de técnicas (ex.: '34 - ANÁLISE DAS TÉCNICAS...').
    Só aceita tabelas com título/cabeçalho de técnicas — sem fallback aleatório.
    """
    melhores = []
    for idx, tbl in enumerate(tabelas):
        sc = _score_tabela_tecnicas(tbl)
        if sc >= 6:
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
        if tbl is not None and _score_tabela_tecnicas(tbl) >= 6:
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

        # Somente seções corretas — sem varrer o documento atrás de texto azul.
        tbl_trans = _encontrar_tabela_transcricao(tabelas)
        tbl_tec = _encontrar_tabela_tecnicas(tabelas)

        transcricoes = _extrair_transcricoes(tbl_trans) if tbl_trans is not None else {}
        tecnicas = _extrair_tecnicas(tbl_tec) if tbl_tec is not None else pd.DataFrame()

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
