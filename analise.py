import re
import unicodedata
from bisect import bisect_right

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
from scipy.stats import chi2_contingency, spearmanr
from sklearn.feature_extraction.text import CountVectorizer
from wordcloud import WordCloud

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
# 2. DICIONÁRIO TÁTICO DIRECIONAL
#    tipo:
#      - risco
#      - protecao
#      - contexto
# ============================================================

DICIONARIO_TATICO = {
    "Sinalização de Rendição / Desescalada de Violência": {
        "tipo": "protecao",
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
            "ta bom": 1.30,
            "tudo bem": 1.30,
            "beleza": 1.10,
            "acabou": 1.70,
            "nao vou fazer": 1.90,
            "desisto disso": 2.30,
            "vou descer": 2.00,
            "estou descendo": 2.00
        }
    },
    "Tentativa de Estabelecimento de Contato": {
        "tipo": "protecao",
        "peso_base": 1.15,
        "termos": {
            "fala comigo": 2.00,
            "conversa comigo": 2.00,
            "me escuta": 1.80,
            "me ouve": 1.80,
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
            "irma": 1.30,
            "esposa": 1.40,
            "mulher": 1.20,
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
            "arma": 1.80,
            "faca": 1.90,
            "sangue": 1.60,
            "refem": 2.40,
            "bala": 1.90,
            "explodir": 2.70,
            "explode": 2.60,
            "ninguem entra": 2.40,
            "afasta": 1.80,
            "se chegar perto": 2.80,
            "chegar perto": 2.00,
            "policia": 1.20,
            "farda": 1.10,
            "encosta nao": 2.30
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
# 3. FUNÇÕES DE NORMALIZAÇÃO
# ============================================================

def normalizar_texto(texto):
    if not isinstance(texto, str) or not texto.strip():
        return ""
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII")
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto

def limpar_texto(texto):
    """Mantida por compatibilidade com o app atual."""
    return normalizar_texto(texto)

def _tokenizar(texto):
    return re.findall(r"\b\w+\b", texto)

# ============================================================
# 4. WORDCLOUD
# ============================================================

def gerar_wordcloud(texto):
    texto_limpo = limpar_texto(texto)
    tokens = [t for t in texto_limpo.split() if t not in STOPWORDS_GATE and len(t) > 2]

    if len(tokens) < 3:
        return None

    wc = WordCloud(
        background_color=None,
        mode="RGBA",
        width=700,
        height=350,
        stopwords=STOPWORDS_GATE,
        colormap="Oranges",
        max_words=50
    ).generate(" ".join(tokens))

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    fig.patch.set_facecolor("#0f0f0f")
    ax.set_facecolor("#0f0f0f")
    return fig

# ============================================================
# 5. MOTOR DIRECIONAL DE N-GRAMAS
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

def analisar_crise_direcional(texto):
    texto_norm = normalizar_texto(texto)
    if not texto_norm:
        return {
            "temas": [],
            "sumario": {
                "tokens_validos": 0,
                "risco_bruto": 0.0,
                "protecao_bruto": 0.0,
                "contexto_bruto": 0.0,
                "risco_index": 0.0,
                "protecao_index": 0.0,
                "contexto_index": 0.0,
                "intensidade_index": 0.0,
                "direcao_index": 0.0,
                "volatilidade_index": 0.0,
                "classificacao": "SEM DADOS",
                "leitura": "Texto insuficiente para análise."
            }
        }

    tokens, starts = _obter_tokens_e_posicoes(texto_norm)
    total_tokens = max(len([t for t in tokens if len(t) > 1]), 1)

    resultados = []
    risco_bruto = 0.0
    protecao_bruto = 0.0
    contexto_bruto = 0.0

    for categoria, cfg in DICIONARIO_TATICO.items():
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

                if negado:
                    evidencias_negadas += 1

                    if tipo == "risco":
                        # Ex.: "não quero morrer" -> reduz risco e cria sinal protetivo fraco
                        score_categoria += peso_final * 0.18
                        protecao_bruto += peso_final * 0.45

                    elif tipo == "protecao":
                        # Ex.: "não vou me entregar" -> desativa proteção e aumenta risco
                        score_categoria += peso_final * 0.18
                        risco_bruto += peso_final * 0.65

                    else:
                        # Contexto negado tem pouco impacto operacional
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

    # Normalização por densidade textual:
    # reduz o viés de transcrições muito longas.
    risco_index = round((risco_bruto / total_tokens) * 100, 2)
    protecao_index = round((protecao_bruto / total_tokens) * 100, 2)
    contexto_index = round((contexto_bruto / total_tokens) * 100, 2)

    intensidade_index = round(risco_index + protecao_index + (contexto_index * 0.35), 2)
    direcao_index = round(protecao_index - risco_index, 2)
    volatilidade_index = round(min(risco_index, protecao_index), 2)

    classificacao, leitura = classificar_estado_crise(
        risco_index=risco_index,
        protecao_index=protecao_index,
        contexto_index=contexto_index,
        intensidade_index=intensidade_index,
        direcao_index=direcao_index,
        volatilidade_index=volatilidade_index
    )

    return {
        "temas": resultados,
        "sumario": {
            "tokens_validos": total_tokens,
            "risco_bruto": round(risco_bruto, 2),
            "protecao_bruto": round(protecao_bruto, 2),
            "contexto_bruto": round(contexto_bruto, 2),
            "risco_index": risco_index,
            "protecao_index": protecao_index,
            "contexto_index": contexto_index,
            "intensidade_index": intensidade_index,
            "direcao_index": direcao_index,
            "volatilidade_index": volatilidade_index,
            "classificacao": classificacao,
            "leitura": leitura
        }
    }

def classificar_estado_crise(
    risco_index,
    protecao_index,
    contexto_index,
    intensidade_index,
    direcao_index,
    volatilidade_index
):
    """
    Regras heurísticas calibráveis.
    O objetivo aqui é gerar leitura operacional mais realista:
    - risco alto + direção negativa => CRÍTICO
    - risco e proteção altos ao mesmo tempo => TRANSIÇÃO INSTÁVEL
    - proteção dominante => DESACELERAÇÃO TÁTICA
    - baixa carga geral => BAIXA PRESSÃO / CONTROLADO

    Observação:
    Esses thresholds devem ser recalibrados com amostra histórica rotulada.
    """

    if intensidade_index < 4:
        return (
            "BAIXA PRESSÃO",
            "Baixa densidade semântica relevante. O material sugere pouca carga crítica ou registro insuficiente para leitura forte."
        )

    if risco_index >= 18 and direcao_index <= -6:
        return (
            "CRÍTICO",
            "Predomínio claro de escalada. Há concentração relevante de linguagem de ameaça, hostilidade ou autoaniquilação, sem contrapeso protetivo suficiente."
        )

    if risco_index >= 12 and protecao_index >= 10 and abs(direcao_index) < 6:
        return (
            "TRANSIÇÃO INSTÁVEL",
            "Há coexistência robusta de sinais de risco e de desescalada. O incidente parece em ponto de inflexão: existe janela de resolução, mas com risco residual alto."
        )

    if protecao_index >= 12 and direcao_index >= 6:
        return (
            "DESACELERAÇÃO DA AGRESSIVIDADE",
            "A carga emocional ainda pode ser alta, porém a direção predominante do diálogo aponta para rendição, vínculo ou cooperação. O risco não desapareceu, mas perdeu centralidade."
        )

    if protecao_index >= 8 and risco_index < 8:
        return (
            "CONTROLADO / COOPERATIVO",
            "Predominam sinais de cooperação, escuta e desescalada. O quadro sugere maior estabilização verbal do incidente."
        )

    if risco_index >= 10 and direcao_index < 0:
        return (
            "MODERADO COM VIÉS DE ESCALADA",
            "Existem sinais de deterioração ou endurecimento discursivo, embora sem configuração semântica forte o bastante para enquadramento como crítico."
        )

    return (
        "AMBIVALENTE / INDETERMINADO",
        "O material indica mistura de sinais ou densidade semântica intermediária. Recomenda-se leitura integrada com contexto operacional, timeline e interlocutor."
    )

# ============================================================
# 6. EXTRAÇÃO DE N-GRAMAS + INTERPRETAÇÃO FINAL
#    Mantém compatibilidade com o app.py
# ============================================================

def extrair_topicos_ngrams(texto):
    texto_norm = limpar_texto(texto)
    palavras_validas = [p for p in texto_norm.split() if p not in STOPWORDS_GATE and len(p) > 2]

    if len(palavras_validas) < 5:
        return ["*Texto insuficiente para análise semântica.*"]

    analise = analisar_crise_direcional(texto)
    temas = analise["temas"]
    resumo = analise["sumario"]

    resultado = []

    if temas:
        for i, item in enumerate(temas, start=1):
            polaridade = {
                "risco": "risco",
                "protecao": "proteção",
                "contexto": "contexto"
            }.get(item["tipo"], item["tipo"])

            texto_neg = ""
            if item["evidencias_negadas"] > 0:
                texto_neg = f" | negadas/contextualizadas: {item['evidencias_negadas']}"

            resultado.append(
                f"**Tema {i}:** {item['categoria']} "
                f"*(score ponderado: {item['score']:.2f} | evidências: {item['evidencias']} | polaridade: {polaridade}{texto_neg})*"
            )
    else:
        resultado.append("*Diálogo pulverizado: nenhum tema dominante detectado.*")

    # N-gramas estatísticos recorrentes
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

        pares = sorted(
            [(features[idx], int(scores[idx])) for idx in scores.argsort()[::-1] if scores[idx] > 1],
            key=lambda x: x[1],
            reverse=True
        )

        for feature, score in pares:
            resultado.append(f"*(Padrão de fala recorrente: '{feature.title()}' - {score}x)*")
    except Exception:
        pass

    # Bloco final: vetores e classificação direcional
    resultado.append("")
    resultado.append(f"**Vetor de Risco:** `{resumo['risco_index']:.2f}`")
    resultado.append(f"**Vetor de Proteção / Desescalada:** `{resumo['protecao_index']:.2f}`")
    resultado.append(f"**Vetor Contextual:** `{resumo['contexto_index']:.2f}`")
    resultado.append(f"**Intensidade Global do Incidente:** `{resumo['intensidade_index']:.2f}`")

    if resumo["direcao_index"] > 0:
        direcao_txt = "predomínio de desescalada"
    elif resumo["direcao_index"] < 0:
        direcao_txt = "predomínio de escalada"
    else:
        direcao_txt = "equilíbrio entre forças opostas"

    resultado.append(
        f"**Direção da Crise:** `{resumo['direcao_index']:.2f}` "
        f"*({direcao_txt})*"
    )
    resultado.append(f"**Volatilidade Semântica:** `{resumo['volatilidade_index']:.2f}`")
    resultado.append(f"**Classificação Final:** **{resumo['classificacao']}**")
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
# 8. TESTES ESTATÍSTICOS
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
            "msg": f"Erro estatístico: {str(e)}"
        }

def calcular_qui_quadrado(df_historico, col_cat1, col_cat2):
    df_limpo = df_historico[[col_cat1, col_cat2]].dropna().copy()

    if df_limpo.empty:
        return {"valido": False, "msg": "DataFrame vazio."}

    tabela = pd.crosstab(df_limpo[col_cat1], df_limpo[col_cat2])

    if tabela.shape[0] < 2 or tabela.shape[1] < 2:
        return {"valido": False, "msg": "Variância insuficiente nas categorias."}

    try:
        chi2, p_val, dof, expected = chi2_contingency(tabela)

        if (expected < 5).mean() > 0.2:
            return {
                "valido": False,
                "msg": "Frequências esperadas muito baixas (<5) violam premissas do teste."
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
            "msg": f"Erro no cálculo: {str(e)}"
        }

##INCLUSAO DE MOTOR ESTATISTICO PARA ANALISE VIA CHAT

def _normalizar_nome_coluna(texto):
    texto = str(texto)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.lower().strip()

def _achar_coluna(df, candidatos):
    if df is None or df.empty:
        return None

    mapa = {_normalizar_nome_coluna(col): col for col in df.columns}

    for candidato in candidatos:
        chave = _normalizar_nome_coluna(candidato)
        if chave in mapa:
            return mapa[chave]

    for col_norm, col_real in mapa.items():
        for candidato in candidatos:
            if _normalizar_nome_coluna(candidato) in col_norm:
                return col_real

    return None

def _tempo_para_minutos(valor):
    try:
        if isinstance(valor, list):
            valor = valor[0] if valor else None
        if pd.isna(valor) or valor in ["", "N/D", None]:
            return np.nan
        return float(valor) / 60.0
    except Exception:
        return np.nan

def sumarizar_banco_para_ia(df_quali, df_tec=None):
    """
    Resume a base filtrada para uso no chat com IA.
    Retorna apenas fatos agregados, evitando enviar a base bruta.
    """

    if df_quali is None or df_quali.empty:
        return {
            "n_total_ocorrencias": 0,
            "resolucoes": {},
            "tipologias": {},
            "modalidades": {},
            "negociadores": {},
            "tempo_medio_min": None,
            "top_tecnicas": {},
            "observacao": "Base vazia para os filtros atuais."
        }

    resumo = {
        "n_total_ocorrencias": int(len(df_quali)),
        "resolucoes": {},
        "tipologias": {},
        "modalidades": {},
        "negociadores": {},
        "tempo_medio_min": None,
        "top_tecnicas": {},
        "observacao": "Resumo gerado com sucesso."
    }

    col_resolucao = _achar_coluna(df_quali, ["Resolução", "RESOLUCAO"])
    col_tipologia = _achar_coluna(df_quali, ["Tipologia"])
    col_modalidade = _achar_coluna(df_quali, ["Modalidade do incidente", "Modalidade"])
    col_negociador = _achar_coluna(df_quali, ["Negociador Principal", "Negociador principal"])
    col_tempo = _achar_coluna(df_quali, ["Tempo de Negociação Real", "Tempo Total"])

    if col_resolucao:
        resumo["resolucoes"] = df_quali[col_resolucao].fillna("N/D").astype(str).value_counts().head(10).to_dict()

    if col_tipologia:
        resumo["tipologias"] = df_quali[col_tipologia].fillna("N/D").astype(str).value_counts().head(10).to_dict()

    if col_modalidade:
        resumo["modalidades"] = df_quali[col_modalidade].fillna("N/D").astype(str).value_counts().head(10).to_dict()

    if col_negociador:
        resumo["negociadores"] = df_quali[col_negociador].fillna("N/D").astype(str).value_counts().head(10).to_dict()

    if col_tempo:
        tempos = df_quali[col_tempo].apply(_tempo_para_minutos).dropna()
        if not tempos.empty:
            resumo["tempo_medio_min"] = round(float(tempos.mean()), 2)

    if df_tec is not None and not df_tec.empty:
        col_tecnica = _achar_coluna(df_tec, ["TÉCNICAS", "TECNICAS", "TÉCNICA", "TECNICA"])
        if col_tecnica:
            resumo["top_tecnicas"] = (
                df_tec[col_tecnica]
                .dropna()
                .astype(str)
                .str.strip()
                .replace("", np.nan)
                .dropna()
                .value_counts()
                .head(10)
                .to_dict()
            )

    return resumo    