import re
import unicodedata
from bisect import bisect_right

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import chi2_contingency, spearmanr
from sklearn.feature_extraction.text import CountVectorizer
from wordcloud import WordCloud
from sklearn.metrics.pairwise import cosine_similarity

# ============================================================
# 1. STOPWORDS E CONFIGURAÇÕES GERAIS
# ============================================================

STOPWORDS_GATE = {
    "o", "a", "os", "as", "um", "uma", "de", "do", "da", "em", "no", "na", "nos", "nas",
    "para", "com", "por", "que", "se", "e", "ou", "mas", "como", "ao", "aos", "dos", "das",
    "é", "foi", "ser", "ter", "estar", "fazer", "houve", "isso", "esse", "essa", "aquele",
    "aquela", "ele", "ela", "eles", "elas", "eu", "voce", "você", "vocês", "voces", "nos", "nós", "me", "te",
    "lhe", "minha", "meu", "seu", "sua", "dele", "dela", "daqui", "aqui", "ali", "la", "lá",
    "ja", "já", "so", "só", "mais", "muito", "pouco", "bem", "bom", "entao", "então", "agora",
    "quando", "onde", "quem", "qual", "porque", "pra", "pro", "ta", "tá", "to", "tô", "vai",
    "vou", "tem", "tudo", "nada", "coisa", "ai", "aí", "ne", "né", "acho", "gente", "dá",
    "causador", "negociador", "principal", "secundario", "secundário", "lider", "líder",
    "equipe", "ocorrencia", "ocorrência", "incidente", "forma",  "mano", "manow", "meu", "meu filho",
    "cara", "parça", "bixo", "porra", "tipo", "tipo assim", "tipo ó", "saca", "saquei", "entende", "tá ligado",
    "fica", "calma", "tranquilo", "relaxa", "né", "fico", "tá", "ta", "tô", "to", "cara", "parça", "tipo assim", 
}

NEGADORES = {
    "nao", "não", "nunca", "jamais", "nem", "sem"
}

INTENSIFICADORES = {
    "muito", "demais", "mesmo", "realmente", "totalmente", "de verdade", "pra caramba",
    "agora", "ja", "já", "urgente", "logo"
}

ATENUADORES = {
    "talvez", "acho", "um pouco", "mais ou menos", "quase"
}

# ============================================================
# 2. DICIONÁRIO OPERACIONAL (MANTIDO IDÊNTICO)
# ============================================================

DICIONARIO_OPERACIONAL = {
    "Sinalização de Rendição / Desescalada da agressividade": {
        "tipo": "progressão",
        "peso_base": 1.60,
        "termos": {
            "me entrego": 2.80,
            "vou me entregar": 2.80,
            "pode entrar": 2.20,
            "pode subir": 2.20,
            "vou sair": 2.20,
            "estou saindo": 2.10,
            "to saindo": 2.10,
            "vou abrir": 2.00,
            "porta aberta": 2.00,
            "larga a arma": 2.40,
            "vou largar": 2.30,
            "larguei": 2.10,
            "calma": 1.10,
            "tranquilo": 1.20,
            "concordo": 1.60,
            "ta bom": 1.00,
            "tudo bem": 1.30,
            "beleza": 1.10,
            "acabou": 0.30,
            "nao vou fazer": 1.90,
            "desisto disso": 0.30,
            "vou descer": 2.00,
            "estou descendo": 2.00
        }
    },
    "Tentativa de Estabelecimento de Contato": {
        "tipo": "protecao",
        "peso_base": 1.15,
        "termos": {
            "fala comigo": 0.30,
            "conversa comigo": 0.30,
            "me escuta": 1.00,
            "me ouve": 1.00,
            "eu te escuto": 1.80,
            "to te ouvindo": 1.90,
            "estou te ouvindo": 1.90,
            "to aqui": 1.40,
            "estou aqui": 1.40,
            "confia em mim": 1.90,
            "quero te ajudar": 2.00,
            "posso te ajudar": 1.90,
            "vamos conversar": 1.60,
            "conversa": 1.00,
            "escuta": 0.95,
            "ouve": 0.95,
            "ajuda": 1.10,
            "ajudar": 1.10,
            "fala": 0.80,
            "falar": 0.80
        }
    },
    "Vínculos Familiares e Afetivos": {
        "tipo": "protecao",
        "peso_base": 1.10,
        "termos": {
            "mae": 1.50,
            "pai": 1.40,
            "filho": 1.70,
            "filha": 1.70,
            "filhos": 1.80,
            "familia": 1.70,
            "irmao": 1.30,
            "irmão": 1.30,
            "irma": 1.30,
            "esposa": 1.40,
            "noiva": 1.30,
            "noivo": 1.30,
            "mulher": 1.00,
            "marido": 1.20,
            "namorada": 1.20,
            "parente": 1.00
        }
    },
    "Ganchos Morais e Espirituais": {
        "tipo": "protecao",
        "peso_base": 0.95,
        "termos": {
            "deus": 1.60,
            "jesus": 1.50,
            "igreja": 1.20,
            "pastor": 1.20,
            "fe": 1.40,
            "orar": 1.30,
            "rezar": 1.30,
            "perdao": 1.20,
            "pecado": 1.10,
            "biblia": 1.10
        }
    },
    "Ambivalência / Pedido de Ajuda Velado": {
        "tipo": "protecao",
        "peso_base": 1.00,
        "termos": {
            "me ajuda": 2.20,
            "quero ajuda": 2.00,
            "preciso de ajuda": 2.00,
            "me salva": 2.10,
            "socorro": 1.80,
            "nao sei": 1.20,
            "estou cansado": 1.50,
            "to cansado": 1.50,
            "nao aguento mais": 1.80,
            "eu nao queria": 1.50,
            "nao era pra isso": 1.60,
            "nao quero problema": 1.70,
            "me tira disso": 1.90,
            "quero sair disso": 1.90
        }
    },
    "Fatores Socioeconômicos / Frustração": {
        "tipo": "contexto",
        "peso_base": 0.90,
        "termos": {
            "divida": 1.50,
            "dinheiro": 1.20,
            "desempregado": 1.50,
            "emprego": 1.20,
            "trabalho": 1.10,
            "conta": 1.00,
            "pagar": 1.00,
            "perdi tudo": 1.80,
            "injustica": 1.30,
            "traicao": 1.30,
            "patrao": 1.00,
            "roubo": 1.10,
            "acidente": 1.00
        }
    },
    "Ideação Suicida / Desesperança (Pensamento Suicida Declarado)": {
        "tipo": "risco",
        "peso_base": 1.70,
        "termos": {
            "vou me matar": 3.20,
            "quero morrer": 3.00,
            "nao quero viver": 2.80,
            "vou pular": 3.10,
            "acabou pra mim": 3.10,
            "chega, não da mais": 2.80,           
            "acabar com tudo": 2.70,
            "dar fim": 2.50,
            "me matar": 2.70,
            "morrer": 1.80,
            "sem saida": 2.00,
            "cansei de viver": 2.60,
            "desisto da vida": 2.60,
            "minha vida acabou": 2.30,
            "sofrimento": 1.30,
            "dor": 1.10
        }
    },
            "Sinais de Despedida / Comportamento Terminal Iminente": {
            "tipo": "risco",
            "peso_base": 3.80,  # PESO MÁXIMO - crítico!
            "termos": {
                "quero falar com": 3.20,
                "preciso falar com": 3.20,
                "última vez": 3.50,
                "despedir de": 3.40,
                "antes disso": 3.30,
                "antes de fazer": 1.80,
                "antes de partir": 3.60,
                "quando trouxer": 1.20,
                "se trazer": 1.10,
                "uma última": 3.50,
                "me despeço": 3.60,
                "deixa eu falar com": 2.90,
                "preciso ver minha/meu": 2.10,
                "uma última conversa": 3.50,
                "fechar assuntos": 1.20
            }
        },

    "Risco à Integridade / Hostilidade (Crise Externa)": {
        "tipo": "risco",
        "peso_base": 1.80,
        "termos": {
            "vou matar": 3.10,
            "mato": 2.40,
            "tiro": 2.10,
            "atirar": 2.30,
            "arma": 1.20,
            "faca": 1.20,
            "sangue": 1.60,
            "não aguento mais": 1.60,
            "refem": 1.40,
            "bala": 1.90,
            "explodir": 2.70,
            "explode": 2.60,
            "ninguem entra": 2.40,
            "afasta": 1.80,
            "se chegar perto": 2.80,
            "chegar perto": 2.00,
            "policia": 1.20,
            "hostil": 1.90,
            "agressivo": 1.70,
            "destruir": 1.80
        }
    },
    "Demandas e Exigências (Instrumentais)": {
        "tipo": "risco",
        "peso_base": 0.95,
        "termos": {
            "exijo": 2.10,
            "quero": 1.00,
            "traz": 1.10,
            "chama": 1.00,
            "cade": 1.00,
            "advogado": 1.30,
            "imprensa": 1.40,
            "reportagem": 1.20,
            "carro": 1.30,
            "fuga": 1.70,
            "agua": 0.90,
            "comida": 0.90,
            "cigarro": 0.90,
            "dinheiro pra fugir": 1.80,
            "quero falar com": 1.10
        }
    }
}

# ============================================================
# 3. FUNÇÕES AUXILIARES
# ============================================================

def normalizar_texto(texto):
    if not texto or not isinstance(texto, str):
        return ""
    
    try:
        texto = unicodedata.normalize("NFD", texto)
        texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
        texto = re.sub(r"\s+", " ", texto.lower().strip())
        return texto
    except Exception:
        return ""

def limpar_texto(texto):
    return normalizar_texto(texto)

def limpar_valor(valor):
    if pd.isna(valor) or valor in [None, "nan", "NaN", "N/D", "n/d", ""]:
        return ""
    return str(valor).strip()

