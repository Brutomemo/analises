import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from sklearn.feature_extraction.text import CountVectorizer
from scipy.stats import spearmanr, chi2_contingency
from collections import Counter
import re
import unicodedata

# 1. LISTA DE BLOQUEIO DO GATE
STOPWORDS_GATE = {
    'o', 'a', 'os', 'as', 'um', 'uma', 'de', 'do', 'da', 'em', 'no', 'na', 'para', 'com', 'por', 'que', 'se', 'não',
    'é', 'dos', 'das', 'ao', 'aos', 'foi', 'houve', 'como', 'mas', 'ou', 'ele', 'ela', 'eu', 'você', 'voce', 'vc' 'nós', 'nos',
    'tá', 'já', 'só', 'mais', 'muito', 'isso', 'esse', 'essa', 'quando', 'onde', 'quem', 'causador', 'negociador',
    'principal', 'secundário', 'lider', 'equipe', 'ocorrência', 'incidente', 'forma', 'sim', 'ser', 'ter', 'fazer',
    'aqui', 'pra', 'vai', 'vou', 'está', 'falar', 'quer', 'então', 'coisa', 'aí', 'lá', 'né', 'bom', 'bem',
    'agora', 'tudo', 'porque', 'qual', 'pode', 'mesmo', 'dizer', 'acho', 'gente', 'dá'
}

NEGACOES = {'não', 'nao', 'nunca', 'jamais', 'nem', 'nenhum', 'nenhuma', 'sem'}
INTENSIFICADORES = {'muito', 'demais', 'bastante', 'extremamente', 'totalmente', 'cada vez mais'}
MARCADORES_URGENCIA = {'agora', 'hoje', 'já', 'ja', 'imediatamente', 'nesse momento', 'acabou'}

