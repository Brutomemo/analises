"""
ANÁLISE DE PERFIL DE NEGOCIADORES
Comparação: Escuta Ativa vs Persuasão/Influência
Testes estatísticos: ANOVA, Chi-quadrado, K-means
Geração de grafos interativos com Pyvis
"""

import pandas as pd
import numpy as np
from scipy.stats import f_oneway, chi2_contingency
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import plotly.graph_objects as go
import plotly.express as px
from collections import Counter
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import streamlit as st

# ============================================================
# 1. CLASSIFICAÇÃO DE TÉCNICAS (MODULAR - FÁCIL EDITAR)
# ============================================================

TECNICAS_ESCUTA_ATIVA = [
    "Paráfrase",
    "Declarações empáticas",
    "Classificação de emoções",
    "Classificação das Emoções",
    "Resumo",
    "Mínimo de motivação",
]

TECNICAS_PERSUASAO = [
    "Desconstrução",
    "Compromisso e coerência",
    "Reciprocidade",
    "Escassez",
    "Medo",
    "Inquietação",
    "Escolha condicionada",
    "Rejeição + Recuo",
    "Rejeição seguida de recuo",
    "Distração",
]

def classificar_tecnica(tecnica_nome):
    """Classifica uma técnica em Escuta Ativa (1) ou Persuasão (-1)"""
    tecnica_limpa = str(tecnica_nome).strip().lower()
    
    for t in TECNICAS_ESCUTA_ATIVA:
        if t.lower() in tecnica_limpa:
            return "Escuta Ativa"
    
    for t in TECNICAS_PERSUASAO:
        if t.lower() in tecnica_limpa:
            return "Persuasão"
    
    return "Não classificada"

# ============================================================
# 2. CÁLCULO DE SCORE DE TENDÊNCIA (PONDERADO POR EFETIVIDADE)
# ============================================================



def calcular_score_tendencia(df_tecnicas):
    """
    Calcula score de tendência para cada negociador.
    Score = (Soma atitudes Escuta - Soma atitudes Persuasão) / Total × 100
    
    Resultado: -100 (Persuasão) a +100 (Escuta Ativa)
    """

    # CORRIGIR: Garantir que NEGOCIADOR PRINCIPAL é string, não lista
    df_tecnicas['NEGOCIADOR PRINCIPAL'] = df_tecnicas['NEGOCIADOR PRINCIPAL'].apply(
        lambda x: x[0] if isinstance(x, list) else str(x)
    )
    
    # Classificar técnicas
    df_tecnicas['grupo'] = df_tecnicas['TÉCNICAS'].apply(classificar_tecnica)
    
    # Converter ATITUDE DO CAUSADOR para numérico
    df_tecnicas['atitude_num'] = df_tecnicas['ATITUDE DO CAUSADOR'].apply(
        lambda x: {
            '🟢 Reação Positiva': 1,
            'Reação Positiva': 1,
            '1': 1,
            1: 1,
            1.0: 1,
            '⚪ Reação Neutra': 0,
            'Reação Neutra': 0,
            '0': 0,
            0: 0,
            0.0: 0,
            '🔴 Reação Negativa': -1,
            'Reação Negativa': -1,
            '-1': -1,
            -1: -1,
            -1.0: -1,
        }.get(x, np.nan)
    )
    
    # Classificar técnicas
    df_tecnicas['grupo'] = df_tecnicas['TÉCNICAS'].apply(classificar_tecnica)
    
    # Converter ATITUDE DO CAUSADOR para numérico
    df_tecnicas['atitude_num'] = df_tecnicas['ATITUDE DO CAUSADOR'].apply(
        lambda x: {
            '🟢 Reação Positiva': 1,
            'Reação Positiva': 1,
            '1': 1,
            1: 1,
            '⚪ Reação Neutra': 0,
            'Reação Neutra': 0,
            '0': 0,
            0: 0,
            '🔴 Reação Negativa': -1,
            'Reação Negativa': -1,
            '-1': -1,
            -1: -1,
        }.get(x, np.nan)
    )
    
    resultados = []
    
    for negociador in df_tecnicas['NEGOCIADOR PRINCIPAL'].unique():
        df_neg = df_tecnicas[df_tecnicas['NEGOCIADOR PRINCIPAL'] == negociador]
        
        # Escuta Ativa
        escuta = df_neg[df_neg['grupo'] == 'Escuta Ativa']
        soma_escuta = escuta['atitude_num'].sum()
        count_escuta = len(escuta)
        
        # Persuasão
        persuasao = df_neg[df_neg['grupo'] == 'Persuasão']
        soma_persuasao = persuasao['atitude_num'].sum()
        count_persuasao = len(persuasao)
        
        # Score tendência ponderado por atitude
        total_atitude = abs(soma_escuta) + abs(soma_persuasao)
        
        if total_atitude > 0:
            score = (soma_escuta - soma_persuasao) / total_atitude * 100
        else:
            score = 0
        
        # Efetividade média de cada grupo
        efet_escuta = escuta['atitude_num'].mean() if len(escuta) > 0 else 0
        efet_persuasao = persuasao['atitude_num'].mean() if len(persuasao) > 0 else 0
        
        resultados.append({
            'Negociador': negociador,
            'Score Tendência': round(score, 1),
            'Técnicas Escuta Ativa': count_escuta,
            'Técnicas Persuasão': count_persuasao,
            'Efetividade Escuta': round(efet_escuta, 2),
            'Efetividade Persuasão': round(efet_persuasao, 2),
            'Soma Atitude Escuta': soma_escuta,
            'Soma Atitude Persuasão': soma_persuasao,
        })
    
    df_resultado = pd.DataFrame(resultados)
    return df_resultado, df_tecnicas