def gerar_wordcloud(texto):
    texto_limpo = limpar_texto(texto)
    if not texto_limpo or len(texto_limpo) < 10:
        return None
    
    try:
        palavras = [p for p in texto_limpo.split() if p not in STOPWORDS_GATE and len(p) > 2]
        if len(palavras) < 5:
            return None
        
        wc = WordCloud(
            width=400,
            height=300,
            background_color="#0a0a0a",
            colormap="hot",
            relative_scaling=0.5,
            min_font_size=10
        ).generate(" ".join(palavras))
        
        fig, ax = plt.subplots(figsize=(8, 6), facecolor="#0a0a0a")
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        return fig
    except Exception:
        return None

# ============================================================
# 4. WORDCLOUD
# ============================================================

# em analise.py
import matplotlib.pyplot as plt
from wordcloud import WordCloud

def gerar_wordcloud(texto):
    if not texto or len(texto.strip()) < 5:
        return None

    wc = WordCloud(
        width=1600,
        height=800,
        background_color="black",
        colormap="Oranges",
        stopwords=STOPWORDS_GATE
    ).generate(texto)

    fig, ax = plt.subplots(figsize=(16, 8))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    fig.tight_layout()

    return fig

# ============================================================
# 4. MOTOR DIRECIONAL MELHORADO (Interpretação APA)
# ============================================================
def deve_mostrar_metricas_apa(nome_aba):
    """Mostra métricas APA apenas em abas específicas"""
    abas_com_metricas = [
        "✔️ Convergência Temática",
        "✔️ Estado da Crise"
    ]
    return nome_aba in abas_com_metricas

def _obter_tokens_e_posicoes(texto_norm):
    matches = list(re.finditer(r"\b\w+\b", texto_norm))
    tokens = [m.group(0) for m in matches]
    starts = [m.start() for m in matches]
    return tokens, starts

def _indice_token_por_char(starts, char_pos):
    return max(0, bisect_right(starts, char_pos) - 1)

def _avaliar_modificadores(tokens, idx_inicio, idx_fim):
    janela_pre = tokens[max(0, idx_inicio - 4):idx_inicio]
    janela_pos = tokens[idx_fim:min(len(tokens), idx_fim + 2)]
    janela_total = janela_pre + janela_pos

    negado = any(tok in NEGADORES for tok in janela_pre[-3:] + janela_pos[:1])

    intensificador = 1.0
    if any(tok in INTENSIFICADORES for tok in janela_total):
        intensificador *= 1.25
    if any(tok in ATENUADORES for tok in janela_total):
        intensificador *= 0.85

    return negado, intensificador

def _clamp(valor, minimo=0.0, maximo=100.0):
    return max(minimo, min(maximo, float(valor or 0)))


def _confianca_amostral(tokens_validos, vocabulario_unico):
    """
    Confiança simples da análise textual.
    Evita dar aparência de precisão para transcrições curtas/repetitivas.
    """
    if tokens_validos <= 0:
        return 0.0

    fator_volume = min(1.0, tokens_validos / 120)
    fator_diversidade = min(1.0, vocabulario_unico / 45)

    return round((0.65 * fator_volume) + (0.35 * fator_diversidade), 2)


def _normalizar_score_percentual(score_bruto, total_tokens, carga_maxima_esperada=100):
    """
    Normaliza score bruto combinando carga absoluta e densidade textual.
    Mantém compatibilidade com o modelo antigo, mas reduz distorções por corpus longo/curto.
    """
    if total_tokens <= 0:
        return 0.0

    carga_absoluta = (score_bruto / carga_maxima_esperada) * 100
    densidade_100_tokens = (score_bruto / total_tokens) * 100

    score = (0.55 * carga_absoluta) + (0.45 * densidade_100_tokens)

    return round(_clamp(score, 0, 100), 2)

VOCATIVOS_BASE = set([
    'fala', 'fale', 'fala comigo', 'escuta', 'oi', 'alô', 'alo', 'vem', 'venha',
])

def eh_vocativo(tokens, idx_inicio, idx_fim, repeticao_threshold=3):
    span = tokens[idx_inicio:idx_fim]
    if not span:
        return False

    texto_span = " ".join(span)

    if texto_span in VOCATIVOS_BASE:
        return True

    if any(tok in VOCATIVOS_BASE for tok in span):
        return True

    token0 = span[0]
    janela = tokens[max(0, idx_inicio - 6): min(len(tokens), idx_fim + 6)]

    if janela.count(token0) >= repeticao_threshold and len(span) == 1:
        return True

    if idx_inicio > 0 and tokens[idx_inicio - 1] == token0:
        return True

    if idx_fim < len(tokens) and tokens[idx_fim] == token0:
        return True

    return False

def _eh_resolucao_intervencao(resolucao_tipo):
    resolucao_norm = str(resolucao_tipo or "").strip().lower()
    return (
        resolucao_norm in {"nao_negociacao", "não negociação"}
        or "interven" in resolucao_norm
    )

def analisar_crise_direcional(texto, resolucao_tipo="desconhecida"):
    """
    Motor de análise semântica direcional.
    Retorna vetores de Risco, Proteção e Contexto com interpretação para APA.
    """
    carga_maxima_esperada = 100
    houve_intervencao = _eh_resolucao_intervencao(resolucao_tipo)

    texto_norm = normalizar_texto(texto)
    if not texto_norm:
        return {
            "temas": [],
            "sumario": {
                "tokens_validos": 0,
                "risco_bruto": 0.0,
                "protecao_bruto": 0.0,
                "contexto_bruto": 0.0,
                "risco_observado": 0.0,
                "abertura_observada": 0.0,
                "raiz_observada": 0.0,
                "intensidade_index": 0.0,
                "direcao_index": 0.0,
                "volatilidade_index": 0.0,
                "vocabulario_unico": vocabulario_unico,
                "confianca_amostral": confianca_amostral,
                "classificacao": "HOUVE INTERVENÇÃO" if houve_intervencao else "SEM DADOS",
                "leitura": (
                    "Ocorrência resolvida por intervenção. Não há corpus verbal suficiente para medir desescalada conversacional."
                    if houve_intervencao
                    else "Texto insuficiente para análise."
                )
            }
        }

    tokens, starts = _obter_tokens_e_posicoes(texto_norm)
    tokens_validos = [t for t in tokens if len(t) > 1 and t not in STOPWORDS_GATE]
    total_tokens = len(tokens_validos)
    vocabulario_unico = len(set(tokens_validos))
    confianca_amostral = _confianca_amostral(total_tokens, vocabulario_unico)

    if total_tokens < 20 or vocabulario_unico < 8:
        return {
            "temas": [],
            "sumario": {
                "tokens_validos": total_tokens,
                "risco_bruto": 0.0,
                "protecao_bruto": 0.0,
                "contexto_bruto": 0.0,
                "risco_observado": 0.0,
                "abertura_observada": 0.0,
                "raiz_observada": 0.0,
                "intensidade_index": 0.0,
                "direcao_index": 0.0,
                "volatilidade_index": 0.0,
                "classificacao": "HOUVE INTERVENÇÃO" if houve_intervencao else "DADOS INSUFICIENTES",
                "confianca_amostral": confianca_amostral,
                "vocabulario_unico": vocabulario_unico,
                "leitura": (
                    "Ocorrência resolvida por intervenção. Corpus verbal curto; os indicadores linguísticos devem ser lidos apenas como apoio contextual."
                    if houve_intervencao
                    else "Corpus insuficiente para análise confiável."
                )
            }
        }

    resultados = []
    risco_bruto = 0.0
    protecao_bruto = 0.0
    contexto_bruto = 0.0

    for categoria, cfg in DICIONARIO_OPERACIONAL.items():
        tipo = cfg["tipo"]
        peso_base = cfg["peso_base"]
        termos = cfg["termos"]

        score_categoria = 0.0
        evidencias = 0
        evidencias_negadas = 0

        for termo, peso_termo in termos.items():
            padrao = rf"\b{re.escape(termo)}\b"
            for match in re.finditer(padrao, texto_norm):
                idx_inicio = _indice_token_por_char(starts, match.start())
                qtd_tokens_termo = len(termo.split())
                idx_fim = idx_inicio + qtd_tokens_termo

                negado, fator_contexto = _avaliar_modificadores(tokens, idx_inicio, idx_fim)
                peso_final = peso_base * peso_termo * fator_contexto
                evidencias += 1

                if eh_vocativo(tokens, idx_inicio, idx_fim):
                    score_categoria += peso_final * 0.12
                    contexto_bruto += peso_final * 0.10
                    continue

                if negado:
                    evidencias_negadas += 1
                    if tipo == "risco":
                        score_categoria += peso_final * 0.18
                        protecao_bruto += peso_final * 0.45
                    elif tipo == "protecao":
                        score_categoria += peso_final * 0.18
                        risco_bruto += peso_final * 0.65
                    else:
                        score_categoria += peso_final * 0.30
                        contexto_bruto += peso_final * 0.20
                else:
                    score_categoria += peso_final
                    if tipo == "risco":
                        risco_bruto += peso_final
                    elif tipo == "protecao":
                        protecao_bruto += peso_final
                    else:
                        contexto_bruto += peso_final

        if evidencias > 0:
            resultados.append({
                "categoria": categoria,
                "tipo": tipo,
                "score": round(score_categoria, 2),
                "evidencias": int(evidencias),
                "evidencias_negadas": int(evidencias_negadas)
            })

    resultados = sorted(resultados, key=lambda x: x["score"], reverse=True)

    # Normalização por densidade textual
    # ✅ CORRETO — todos dividem pela mesma base
    # Normalização híbrida: carga absoluta + densidade por volume textual.
    # Evita que textos longos diluam risco e que textos curtos inflem conclusões.
    risco_observado = _normalizar_score_percentual(
        risco_bruto,
        total_tokens,
        carga_maxima_esperada
    )

    abertura_observada = _normalizar_score_percentual(
        protecao_bruto,
        total_tokens,
        carga_maxima_esperada
    )

    raiz_observada = _normalizar_score_percentual(
        contexto_bruto,
        total_tokens,
        carga_maxima_esperada
    )

    intensidade_index  = round(risco_observado + abertura_observada + (raiz_observada * 0.35), 2)
    direcao_index      = round(abertura_observada - risco_observado, 2)
    volatilidade_index = round(min(risco_observado, abertura_observada), 2)

    classificacao, leitura = classificar_estado_crise_apa(
        risco_observado=risco_observado,
        abertura_observada=abertura_observada,
        raiz_observada=raiz_observada,
        intensidade_index=intensidade_index,
        direcao_index=direcao_index,
        volatilidade_index=volatilidade_index,
        tokens_validos=total_tokens,
        resolucao_tipo=resolucao_tipo
    )

    return {
        "temas": resultados,
        "sumario": {
            "tokens_validos": total_tokens,
            "risco_bruto": round(risco_bruto, 2),
            "protecao_bruto": round(protecao_bruto, 2),
            "contexto_bruto": round(contexto_bruto, 2),
            "risco_observado": risco_observado,
            "abertura_observada": abertura_observada,
            "raiz_observada": raiz_observada,
            "intensidade_index": intensidade_index,
            "direcao_index": direcao_index,
            "volatilidade_index": volatilidade_index,
            "classificacao": classificacao,
            "leitura": leitura
        }
    }