DICIONARIO_TATICO = {
    'Tentativa de Estabelecimento de Contato / Rapport': {
        'peso_base': 1.0,
        'termos': {
            'fala': 1.0, 'falar': 0.9, 'falou': 0.9, 'falando': 0.9,
            'ouve': 1.0, 'ouvir': 1.0, 'escuta': 1.1, 'conversa': 1.0,
            'comigo': 0.8, 'ajuda': 0.8, 'ajudar': 0.8, 'atenção': 0.9,
            'me escuta': 1.5, 'pode falar': 1.3, 'to aqui': 1.4, 'tô aqui': 1.4,
            'quero conversar': 1.5, 'pode me ouvir': 1.6
        }
    },
    'Vínculos Familiares e Afetivos': {
        'peso_base': 1.2,
        'termos': {
            'mãe': 1.5, 'pai': 1.5, 'filho': 1.8, 'filhos': 1.6, 'filha': 1.8,
            'mulher': 1.2, 'esposa': 1.3, 'marido': 1.3, 'irmão': 1.3, 'irmã': 1.3,
            'família': 1.4, 'parente': 1.1, 'namorada': 1.2,
            'meu filho': 2.0, 'minha filha': 2.0, 'minha mãe': 1.8, 'minha família': 1.7
        }
    },
    'Ganchos Morais e Espirituais': {
        'peso_base': 1.0,
        'termos': {
            'deus': 1.5, 'jesus': 1.5, 'igreja': 1.1, 'pastor': 1.2, 'fé': 1.2,
            'orar': 1.3, 'rezar': 1.3, 'perdoar': 1.4, 'pecado': 1.2, 'bíblia': 1.2,
            'pelo amor de deus': 2.0, 'deus me perdoe': 2.2, 'so deus sabe': 1.8, 'só deus sabe': 1.8
        }
    },
    'Fatores Socioeconômicos / Frustração': {
        'peso_base': 1.0,
        'termos': {
            'emprego': 1.2, 'dinheiro': 1.0, 'dívida': 1.3, 'trabalho': 1.0, 'pagar': 1.0,
            'conta': 1.0, 'patrão': 1.2, 'justiça': 1.1, 'injustiça': 1.5, 'roubo': 1.5,
            'acidente': 1.1, 'traição': 1.6, 'perdi meu emprego': 2.0, 'não tenho nada': 1.8,
            'fui traído': 1.9, 'nao tenho nada': 1.8
        }
    },
    'Ideação Suicida / Desesperança (Crise Interna)': {
        'peso_base': 2.0,
        'termos': {
            'morrer': 2.0, 'pular': 2.5, 'minha vida': 1.4, 'dor': 1.1, 'sofrimento': 1.3,
            'não aguento': 2.0, 'nao aguento': 2.0, 'ninguém': 1.0, 'sozinho': 1.5, 'remédio': 1.1,
            'desisto': 2.0, 'acabar com tudo': 3.0, 'não quero mais viver': 3.5, 'nao quero mais viver': 3.5,
            'quero morrer': 3.5, 'vou me matar': 4.0, 'minha vida não vale nada': 3.0,
            'minha vida nao vale nada': 3.0, 'não tem mais jeito': 2.5, 'nao tem mais jeito': 2.5
        }
    },
    'Risco à Integridade / Hostilidade (Crise Externa)': {
        'peso_base': 2.5,
        'termos': {
            'matar': 3.0, 'arma': 2.5, 'faca': 2.5, 'tiro': 3.0, 'sangue': 2.0,
            'polícia': 1.1, 'policia': 1.1, 'farda': 1.0, 'afasta': 1.5, 'refém': 3.5,
            'pipoco': 2.5, 'bala': 2.5, 'vou matar': 4.0, 'chega perto eu mato': 4.5,
            'to armado': 3.5, 'tô armado': 3.5, 'não chega': 2.0, 'nao chega': 2.0
        }
    },
    'Demandas e Exigências (Instrumentais)': {
        'peso_base': 1.0,
        'termos': {
            'quero': 0.8, 'exijo': 1.5, 'traz': 1.0, 'chama': 0.8, 'juiz': 1.3,
            'imprensa': 1.8, 'reportagem': 1.4, 'advogado': 1.5, 'carro': 1.1, 'fuga': 1.3,
            'água': 0.8, 'comida': 0.8, 'fome': 0.8, 'cigarro': 0.9,
            'quero falar com': 1.5, 'preciso de': 1.0, 'me traz': 1.2
        }
    },
    'Sinalização de Rendição / Desescalada de violência': {
        'peso_base': 1.5,
        'termos': {
            'entregar': 2.0, 'sair': 1.5, 'porta': 0.7, 'abrir': 1.5, 'desce': 1.0, 'mão': 0.7,
            'calma': 1.8, 'tranquilo': 1.6, 'acabou': 2.0, 'paz': 1.8, 'concordo': 1.5, 'beleza': 1.0,
            'to saindo': 2.5, 'tô saindo': 2.5, 'pode entrar': 2.5, 'não vou fazer nada': 2.0,
            'nao vou fazer nada': 2.0, 'me rendo': 3.0, 'ta bom': 1.5, 'tá bom': 1.5
        }
    },
    'Ambivalência / Pedido de Ajuda Velado': {
        'peso_base': 1.8,
        'termos': {
            'não sei': 1.2, 'nao sei': 1.2, 'to confuso': 1.5, 'tô confuso': 1.5,
            'não consigo': 1.3, 'nao consigo': 1.3, 'me ajuda': 2.0, 'não sei o que fazer': 2.5,
            'nao sei o que fazer': 2.5, 'quero mas não consigo': 3.0, 'quero mas nao consigo': 3.0,
            'to com medo': 2.0, 'tô com medo': 2.0, 'alguém me ajuda': 2.5, 'alguem me ajuda': 2.5
        }
    }
}

PESO_RISCO_CATEGORIA = {
    'Ideação Suicida / Desesperança (Crise Interna)': 1.35,
    'Risco à Integridade / Hostilidade': 1.45,
    'Ambivalência / Pedido de Ajuda Velado': 1.15,
    'Sinalização de Rendição / Desescalada de violência': -0.55,
}


def normalizar_texto(texto):
    if not isinstance(texto, str) or not texto.strip():
        return ''
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto


def limpar_texto(texto):
    return normalizar_texto(texto)


def gerar_wordcloud(texto):
    texto_limpo = limpar_texto(texto)
    if len(texto_limpo.split()) < 3:
        return None

    wc = WordCloud(
        background_color='rgba(15, 15, 15, 1)',
        width=600,
        height=300,
        stopwords=STOPWORDS_GATE,
        colormap='Oranges',
        max_words=40,
        mode='RGBA'
    ).generate(texto_limpo)

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    fig.patch.set_facecolor('#0f0f0f')
    return fig


