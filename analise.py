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

# --- DICIONÁRIO TÁTICO ---
DICIONARIO_TATICO = {
    "Tentativa de Estabelecimento de Contato / Rapport": ["fala", "comigo", "ouvir", "escuta", "atende", "conversa", "ajudar", "olha", "atenção"],
    "Vínculos Familiares e Afetivos": ["mãe", "pai", "filho", "filha", "mulher", "esposa", "marido", "padrasto", "irmão", "família", "parente"],
    "Fatores Socioeconômicos / Frustração": ["emprego", "dinheiro", "dívida", "trabalho", "pagar", "conta", "patrão", "justiça", "acidente"],
    "Exigências e Demandas do Causador": ["quero", "exijo", "traz", "chama", "juiz", "imprensa", "advogado", "carro", "fuga"],
    "Risco à Integridade / Agressividade": ["matar", "morrer", "arma", "faca", "tiro", "sangue", "acabar", "ninguém", "pular"],
    "Sinalização de Rendição / Desescalada": ["entregar", "sair", "porta", "abrir", "desce", "mão", "calma", "tranquilo", "acabou"]
}

def extrair_topicos_ngrams(texto):
    texto_limpo = limpar_texto(texto)
    palavras = [p for p in texto_limpo.split() if p not in STOPWORDS_GATE and len(p) > 2]
    texto_processado = " ".join(palavras)
    
    if len(texto_processado.split()) < 5:
        return ["*Texto insuficiente para análise semântica.*"]
    
    temas_encontrados = {}
    for categoria, palavras_chave in DICIONARIO_TATICO.items():
        ocorrencias = sum(1 for p in palavras if p in palavras_chave)
        if ocorrencias > 0:
            temas_encontrados[categoria] = ocorrencias

    resultado = []
    if temas_encontrados:
        temas_ordenados = sorted(temas_encontrados.items(), key=lambda x: x[1], reverse=True)
        for i, (tema, peso) in enumerate(temas_ordenados):
            resultado.append(f"**Tema {i+1}:** {tema} *(Evidência semântica: {peso} menções relacionadas)*")
    
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

# =========================================================
# GERAÇÃO DE GRÁFICOS (TREEMAP ATUALIZADO)
# =========================================================

def gerar_treemap(df_tecnicas):
    """
    Treemap com Frequência Absoluta (Contagem) e Relativa (%).
    Mapeia a coluna 'TÉCNICAS' do Airtable.
    """
    # Padronização de coluna para garantir leitura
    col_alvo = "TÉCNICAS"
    if col_alvo not in df_tecnicas.columns:
        # Tenta localizar por aproximação se o nome vier diferente
        cols = [c for c in df_tecnicas.columns if "TECNICA" in c.upper()]
        if cols: col_alvo = cols[0]
        else: return None
        
    if df_tecnicas.empty:
        return None

    # Cálculo da Frequência Relativa (%)
    total_frequencia = df_tecnicas['frequencia'].sum()
    df_tecnicas['freq_relativa'] = (df_tecnicas['frequencia'] / total_frequencia * 100).round(1)
    
    # Criando o label customizado: Nome da Técnica + Qtd + %
    df_tecnicas['label_completo'] = (
        df_tecnicas[col_alvo] + "<br>" +
        "Qtd: " + df_tecnicas['frequencia'].astype(str) + "<br>" +
        df_tecnicas['freq_relativa'].astype(str) + "%"
    )
        
    fig = px.treemap(
        df_tecnicas, 
        path=['label_completo'], # Usa o novo label com numerador
        values='frequencia', 
        color='frequencia',
        color_continuous_scale='Oranges',
        title="Dominância de Técnicas (Frequência Absoluta e Relativa)"
    )
    
    fig.update_layout(
        margin=dict(t=50, b=10, l=10, r=10), 
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FFFFFF"
    )
    
    # Remove a legenda de cor se preferir um visual mais limpo
    fig.update_coloraxes(showscale=False)
    
    return fig

# =========================================================
# MOTOR ESTATÍSTICO INFERENCIAL
# =========================================================

def calcular_spearman(df_historico, col_x, col_y):
    df_limpo = df_historico[[col_x, col_y]].dropna().copy()
    df_limpo = df_limpo[(df_limpo[col_x] != 'N/D') & (df_limpo[col_y] != 'N/D')]
    
    if len(df_limpo) < 3:
        return {'valido': False, 'p_value': 0.0, 'rho': 0.0, 'msg': 'Dados insuficientes (N<3).'}
        
    try:
        x = pd.to_numeric(df_limpo[col_x])
        y = pd.to_numeric(df_limpo[col_y])
        rho, p_val = spearmanr(x, y)
        return {'valido': True, 'rho': float(rho), 'p_value': float(p_val), 'msg': 'Sucesso.'}
    except:
        return {'valido': False, 'rho': 0.0, 'p_value': 0.0, 'msg': 'Erro na conversão numérica.'}

def calcular_qui_quadrado(df_historico, col_cat1, col_cat2):
    df_limpo = df_historico[[col_cat1, col_cat2]].dropna().copy()
    if df_limpo.empty: return {'valido': False}
    
    tabela = pd.crosstab(df_limpo[col_cat1], df_limpo[col_cat2])
    if tabela.shape[0] < 2 or tabela.shape[1] < 2:
        return {'valido': False, 'msg': 'Variância insuficiente.'}
    
    try:
        chi2, p_val, dof, expected = chi2_contingency(tabela)
        return {'valido': True, 'chi2': float(chi2), 'p_value': float(p_val), 'tabela': tabela}
    except:
        return {'valido': False}