def classificar_estado_crise_apa(
    risco_observado,
    abertura_observada,
    raiz_observada,
    intensidade_index,
    direcao_index,
    volatilidade_index,
    tokens_validos=None,
    resolucao_tipo="desconhecida"
):
    """
    Classificação com interpretação para APA.
    Vetores renomeados: Risco Observado, Abertura Observada, Raiz Observada.
    """
    resolucao_norm = str(resolucao_tipo or "").strip().lower()

    if (
        resolucao_norm in {"nao_negociacao", "não negociação"}
        or "interven" in resolucao_norm
    ):
        return (
            "HOUVE INTERVENÇÃO",
            "Ocorrência resolvida fora da negociação verbal. Requer análise rigorosa da atuação em desescalada."
        )

    if tokens_validos is not None and tokens_validos < 15:
        return (
            "DADOS INSUFICIENTES",
            "Corpus insuficiente para análise confiável."
        )

    if intensidade_index < 4:
        return (
            "BAIXA PRESSÃO",
            "Densidade semântica baixa. Indicador de pouca carga crítica ou registro insuficiente."
        )

    if risco_observado >= 18 and direcao_index <= -6:
        return (
            "CRÍTICO",
            "Predomínio de escalada. Alta concentração de linguagem de ameaça sem contrapeso protetivo."
        )

    if risco_observado >= 12 and abertura_observada >= 10 and abs(direcao_index) < 6:
        return (
            "TRANSIÇÃO INSTÁVEL",
            "Coexistência de risco e desescalada. Incidente em ponto de inflexão com janela de resolução."
        )

    if abertura_observada >= 12 and direcao_index >= 6:
        return (
            "DESACELERAÇÃO DA AGRESSIVIDADE",
            "Predomínio de sinais de cooperação e rendição. Risco perdeu centralidade."
        )

    if abertura_observada >= 8 and risco_observado < 8:
        return (
            "CONTROLADO / COOPERATIVO",
            "Predominam sinais de cooperação e desescalada. Estabilização verbal do incidente."
        )

    if risco_observado >= 10 and direcao_index < 0:
        return (
            "MODERADO COM VIÉS DE ESCALADA",
            "Sinais de deterioração discursiva sem atingir crítico."
        )

    return (
        "AMBIVALENTE / INDETERMINADO",
        "Mistura de sinais. Recomenda-se análise integrada com contexto operacional e timeline."
    )

def gerar_radar_crise_individual(risco, abertura, raiz, volatilidade):
    """Gera radar de crise individual"""
    import plotly.graph_objects as go

    fig = go.Figure(data=go.Scatterpolar(
        r=[risco, abertura, raiz, volatilidade],
        theta=['Risco Observado', 'Abertura Observada', 'Raiz Observada', 'Volatilidade'],
        fill='toself',
        name='Estado da Crise',
        line=dict(color='#ef4444', width=2),
        fillcolor='rgba(239,68,68,0.25)'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max(30, risco * 1.2, abertura * 1.2, raiz * 1.2, volatilidade * 1.2)]),
            bgcolor='rgba(0,0,0,0)'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#fff'),
        height=400
    )

    return fig

#atualização radar convergencia

def gerar_radar_convergencia_tematica_corrigido(temas_causador, temas_negociador, convergencia_por_tema):
    """
    Gera radar com:
    - Eixos = temas compartilhados
    - Duas linhas = causador vs negociador
    - Altura = score (intensidade) de cada tema
    
    Permite comparar visualmente a intensidade de abordagem de cada tema.
    """
    import plotly.graph_objects as go
    
    if not convergencia_por_tema:
        fig = go.Figure()
        fig.add_annotation(
            text="Sem temas compartilhados para gerar radar",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(color="#fff", size=14)
        )
        return fig
    
    # ── Extrair dados ────────────────────────────────────────────
    temas = list(convergencia_por_tema.keys())
    scores_c = [convergencia_por_tema[t]["score_causador"] for t in temas]
    scores_np = [convergencia_por_tema[t]["score_negociador"] for t in temas]
    
    # ── Criar figura com duas traces ─────────────────────────────
    fig = go.Figure()
    
    # Trace 1: Causador (vermelho)
    fig.add_trace(go.Scatterpolar(
        r=scores_c,
        theta=temas,
        fill='toself',
        name='Causador',
        line=dict(color='#ef4444', width=2),
        fillcolor='rgba(239,68,68,0.15)',
        hovertemplate='<b>%{theta}</b><br>Causador: %{r:.2f}<extra></extra>'
    ))
    
    # Trace 2: Negociador (verde)
    fig.add_trace(go.Scatterpolar(
        r=scores_np,
        theta=temas,
        fill='toself',
        name='Negociador',
        line=dict(color='#10b981', width=2),
        fillcolor='rgba(16,185,129,0.15)',
        hovertemplate='<b>%{theta}</b><br>Negociador: %{r:.2f}<extra></extra>'
    ))
    
    # ── Layout ───────────────────────────────────────────────────
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(max(scores_c), max(scores_np)) * 1.1],
                tickfont=dict(color='#aaa', size=10),
                gridcolor='#333',
                linecolor='#666'
            ),
            bgcolor='rgba(0,0,0,0)',
            angularaxis=dict(
                tickfont=dict(color='#FFD700', size=11),
                gridcolor='#333',
                linecolor='#666'
            )
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#fff', size=11),
        legend=dict(
            font=dict(color='#fff', size=12),
            bgcolor='rgba(0,0,0,0.4)',
            bordercolor='#444',
            borderwidth=1
        ),
        margin=dict(t=30, b=30, l=40, r=40),
        height=450,
        hovermode='closest'
    )
    
    return fig


def gerar_grafico_barras_intensidade_temas(convergencia_por_tema):
    """
    Gera gráfico de barras agrupadas mostrando intensidade de cada tema.
    Alternativa ao radar para quem prefere tabular.
    """
    import plotly.graph_objects as go
    
    temas = list(convergencia_por_tema.keys())
    scores_c = [convergencia_por_tema[t]["score_causador"] for t in temas]
    scores_np = [convergencia_por_tema[t]["score_negociador"] for t in temas]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=temas,
        y=scores_c,
        name='Causador',
        marker_color='#ef4444',
        hovertemplate='<b>%{x}</b><br>Causador: %{y:.2f}<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        x=temas,
        y=scores_np,
        name='Negociador',
        marker_color='#10b981',
        hovertemplate='<b>%{x}</b><br>Negociador: %{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        barmode='group',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#fff', size=11),
        legend=dict(
            font=dict(color='#fff', size=12),
            bgcolor='rgba(0,0,0,0.4)',
            bordercolor='#444'
        ),
        xaxis=dict(
            tickfont=dict(color='#FFD700', size=10),
            gridcolor='#333',
            linecolor='#666'
        ),
        yaxis=dict(
            tickfont=dict(color='#aaa', size=10),
            gridcolor='#333',
            linecolor='#666',
            title='Score (Intensidade)'
        ),
        height=400,
        margin=dict(t=20, b=100, l=50, r=30),
        hovermode='closest'
    )
    
    return fig



