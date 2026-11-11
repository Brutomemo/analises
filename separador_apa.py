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

Limpeza da fala (após juntar o parágrafo):
  - remove horários completos e fragmentados (00 18 35, 00:2 5 40…)
  - remove todos os dígitos
  - remove marcadores em CAIXA ALTA (independente da cor)
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


def _eh_cor_preta(hx: str | None) -> bool:
    """True para preto explícito / quase preto (marcadores de técnica na APA)."""
    if not hx:
        return False
    hx = hx.upper().strip()
    if hx in {'000000', '1A1C1E', '0D0D0D', '212121', 'AUTO'}:
        return True
    try:
        r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
    except (ValueError, IndexError):
        return False
    return r < 45 and g < 45 and b < 45


def _eh_marcador_caixa_alta(texto: str) -> bool:
    """
    Marcadores de técnica / seção em CAIXA ALTA
    (ex.: PERGUNTAS ABERTAS, VIDEO 1 PRINCIPAL, INTRODUÇÃO DE ASSUNTO).
    """
    t = (texto or '').strip().strip('()[]{}')
    if len(t) < 3:
        return False
    letras = [c for c in t if c.isalpha()]
    if len(letras) < 3:
        return False
    maius = sum(1 for c in letras if c.isupper())
    return (maius / len(letras)) >= 0.85


# ============================================================
# LIMPEZA
# ============================================================

# Horário completo (ainda usado na detecção de linha e limpeza preliminar).
_RE_TIMESTAMP = re.compile(
    r'(?:(?<=^)|(?<=\s)|(?<=\n))\d{1,2}:\d{2}(?::\d{2})?(?=\s|[A-Za-zÀ-ÿ,.!?;:\)]|$)'
)
_RE_TIMESTAMP_QUALQUER = re.compile(r'\b\d{1,2}:\d{2}(?::\d{2})?\b')
# Horário quebrado pelo Word em vários runs: "00 18 35", "00:2 5 40", "00 17 4 3"
_RE_TIMESTAMP_QUEBRADO = re.compile(
    r'(?:(?<=^)|(?<=\s))'
    r'\d{1,2}(?:\s*[:.]?\s*\d{1,2}){1,4}'
    r'(?=\s|[A-Za-zÀ-ÿ,.!?;:]|$)'
)
_RE_DIGITOS = re.compile(r'\d+')
_RE_DOIS_PONTOS_SOLTOS = re.compile(r'\s*:\s*')
_RE_ESPACOS = re.compile(r'[ \t]{2,}')
# Marcadores em CAIXA ALTA (técnica/seção) — independente da cor do run
_RE_CAIXA_ALTA_BLOCO = re.compile(
    r'(?<![A-Za-zÀ-ÿ])'
    r'[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{3,}'
    r'(?:\s+(?:\d+|[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,})){0,10}'
    r'(?![A-Za-zÀ-ÿ])'
)
_RE_MARCADORES_CONHECIDOS = re.compile(
    r'\b(?:'
    r'PERGUNTAS?\s+ABERTAS?|'
    r'PERGUNTAS?\s+FECHADAS?|'
    r'DESCONSTRU[CÇ][AÃ]O|'
    r'INTRODU[CÇ][AÃ]O\s+DE\s+ASSUNTO|'
    r'PRIMAZIA(?:\s+POR\s+TERCEIROS)?|'
    r'V[IÍ]DEO\s+\d+\s+PRINCIPAL|'
    r'PAUSA'
    r')\b',
    re.IGNORECASE,
)
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


def _texto_run_para_buffer(texto: str) -> str:
    """
    Texto bruto do run para o buffer do interlocutor.
    Não limpa horário aqui (evita deixar pedaços '00' / '18'); a limpeza é no parágrafo juntado.
    """
    texto = (texto or '').strip()
    if not texto:
        return ''
    # CAIXA ALTA = marcador de técnica/seção — ignora independente da cor
    if _eh_marcador_caixa_alta(texto):
        return ''
    if _RE_MARCADORES_CONHECIDOS.fullmatch(texto.strip('()[]{}')):
        return ''
    texto = _RE_LEGENDA_INLINE.sub('', texto)
    if not texto.strip():
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
    if re.fullmatch(r'[_.\s]+', texto):
        return ''
    return texto