# ============================================================
# 3. TESTES ESTATÍSTICOS
# ============================================================

def testar_anova(df_tecnicas):
    """ANOVA: Efetividade entre negociadores é significativamente diferente?"""
    grupos = []
    negociadores = []
    
    for neg in df_tecnicas['NEGOCIADOR PRINCIPAL'].unique():
        df_neg = df_tecnicas[df_tecnicas['NEGOCIADOR PRINCIPAL'] == neg]
        atitudes = df_neg['atitude_num'].dropna().values
        
        if len(atitudes) > 0:
            grupos.append(atitudes)
            negociadores.append(neg)
    
    if len(grupos) > 1:
        f_stat, p_value = f_oneway(*grupos)
        return {
            'teste': 'ANOVA',
            'f_statistic': round(f_stat, 4),
            'p_value': round(p_value, 4),
            'significativo': p_value < 0.05,
            'interpretacao': 'Efetividades entre negociadores SÃO significativamente diferentes' if p_value < 0.05 else 'Efetividades entre negociadores NÃO são significativamente diferentes'
        }
    return None

def testar_chi_quadrado(df_tecnicas):
    """Chi-quadrado: Distribuição de grupos técnicos depende do negociador?"""
    
    # Tabela de contingência
    tabela = pd.crosstab(
        df_tecnicas['NEGOCIADOR PRINCIPAL'],
        df_tecnicas['grupo']
    )
    
    chi2, p_value, dof, expected = chi2_contingency(tabela)
    
    return {
        'teste': 'Chi-quadrado',
        'chi2_statistic': round(chi2, 4),
        'p_value': round(p_value, 4),
        'df': dof,
        'significativo': p_value < 0.05,
        'interpretacao': 'Distribuição de técnicas DEPENDE do negociador (cada um tem padrão único)' if p_value < 0.05 else 'Distribuição de técnicas é ALEATÓRIA (não há padrão por negociador)'
    }

def aplicar_kmeans(df_resultado, k=2):
    """K-means: Agrupar negociadores em k clusters baseado no score"""
    
    X = df_resultado[['Score Tendência', 'Efetividade Escuta', 'Efetividade Persuasão']].values
    
    # Normalizar
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # K-means
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)
    
    df_resultado['Cluster'] = clusters
    
    # Interpretar clusters para k=2
    if k == 2:
        for i in range(2):
            media_score = df_resultado[df_resultado['Cluster'] == i]['Score Tendência'].mean()
            if media_score > 0:
                df_resultado.loc[df_resultado['Cluster'] == i, 'Perfil_Cluster'] = 'Escuta Ativa'
            else:
                df_resultado.loc[df_resultado['Cluster'] == i, 'Perfil_Cluster'] = 'Persuasão'
    
    return df_resultado, kmeans, scaler, X_scaled

# ============================================================
# 4. GRAFO DE PALAVRAS (PYVIS)
# ============================================================