def gerar_narrativa_crise(risco_observado, abertura_observada, raiz_observada,
                          intensidade_index, direcao_index, volatilidade_index,
                          classificacao, resolucao_tipo="desconhecida"):
    """
    Gera narrativa automática em linguagem simples para leitura por leigos.
    Resposta flexível conforme os valores reais.
    """

    linhas = []

    # ── 1. ABERTURA ──────────────────────────────────────────────────────────
    if classificacao == "SEM DADOS":
        return "⚠️ Sem dados suficientes para análise narrativa."
    if classificacao == "DADOS INSUFICIENTES":
        return "⚠️ Transcrição muito curta. Não é possível gerar narrativa confiável."
    if classificacao == "HOUVE INTERVENÇÃO":
        return ("🚨 Esta ocorrência foi resolvida fora da negociação verbal. "
                "A análise narrativa não se aplica ao modelo de desescalada conversacional.")

    # ── 2. RISCO ─────────────────────────────────────────────────────────────
    if risco_observado >= 60:
        txt_risco = (
            f"🔴 **Risco extremamente elevado ({risco_observado:.1f}%):** "
            "O causador utilizou linguagem predominantemente ameaçadora e hostil durante toda a ocorrência. "
            "A carga de palavras ligadas à violência, morte ou dano foi muito intensa."
        )
    elif risco_observado >= 35:
        txt_risco = (
            f"🔴 **Risco alto ({risco_observado:.1f}%):** "
            "O causador demonstrou linguagem claramente hostil e ameaçadora em grande parte do discurso. "
            "Havia concentração significativa de palavras de perigo e agressão."
        )
    elif risco_observado >= 18:
        txt_risco = (
            f"🟡 **Risco moderado ({risco_observado:.1f}%):** "
            "Havia sinais de hostilidade presentes, mas não dominantes. "
            "O causador alternava entre linguagem agressiva e momentos de menor tensão."
        )
    elif risco_observado >= 8:
        txt_risco = (
            f"🟢 **Risco baixo ({risco_observado:.1f}%):** "
            "Pouca linguagem ameaçadora detectada. "
            "O causador não estava em escalada verbal clara."
        )
    else:
        txt_risco = (
            f"🟢 **Risco muito baixo ({risco_observado:.1f}%):** "
            "Quase nenhuma linguagem hostil detectada no discurso do causador."
        )
    linhas.append(txt_risco)

    # ── 3. ABERTURA ──────────────────────────────────────────────────────────
    if abertura_observada >= 40:
        txt_ab = (
            f"🟢 **Abertura alta ({abertura_observada:.1f}%):** "
            "O causador demonstrou muitos sinais de cooperação, rendição ou disposição para diálogo. "
            "Havia ambivalência — apesar do risco, ele ainda sinalizava saída."
        )
    elif abertura_observada >= 20:
        txt_ab = (
            f"🟡 **Abertura moderada ({abertura_observada:.1f}%):** "
            "Alguns sinais de cooperação foram detectados, mas não suficientes para caracterizar disposição clara para resolução."
        )
    elif abertura_observada >= 8:
        txt_ab = (
            f"🔴 **Abertura baixa ({abertura_observada:.1f}%):** "
            "Poucos sinais de cooperação. O causador estava pouco receptivo ao diálogo neste momento."
        )
    else:
        txt_ab = (
            f"🔴 **Abertura muito baixa ({abertura_observada:.1f}%):** "
            "Praticamente nenhum sinal de cooperação ou rendição detectado."
        )
    linhas.append(txt_ab)

    # ── 4. RAIZ ──────────────────────────────────────────────────────────────
    if raiz_observada >= 40:
        txt_raiz = (
            f"🟡 **Raiz muito presente ({raiz_observada:.1f}%):** "
            "O causador estava fortemente focado na origem do problema — o motivo que o levou à crise. "
            "Isso pode indicar fixação, dificultando avanço na negociação, "
            "mas também revela o ponto central que precisa ser endereçado."
        )
    elif raiz_observada >= 20:
        txt_raiz = (
            f"🟡 **Raiz presente ({raiz_observada:.1f}%):** "
            "O causador mencionou frequentemente os gatilhos e motivos da crise. "
            "Há clareza sobre a origem do conflito."
        )
    elif raiz_observada >= 8:
        txt_raiz = (
            f"🟢 **Raiz moderada ({raiz_observada:.1f}%):** "
            "O causador tocou na origem da crise, mas sem obsessão. "
            "Ponto de entrada para o negociador trabalhar."
        )
    else:
        txt_raiz = (
            f"⚠️ **Raiz pouco articulada ({raiz_observada:.1f}%):** "
            "O causador não verbalizou claramente a origem da crise. "
            "Pode haver dificuldade em identificar o motivo real ou resistência em expressá-lo."
        )
    linhas.append(txt_raiz)

    # ── 5. DIREÇÃO ───────────────────────────────────────────────────────────
    if direcao_index <= -30:
        txt_dir = (
            f"✔️ **Direção: escalada intensa ({direcao_index:.1f}):** "
            "O discurso do causador estava predominantemente em escalada. "
            "A tensão verbal era muito superior aos sinais de cooperação."
        )
    elif direcao_index <= -10:
        txt_dir = (
            f"✔️ **Direção: tendência de escalada ({direcao_index:.1f}):** "
            "Havia mais hostilidade do que cooperação, indicando que a crise ainda estava em curso."
        )
    elif direcao_index <= 0:
        txt_dir = (
            f"✔️ **Direção: levemente negativa ({direcao_index:.1f}):** "
            "Crise no limiar — risco e abertura quase empatados, com leve predomínio de tensão."
        )
    elif direcao_index <= 10:
        txt_dir = (
            f"✔️ **Direção: leve desescalada ({direcao_index:.1f}):** "
            "Sinais de cooperação ligeiramente superiores ao risco. Tendência positiva."
        )
    else:
        txt_dir = (
            f"✔️ **Direção: desescalada clara ({direcao_index:.1f}):** "
            "Cooperação predominante. O causador estava visivelmente se acalmando."
        )
    linhas.append(txt_dir)

    # ── 6. INTENSIDADE ───────────────────────────────────────────────────────
    if intensidade_index >= 100:
        txt_int = (
            f"⚡ **Intensidade extrema ({intensidade_index:.1f}):** "
            "Carga emocional muito elevada. Ocorrência de alta complexidade."
        )
    elif intensidade_index >= 60:
        txt_int = (
            f"⚡ **Intensidade alta ({intensidade_index:.1f}):** "
            "Ocorrência com carga emocional significativa."
        )
    elif intensidade_index >= 30:
        txt_int = (
            f"⚡ **Intensidade moderada ({intensidade_index:.1f}):** "
            "Carga emocional presente mas controlável."
        )
    else:
        txt_int = (
            f"⚡ **Intensidade baixa ({intensidade_index:.1f}):** "
            "Baixa carga emocional geral."
        )
    linhas.append(txt_int)

    # ── 7. VOLATILIDADE ──────────────────────────────────────────────────────
    if volatilidade_index >= 30:
        txt_vol = (
            f"🔄 **Volatilidade alta ({volatilidade_index:.1f}):** "
            "Alto risco de mudanças bruscas de comportamento. "
            "Qualquer estímulo pode provocar escalada ou desescalada súbita."
        )
    elif volatilidade_index >= 15:
        txt_vol = (
            f"🔄 **Volatilidade moderada ({volatilidade_index:.1f}):** "
            "Algum risco de mudança brusca. Negociador deve manter atenção constante."
        )
    else:
        txt_vol = (
            f"🔄 **Volatilidade baixa ({volatilidade_index:.1f}):** "
            "Comportamento relativamente previsível neste momento."
        )
    linhas.append(txt_vol)

    # ── 8. SÍNTESE FINAL ─────────────────────────────────────────────────────
    linhas.append("")
    linhas.append("---")
    linhas.append("### ✔️ Síntese Operacional")

    # Combinações de padrão para síntese
    if risco_observado >= 35 and abertura_observada >= 20:
        sintese = (
            "O causador apresentou **perfil ambivalente** — alta hostilidade coexistindo com sinais de cooperação. "
            "Este é o padrão típico de crise com **janela de resolução**: há sofrimento real, mas também abertura. "
            "O negociador deve explorar os sinais de abertura sem ignorar o risco."
        )
    elif risco_observado >= 35 and abertura_observada < 10:
        sintese = (
            "O causador estava em **estado de alta hostilidade com mínima abertura**. "
            "Padrão de crise fechada — resistência ao diálogo era dominante. "
            "Prioridade: construir abertura antes de qualquer tentativa de resolução."
        )
    elif risco_observado < 15 and abertura_observada >= 20:
        sintese = (
            "O causador demonstrou **baixo risco com boa abertura**. "
            "Padrão favorável à resolução — havia disposição para diálogo. "
            "Negociador estava em posição confortável para conduzir a desescalada."
        )
    elif raiz_observada >= 40 and risco_observado >= 20:
        sintese = (
            "O causador estava **muito fixado na origem da crise** com alto risco. "
            "Padrão de ruminação — ele repetia o motivo da crise continuamente. "
            "Estratégia recomendada: validar a causa sem concordar com a forma."
        )
    else:
        sintese = (
            f"Padrão classificado como **{classificacao}**. "
            "Os indicadores sugerem uma ocorrência de complexidade mista. "
            "Recomenda-se análise integrada com o contexto operacional completo."
        )
    linhas.append(sintese)

    # Alerta de resolução
    if resolucao_tipo == "nao_negociacao":
        linhas.append("")
        linhas.append(
            "⚠️ **Atenção:** Esta ocorrência foi resolvida por intervenção, não por negociação. "
            "Os indicadores acima refletem o estado do causador durante o processo, "
            "mas a resolução dependeu de outros fatores operacionais."
        )

    return "\n\n".join(linhas)


# ============================================================
# 5. EXTRAÇÃO DE N-GRAMAS COM INTERPRETAÇÃO APA
# ============================================================

def extrair_topicos_ngrams(texto, resolucao_tipo="desconhecida"):
    """
    Extrai temas principais e padrões de fala.
    Retorna interpretação orientada para APA.
    """
    texto_norm = limpar_texto(texto)
    palavras_validas = [p for p in texto_norm.split() if p not in STOPWORDS_GATE and len(p) > 2]

    if len(palavras_validas) < 8:
        return ["*Texto insuficiente para análise semântica.*"]

    analise = analisar_crise_direcional(texto, resolucao_tipo=resolucao_tipo)
    temas   = analise["temas"]
    resumo  = analise["sumario"]

    resultado = []

    if temas:
        for i, item in enumerate(temas, start=1):
            polaridade = {
                "risco":       "risco",
                "protecao":    "abertura/proteção",
                "contexto":    "raiz da crise",
                "progressão":  "progressão/desescalada"
            }.get(item["tipo"], item["tipo"])

            texto_neg = ""
            if item["evidencias_negadas"] > 0:
                texto_neg = f" | contextualizadas: {item['evidencias_negadas']}"

            resultado.append(
                f"**Tema {i}:** {item['categoria']} "
                f"*(score: {item['score']:.2f} | evidências: {item['evidencias']} | polaridade: {polaridade}{texto_neg})*"
            )
    else:
        if resumo["classificacao"] == "DADOS INSUFICIENTES":
            resultado.append("*Corpus insuficiente para inferência confiável.*")
        else:
            resultado.append("*Diálogo pulverizado: nenhum tema dominante detectado.*")

    # N-gramas recorrentes
    try:
        texto_processado = " ".join(palavras_validas)
        vectorizer = CountVectorizer(
            ngram_range=(2, 3),
            max_features=5,
            stop_words=list(STOPWORDS_GATE)
        )
        counts   = vectorizer.fit_transform([texto_processado])
        features = vectorizer.get_feature_names_out()
        scores   = counts.toarray()[0]

        pares = []
        for idx in scores.argsort()[::-1]:
            score   = int(scores[idx])
            feature = features[idx].strip()
            tokens_feature = feature.split()
            if score <= 1 or len(tokens_feature) < 2 or len(set(tokens_feature)) < 2:
                continue
            pares.append((feature, score))

        pares = sorted(pares, key=lambda x: x[1], reverse=True)
        for feature, score in pares:
            resultado.append(f"*(Padrão recorrente: '{feature.title()}' - {score}x)*")
    except Exception:
        pass

    # Bloco final: vetores APA
    
        resultado.append("")
        resultado.append(f"**🔴 Risco Observado:** `{resumo['risco_observado']:.2f}%` — ...")
        resultado.append(f"**🟢 Abertura Observada:** `{resumo['abertura_observada']:.2f}%` — ...")
        resultado.append(f"**🟡 Raiz Observada:** `{resumo['raiz_observada']:.2f}%` — ...")
        resultado.append(f"**Intensidade Geral:** `{resumo['intensidade_index']:.2f}` — ...")
        resultado.append(f"**{icone} Direção:** `{resumo['direcao_index']:.2f}` — ...")
        resultado.append(f"**Volatilidade:** `{resumo['volatilidade_index']:.2f}` — ...")
        resultado.append(f"**Classificação APA:** **{resumo['classificacao']}**")
        resultado.append(f"**Leitura Operacional:** {resumo['leitura']}")

    return resultado