def _limpar(texto: str) -> str:
    """Compat: limpeza leve de um trecho isolado (legendas/marcadores)."""
    return _texto_run_para_buffer(texto)


def _limpar_transcricao_final(texto: str) -> str:
    """
    Limpeza no texto JÁ JUNTADO do interlocutor:
      1) horários completos e quebrados
      2) todos os dígitos (contorna runs fatiados do Word)
      3) marcadores em CAIXA ALTA (sem depender de cor)
    """
    texto = texto or ''
    texto = _RE_MARCADORES_CONHECIDOS.sub('', texto)
    texto = _RE_CAIXA_ALTA_BLOCO.sub('', texto)
    texto = _RE_TIMESTAMP.sub('', texto)
    texto = _RE_TIMESTAMP_QUALQUER.sub('', texto)
    texto = _RE_TIMESTAMP_QUEBRADO.sub('', texto)
    # Garante remoção de qualquer número remanescente (00, 18, 4.826, etc.)
    texto = _RE_DIGITOS.sub('', texto)
    # Dois-pontos sobrados de horário viram espaço
    texto = _RE_DOIS_PONTOS_SOLTOS.sub(' ', texto)
    texto = _RE_ESPACOS.sub(' ', texto).strip(' \t-–_|:,.')
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


def _titulo_e_secao_transcricao(linha: str) -> int:
    """
    Pontua título de seção de diálogo.
    Aceita:
      - 'NN - TRANSCRIÇÃO INTEGRAL DE VÍDEOS E ÁUDIOS'
      - 'NN - TRANSCRIÇÃO' / 'TRANSCRIÇÃO'
    Recusa coluna 'TRECHO DA TRANSCRIÇÃO' e tabela de técnicas.
    """
    if not linha or len(linha) > 160:
        return 0
    if 'TRECHO DA TRANSCRICAO' in linha:
        return 0
    if 'ANALISE DAS TECNICAS' in linha:
        return 0
    if 'TECNICAS' in linha and ('TEMPO' in linha or 'ATITUDE' in linha):
        return 0

    # Título completo preferencial
    if re.search(r'TRANSCRICAO\s+INTEGRAL(?:\s+DE\s+VIDEOS(?:\s+E\s+AUDIOS)?)?', linha):
        return 20
    # Título curto: opcional "NN - " + TRANSCRICAO (fim da linha ou só isso)
    if re.search(r'(?:^|\b)\d{0,3}\s*[-–.]?\s*TRANSCRICAO\s*$', linha):
        return 12
    if re.search(r'(?:^|\b)\d{0,3}\s*[-–.]?\s*TRANSCRICAO\b', linha) and 'INTEGRAL' not in linha:
        # Ex.: "35 – TRANSCRICAO" com pouco texto extra
        if len(linha) <= 40:
            return 10
    return 0


def _encontrar_tabela_transcricao(tabelas: list) -> ET.Element | None:
    """
    Localiza somente o bloco de diálogo:
    'TRANSCRIÇÃO INTEGRAL DE VÍDEOS E ÁUDIOS' ou título 'TRANSCRIÇÃO'.
    Nunca usa texto azul de outras seções (Modalidade, etc.).
    """
    candidatos = []
    for idx, tbl in enumerate(tabelas):
        linhas_brutas = _linhas_cabecalho(tbl, max_linhas=4)
        titulos = [l for l in linhas_brutas if len(l) <= 160]
        melhor = 0
        for linha in titulos:
            melhor = max(melhor, _titulo_e_secao_transcricao(linha))
        if melhor > 0:
            candidatos.append((melhor, idx, tbl))

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


def _texto_paragrafo(para: ET.Element) -> str:
    return ''.join(t.text or '' for t in para.findall('.//w:t', NS))


