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
    "equipe", "ocorrencia", "ocorrência", "incidente", "forma"
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
    "Ideação Suicida / Desesperança (Crise Interna)": {
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

VOCATIVOS_BASE = set([
    'fala', 'fale', 'fala comigo', 'escuta', 'oi', 'alô', 'alo', 'vem', 'venha',
])

def eh_vocativo(tokens, idx_inicio, idx_fim, repeticao_threshold=3):
    span = tokens[idx_inicio:idx_fim]
    if not span:
        return False

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

def analisar_crise_direcional(texto, resolucao_tipo="desconhecida"):
    """
    Motor de análise semântica direcional.
    Retorna vetores de Risco, Proteção e Contexto com interpretação para APA.
    """
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
                "classificacao": "SEM DADOS",
                "leitura": "Texto insuficiente para análise."
            }
        }

    tokens, starts = _obter_tokens_e_posicoes(texto_norm)
    tokens_validos = [t for t in tokens if len(t) > 1 and t not in STOPWORDS_GATE]
    total_tokens = len(tokens_validos)

    if total_tokens < 15 or len(set(tokens_validos)) < 6:
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
                "classificacao": "DADOS INSUFICIENTES",
                "leitura": "Corpus insuficiente para análise confiável."
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
    risco_observado = round((risco_bruto / max(total_tokens, 1)) * 100, 2)
    abertura_observada = round((protecao_bruto / max(total_tokens, 1)) * 100, 2)
    raiz_observada = round((contexto_bruto / max(total_tokens, 1)) * 100, 2)

    intensidade_index = round(risco_observado + abertura_observada + (raiz_observada * 0.35), 2)
    direcao_index = round(abertura_observada - risco_observado, 2)
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

    if resolucao_tipo == "nao_negociacao":
        return (
            "HOUVE INTERVENÇÃO",
            "Ocorrência resolvida fora da negociação. Requer análise rigorosa da atuação em desescalada."
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
    temas = analise["temas"]
    resumo = analise["sumario"]

    resultado = []

    if temas:
        for i, item in enumerate(temas, start=1):
            polaridade = {
                "risco": "risco",
                "protecao": "abertura/proteção",
                "contexto": "raiz da crise",
                "progressão": "progressão/desescalada"
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
        counts = vectorizer.fit_transform([texto_processado])
        features = vectorizer.get_feature_names_out()
        scores = counts.toarray()[0]

        pares = []
        for idx in scores.argsort()[::-1]:
            score = int(scores[idx])
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
    resultado.append(f"**🔴 Risco Observado:** `{resumo['risco_observado']:.2f}%` — Intensidade de ameaça/hostilidade")
    resultado.append(f"**🟢 Abertura Observada:** `{resumo['abertura_observada']:.2f}%` — Sinais de cooperação/rendição")
    resultado.append(f"**🟡 Raiz Observada:** `{resumo['raiz_observada']:.2f}%` — Gatilhos/motivadores da crise")
    resultado.append(f"**Intensidade Global:** `{resumo['intensidade_index']:.2f}` — Carga emocional total")

    if resumo["direcao_index"] > 0:
        direcao_txt = "desescalada"
        icone = "📈"
    elif resumo["direcao_index"] < 0:
        direcao_txt = "escalada"
        icone = "📉"
    else:
        direcao_txt = "equilíbrio"
        icone = "⚖️"

    resultado.append(
        f"**{icone} Direção:** `{resumo['direcao_index']:.2f}` — Predomínio de {direcao_txt}"
    )
    resultado.append(f"**Volatilidade:** `{resumo['volatilidade_index']:.2f}` — Risco de mudanças bruscas")
    resultado.append(f"**Classificação APA:** **{resumo['classificacao']}**")
    resultado.append(f"**Leitura Operacional:** {resumo['leitura']}")

    return resultado

# ============================================================
# 7. TREEMAP
# ============================================================

def gerar_treemap(df_tecnicas):
    col_alvo = "TÉCNICAS"

    if df_tecnicas.empty or col_alvo not in df_tecnicas.columns:
        return None

    df_tecnicas = df_tecnicas.copy()

    if "frequencia" not in df_tecnicas.columns:
        if col_alvo in df_tecnicas.columns:
            df_tecnicas = df_tecnicas[col_alvo].value_counts().reset_index()
            df_tecnicas.columns = [col_alvo, "frequencia"]
        else:
            return None

    df_tecnicas["label_treemap"] = (
        df_tecnicas[col_alvo].astype(str) + " - " + df_tecnicas["frequencia"].astype(str)
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
        font_color="#FFFF"
    )
    fig.update_coloraxes(showscale=False)
    return fig


# ============================================================
# 6. RADAR COMPARATIVO COM MÉTRICAS COMPLEMENTARES
# ============================================================

def gerar_radar_comparativo(texto_causador, texto_negociador, texto_negociador_sec=None):
    """
    Gera radar comparativo entre causador e negociador(es).
    Inclui métricas complementares: Efetividade, Rapport, Delta de Progresso.
    """
    analise_c  = analisar_crise_direcional(texto_causador, resolucao_tipo="desconhecida")
    analise_np = analisar_crise_direcional(texto_negociador, resolucao_tipo="desconhecida")
    analise_ns = analisar_crise_direcional(texto_negociador_sec, resolucao_tipo="desconhecida") if texto_negociador_sec else None

    s_c  = analise_c.get("sumario")
    s_np = analise_np.get("sumario")
    s_ns = analise_ns.get("sumario") if analise_ns else None

    vals_c  = [
        s_c.get("risco_observado", 0.0),
        s_c.get("abertura_observada", 0.0),
        s_c.get("raiz_observada", 0.0),
        s_c.get("intensidade_index", 0.0),
        s_c.get("volatilidade_index", 0.0)
    ]
    vals_np = [
        s_np.get("risco_observado", 0.0),
        s_np.get("abertura_observada", 0.0),
        s_np.get("raiz_observada", 0.0),
        s_np.get("intensidade_index", 0.0),
        s_np.get("volatilidade_index", 0.0)
    ]
    vals_ns = [
        s_ns.get("risco_observado", 0.0),
        s_ns.get("abertura_observada", 0.0),
        s_ns.get("raiz_observada", 0.0),
        s_ns.get("intensidade_index", 0.0),
        s_ns.get("volatilidade_index", 0.0)
    ] if s_ns else None

    categorias = [
        "Risco Observado",
        "Abertura Observada",
        "Raiz Observada",
        "Intensidade",
        "Volatilidade"
    ]

    try:
        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=vals_c,
            theta=categorias,
            fill="toself",
            name="Causador",
            line=dict(color="#ef4444", width=2),
            fillcolor="rgba(239,68,68,0.12)"
        ))

        fig.add_trace(go.Scatterpolar(
            r=vals_np,
            theta=categorias,
            fill="toself",
            name="Neg. Principal",
            line=dict(color="#10b981", width=2),
            fillcolor="rgba(16,185,129,0.12)"
        ))

        if vals_ns:
            fig.add_trace(go.Scatterpolar(
                r=vals_ns,
                theta=categorias,
                fill="toself",
                name="Neg. Secundário",
                line=dict(color="#3b82f6", width=2),
                fillcolor="rgba(59,130,246,0.12)"
            ))

        fig.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(
                    visible=True,
                    showticklabels=True,
                    tickfont=dict(color="#aaa", size=10),
                    gridcolor="#333",
                    linecolor="#444"
                ),
                angularaxis=dict(
                    tickfont=dict(color="#FFD700", size=12),
                    gridcolor="#333",
                    linecolor="#444"
                )
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#fff"),
            legend=dict(
                font=dict(color="#fff", size=12),
                bgcolor="rgba(0,0,0,0.4)",
                bordercolor="#444"
            ),
            margin=dict(t=30, b=30, l=40, r=40),
            height=420
        )

        # MÉTRICAS COMPLEMENTARES PARA APA
        convergencia = {
            "delta_risco": None,
            "delta_abertura": None,
            "efetividade_negociador": None,
            "rapport_alcancado": None,
            "delta_progresso": None,
            "espelhamento_forma": None,
            "espelhamento": None,
            "leitura_risco": None,
            "leitura_abertura": None,
            "leitura_espelhamento": None,
            "leitura_efetividade": None,
            "debug_msg": None
        }

        if s_c is None or s_np is None:
            convergencia["debug_msg"] = "Dados insuficientes."
            return fig, convergencia

        # Deltas principais
        delta_risco = round(s_c.get("risco_observado", 0.0) - s_np.get("risco_observado", 0.0), 2)
        delta_abertura = round(s_np.get("abertura_observada", 0.0) - s_c.get("abertura_observada", 0.0), 2)

        # MÉTRICA COMPLEMENTAR 1: Efetividade do Negociador
        # = quanto conseguiu reduzir o risco relativo (delta negativo = efetivo)
        efetividade = round(abs(delta_risco) if delta_risco < 0 else -delta_risco, 2)
        
        # MÉTRICA COMPLEMENTAR 2: Rapport Alcançado
        # = proximidade de abertura entre os dois (quanto maior, melhor)
        rapport = round(abs(s_np.get("abertura_observada", 0.0) - s_c.get("abertura_observada", 0.0)), 2)
        
        # MÉTRICA COMPLEMENTAR 3: Delta de Progresso
        # = desescalada total observada (redução de risco + aumento de abertura)
        delta_progresso = round(delta_risco + delta_abertura, 2)

        convergencia["delta_risco"] = delta_risco
        convergencia["delta_abertura"] = delta_abertura
        convergencia["efetividade_negociador"] = efetividade
        convergencia["rapport_alcancado"] = rapport
        convergencia["delta_progresso"] = delta_progresso

        # Interpretações
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

        # Espelhamento forma
        def _normalizar_vetor(v):
            arr = np.array(v, dtype=float)
            norma = np.linalg.norm(arr)
            return arr if norma == 0 else arr / norma

        v_c_norm  = _normalizar_vetor(vals_c)
        v_np_norm = _normalizar_vetor(vals_np)

        espelhamento_forma = 0.0
        try:
            if np.linalg.norm(v_c_norm) != 0 and np.linalg.norm(v_np_norm) != 0:
                espelhamento_forma = float(cosine_similarity([v_c_norm], [v_np_norm])[0][0])
            else:
                espelhamento_forma = 0.0
        except Exception:
            espelhamento_forma = 0.0

        convergencia["espelhamento_forma"] = round(float(espelhamento_forma), 2)
        convergencia["espelhamento"] = convergencia["espelhamento_forma"]

        if espelhamento_forma >= 0.85:
            leitura_espelhamento = "🔁 Alto espelhamento temático — forte convergência."
        elif espelhamento_forma >= 0.65:
            leitura_espelhamento = "🔁 Espelhamento moderado — convergência parcial."
        else:
            leitura_espelhamento = "⚡ Baixo espelhamento — padrões semânticos distintos."

        convergencia["leitura_risco"] = leitura_risco
        convergencia["leitura_abertura"] = leitura_abertura
        convergencia["leitura_espelhamento"] = leitura_espelhamento
        convergencia["leitura_efetividade"] = leitura_efetividade

        return fig, convergencia

    except Exception as err:
        fig = go.Figure()
        fig.update_layout(
            title="Erro ao gerar radar",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#fff")
        )
        convergencia = {
            "delta_risco": None,
            "delta_abertura": None,
            "efetividade_negociador": None,
            "rapport_alcancado": None,
            "delta_progresso": None,
            "espelhamento_forma": None,
            "espelhamento": None,
            "leitura_risco": None,
            "leitura_abertura": None,
            "leitura_espelhamento": None,
            "leitura_efetividade": None,
            "debug_msg": f"Erro: {str(err)}"
        }
        return fig, convergencia

# ============================================================
# 7. TESTES ESTATÍSTICOS (MANTIDOS)
# ============================================================

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