# ============================================================
# CONVERGÊNCIA TEMÁTICA REAL — Funções novas
# ============================================================

def extrair_temas_unicos(texto, resolucao_tipo="desconhecida"):
    """
    Extrai os temas (N-gramas + palavras-chave) de um texto.
    Retorna lista de temas com scores.
    """
    analise = analisar_crise_direcional(texto, resolucao_tipo=resolucao_tipo)
    temas = analise.get("temas", [])
    
    # Retorna apenas categoria + score
    temas_lista = [
        {
            "categoria": t["categoria"],
            "score": t["score"],
            "tipo": t["tipo"],
            "evidencias": t["evidencias"]
        }
        for t in temas
    ]
    return temas_lista


def calcular_convergencia_tematica(temas_causador, temas_negociador):
    """
    Calcula convergência temática real entre causador e negociador.
    """
    if not temas_causador or not temas_negociador:
        return {
            "convergencia_geral": 0.0,
            "temas_compartilhados": [],
            "temas_exclusivos_causador": [],
            "temas_exclusivos_negociador": [],
            "analise_detalhada": "Insuficientes temas para análise."
        }
    
    cats_c = {t["categoria"] for t in temas_causador}
    cats_np = {t["categoria"] for t in temas_negociador}
    
    temas_compartilhados = cats_c & cats_np
    temas_exclusivos_c = cats_c - cats_np
    temas_exclusivos_np = cats_np - cats_c
    
    convergencia_por_tema = {}
    
    for tema in temas_compartilhados:
        score_c = next((t["score"] for t in temas_causador if t["categoria"] == tema), 0)
        score_np = next((t["score"] for t in temas_negociador if t["categoria"] == tema), 0)
        
        max_score = max(score_c, score_np)
        if max_score > 0:
            similitude = (1 - abs(score_c - score_np) / max_score) * 100
        else:
            similitude = 100.0
        
        convergencia_por_tema[tema] = {
            "score_causador": round(score_c, 2),
            "score_negociador": round(score_np, 2),
            "convergencia": round(similitude, 1),
            "tipo": next((t["tipo"] for t in temas_causador if t["categoria"] == tema), "desconhecido")
        }
    
    if temas_compartilhados:
        convergencia_geral = round(
            sum(convergencia_por_tema[t]["convergencia"] for t in temas_compartilhados) 
            / len(temas_compartilhados), 1
        )
    else:
        convergencia_geral = 0.0
    
    linhas_analise = []
    
    if temas_compartilhados:
        linhas_analise.append(f"**✅ Temas compartilhados: {len(temas_compartilhados)}**")
        linhas_analise.append("")
        
        temas_ord = sorted(
            temas_compartilhados,
            key=lambda t: convergencia_por_tema[t]["convergencia"],
            reverse=True
        )
        
        for tema in temas_ord:
            info = convergencia_por_tema[tema]
            conv = info["convergencia"]
            
            if conv >= 80:
                emoji = "🟢"
                status = "Forte alinhamento"
            elif conv >= 50:
                emoji = "🟡"
                status = "Alinhamento moderado"
            else:
                emoji = "🔴"
                status = "Fraco alinhamento"
            
            linhas_analise.append(
                f"{emoji} **{tema}** — {status} ({conv:.0f}%)\n"
                f"  Causador: {info['score_causador']:.2f} | Negociador: {info['score_negociador']:.2f}"
            )
    else:
        linhas_analise.append("⚠️ **Nenhum tema compartilhado detectado.**")
    
    linhas_analise.append("")
    
    if temas_exclusivos_c:
        linhas_analise.append(f"**🔴 Temas só do causador: {len(temas_exclusivos_c)}**")
        for tema in sorted(temas_exclusivos_c):
            score = next((t["score"] for t in temas_causador if t["categoria"] == tema), 0)
            linhas_analise.append(f"  • {tema} (score: {score:.2f})")
        linhas_analise.append("")
    
    if temas_exclusivos_np:
        linhas_analise.append(f"**🟢 Temas só do negociador: {len(temas_exclusivos_np)}**")
        for tema in sorted(temas_exclusivos_np):
            score = next((t["score"] for t in temas_negociador if t["categoria"] == tema), 0)
            linhas_analise.append(f"  • {tema} (score: {score:.2f})")
        linhas_analise.append("")
    
    return {
        "convergencia_geral": convergencia_geral,
        "temas_compartilhados": list(temas_compartilhados),
        "temas_exclusivos_causador": list(temas_exclusivos_c),
        "temas_exclusivos_negociador": list(temas_exclusivos_np),
        "convergencia_por_tema": convergencia_por_tema,
        "analise_detalhada": "\n".join(linhas_analise)
    }


def gerar_tabela_convergencia_tematica(convergencia_data):
    """
    Gera tabela formatada com convergência por tema.
    """
    import pandas as pd
    
    df_dados = []
    for tema, info in convergencia_data["convergencia_por_tema"].items():
        df_dados.append({
            "Tema": tema,
            "Causador": f"{info['score_causador']:.2f}",
            "Negociador": f"{info['score_negociador']:.2f}",
            "Convergência (%)": f"{info['convergencia']:.1f}%",
            "Tipo": info["tipo"]
        })
    
    return pd.DataFrame(df_dados)


# ============================================================
# 7. TREEMAP — CORRIGIDO (aceita string OU DataFrame)
# ============================================================

