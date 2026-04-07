import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from sklearn.feature_extraction.text import CountVectorizer
from scipy.stats import spearmanr, chi2_contingency
import re

# 1. LISTA DE BLOQUEIO AGRESSIVA (Fim das alucinações nas nuvens e tópicos)
STOPWORDS_GATE = {
    'o','a','os','as','um','uma','de','do','da','em','no','na','para','com','por','que','se','não',
    'é','dos','das','ao','aos','foi','houve','como','mas','ou','ele','ela','eu','você','nós','nos',
    'tá','já','só','mais','muito','isso','esse','essa','quando','onde','quem','causador','negociador',
    'principal','secundário','lider','equipe','ocorrência','incidente','forma', 'sim', 'ser', 'ter', 'fazer',
    'aqui', 'pra', 'vai', 'vou', 'está', 'falar', 'quer', 'então', 'coisa', 'aí', 'lá', 'né', 'bom', 'bem',
    'agora', 'tudo', 'porque', 'qual', 'pode', 'mesmo', 'dizer', 'acho', 'gente', 'dá'
}

def limpar_texto(texto):
    """Remove pontuações e números, deixando apenas palavras em minúsculo."""
    if not isinstance(texto, str) or not texto.strip():
        return ""
    texto = re.sub(r'[^a-záàâãéèêíïóôõöúçñ\s]', ' ', texto.lower())
    return texto

def gerar_wordcloud(texto):
    """Gera a nuvem de palavras com design Dark/Orange e sem palavras inúteis."""
    texto_limpo = limpar_texto(texto)
    if len(texto_limpo.split()) < 3:
        return None # Retorna nulo se não houver texto suficiente

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
    """
    Motor Híbrido: Extrai n-grams matemáticos e cruza com a Ontologia Tática do GATE
    para devolver o entendimento semântico da ocorrência de forma dinâmica.
    """
    texto_limpo = limpar_texto(texto)
    palavras = [p for p in texto_limpo.split() if p not in STOPWORDS_GATE and len(p) > 2]
    texto_processado = " ".join(palavras)
    
    if len(texto_processado.split()) < 5:
        return ["*Texto insuficiente para análise semântica.*"]
    
    temas_encontrados = {}
    
    # Varredura Semântica
    for categoria, palavras_chave in DICIONARIO_TATICO.items():
        ocorrencias = sum(1 for p in palavras if p in palavras_chave)
        if ocorrencias > 0:
            temas_encontrados[categoria] = ocorrencias

    resultado = []
    
    # 1. Se encontrou contexto semântico na doutrina do GATE
    if temas_encontrados:
        # Ordena as categorias que mais apareceram
        temas_ordenados = sorted(temas_encontrados.items(), key=lambda x: x[1], reverse=True)
        for i, (tema, peso) in enumerate(temas_ordenados):
            resultado.append(f"**Tema {i+1}:** {tema} *(Evidência semântica: {peso} menções relacionadas)*")
    
    # 2. Padrão matemático bruto (O que o Scikit-Learn pegou de repetição pura)
    try:
        vectorizer = CountVectorizer(ngram_range=(2, 3), max_features=2)
        counts = vectorizer.fit_transform([texto_processado])
        features = vectorizer.get_feature_names_out()
        scores = counts.toarray()[0]
        
        for i, idx in enumerate(scores.argsort()[::-1]):
            if scores[idx] > 1: # Só mostra se repetiu de verdade
                resultado.append(f"*(Padrão de Fala Recorrente: '{features[idx].title()}' - {scores[idx]}x)*")
    except:
        pass

    if not resultado:
        return ["*Diálogo pulverizado: Nenhum tema dominante ou padrão repetitivo detectado.*"]
        
    return resultado

def gerar_treemap(df_tecnicas):
    """
    Gera o Mapa de Árvore (Item 34) aplicando o degradê Laranja baseado na frequência.
    Espera um DataFrame com as colunas ['tecnica', 'frequencia', 'percepcao']
    """
    if df_tecnicas.empty or 'tecnica' not in df_tecnicas.columns or 'frequencia' not in df_tecnicas.columns:
        return None
        
    fig = px.treemap(
        df_tecnicas, 
        path=['tecnica'], 
        values='frequencia', 
        color='frequencia', # AQUI ESTÁ A CORREÇÃO DO DEGRADÊ
        color_continuous_scale='Oranges',
        title="Mapeamento de Técnicas Empregadas"
    )
    
    # Fundo transparente e texto branco para casar com a UI do Streamlit
    fig.update_layout(
        margin=dict(t=30, b=0, l=0, r=0), 
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FFFFFF"
    )
    return fig

# =========================================================
# MOTOR ESTATÍSTICO (NOVO)
# =========================================================

def calcular_spearman(df_historico, col_x, col_y):
    """
    Calcula a correlação de Spearman entre duas variáveis ordinais/contínuas no DataFrame.
    """
    # Remove valores nulos ou N/D para a matemática não quebrar
    df_limpo = df_historico[[col_x, col_y]].dropna().copy()
    df_limpo = df_limpo[(df_limpo[col_x] != 'N/D') & (df_limpo[col_y] != 'N/D')]
    
    if len(df_limpo) < 3: # Precisamos de pelo menos 3 pontos
        return {'valido': False, 'p_value': 0.0, 'rho': 0.0, 'msg': 'Dados insuficientes (N<3).'}
        
    try:
        # Tenta converter para numérico
        x = pd.to_numeric(df_limpo[col_x])
        y = pd.to_numeric(df_limpo[col_y])
        
        rho, p_val = spearmanr(x, y)
        
        return {
            'valido': True,
            'rho': float(rho),
            'p_value': float(p_val),
            'msg': 'Cálculo realizado.'
        }
    except Exception as e:
        return {'valido': False, 'rho': 0.0, 'p_value': 0.0, 'erro': str(e)}

def calcular_qui_quadrado(df_historico, col_categoria_1, col_categoria_2):
    """
    Calcula o Qui-Quadrado (Chi-Square) para ver se há dependência entre duas categorias.
    """
    df_limpo = df_historico[[col_categoria_1, col_categoria_2]].dropna().copy()
    df_limpo = df_limpo[(df_limpo[col_categoria_1] != 'N/D') & (df_limpo[col_categoria_2] != 'N/D')]
    
    if df_limpo.empty:
        return {'valido': False, 'p_value': 0.0}
        
    # Cria a tabela de contingência cruzada
    tabela_contingencia = pd.crosstab(df_limpo[col_categoria_1], df_limpo[col_categoria_2])
    
    # O teste exige pelo menos uma matriz 2x2
    if tabela_contingencia.shape[0] < 2 or tabela_contingencia.shape[1] < 2:
        return {'valido': False, 'p_value': 0.0, 'msg': 'Variância insuficiente para Qui-Quadrado.'}
    
    try:
        chi2, p_val, dof, expected = chi2_contingency(tabela_contingencia)
        return {
            'valido': True,
            'chi2': float(chi2),
            'p_value': float(p_val),
            'tabela': tabela_contingencia
        }
    except Exception as e:
        return {'valido': False, 'erro': str(e)}

def calcular_spearman_arrays(array_x, array_y):
    """
    Calcula a correlação diretamente de duas listas/arrays (Mantido para compatibilidade legado).
    """
    if len(array_x) < 3 or len(array_y) < 3 or len(array_x) != len(array_y):
        return {"rho": None, "p_value": None, "valido": False, "msg": "Dados insuficientes (N<3)."}
        
    rho, p_value = spearmanr(array_x, array_y)
    return {"rho": rho, "p_value": p_value, "valido": True, "msg": "Cálculo realizado."}