def _paragrafo_tem_fala_com_horario(texto: str) -> bool:
    """True só se houver horário de diálogo (00:00 ...) seguido de fala."""
    if not texto or not texto.strip():
        return False
    if _RE_INSTRUCAO.search(texto):
        return False
    # Precisa de pelo menos um HH:MM seguido de conteúdo de fala
    for m in re.finditer(r'\d{1,2}:\d{2}(?::\d{2})?', texto):
        depois = texto[m.end():].strip()
        # Ignora "PAUSA" / marcadores sem fala real imediata vazia
        if not depois:
            continue
        # Exige letra (diálogo), não só pontuação
        if re.search(r'[A-Za-zÀ-ÿ]', depois):
            return True
    return False


def _extrair_fala_do_paragrafo(para: ET.Element, falas: dict) -> None:
    """
    Extrai interlocutores coloridos de um parágrafo que já é linha de diálogo.

    Fluxo:
      1) classifica por cor (algoritmo existente)
      2) ignora preto e CAIXA ALTA (marcadores), independente da cor
      3) junta o texto do parágrafo por interlocutor
      4) limpa horário/números/CAIXA ALTA só no texto juntado
    """
    papel_atual = None
    buffer = {k: [] for k in falas}

    for run in para.findall('./w:r', NS) or para.findall('.//w:r', NS):
        texto = ''.join(t.text or '' for t in run.findall('w:t', NS))
        if not texto:
            continue

        hx = _cor_do_run(run)
        papel = _papel_do_run(run)

        # Preto: marcador/técnica — não entra e não altera o papel atual
        if _eh_cor_preta(hx):
            continue

        # CAIXA ALTA = marcador (mesmo se herdou azul/vermelho)
        if _eh_marcador_caixa_alta(texto):
            continue

        if papel:
            papel_atual = papel

        if not papel_atual or papel_atual not in falas:
            continue

        bruto = _texto_run_para_buffer(texto)
        if bruto:
            buffer[papel_atual].append(bruto)

    for papel, partes in buffer.items():
        if not partes:
            continue
        # Junta primeiro; só então remove horários fatiados / dígitos / CAIXA ALTA
        junto = _limpar_transcricao_final(_RE_ESPACOS.sub(' ', ' '.join(partes)).strip())
        if junto:
            falas[papel].append(junto)


def _extrair_transcricoes(tbl: ET.Element) -> dict:
    """
    Extrai somente diálogos da seção Transcrição / Transcrição Integral.

    Regras:
      - bloco certo (título TRANSCRIÇÃO ou TRANSCRIÇÃO INTEGRAL...)
      - só falas com registro de hora (ex.: '00:00 Oi Arthur...') — a hora só detecta a linha
      - classifica por cor (vermelho/azul-ciano/verde)
      - no texto juntado: remove horários/números e marcadores em CAIXA ALTA
      - não pega texto azul de outras seções nem legendas/instruções
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
        if len(linha_texto) <= 160:
            if _titulo_e_secao_transcricao(linha_texto) > 0:
                continue
            if linha_texto.strip() in {'PARTE 2', 'PARTE2'}:
                continue
            if 'ANALISE DAS TECNICAS' in linha_texto:
                continue
            if 'TECNICAS' in linha_texto and 'TEMPO' in linha_texto:
                continue

        for cell in row.findall('./w:tc', NS) or row.findall('w:tc', NS):
            for para in _paragrafos_sem_tabela_aninhada(cell):
                texto_para = _texto_paragrafo(para)
                if not _paragrafo_tem_fala_com_horario(texto_para):
                    continue
                _extrair_fala_do_paragrafo(para, falas)

    return {
        papel: _limpar_transcricao_final(' '.join(linhas))
        for papel, linhas in falas.items()
    }


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

    # Aviso se nada foi extraído
    total_palavras = sum(len(trans.get(c, '').split()) for c in tabs_chaves)
    if total_palavras == 0:
        st.warning(
            "⚠️ Nenhuma transcrição foi extraída. "
            "Verifique se o arquivo contém texto colorido conforme o padrão da APA."
        )