def gerar_treemap(entrada):
    """
    Aceita string de texto OU DataFrame com coluna TÉCNICAS.
    """
    import pandas as pd
    import re as _re
    from collections import Counter

    col_alvo = "TÉCNICAS"

    # ✅ Se recebeu STRING
    if isinstance(entrada, str):
        if not entrada or len(entrada.strip()) < 5:
            return None
        itens = _re.split(r'[,;\n]+', entrada)
        itens = [i.strip() for i in itens if len(i.strip()) > 2]
        if not itens:
            return None
        contagem = Counter(itens)
        df_tecnicas = pd.DataFrame(contagem.items(), columns=[col_alvo, "frequencia"])

    # ✅ Se recebeu DATAFRAME
    elif isinstance(entrada, pd.DataFrame):
        if entrada.empty or col_alvo not in entrada.columns:
            return None
        df_tecnicas = entrada.copy()
        if "frequencia" not in df_tecnicas.columns:
            df_tecnicas = df_tecnicas[col_alvo].value_counts().reset_index()
            df_tecnicas.columns = [col_alvo, "frequencia"]
    else:
        return None

    if df_tecnicas.empty:
        return None

    df_tecnicas["label_treemap"] = (
        df_tecnicas[col_alvo].astype(str) + " — " + df_tecnicas["frequencia"].astype(str) + "x"
    )

    fig = px.treemap(
        df_tecnicas,
        path=["label_treemap"],
        values="frequencia",
        color="frequencia",
        color_continuous_scale="Oranges",
        title="Frequência de Técnicas Empregadas (GATE)"
    )

    fig.update_layout(
        margin=dict(t=30, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FFFFFF"
    )
    fig.update_coloraxes(showscale=False)
    return fig


# ============================================================
# 6. RADAR COMPARATIVO — CORRIGIDO
# ============================================================
# ============================================================
# 6. RADAR COMPARATIVO — COM EFETIVIDADE TÁTICA GATE/PMESP
# ============================================================

def calcular_efetividade_negociador(
    delta_risco,
    resolucao_tipo,
    tempo_negociacao_real=0,
    tempo_negociacao_tatica=0
):
    """
    Calcula efetividade do negociador — modelo GATE/PMESP.

    REGRAS:
    - "Negociação Real"   → usa delta_risco + tempo_real
    - "Negociação Tática" → usa APENAS tempo_tatico (tempo_real ignorado)
    - "Intervenção"       → efetividade N/A (negociador não participou)

    Retorna: (score float 0-10 ou None, leitura str, detalhamento dict)
    """

    detalhamento = {
        "componente_verbal":    0.0,
        "componente_tatico":    0.0,
        "componente_resultado": 0.0,
        "penalidade":           0.0,
        "score_final":          0.0,
        "interpretacao":        ""
    }

    # ── INTERVENÇÃO: negociador não participou ───────────────
    if resolucao_tipo == "Intervenção":
        leitura = "— Ocorrência resolvida por intervenção. Efetividade do negociador não se aplica."
        detalhamento["interpretacao"] = leitura
        detalhamento["score_final"]   = None
        return None, leitura, detalhamento

    # ── NEGOCIAÇÃO TÁTICA: apenas tempo tático importa ───────
    if resolucao_tipo == "Negociação Tática":
        # Escala: 0 min = 0 | 15 min = 5.0 | 30 min+ = 10.0
        score = min(10.0, (tempo_negociacao_tatica / 30.0) * 10.0)
        score = round(score, 2)

        if score >= 8:
            leitura = (
                f"✅ Alta participação tática ({tempo_negociacao_tatica} min). "
                f"Negociador foi peça-chave na resolução — comprou tempo crítico para a ação."
            )
        elif score >= 5:
            leitura = (
                f"🔵 Participação tática moderada ({tempo_negociacao_tatica} min). "
                f"Negociador contribuiu para a janela de resolução tática."
            )
        elif score >= 2:
            leitura = (
                f"⚠️ Participação tática baixa ({tempo_negociacao_tatica} min). "
                f"Negociador comprou pouco tempo para a ação tática."
            )
        else:
            leitura = (
                f"❌ Participação tática mínima ({tempo_negociacao_tatica} min). "
                f"Tempo de apoio insuficiente para impacto relevante."
            )

        detalhamento["componente_tatico"] = score
        detalhamento["score_final"]       = score
        detalhamento["interpretacao"]     = leitura
        return score, leitura, detalhamento

    # ── NEGOCIAÇÃO REAL: delta_risco + tempo real ─────────────
    if resolucao_tipo == "Negociação Real":

        # Componente 1: Redução de risco verbal (0-5 pts)
        if delta_risco < 0:
            comp_verbal = min(5.0, abs(delta_risco) * 0.5)
        elif delta_risco == 0:
            comp_verbal = 2.5
        else:
            comp_verbal = max(0.0, 2.5 - delta_risco * 0.3)

        # Componente 2: Tempo de negociação real (0-3 pts)
        comp_tempo = min(3.0, (tempo_negociacao_real / 60.0) * 3.0)

        # Componente 3: Resultado fixo (resolveu verbalmente)
        comp_resultado = 2.0

        # Penalidade: risco subiu muito
        penalidade = 0.0
        if delta_risco > 5:
            penalidade = min(2.0, delta_risco * 0.2)

        score = round(
            min(10.0, max(0.0,
                comp_verbal + comp_tempo + comp_resultado - penalidade
            )), 2
        )

        if score >= 8:
            leitura = (
                f"✅ Negociação real muito efetiva (score {score:.1f}). "
                f"Causador cedeu verbalmente após {tempo_negociacao_real} min."
            )
        elif score >= 6:
            leitura = (
                f"🔵 Negociação real efetiva (score {score:.1f}). "
                f"Boa condução em {tempo_negociacao_real} min com redução de tensão."
            )
        elif score >= 4:
            leitura = (
                f"⚠️ Negociação real moderada (score {score:.1f}). "
                f"Resolução verbal alcançada mas com dificuldades."
            )
        else:
            leitura = (
                f"❌ Negociação real com baixa efetividade (score {score:.1f}). "
                f"Resolução verbal obtida mas risco verbal aumentou no processo."
            )

        detalhamento["componente_verbal"]    = round(comp_verbal,    2)
        detalhamento["componente_tatico"]    = 0.0
        detalhamento["componente_resultado"] = round(comp_resultado, 2)
        detalhamento["penalidade"]           = round(penalidade,     2)
        detalhamento["score_final"]          = score
        detalhamento["interpretacao"]        = leitura
        return score, leitura, detalhamento

    # ── FALLBACK ──────────────────────────────────────────────
    # resolucao desconhecida: usa lógica simples de delta_risco
    efetividade_fallback = round(abs(delta_risco) if delta_risco < 0 else -delta_risco, 2)
    if efetividade_fallback > 5:
        leitura = "✅ Atuação muito efetiva em reduzir carga de risco."
    elif efetividade_fallback > 2:
        leitura = "🔵 Efetividade moderada em gestão de risco."
    else:
        leitura = "⚠️ Atuação pouco efetiva ou sem redução de risco."
    detalhamento["score_final"]       = efetividade_fallback
    detalhamento["interpretacao"]     = leitura
    return efetividade_fallback, leitura, detalhamento


def gerar_radar_comparativo(
    texto_causador,
    texto_negociador,
    texto_negociador_sec=None,
    resolucao_tipo="desconhecida",
    tempo_negociacao_real=0,
    tempo_negociacao_tatica=0
):
    """
    Gera radar comparativo entre causador e negociador(es).
    Inclui métricas complementares: Efetividade, Rapport, Delta de Progresso.
    """
    analise_c  = analisar_crise_direcional(texto_causador,      resolucao_tipo="desconhecida")
    analise_np = analisar_crise_direcional(texto_negociador,     resolucao_tipo="desconhecida")
    analise_ns = analisar_crise_direcional(texto_negociador_sec, resolucao_tipo="desconhecida") if texto_negociador_sec else None

    s_c  = analise_c.get("sumario")
    s_np = analise_np.get("sumario")
    s_ns = analise_ns.get("sumario") if analise_ns else None

    vals_c = [
        s_c.get("risco_observado",    0.0),
        s_c.get("abertura_observada", 0.0),
        s_c.get("raiz_observada",     0.0),
        s_c.get("intensidade_index",  0.0),
        s_c.get("volatilidade_index", 0.0),
    ]
    vals_np = [
        s_np.get("risco_observado",    0.0),
        s_np.get("abertura_observada", 0.0),
        s_np.get("raiz_observada",     0.0),
        s_np.get("intensidade_index",  0.0),
        s_np.get("volatilidade_index", 0.0),
    ]
    vals_ns = [
        s_ns.get("risco_observado",    0.0),
        s_ns.get("abertura_observada", 0.0),
        s_ns.get("raiz_observada",     0.0),
        s_ns.get("intensidade_index",  0.0),
        s_ns.get("volatilidade_index", 0.0),
    ] if s_ns else None

    categorias = [
        "Risco Observado",
        "Abertura Observada",
        "Raiz Observada",
        "Intensidade",
        "Volatilidade",
    ]

    convergencia_vazia = {
        "delta_risco":            None,
        "delta_abertura":         None,
        "efetividade_negociador": None,
        "rapport_alcancado":      None,
        "delta_progresso":        None,
        "espelhamento_forma":     None,
        "espelhamento":           None,
        "leitura_risco":          None,
        "leitura_abertura":       None,
        "leitura_espelhamento":   None,
        "leitura_efetividade":    None,
        "falsa_conexao":          None,
        "resolucao_tipo":         resolucao_tipo,
        "debug_msg":              None,
    }

    try:
        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=vals_c, theta=categorias,
            fill="toself", name="Causador",
            line=dict(color="#ef4444", width=2),
            fillcolor="rgba(239,68,68,0.12)"
        ))
        fig.add_trace(go.Scatterpolar(
            r=vals_np, theta=categorias,
            fill="toself", name="Neg. Principal",
            line=dict(color="#10b981", width=2),
            fillcolor="rgba(16,185,129,0.12)"
        ))
        if vals_ns:
            fig.add_trace(go.Scatterpolar(
                r=vals_ns, theta=categorias,
                fill="toself", name="Neg. Secundário",
                line=dict(color="#3b82f6", width=2),
                fillcolor="rgba(59,130,246,0.12)"
            ))

        fig.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(
                    visible=True, showticklabels=True,
                    tickfont=dict(color="#aaa", size=10),
                    gridcolor="#333", linecolor="#444"
                ),
                angularaxis=dict(
                    tickfont=dict(color="#FFD700", size=12),
                    gridcolor="#333", linecolor="#444"
                )
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#fff"),
            legend=dict(
                font=dict(color="#fff", size=12),
                bgcolor="rgba(0,0,0,0.4)", bordercolor="#444"
            ),
            margin=dict(t=30, b=30, l=40, r=40),
            height=420
        )

        convergencia = dict(convergencia_vazia)

        if s_c is None or s_np is None:
            convergencia["debug_msg"] = "Dados insuficientes."
            return fig, convergencia

        # ── Deltas ──────────────────────────────────────────────────────────
        delta_risco    = round(s_c.get("risco_observado", 0.0)     - s_np.get("risco_observado", 0.0),   2)
        delta_abertura = round(s_np.get("abertura_observada", 0.0) - s_c.get("abertura_observada", 0.0), 2)

        # ── Efetividade — modelo GATE/PMESP ─────────────────────────────────
        efetividade, leitura_efetividade, _ = calcular_efetividade_negociador(
            delta_risco             = delta_risco,
            resolucao_tipo          = resolucao_tipo,
            tempo_negociacao_real   = tempo_negociacao_real,
            tempo_negociacao_tatica = tempo_negociacao_tatica
        )

        # ── Espelhamento (cosine similarity) — calculado ANTES do rapport ───
        def _normalizar_vetor(v):
            arr   = np.array(v, dtype=float)
            norma = np.linalg.norm(arr)
            return arr if norma == 0 else arr / norma

        v_c_norm  = _normalizar_vetor(vals_c)
        v_np_norm = _normalizar_vetor(vals_np)

        espelhamento_forma = 0.0
        try:
            if np.linalg.norm(v_c_norm) != 0 and np.linalg.norm(v_np_norm) != 0:
                espelhamento_forma = float(
                    cosine_similarity([v_c_norm], [v_np_norm])[0][0]
                )
        except Exception:
            espelhamento_forma = 0.0

        # ── Rapport ─────────────────────────────────────────────────────────
        def calcular_rapport_real(s_c, s_np):
            try:
                diff_ab            = abs(s_np.get("abertura_observada", 0.0) - s_c.get("abertura_observada", 0.0))
                score_abertura     = max(0.0, 10.0 - diff_ab)
                score_convergencia = min(10.0, espelhamento_forma * 10)
                score_validacao    = score_abertura  # fallback: abertura ≈ validação

                rapport_calc = (
                    0.4 * score_abertura +
                    0.4 * score_convergencia +
                    0.2 * score_validacao
                )
                return round(min(10.0, max(0.0, rapport_calc)), 2)
            except Exception:
                diff_ab = abs(s_np.get("abertura_observada", 0.0) - s_c.get("abertura_observada", 0.0))
                return round(max(0.0, 10.0 - diff_ab), 2)

        rapport         = calcular_rapport_real(s_c, s_np)
        delta_progresso = round(delta_risco + delta_abertura, 2)

        # ── Preencher convergencia ───────────────────────────────────────────
        convergencia["delta_risco"]            = delta_risco
        convergencia["delta_abertura"]         = delta_abertura
        convergencia["efetividade_negociador"] = efetividade
        convergencia["rapport_alcancado"]      = rapport
        convergencia["delta_progresso"]        = delta_progresso
        convergencia["espelhamento_forma"]     = round(float(espelhamento_forma), 2)
        convergencia["espelhamento"]           = convergencia["espelhamento_forma"]
        convergencia["resolucao_tipo"]         = resolucao_tipo

        # ── Leituras ─────────────────────────────────────────────────────────
        if delta_risco > 3:
            leitura_risco = "⚠️ Causador com carga de risco significativamente maior."
        elif delta_risco < -3:
            leitura_risco = "✅ Negociador mantém risco equilibrado ou menor."
        else:
            leitura_risco = "🔵 Carga de risco equilibrada."

        if delta_abertura > 3:
            leitura_abertura = "✅ Negociador puxando ativamente para desescalada."
        elif delta_abertura < -3:
            leitura_abertura = "⚠️ Causador com mais sinais protetivos que negociador."
        else:
            leitura_abertura = "🔵 Linguagem protetiva similar entre os dois."

        if espelhamento_forma >= 0.85:
            leitura_espelhamento = "🔁 Alto espelhamento temático — forte convergência."
        elif espelhamento_forma >= 0.65:
            leitura_espelhamento = "🔁 Espelhamento moderado — convergência parcial."
        else:
            leitura_espelhamento = "⚡ Baixo espelhamento — padrões semânticos distintos."

        convergencia["leitura_risco"]        = leitura_risco
        convergencia["leitura_abertura"]     = leitura_abertura
        convergencia["leitura_efetividade"]  = leitura_efetividade
        convergencia["leitura_espelhamento"] = leitura_espelhamento

        return fig, convergencia

    except Exception as err:
        fig_err = go.Figure()
        fig_err.update_layout(
            title="Erro ao gerar radar",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#fff")
        )
        convergencia_vazia["debug_msg"] = f"Erro: {str(err)}"
        return fig_err, convergencia_vazia