def gerar_grafo_palavras(df_tecnicas, negociadores_cores):
    """
    Gera grafo Pyvis com palavras do 'TRECHO DA TRANSCRIÇÃO'
    Nós = palavras
    Cores = negociador que mais usou
    Conexões = co-ocorrência no mesmo trecho
    """
    
    from pyvis.network import Network
    
    # Stopwords português
    stopwords_pt = {
        'o', 'a', 'de', 'e', 'é', 'em', 'para', 'com', 'um', 'uma',
        'na', 'no', 'os', 'as', 'dos', 'das', 'ao', 'aos', 'por', 'se',
        'ou', 'não', 'sim', 'que', 'como', 'do', 'da', 'eu', 'você',
        'ele', 'ela', 'nós', 'eles', 'elas', 'meu', 'seu', 'seu', 'dele'
    }
    
    # Contar palavras por negociador
    palavras_negociador = {}
    palavras_freq = Counter()
    
    for _, row in df_tecnicas.iterrows():
        neg = row['NEGOCIADOR PRINCIPAL']
        trecho = str(row.get('TRECHO DA TRANSCRIÇÃO', '')).lower()
        
        if not trecho or trecho == 'nan':
            continue
        
        # Tokenizar
        palavras = re.findall(r'\b\w+\b', trecho)
        palavras = [p for p in palavras if p not in stopwords_pt and len(p) > 3]
        
        for p in palavras:
            if p not in palavras_negociador:
                palavras_negociador[p] = Counter()
            palavras_negociador[p][neg] += 1
            palavras_freq[p] += 1
    
    # Top 50 palavras
    top_palavras = [p for p, _ in palavras_freq.most_common(50)]
    
    # Criar rede
    net = Network(height='750px', width='100%', directed=False, notebook=False)
    net.physics.enabled = True
    
    # Adicionar nós (palavras)
    for palavra in top_palavras:
        # Qual negociador mais usou?
        negociador_principal = palavras_negociador[palavra].most_common(1)[0][0]
        cor = negociadores_cores.get(negociador_principal, '#888888')
        
        # Tamanho = frequência
        size = min(int(palavras_freq[palavra] * 2), 50)
        
        net.add_node(
            palavra,
            label=palavra,
            title=f"{palavra} ({palavras_freq[palavra]}x)",
            color=cor,
            size=size,
            font={'size': 14}
        )
    
    # Adicionar conexões (co-ocorrência)
    for _, row in df_tecnicas.iterrows():
        trecho = str(row.get('TRECHO DA TRANSCRIÇÃO', '')).lower()
        
        if not trecho or trecho == 'nan':
            continue
        
        palavras = re.findall(r'\b\w+\b', trecho)
        palavras = [p for p in palavras if p in top_palavras]
        
        # Conectar palavras que aparecem juntas
        for i, p1 in enumerate(palavras):
            for p2 in palavras[i+1:]:
                net.add_edge(p1, p2, weight=1)
    
    # Configurar física
    net.physics.forceAtlas2based.gravitationalConstant = -26
    net.physics.forceAtlas2based.centralGravity = 0.005
    net.physics.forceAtlas2based.springLength = 200
    
    return net

# ============================================================
# 5. VISUALIZAÇÕES PLOTLY
# ============================================================

def gerar_tabela_score(df_resultado):
    """Tabela formatada com scores e efetividades"""
    
    df_display = df_resultado[[
        'Negociador', 'Score Tendência', 'Técnicas Escuta Ativa',
        'Técnicas Persuasão', 'Efetividade Escuta', 'Efetividade Persuasão'
    ]].copy()
    
    return df_display

def gerar_scatter_score_efetividade(df_resultado):
    """Scatter: Score Tendência vs Efetividade Média"""
    
    df_resultado['Efetividade Média'] = (
        df_resultado['Efetividade Escuta'] + df_resultado['Efetividade Persuasão']
    ) / 2
    
    fig = px.scatter(
        df_resultado,
        x='Score Tendência',
        y='Efetividade Média',
        hover_name='Negociador',
        color='Score Tendência',
        size='Técnicas Escuta Ativa',
        color_continuous_scale='RdYlGn',
        labels={
            'Score Tendência': 'Tendência (Persuasão ← → Escuta Ativa)',
            'Efetividade Média': 'Efetividade Média'
        },
        title='Perfil de Negociadores: Tendência vs Efetividade'
    )
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FFF",
        height=500
    )
    
    return fig

def gerar_barras_grupos(df_resultado):
    """Barras: Contagem de técnicas por grupo"""
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Escuta Ativa',
        x=df_resultado['Negociador'],
        y=df_resultado['Técnicas Escuta Ativa'],
        marker_color='#10b981'
    ))
    
    fig.add_trace(go.Bar(
        name='Persuasão',
        x=df_resultado['Negociador'],
        y=df_resultado['Técnicas Persuasão'],
        marker_color='#f59e0b'
    ))
    
    fig.update_layout(
        barmode='group',
        title='Distribuição de Técnicas por Negociador',
        xaxis_title='Negociador',
        yaxis_title='Quantidade',
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FFF",
        height=500
    )
    
    return fig

# ============================================================
# 6. FUNÇÃO PRINCIPAL
# ============================================================

def analisar_perfil_negociadores(df_tecnicas):
    """
    Função principal que executa toda a análise.
    Retorna: df_resultado, testes_stats, kmeans_result
    """
    
    # Calcular score
    df_resultado, df_tecnicas_classificadas = calcular_score_tendencia(df_tecnicas)
    
    # Testes estatísticos
    anova_result = testar_anova(df_tecnicas_classificadas)
    chi2_result = testar_chi_quadrado(df_tecnicas_classificadas)
    
    # K-means
    df_resultado, kmeans, scaler, X_scaled = aplicar_kmeans(df_resultado, k=2)
    
    return {
        'df_resultado': df_resultado,
        'df_tecnicas_classificadas': df_tecnicas_classificadas,
        'anova': anova_result,
        'chi2': chi2_result,
        'kmeans': kmeans,
        'scaler': scaler,
        'X_scaled': X_scaled
    }