def tokenizar(texto):
    return limpar_texto(texto).split()


def gerar_ngrams_tokens(tokens, n):
    if len(tokens) < n:
        return []
    return [' '.join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def extrair_ngrams_relevantes(texto, top_k=5):
    tokens = [p for p in tokenizar(texto) if p not in STOPWORDS_GATE and len(p) > 2]
    if len(tokens) < 5:
        return []

    frequencias = Counter()
    for n in (2, 3):
        frequencias.update(gerar_ngrams_tokens(tokens, n))

    return frequencias.most_common(top_k)


def analisar_valencia_termo(tokens, indice_termo):
    janela_inicio = max(0, indice_termo - 3)
    janela = tokens[janela_inicio:indice_termo]
    negado = any(token in NEGACOES for token in janela)
    intensificado = any(token in INTENSIFICADORES for token in janela)
    urgente = any(token in MARCADORES_URGENCIA for token in janela)
    return negado, intensificado, urgente


def calcular_score_categorias(texto):
    texto_norm = limpar_texto(texto)
    tokens = texto_norm.split()
    scores = {}
    detalhes = {}

    for categoria, config in DICIONARIO_TATICO.items():
        score_categoria = 0.0
        evidencias = []

        for termo, peso in config['termos'].items():
            termo_norm = limpar_texto(termo)
            termo_tokens = termo_norm.split()
            if not termo_tokens:
                continue

            for idx in range(len(tokens) - len(termo_tokens) + 1):
                trecho = tokens[idx:idx + len(termo_tokens)]
                if trecho != termo_tokens:
                    continue

                negado, intensificado, urgente = analisar_valencia_termo(tokens, idx)
                peso_final = peso * config['peso_base']

                if negado:
                    peso_final *= -0.45
                if intensificado:
                    peso_final *= 1.3
                if urgente:
                    peso_final *= 1.15

                score_categoria += peso_final
                evidencias.append({
                    'termo': termo,
                    'peso_original': peso,
                    'peso_final': round(peso_final, 2),
                    'negado': negado,
                    'intensificado': intensificado,
                    'urgente': urgente,
                })

        if score_categoria != 0:
            scores[categoria] = round(score_categoria, 2)
            detalhes[categoria] = sorted(evidencias, key=lambda item: abs(item['peso_final']), reverse=True)

    scores = dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))
    return scores, detalhes


def calcular_indice_global_crise(scores):
    if not scores:
        return 0.0

    indice = 0.0
    for categoria, score in scores.items():
        multiplicador = PESO_RISCO_CATEGORIA.get(categoria, 1.0)
        indice += score * multiplicador

    return round(max(indice, 0.0), 2)


def classificar_risco(indice_global):
    if indice_global >= 18:
        return '🔴 CRÍTICO'
    if indice_global >= 8:
        return '🟡 MODERADO'
    return '🟢 BAIXO'


def analisar_por_interlocutor(texto_causador='', texto_principal='', texto_secundario=''):
    blocos = {
        'causador': texto_causador or '',
        'negociador_principal': texto_principal or '',
        'negociador_secundario': texto_secundario or '',
    }
    resultado = {}

    for papel, texto in blocos.items():
        scores, detalhes = calcular_score_categorias(texto)
        resultado[papel] = {
            'scores': scores,
            'detalhes': detalhes,
            'indice_global': calcular_indice_global_crise(scores),
            'classificacao_risco': classificar_risco(calcular_indice_global_crise(scores)),
            'ngrams_relevantes': extrair_ngrams_relevantes(texto),
        }

    texto_global = ' '.join(blocos.values()).strip()
    scores_globais, detalhes_globais = calcular_score_categorias(texto_global)
    indice_global = calcular_indice_global_crise(scores_globais)
    resultado['global'] = {
        'scores': scores_globais,
        'detalhes': detalhes_globais,
        'indice_global': indice_global,
        'classificacao_risco': classificar_risco(indice_global),
        'ngrams_relevantes': extrair_ngrams_relevantes(texto_global),
    }
    return resultado