def gerar_radar_comparativo(texto_causador, texto_negociador, texto_negociador_sec=None):
    """
    Gera radar comparativo entre causador e negociador(es).
    Inclui métricas complementares: Efetividade, Rapport, Delta de Progresso.
    """
    analise_c  = analisar_crise_direcional(texto_causador,       resolucao_tipo="desconhecida")
    analise_np = analisar_crise_direcional(texto_negociador,      resolucao_tipo="desconhecida")
    analise_ns = analisar_crise_direcional(texto_negociador_sec,  resolucao_tipo="desconhecida") if texto_negociador_sec else None

    s_c  = analise_c.get("sumario")
    s_np = analise_np.get("sumario")
    s_ns = analise_ns.get("sumario") if analise_ns else None

    vals_c = [
        s_c.get("risco_observado",    0.0),
        s_c.get("abertura_observada", 0.0),
        s_c.get("raiz_observada",     0.0),
        s_c.get("intensidade_index",  0.0),
        s_c.get("volatilidade_index", 0.0),
    ]
    vals_np = [
        s_np.get("risco_observado",    0.0),
        s_np.get("abertura_observada", 0.0),
        s_np.get("raiz_observada",     0.0),
        s_np.get("intensidade_index",  0.0),
        s_np.get("volatilidade_index", 0.0),
    ]
    vals_ns = [
        s_ns.get("risco_observado",    0.0),
        s_ns.get("abertura_observada", 0.0),
        s_ns.get("raiz_observada",     0.0),
        s_ns.get("intensidade_index",  0.0),
        s_ns.get("volatilidade_index", 0.0),
    ] if s_ns else None

    categorias = [
        "Risco Observado",
        "Abertura Observada",
        "Raiz Observada",
        "Intensidade",
        "Volatilidade",
    ]

    convergencia_vazia = {
        "delta_risco":            None,
        "delta_abertura":         None,
        "efetividade_negociador": None,
        "rapport_alcancado":      None,
        "delta_progresso":        None,
        "espelhamento_forma":     None,
        "espelhamento":           None,
        "leitura_risco":          None,
        "leitura_abertura":       None,
        "leitura_espelhamento":   None,
        "leitura_efetividade":    None,
        "falsa_conexao":          None,
        "debug_msg":              None,
    }

    try:
        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=vals_c, theta=categorias,
            fill="toself", name="Causador",
            line=dict(color="#ef4444", width=2),
            fillcolor="rgba(239,68,68,0.12)"
        ))
        fig.add_trace(go.Scatterpolar(
            r=vals_np, theta=categorias,
            fill="toself", name="Neg. Principal",
            line=dict(color="#10b981", width=2),
            fillcolor="rgba(16,185,129,0.12)"
        ))
        if vals_ns:
            fig.add_trace(go.Scatterpolar(
                r=vals_ns, theta=categorias,
                fill="toself", name="Neg. Secundário",
                line=dict(color="#3b82f6", width=2),
                fillcolor="rgba(59,130,246,0.12)"
            ))

        fig.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(
                    visible=True, showticklabels=True,
                    tickfont=dict(color="#aaa", size=10),
                    gridcolor="#333", linecolor="#444"
                ),
                angularaxis=dict(
                    tickfont=dict(color="#FFD700", size=12),
                    gridcolor="#333", linecolor="#444"
                )
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#fff"),
            legend=dict(
                font=dict(color="#fff", size=12),
                bgcolor="rgba(0,0,0,0.4)", bordercolor="#444"
            ),
            margin=dict(t=30, b=30, l=40, r=40),
            height=420
        )

        convergencia = dict(convergencia_vazia)

        if s_c is None or s_np is None:
            convergencia["debug_msg"] = "Dados insuficientes."
            return fig, convergencia

        # ── Deltas ──────────────────────────────────────────────────────────
        delta_risco    = round(s_c.get("risco_observado", 0.0)     - s_np.get("risco_observado", 0.0),    2)
        delta_abertura = round(s_np.get("abertura_observada", 0.0) - s_c.get("abertura_observada", 0.0),  2)

        # ── Efetividade ──────────────────────────────────────────────────────
        efetividade = round(abs(delta_risco) if delta_risco < 0 else -delta_risco, 2)

        # ── Espelhamento (cosine similarity) — calculado ANTES do rapport ───
        def _normalizar_vetor(v):
            arr   = np.array(v, dtype=float)
            norma = np.linalg.norm(arr)
            return arr if norma == 0 else arr / norma

        v_c_norm  = _normalizar_vetor(vals_c)
        v_np_norm = _normalizar_vetor(vals_np)

        espelhamento_forma = 0.0
        try:
            if np.linalg.norm(v_c_norm) != 0 and np.linalg.norm(v_np_norm) != 0:
                espelhamento_forma = float(
                    cosine_similarity([v_c_norm], [v_np_norm])[0][0]
                )
        except Exception:
            espelhamento_forma = 0.0

        # ── Rapport ─────────────────────────────────────────────────────────
        # ✅ CORRIGIDO: variáveis com nomes corretos, usa espelhamento_forma já calculado
        def calcular_rapport_real(s_c, s_np):
            try:
                diff_ab            = abs(s_np.get("abertura_observada", 0.0) - s_c.get("abertura_observada", 0.0))
                score_abertura     = max(0.0, 10.0 - diff_ab)
                score_convergencia = min(10.0, espelhamento_forma * 10)
                score_validacao    = score_abertura  # fallback: abertura ≈ validação

                rapport_calc = (
                    0.4 * score_abertura +
                    0.4 * score_convergencia +
                    0.2 * score_validacao
                )
                return round(min(10.0, max(0.0, rapport_calc)), 2)
            except Exception:
                diff_ab = abs(s_np.get("abertura_observada", 0.0) - s_c.get("abertura_observada", 0.0))
                return round(max(0.0, 10.0 - diff_ab), 2)

        rapport         = calcular_rapport_real(s_c, s_np)
        delta_progresso = round(delta_risco + delta_abertura, 2)

        # ── Preencher convergencia ───────────────────────────────────────────
        convergencia["delta_risco"]            = delta_risco
        convergencia["delta_abertura"]         = delta_abertura
        convergencia["efetividade_negociador"] = efetividade
        convergencia["rapport_alcancado"]      = rapport
        convergencia["delta_progresso"]        = delta_progresso
        convergencia["espelhamento_forma"]     = round(float(espelhamento_forma), 2)
        convergencia["espelhamento"]           = convergencia["espelhamento_forma"]

        # ── Leituras ─────────────────────────────────────────────────────────
        if delta_risco > 3:
            leitura_risco = "⚠️ Causador com carga de risco significativamente maior."
        elif delta_risco < -3:
            leitura_risco = "✅ Negociador mantém risco equilibrado ou menor."
        else:
            leitura_risco = "🔵 Carga de risco equilibrada."

        if delta_abertura > 3:
            leitura_abertura = "✅ Negociador puxando ativamente para desescalada."
        elif delta_abertura < -3:
            leitura_abertura = "⚠️ Causador com mais sinais protetivos que negociador."
        else:
            leitura_abertura = "🔵 Linguagem protetiva similar entre os dois."

        if efetividade > 5:
            leitura_efetividade = "✅ Atuação muito efetiva em reduzir carga de risco."
        elif efetividade > 2:
            leitura_efetividade = "🔵 Efetividade moderada em gestão de risco."
        else:
            leitura_efetividade = "⚠️ Atuação pouco efetiva ou sem redução de risco."

        if espelhamento_forma >= 0.85:
            leitura_espelhamento = "🔁 Alto espelhamento temático — forte convergência."
        elif espelhamento_forma >= 0.65:
            leitura_espelhamento = "🔁 Espelhamento moderado — convergência parcial."
        else:
            leitura_espelhamento = "⚡ Baixo espelhamento — padrões semânticos distintos."

        convergencia["leitura_risco"]        = leitura_risco
        convergencia["leitura_abertura"]     = leitura_abertura
        convergencia["leitura_efetividade"]  = leitura_efetividade
        convergencia["leitura_espelhamento"] = leitura_espelhamento

        return fig, convergencia

    except Exception as err:
        fig_err = go.Figure()
        fig_err.update_layout(
            title="Erro ao gerar radar",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#fff")
        )
        convergencia_vazia["debug_msg"] = f"Erro: {str(err)}"
        return fig_err, convergencia_vazia
    
    
