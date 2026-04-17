import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from sklearn.feature_extraction.text import CountVectorizer
from scipy.stats import spearmanr, chi2_contingency
import re

# 1. LISTA DE BLOQUEIO DO GATE
STOPWORDS_GATE = {
    'o','a','os','as','um','uma','de','do','da','em','no','na','para','com','por','que','se','não',
    'é','dos','das','ao','aos','foi','houve','como','mas','ou','ele','ela','eu','você','nós','nos',
    'tá','já','só','mais','muito','isso','esse','essa','quando','onde','quem','causador','negociador',
    'principal','secundário','lider','equipe','ocorrência','incidente','forma', 'sim', 'ser', 'ter', 'fazer',
    'aqui', 'pra', 'vai', 'vou', 'está', 'falar', 'quer', 'então', 'coisa', 'aí', 'lá', 'né', 'bom', 'bem',
    'agora', 'tudo', 'porque', 'qual', 'pode', 'mesmo', 'dizer', 'acho', 'gente', 'dá'
}

def limpar_texto(texto):
    if not isinstance(texto, str) or not texto.strip():
        return ""
    texto = re.sub(r'[^a-záàâãéèêíïóôõöúçñ\s]', ' ', texto.lower())
    return texto

def gerar_wordcloud(texto):
    texto_limpo = limpar_texto(texto)
    if len(texto_limpo.split()) < 3:
        return None

    wc = WordCloud(
        background_color="rgba(15, 15, 15, 1)", 
        width=600, height=300,
        stopwords=STOPWORDS_GATE, 
        colormap="Oranges", 
        max_words=40,
        mode="RGBA"
    ).generate(texto_limpo)
    
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis("off")
    fig.patch.set_facecolor('#0f0f0f') 
    return fig

# --- DICIONÁRIO PARA TEMAS GLOBAIS ---
DICIONARIO_TATICO = {
    "Tentativa de Estabelecimento de Contato / Rapport": [
        "fala", "falar", "falou", "falando", "comigo", "ouvir", "ouve", "escuta", 
        "atende", "conversa", "conversar", "ajuda", "ajudar", "ajudando", "olha", "atenção"
    ],
    "Vínculos Familiares e Afetivos": [
        "mãe", "pai", "filho", "filhos", "filha", "mulher", "esposa", "marido", 
        "padrasto", "irmão", "irmã", "família", "parente", "namorada"
    ],
    "Ganchos Morais e Espirituais": [
        "deus", "jesus", "igreja", "pastor", "fé", "orar", "rezar", "perdoar", "pecado", "bíblia"
    ],
    "Fatores Socioeconômicos / Frustração": [
        "emprego", "dinheiro", "dívida", "trabalho", "pagar", "conta", "patrão", 
        "justiça", "injustiça", "roubo", "acidente", "traição"
    ],
    "Ideação Suicida / Desesperança (Crise Interna)": [
        "morrer", "pular", "acabar com tudo", "minha vida", "dor", "sofrimento", 
        "não aguento", "ninguém", "sozinho", "remédio", "desisto"
    ],
    "Risco à Integridade / Hostilidade (Crise Externa)": [
        "matar", "arma", "faca", "tiro", "sangue", "polícia", "farda", "afasta", 
        "chegar perto", "refém", "pipoco", "bala"
    ],
    "Demandas e Exigências (Instrumentais)": [
        "quero", "exijo", "traz", "chama", "juiz", "imprensa", "reportagem", "advogado", 
        "carro", "fuga", "água", "comida", "fome", "cigarro"
    ],
    "Sinalização de Rendição / Desescalada": [
        "entregar", "sair", "porta", "abrir", "desce", "mão", "calma", "tranquilo", 
        "acabou", "paz", "concordo", "beleza"
    ]
}

def extrair_topicos_ngrams(texto):
    texto_limpo = limpar_texto(texto)
    palavras = [p for p in texto_limpo.split() if p not in STOPWORDS_GATE and len(p) > 2]
    texto_processado = " ".join(palavras)
    
    if len(texto_processado.split()) < 5:
        return ["*Texto insuficiente para análise semântica.*"]
    
    temas_encontrados = {}
    
    # NOVA LÓGICA DE CIÊNCIA DE DADOS: Busca por Word Boundaries (Regex)
    # Permite capturar frases compostas (ex: "acabar com tudo") e evita falsos positivos
    for categoria, palavras_chave in DICIONARIO_TATICO.items():
        ocorrencias = 0
        for termo in palavras_chave:
            # Busca o termo exato no texto original (em minúsculas) para preservar N-Grams
            ocorrencias += len(re.findall(rf'\b{termo}\b', texto.lower()))
        
        if ocorrencias > 0:
            temas_encontrados[categoria] = ocorrencias

    resultado = []
    if temas_encontrados:
        temas_ordenados = sorted(temas_encontrados.items(), key=lambda x: x[1], reverse=True)
        for i, (tema, peso) in enumerate(temas_ordenados):
            resultado.append(f"**Tema {i+1}:** {tema} *(Evidência semântica: {peso} menções relacionadas)*")
    
    # Motor Scikit-Learn de N-Grams Estatísticos não-supervisionados
    try:
        vectorizer = CountVectorizer(ngram_range=(2, 3), max_features=2)
        counts = vectorizer.fit_transform([texto_processado])
        features = vectorizer.get_feature_names_out()
        scores = counts.toarray()[0]
        for i, idx in enumerate(scores.argsort()[::-1]):
            if scores[idx] > 1:
                resultado.append(f"*(Padrão de Fala Recorrente: '{features[idx].title()}' - {scores[idx]}x)*")
    except:
        pass 

    return resultado if resultado else ["*Diálogo pulverizado: Nenhum tema dominante detectado.*"]

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
        font_color="#FFFFFF"
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