def extrair_topicos_ngrams(texto):
    texto_limpo = limpar_texto(texto)
    palavras = [p for p in texto_limpo.split() if p not in STOPWORDS_GATE and len(p) > 2]
    texto_processado = ' '.join(palavras)

    if len(texto_processado.split()) < 5:
        return ['*Texto insuficiente para análise semântica.*']

    scores, detalhes = calcular_score_categorias(texto)
    resultado = []

    if scores:
        for i, (tema, score) in enumerate(scores.items(), start=1):
            qtd_evidencias = len(detalhes.get(tema, []))
            resultado.append(
                f"**Tema {i}:** {tema} *(score ponderado: {score:.2f} | evidências: {qtd_evidencias})*"
            )

    try:
        vectorizer = CountVectorizer(ngram_range=(2, 3), max_features=5)
        counts = vectorizer.fit_transform([texto_processado])
        features = vectorizer.get_feature_names_out()
        scores_ngram = counts.toarray()[0]
        for idx in scores_ngram.argsort()[::-1]:
            if scores_ngram[idx] > 1:
                resultado.append(
                    f"*(Padrão de fala recorrente: '{features[idx].title()}' - {scores_ngram[idx]}x)*"
                )
    except Exception:
        pass

    indice_global = calcular_indice_global_crise(scores)
    if indice_global > 0:
        resultado.append(
            f"**Índice Global de Crise:** {indice_global:.2f} ({classificar_risco(indice_global)})"
        )

    return resultado if resultado else ['*Diálogo pulverizado: Nenhum tema dominante detectado.*']

def gerar_treemap(df_tecnicas):
    col_alvo = "TÉCNICAS" 
    
    if df_tecnicas.empty or col_alvo not in df_tecnicas.columns:
        return None

    df_tecnicas = df_tecnicas.copy()
    df_tecnicas['label_treemap'] = df_tecnicas[col_alvo].astype(str) + " - " + df_tecnicas['frequencia'].astype(str)
        
    fig = px.treemap(
        df_tecnicas, 
        path=['label_treemap'], 
        values='frequencia',
        color='frequencia',
        color_continuous_scale='Oranges',
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

def calcular_spearman(df_historico, col_x, col_y):
    df_limpo = df_historico[[col_x, col_y]].dropna().copy()
    df_limpo = df_limpo[(df_limpo[col_x] != 'N/D') & (df_limpo[col_y] != 'N/D')]
    
    if len(df_limpo) < 3:
        return {'valido': False, 'p_value': 0.0, 'rho': 0.0, 'msg': 'Dados insuficientes (N<3).'}
        
    try:
        x = pd.to_numeric(df_limpo[col_x], errors='coerce')
        y = pd.to_numeric(df_limpo[col_y], errors='coerce')
        
        # Remover NaNs gerados pela conversão
        mask = ~np.isnan(x) & ~np.isnan(y)
        x = x[mask]
        y = y[mask]

        if len(x) < 3:
             return {'valido': False, 'msg': 'Dados numéricos insuficientes.'}

        rho, p_val = spearmanr(x, y)
        return {'valido': True, 'rho': float(rho), 'p_value': float(p_val), 'msg': 'Sucesso.'}
    except Exception as e:
        return {'valido': False, 'rho': 0.0, 'p_value': 0.0, 'msg': f'Erro estatístico: {str(e)}'}

def calcular_qui_quadrado(df_historico, col_cat1, col_cat2):
    df_limpo = df_historico[[col_cat1, col_cat2]].dropna().copy()
    if df_limpo.empty: return {'valido': False, 'msg': 'DataFrame vazio.'}
    
    tabela = pd.crosstab(df_limpo[col_cat1], df_limpo[col_cat2])
    if tabela.shape[0] < 2 or tabela.shape[1] < 2:
        return {'valido': False, 'msg': 'Variância insuficiente nas categorias.'}
    
    try:
        chi2, p_val, dof, expected = chi2_contingency(tabela)
        # Validação estatística: P-valor só é confiável se frequências esperadas >= 5 na maioria das células
        if (expected < 5).mean() > 0.2:
            return {'valido': False, 'msg': 'Frequências esperadas muito baixas (<5) violam premissas do teste.'}
            
        return {'valido': True, 'chi2': float(chi2), 'p_value': float(p_val), 'tabela': tabela}
    except Exception as e:
        return {'valido': False, 'msg': f'Erro no cálculo: {str(e)}'}