# ============================================================
# 7. TESTES ESTATÍSTICOS
# ============================================================
# ============================================================
# DETECTOR DE FALSA CONEXÃO (Adicionar antes de calcular_spearman)
# ============================================================

def detectar_falsa_conexao(similitude_percent, convergencia_percent):
    """
    Identifica quando há similitude alta mas convergência baixa
    = falsa conexão, negociador não está realmente sincronizado.
    
    Args:
        similitude_percent: Índice de similitude (0-100)
        convergencia_percent: Convergência temática (0-100)
    
    Returns:
        dict com análise de falsa conexão
    """
    
    if similitude_percent is None or convergencia_percent is None:  
        return {
            "alerta": False,
            "severidade": None,
            "mensagem": None,
            "recomendacao": None
        }
    
    # Padrão crítico: similitude alta + convergência baixa
    if similitude_percent > 40 and convergencia_percent < 50:
        return {
            "alerta": True,
            "severidade": "Crítica",
            "mensagem": "Desconexão severa: ambos usam palavras similares mas temas radicalmente diferentes",
            "recomendacao": "Negociador repetindo vícios sem validar realidade do causador. Efetividade reduzida. Mudar estratégia IMEDIATAMENTE."
        }
    
    # Padrão de risco: similitude alta + convergência moderada-baixa
    elif similitude_percent > 35 and convergencia_percent < 70:
        return {
            "alerta": True,
            "severidade": "Alta",
            "mensagem": "Falsa conexão detectada: palavras compartilhadas mascarando falta de sincronização temática",
            "recomendacao": "Possível vício de linguagem (ex: 'mano') inflando similitude. Validar se convergência temática real existe."
        }
    
    # Padrão positivo: ambas altas = real conexão
    elif similitude_percent > 30 and convergencia_percent >= 70:
        return {
            "alerta": False,
            "severidade": None,
            "mensagem": "Sincronização saudável: palavras E temas alinhados",
            "recomendacao": None
        }
    
    # Padrão também positivo: similitude baixa + convergência alta = bom
    elif similitude_percent <= 30 and convergencia_percent >= 60:
        return {
            "alerta": False,
            "severidade": None,
            "mensagem": "Convergência temática forte apesar de vocabulários diferentes: bom rapport",
            "recomendacao": None
        }
    
    else:
        return {
            "alerta": False,
            "severidade": None,
            "mensagem": None,
            "recomendacao": None
        }
    
def calcular_efetividade_negociador(
delta_risco,
resolucao_tipo,
tempo_negociacao_real=0,
tempo_negociacao_tatica=0
):
    """
    Calcula efetividade do negociador — modelo GATE/PMESP.

    REGRAS:
    - "Negociação Real"   → usa delta_risco + tempo_real
    - "Negociação Tática" → usa APENAS tempo_tatico (tempo_real ignorado)
    - "Intervenção"       → efetividade N/A (negociador não participou)

    Retorna: (score float 0-10, leitura str, detalhamento dict)
    """

    detalhamento = {
        "componente_verbal":    0.0,
        "componente_tatico":    0.0,
        "componente_resultado": 0.0,
        "penalidade":           0.0,
        "score_final":          0.0,
        "interpretacao":        ""
    }

    # ── INTERVENÇÃO: negociador não participou ───────────────
    if resolucao_tipo == "Intervenção":
        leitura = "— Ocorrência resolvida por intervenção. Efetividade do negociador não se aplica."
        detalhamento["interpretacao"] = leitura
        detalhamento["score_final"]   = None
        return None, leitura, detalhamento

    # ── NEGOCIAÇÃO TÁTICA: apenas tempo tático importa ───────
    if resolucao_tipo == "Negociação Tática":
        # Quanto mais tempo comprando = mais participou
        # Escala: 0 min = 0 | 15 min = 5.0 | 30 min+ = 10.0
        score = min(10.0, (tempo_negociacao_tatica / 30.0) * 10.0)
        score = round(score, 2)

        if score >= 8:
            leitura = (
                f"✅ Alta participação tática ({tempo_negociacao_tatica} min). "
                f"Negociador foi peça-chave na resolução — comprou tempo crítico para a ação."
            )
        elif score >= 5:
            leitura = (
                f"🔵 Participação tática moderada ({tempo_negociacao_tatica} min). "
                f"Negociador contribuiu para a janela de resolução tática."
            )
        elif score >= 2:
            leitura = (
                f"⚠️ Participação tática baixa ({tempo_negociacao_tatica} min). "
                f"Negociador comprou pouco tempo para a ação tática."
            )
        else:
            leitura = (
                f"❌ Participação tática mínima ({tempo_negociacao_tatica} min). "
                f"Tempo de apoio insuficiente para impacto relevante."
            )

        detalhamento["componente_tatico"]  = score
        detalhamento["score_final"]        = score
        detalhamento["interpretacao"]      = leitura
        return score, leitura, detalhamento

    # ── NEGOCIAÇÃO REAL: delta_risco + tempo real ─────────────
    if resolucao_tipo == "Negociação Real":

        # COMPONENTE 1: Redução de risco verbal (0-5 pts)
        if delta_risco < 0:
            # Risco caiu = efetivo
            comp_verbal = min(5.0, abs(delta_risco) * 0.5)
        elif delta_risco == 0:
            # Risco estável = neutro (conteve)
            comp_verbal = 2.5
        else:
            # Risco subiu = inefetivo
            comp_verbal = max(0.0, 2.5 - delta_risco * 0.3)

        # COMPONENTE 2: Tempo de negociação real (0-3 pts)
        # Mais tempo = mais persistência = bônus
        # 0 min = 0 | 30 min = 1.5 | 60 min+ = 3.0
        comp_tempo = min(3.0, (tempo_negociacao_real / 60.0) * 3.0)

        # COMPONENTE 3: Resultado (0-2 pts)
        # Negociação Real que resolveu = bônus fixo
        comp_resultado = 2.0

        # PENALIDADE: risco subiu muito em negociação real
        penalidade = 0.0
        if delta_risco > 5:
            penalidade = min(2.0, delta_risco * 0.2)

        score = round(
            min(10.0, max(0.0,
                comp_verbal + comp_tempo + comp_resultado - penalidade
            )), 2
        )

        if score >= 8:
            leitura = (
                f"✅ Negociação real muito efetiva (score {score:.1f}). "
                f"Causador cedeu verbalmente após {tempo_negociacao_real} min de negociação."
            )
        elif score >= 6:
            leitura = (
                f"🔵 Negociação real efetiva (score {score:.1f}). "
                f"Boa condução em {tempo_negociacao_real} min com redução de tensão."
            )
        elif score >= 4:
            leitura = (
                f"⚠️ Negociação real moderada (score {score:.1f}). "
                f"Resolução verbal alcançada mas com dificuldades."
            )
        else:
            leitura = (
                f"❌ Negociação real com baixa efetividade (score {score:.1f}). "
                f"Resolução verbal obtida mas o risco verbal aumentou no processo."
            )

        detalhamento["componente_verbal"]    = round(comp_verbal,    2)
        detalhamento["componente_tatico"]    = 0.0
        detalhamento["componente_resultado"] = round(comp_resultado, 2)
        detalhamento["penalidade"]           = round(penalidade,     2)
        detalhamento["score_final"]          = score
        detalhamento["interpretacao"]        = leitura
        return score, leitura, detalhamento

    # ── FALLBACK: resolução não identificada ──────────────────
    leitura = "— Tipo de resolução não identificado. Efetividade não calculada."
    detalhamento["interpretacao"] = leitura
    detalhamento["score_final"]   = None
    return None, leitura, detalhamento

def calcular_spearman(df_historico, col_x, col_y):
    df_limpo = df_historico[[col_x, col_y]].dropna().copy()
    df_limpo = df_limpo[(df_limpo[col_x] != "N/D") & (df_limpo[col_y] != "N/D")]

    if len(df_limpo) < 3:
        return {
            "valido": False,
            "p_value": 0.0,
            "rho": 0.0,
            "msg": "Dados insuficientes (N<3)."
        }

    try:
        x = pd.to_numeric(df_limpo[col_x], errors="coerce")
        y = pd.to_numeric(df_limpo[col_y], errors="coerce")

        mask = ~np.isnan(x) & ~np.isnan(y)
        x = x[mask]
        y = y[mask]

        if len(x) < 3:
            return {
                "valido": False,
                "rho": 0.0,
                "p_value": 0.0,
                "msg": "Dados numéricos insuficientes."
            }

        rho, p_val = spearmanr(x, y)
        return {
            "valido": True,
            "rho": float(rho),
            "p_value": float(p_val),
            "msg": "Sucesso."
        }

    except Exception as e:
        return {
            "valido": False,
            "rho": 0.0,
            "p_value": 0.0,
            "msg": f"Erro: {str(e)}"
        }

def calcular_qui_quadrado(df_historico, col_cat1, col_cat2):
    df_limpo = df_historico[[col_cat1, col_cat2]].dropna().copy()

    if df_limpo.empty:
        return {"valido": False, "msg": "DataFrame vazio."}

    tabela = pd.crosstab(df_limpo[col_cat1], df_limpo[col_cat2])

    if tabela.shape[0] < 2 or tabela.shape[1] < 2:
        return {"valido": False, "msg": "Variância insuficiente."}

    try:
        chi2, p_val, dof, expected = chi2_contingency(tabela)

        if (expected < 5).mean() > 0.2:
            return {
                "valido": False,
                "msg": "Frequências esperadas muito baixas."
            }

        return {
            "valido": True,
            "chi2": float(chi2),
            "p_value": float(p_val),
            "tabela": tabela
        }

    except Exception as e:
        return {
            "valido": False,
            "msg": f"Erro: {str(e)}"
        }
    
    
