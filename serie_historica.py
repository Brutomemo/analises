# ============================================================
# serie_historica.py
# ABA 2: SÉRIE HISTÓRICA — PAINEL (HISTÓRICO)
# Extraído integralmente de app.py
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from scipy import stats as sp_stats
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

import analise
import ia_estatistica


def render_toggle_button(
    label: str,
    session_key: str,
    button_key: str,
    width_ratio: float = 0.6
) -> bool:
    """Renderiza um botão toggle padronizado."""
    if session_key not in st.session_state:
        st.session_state[session_key] = False

    col_btn, col_spacer = st.columns([width_ratio, 1 - width_ratio])
    with col_btn:
        if st.button(label, key=button_key, use_container_width=True):
            st.session_state[session_key] = not st.session_state[session_key]

    return st.session_state[session_key]


def limpar_valor(val):
    if isinstance(val, list): return val[0] if len(val) > 0 else "N/D"
    return str(val) if pd.notna(val) else "N/D"


def somar_tempos_segundos(serie):
    total_s = 0
    for val in serie:
        try:
            if isinstance(val, list): val = val[0]
            if pd.notna(val) and val != "N/D" and val != "":
                total_s += int(float(val))
        except: pass
    h = total_s // 3600
    m = (total_s % 3600) // 60
    return f"{h:02d}h {m:02d}m"


def render_serie_historica(df_quali):
    """
    ABA 2: SÉRIE HISTÓRICA — PAINEL DE ANÁLISE HISTÓRICA
    Gráficos estatísticos + Análise estruturada com IA
    """
    df_tec = st.session_state.get("df_tec", pd.DataFrame())

    st.markdown("### Série Histórica - Negociações GATE")
    st.markdown("<h5 style='color: #f97;'>Filtros por: Negociador, Tipologia e Modalidade do Incidente</h5>", unsafe_allow_html=True)
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        if 'Neg_Limpo' not in df_quali.columns:
            df_quali['Neg_Limpo'] = df_quali['Negociador Principal'].apply(
                lambda x: x[0] if isinstance(x, list) and len(x) > 0 else (str(x) if pd.notna(x) else 'N/D')
            )

        lista_neg_g = ["Todos"] + sorted(df_quali[df_quali['Neg_Limpo'] != 'N/D']['Neg_Limpo'].unique().tolist())
    filtro_neg_g = st.selectbox("Filtrar por Negociador:", lista_neg_g, key="f_neg_historico")

    df_quali_filt = df_quali.copy()
    if filtro_neg_g != "Todos": df_quali_filt = df_quali_filt[df_quali_filt['Neg_Limpo'] == filtro_neg_g]

    st.markdown("---")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1: st.metric("Ocorrências Analisadas", len(df_quali_filt))
    with col_m2: st.metric("Tempo Total de Negociação Real", somar_tempos_segundos(df_quali_filt.get('Tempo de Negociação Real', [])))
    with col_m3: st.metric("Tempo Total de Negociação Tática", somar_tempos_segundos(df_quali_filt.get('Tempo de Negociação Tática', [])))

    st.markdown("---")
    
    # ====
    # NOVOS GRÁFICOS: VISÃO GERAL DA AMOSTRA
    # ====
    st.markdown("""
                    <div class='info-card'>
                    <h5 style='color: #FFD700; margin-top: 0;'>Visão Geral da Série Histórica</h5>
                    <p style='font-size:1.2rem;color:#ddd;'>
                    Metadados</strong>                 
                    </p>
                    </div>
                    """, unsafe_allow_html=True)
            

    # ── BOTÃO TOGGLE ───────────────────────────────────────────
    col_left, col_center, col_right = st.columns([1, 1, 1])
    with col_center:
        is_visao_geral = render_toggle_button(
            label="✔️ Abrir Visão Geral",
            session_key="analise1_visao_geral",
            button_key="btn_analise1_visao_geral"
        )
    
    st.markdown("---")
    
    if is_visao_geral:
        def gerar_grafico_resumo(df, coluna, titulo):
            """Gera gráfico de rosca (donut) padronizado com o Design System."""
            if coluna not in df.columns: return None
            
            # Limpa listas vazias e formata strings
            serie = df[coluna].apply(lambda x: x[0] if isinstance(x, list) and len(x)>0 else str(x))
            serie = serie[~serie.isin(["N/D", "nan", "", "None"])]
            
            if serie.empty: return None
            
            contagem = serie.value_counts().reset_index()
            contagem.columns = [coluna, 'Frequência']
            # para garantir que a maior fatia pegue a cor mais forte
            contagem = contagem.sort_values('Frequência', ascending=False)

            cores_contraste = ['#FF8C00', '#8B4513', "#A53A00", '#DEB887', "#EBE9E7" ]

            # Criação do Gráfico de Rosca
            fig = px.pie(
                contagem, 
                values='Frequência', 
                names=coluna, 
                title=titulo,
                hole=0.5, # Define o buraco central para transformar em rosca
                color_discrete_sequence=cores_contraste
            )
            
            # Configuração das legendas e rótulos
            fig.update_traces(
                textinfo='value+percent', # Mostra o número absoluto e a porcentagem
                textposition='outside',   # Coloca os números para fora para não poluir
                marker=dict(line=dict(color='#FFFFFF', width=1))
            )
            
            # Layout padronizado
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", 
                plot_bgcolor="rgba(0,0,0,0)", 
                font_color="#FFF", 
                margin=dict(t=50, b=10, l=10, r=10),
                showlegend=True,
                legend=dict(
                    orientation="h",       # Legenda horizontal
                    yanchor="bottom", 
                    y=-0.3, 
                    xanchor="center", 
                    x=0.5
                )
            )
            return fig

        c_g1, c_g2, c_g3 = st.columns(3)
        
        with c_g1:
            fig_res = gerar_grafico_resumo(df_quali_filt, 'Resolução', 'Resolução do Incidente')
            if fig_res: st.plotly_chart(fig_res, use_container_width=True)
            else: st.info("Sem dados de Resolução para os filtros atuais.")
            
            fig_uni = gerar_grafico_resumo(df_quali_filt, 'Uniforme Usado', 'Uniforme Utilizado')
            if fig_uni: st.plotly_chart(fig_uni, use_container_width=True)
            else: st.info("Sem dados de Uniforme para os filtros atuais.")

        with c_g2:
            fig_trans = gerar_grafico_resumo(df_quali_filt, 'Forma de Transição', 'Forma de Transição')
            if fig_trans: st.plotly_chart(fig_trans, use_container_width=True)
            else: st.info("Sem dados de Transição para os filtros atuais.")
            
            fig_sexo = gerar_grafico_resumo(df_quali_filt, 'Sexo do Causador', 'Sexo do Causador')
            if fig_sexo: st.plotly_chart(fig_sexo, use_container_width=True)
            else: st.info("Sem dados de Sexo para os filtros atuais.")


        with c_g3:
            fig_mod = gerar_grafico_resumo(df_quali_filt, 'Modalidade do incidente', 'Modalidade do incidente')
            if fig_mod: st.plotly_chart(fig_mod, use_container_width=True)
            else: st.info("Sem dados de Modalidade do incidente para os filtros atuais.")
            
            fig_tip = gerar_grafico_resumo(df_quali_filt, 'Tipologia', 'Tipologia')
            if fig_tip: st.plotly_chart(fig_tip, use_container_width=True)
            else: st.info("Sem dados de Tipologia para os filtros atuais.")

        st.markdown("---")



        # ══════════════════════════════════════════════════════════════════════════════
        # SEÇÃO: INFORMAÇÃO LONGITUDINAL
        # ══════════════════════════════════════════════════════════════════════════════

        st.markdown("<h5 style='color: #FFD700;'>✔️ Informação Longitudinal</h5>", unsafe_allow_html=True)
        st.markdown("<p style='color: #aaa; font-size: 0.95rem;'>Como tem evoluído o volume de negociações ao longo do tempo?</p>", unsafe_allow_html=True)

        col_data = next((col for col in ['Data da ocorrência', 'Data', 'DATA'] if col in df_quali_filt.columns), None)
        if col_data:
            df_quali_filt['Data_DT'] = pd.to_datetime(df_quali_filt[col_data], errors='coerce')
            df_time = df_quali_filt.dropna(subset=['Data_DT']).sort_values('Data_DT')
            if not df_time.empty:
                df_time['Mes_Ano'] = df_time['Data_DT'].dt.to_period('M').astype(str)
                df_trend = df_time['Mes_Ano'].value_counts().sort_index().reset_index()
                df_trend.columns = ['Mês', 'Qtd Ocorrências']
                
                st.markdown(
                    f"""
                    **Resumo:** Total de {len(df_time)} ocorrências registradas de {df_trend['Mês'].min()} a {df_trend['Mês'].max()}
                    """
                )
                
                fig_time = px.line(
                    df_trend, 
                    x='Mês', 
                    y='Qtd Ocorrências', 
                    markers=True, 
                    color_discrete_sequence=['#FFD700'],
                    title="Evolução Temporal de Negociações"
                )
                fig_time.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", 
                    plot_bgcolor="rgba(0,0,0,0)", 
                    font_color="#FFF",
                    hovermode='x unified'
                )
                st.plotly_chart(fig_time, use_container_width=True)
            else: 
                st.info("⚠️ Sem datas válidas nos registros.")
        else: 
            st.info("⚠️ Coluna de Data não encontrada. Adicione uma coluna 'Data' ao seu formulário.")

        st.markdown("---")


    # ============================================================
    # BLOCO: Ranking de Técnicas + Padrões e Correlações
    # ============================================================
    
    st.markdown("""
                    <div class='info-card'>
                    <h5 style='color: #FFD700; margin-top: 0;'>Ranking e Efetividade das Técnicas Aplicadas</h5>
                    <p style='font-size:1.2rem;color:#ddd;'>
                    Técnicas mais usadas pelos Negociadores e sua Efetividade</strong>                 
                    </p>
                    </div>
                    """, unsafe_allow_html=True)        

    col_left, col_center, col_right = st.columns([1, 1, 1])  
    with col_center:
        is_ranking = render_toggle_button(
            label="✔️ Abrir Ranking de Técnicas",
            session_key="ranking_de_tecnicas_expanded",
            button_key="btn_ranking_tecnicas"
        )

    st.markdown("---")

    if is_ranking:
        
        if not df_tec.empty:
            df_tec["Neg_Limpo"] = (
                df_tec["Negociador Principal do incidente crítico"].apply(limpar_valor)
                if "Negociador Principal do incidente crítico" in df_tec.columns
                else "N/D"
            )
            df_tec["Tip_Limpa"] = (
                df_tec["Tipologia do incidente crítico"].apply(limpar_valor)
                if "Tipologia do incidente crítico" in df_tec.columns
                else "N/D"
            )
            df_tec["Mod_Limpa"] = (
                df_tec["Modalidade do incidente crítico"].apply(limpar_valor)
                if "Modalidade do incidente crítico" in df_tec.columns
                else "N/D"
            )

            df_tec_filt = df_tec.copy()
            if filtro_neg_g != "Todos":
                df_tec_filt = df_tec_filt[df_tec_filt["Neg_Limpo"] == filtro_neg_g]
            if filtro_tip_g != "Todas":
                df_tec_filt = df_tec_filt[df_tec_filt["Tip_Limpa"] == filtro_tip_g]
            if filtro_mod_g != "Todas":
                df_tec_filt = df_tec_filt[df_tec_filt["Mod_Limpa"] == filtro_mod_g]

        # ----------------------------------------------------------
        # Ranking visual
        # ----------------------------------------------------------
        if not df_tec_filt.empty:
            col_t = next(
                (
                    col
                    for col in ["TÉCNICAS", "TECNICAS", "TÉCNICA", "TECNICA"]
                    if col in df_tec_filt.columns
                ),
                None,
            )
            if col_t:
                freq_global = df_tec_filt[col_t].value_counts().reset_index()
                freq_global.columns = ["Técnica", "Vezes Utilizada"]

                c_tab, c_tree = st.columns([1, 2])
                with c_tab:
                    st.dataframe(freq_global, use_container_width=True, hide_index=True)
                with c_tree:
                    fig_g = px.treemap(
                        freq_global,
                        path=["Técnica"],
                        values="Vezes Utilizada",
                        color="Vezes Utilizada",
                        color_continuous_scale="Oranges",
                    )
                    fig_g.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#FFF",
                        margin=dict(t=0, l=0, r=0, b=0),
                    )
                    st.plotly_chart(fig_g, use_container_width=True)
            else:
                st.warning("Coluna 'TÉCNICAS' não encontrada.")
        else:
            st.info("Nenhuma técnica encontrada para os filtros selecionados.")

        st.markdown("---")


        #NOVAS ANALISES 21MAI

                    
        # ============================================================
        # ANÁLISE 4: EFETIVIDADE DAS TÉCNICAS (SÉRIE HISTÓRICA)
        # ============================================================

        st.markdown("<h5 style='color: #FFD700;'>Efetividade das Técnicas</h5>", unsafe_allow_html=True)

        col_left, col_center, col_right = st.columns([1, 1, 1])
        with col_center:
            is_Efetividade_Técnicas = render_toggle_button(
                label="✔️ Abrir Efetividade das Técnicas",
                session_key="Efetividade_Técnicas",
                button_key="btn_Efetividade_Técnicas"
            )

        st.markdown("---")

        if is_Efetividade_Técnicas:
            if not df_tec_filt.empty:
                col_tecnica = next(
                    (col for col in ['TÉCNICAS', 'TECNICAS', 'TÉCNICA', 'TECNICA'] if col in df_tec_filt.columns),
                    None,
                )
                col_reacao = next(
                    (col for col in df_tec_filt.columns if 'ATITUDE' in col.upper()),
                    None,
                )

                if col_tecnica and col_reacao:

                    def normalizar_reacao(val):
                        if val is None:
                            return None
                        s = str(val).strip()
                        if any(x in s for x in ["-1", "-1.0", "🔴", "Negativa", "negativa"]):
                            return -1
                        elif any(x in s for x in ["0", "0.0", "⚪", "Neutra", "neutra"]):
                            return 0
                        elif any(x in s for x in ["1", "1.0", "🟢", "Positiva", "positiva"]):
                            return 1
                        else:
                            return None

                    df_ef = df_tec_filt.copy()
                    df_ef['_reacao_num'] = df_ef[col_reacao].apply(normalizar_reacao)

                    # ── Agrupar por técnica ───────────────────────────────
                    resumo = []
                    for tecnica, grupo in df_ef.groupby(col_tecnica):
                        total    = len(grupo)
                        positivo = (grupo['_reacao_num'] == 1).sum()
                        neutro   = (grupo['_reacao_num'] == 0).sum()
                        negativo = (grupo['_reacao_num'] == -1).sum()
                        inaud    = grupo['_reacao_num'].isna().sum()

                        observados = positivo + neutro + negativo
                        if observados > 0:
                            score = round(((positivo - negativo) / observados) * 100, 1)
                        else:
                            score = None

                        resumo.append({
                            "Técnica":      tecnica,
                            "Total":        total,
                            "Positivas":    int(positivo),
                            "Neutras":      int(neutro),
                            "Negativas":    int(negativo),
                            "Inaudível":    int(inaud),
                            "Score":        score
                        })

                    df_resumo_tec = pd.DataFrame(resumo).sort_values("Score", ascending=False, na_position='last')

                    # ── SCORECARD GERAL ───────────────────────────────────
                    st.markdown("### ✔️ Resumo Geral")

                    total_usos     = int(df_resumo_tec["Total"].sum())
                    total_positivo = int(df_resumo_tec["Positivas"].sum())
                    total_negativo = int(df_resumo_tec["Negativas"].sum())
                    observados_total = total_positivo + int(df_resumo_tec["Neutras"].sum()) + total_negativo
                    score_geral    = round(((total_positivo - total_negativo) / max(1, observados_total)) * 100, 1)

                    col_eg1, col_eg2, col_eg3, col_eg4 = st.columns(4)
                    with col_eg1:
                        st.metric('Total de Usos', total_usos)
                    with col_eg2:
                        st.metric('Positivas', total_positivo, delta='🟢')
                    with col_eg3:
                        st.metric('Negativas', total_negativo, delta='🔴')
                    with col_eg4:
                        st.metric('Score Geral', f'{score_geral:+.1f}%')

                    # ── TABELA + GRÁFICO ──────────────────────────────────
                    st.markdown("### ✔️ Efetividade por Técnica")

                    col_ef1, col_ef2 = st.columns([1, 2])

                    with col_ef1:
                        st.dataframe(
                            df_resumo_tec[['Técnica', 'Total', 'Positivas', 'Negativas', 'Score']].head(10),
                            use_container_width=True,
                            hide_index=True
                        )

                    with col_ef2:
                        # ── GRÁFICO BARRAS EMPILHADAS (igual Aba Individual) ──
                        import plotly.graph_objects as go

                        tecnicas  = df_resumo_tec["Técnica"].tolist()
                        positivos = df_resumo_tec["Positivas"].tolist()
                        neutros   = df_resumo_tec["Neutras"].tolist()
                        negativos = df_resumo_tec["Negativas"].tolist()

                        fig_barras = go.Figure()

                        fig_barras.add_trace(go.Bar(
                            name="🟢 Positiva",
                            x=tecnicas, y=positivos,
                            marker_color="#10b981"
                        ))
                        fig_barras.add_trace(go.Bar(
                            name="⚪ Neutra",
                            x=tecnicas, y=neutros,
                            marker_color="#6b7280"
                        ))
                        fig_barras.add_trace(go.Bar(
                            name="🔴 Negativa",
                            x=tecnicas, y=negativos,
                            marker_color="#ef4444"
                        ))

                        fig_barras.update_layout(
                            barmode="stack",
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#fff"),
                            legend=dict(
                                font=dict(color="#fff"),
                                bgcolor="rgba(0,0,0,0.4)"
                            ),
                            xaxis=dict(tickfont=dict(color="#FFD700"), gridcolor="#333"),
                            yaxis=dict(tickfont=dict(color="#aaa"), gridcolor="#333"),
                            height=420,
                            margin=dict(t=20, b=120, l=40, r=40)
                        )

                        st.plotly_chart(fig_barras, use_container_width=True)

                    # ── LEITURA OPERACIONAL ───────────────────────────────
                    st.markdown("---")
                    st.markdown("### ✔️ Leitura Operacional")

                    # Só técnicas com pelo menos 2 usos observados
                    df_com_score = df_resumo_tec[
                        df_resumo_tec["Score"].notna() &
                        (df_resumo_tec["Total"] >= 2)
                    ]
                    if df_com_score.empty:
                        df_com_score = df_resumo_tec[df_resumo_tec["Score"].notna()]

                    if not df_com_score.empty:

                        # Mais efetiva
                        score_maximo = df_com_score["Score"].max()
                        tecnicas_maximas = df_com_score[df_com_score["Score"] == score_maximo]

                        if len(tecnicas_maximas) == 1:
                            melhor = tecnicas_maximas.iloc[0]
                            txt_melhor = (
                                f"✅ <strong>Técnica mais efetiva:</strong> {melhor['Técnica']} "
                                f"— Score {melhor['Score']:+.1f}% "
                                f"({int(melhor['Positivas'])} positivas / {int(melhor['Total'])} usos)"
                            )
                        else:
                            tecnicas_nomes = ", ".join(tecnicas_maximas['Técnica'].tolist())
                            txt_melhor = (
                                f"✅ <strong>Técnicas mais efetivas (empate):</strong> {tecnicas_nomes} "
                                f"— Score {score_maximo:+.1f}%"
                            )

                        st.markdown(f"""
                        <div style='background:rgba(16,185,129,0.08);padding:12px;border-radius:8px;border-left:3px solid #10b981;margin-bottom:10px;'>
                        <p style='color:#ddd;font-size:0.9rem;margin:0;'>{txt_melhor}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        # Menos efetiva
                        score_minimo = df_com_score["Score"].min()
                        tecnicas_minimas = df_com_score[df_com_score["Score"] == score_minimo]

                        if len(tecnicas_minimas) == 1:
                            pior = tecnicas_minimas.iloc[0]
                            txt_pior = (
                                f"⚠️ <strong>Técnica menos efetiva:</strong> {pior['Técnica']} "
                                f"— Score {pior['Score']:+.1f}% "
                                f"({int(pior['Negativas'])} negativas / {int(pior['Total'])} usos)"
                            )
                        else:
                            tecnicas_nomes = ", ".join(tecnicas_minimas['Técnica'].tolist())
                            txt_pior = (
                                f"⚠️ <strong>Técnicas menos efetivas (empate):</strong> {tecnicas_nomes} "
                                f"— Score {score_minimo:+.1f}%"
                            )

                        st.markdown(f"""
                        <div style='background:rgba(239,68,68,0.08);padding:12px;border-radius:8px;border-left:3px solid #ef4444;margin-bottom:10px;'>
                        <p style='color:#ddd;font-size:0.9rem;margin:0;'>{txt_pior}</p>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("""
                    **Interpretação:**
                    - **Score > 50%** = Técnica efetiva (mais sucessos que fracassos)
                    - **Score próximo a 0%** = Técnica neutra (sucessos ≈ fracassos)
                    - **Score < -50%** = Técnica contraproducente (mais fracassos que sucessos)
                    """)

                else:
                    st.warning("⚠️ Colunas necessárias não encontradas (TÉCNICAS e ATITUDE).")
            else:
                st.info("⚠️ Nenhuma técnica encontrada para os filtros selecionados.")

        st.markdown("---")

        
    # ============================================================
    # ANÁLISE: CONVERGÊNCIA TEMÁTICA (COM AUDITORIA ESTATÍSTICA)
    # ============================================================
    
    # ============================================================
    # FUNÇÕES AUXILIARES DE AUDITORIA ESTATÍSTICA
    # ============================================================

    def calcular_intervalo_confianca_95(dados):
        """
        Calcula o Intervalo de Confiança 95% (IC 95%)
        
        Em linguagem leiga: "Se repetíssemos essa análise 100 vezes,
        em 95 delas a média verdadeira estaria dentro deste intervalo"
        """
        n = len(dados)
        media = np.mean(dados)
        dp = np.std(dados, ddof=1)  # Desvio padrão amostral
        
        # Erro padrão (quanto a média varia)
        erro_padrao = dp / np.sqrt(n)
        
        # t-crítico para 95% (depende do N)
        t_critico = sp_stats.t.ppf(0.975, df=n-1)
        
        # Margem de erro
        margem = t_critico * erro_padrao
        
        return {
            'media': media,
            'limite_inferior': media - margem,
            'limite_superior': media + margem,
            'margem_erro': margem,
            'erro_padrao': erro_padrao
        }

    def testar_normalidade_shapiro(dados):
        """
        Teste de Normalidade (Shapiro-Wilk)
        
        Em linguagem leiga: "Os dados seguem uma distribuição normal 
        (em forma de sino)?"
        
        p-value > 0.05 = Sim, é aproximadamente normal
        p-value < 0.05 = Não, se desvia de uma distribuição normal
        """
        statistica, p_value = sp_stats.shapiro(dados)
        
        return {
            'p_value': p_value,
            'eh_normal': p_value > 0.05,  # Verdadeiro se p > 0.05
            'interpretacao': (
                '✅ Aproximadamente normal (dados bem distribuídos)' 
                if p_value > 0.05 
                else '⚠️ Não é normal (dados concentrados em alguns valores)'
            )
        }

    def calcular_coeficiente_variacao(dados):
        """
        Coeficiente de Variação (CV)
        
        Em linguagem leiga: "Qual é o tamanho da variabilidade 
        em relação à média?"
        
        CV < 15% = Baixa variabilidade (dados consistentes) ✅
        CV 15-30% = Moderada variabilidade ⚠️
        CV > 30% = Alta variabilidade (dados muito diferentes) 🔴
        """
        media = np.mean(dados)
        dp = np.std(dados, ddof=1)
        
        cv = (dp / media) * 100 if media != 0 else 0
        
        if cv < 15:
            status = '✅ Baixa variabilidade (dados consistentes)'
        elif cv < 30:
            status = '⚠️ Moderada variabilidade'
        else:
            status = '🔴 Alta variabilidade (dados muito diferentes entre si)'
        
        return {
            'valor': cv,
            'status': status,
            'interpretacao': f'Para cada 100% da média, há ±{cv:.1f}% de dispersão'
        }

    def detectar_outliers_iqr(dados):
        """
        Detecção de Outliers usando Intervalo Interquartil (IQR)
        
        Em linguagem leiga: "Existem valores muito diferentes dos outros?
        (aqueles pontinhos isolados no gráfico)"
        """
        Q1 = np.percentile(dados, 25)
        Q3 = np.percentile(dados, 75)
        IQR = Q3 - Q1
        
        limite_inferior = Q1 - 1.5 * IQR
        limite_superior = Q3 + 1.5 * IQR
        
        outliers = [x for x in dados if x < limite_inferior or x > limite_superior]
        
        return {
            'tem_outliers': len(outliers) > 0,
            'quantidade': len(outliers),
            'valores': outliers,
            'limite_inferior': limite_inferior,
            'limite_superior': limite_superior
        }

    def validar_robustez_amostral(n):
        """
        Valida se o tamanho da amostra é suficiente para análises robustas
        
        Em linguagem leiga: "Temos dados suficientes para confiar nessa análise?"
        """
        recomendacao_minima = 30
        
        if n < 10:
            nivel = '🔴 EXPLORATÓRIA'
            descricao = 'Use apenas para identificar padrões iniciais. NÃO recomendado para decisões críticas.'
            confianca = 'Muito baixa'
        elif n < 20:
            nivel = '🟡 PRELIMINAR'
            descricao = 'Útil para direções iniciais, mas colete mais dados para conclusões sólidas.'
            confianca = 'Baixa a média'
        elif n < 30:
            nivel = '🟡 ACEITÁVEL'
            descricao = 'Moderadamente confiável. Idealmente, chegue a 30+ observações.'
            confianca = 'Média'
        else:
            nivel = '✅ ROBUSTA'
            descricao = 'Altamente confiável para decisões operacionais.'
            confianca = 'Alta'
        
        return {
            'nivel': nivel,
            'descricao': descricao,
            'confianca': confianca,
            'percentual_recomendacao': (n / recomendacao_minima) * 100,
            'deficit': max(0, recomendacao_minima - n)
        }

    # ============================================================
    # BLOCO PRINCIPAL: CONVERGÊNCIA TEMÁTICA COM AUDITORIA
    # ============================================================

    st.markdown("""
        <div class='info-card'>
        <h5 style='color: #FFD700; margin-top: 0;'>
        Convergência Temática: Quanto de sincronização temática existe entre negociador e causador
        </h5>
        <p style='font-size:1.2rem;color:#ddd;'>
        Análise descritiva da média de convergência temática com validação estatística
        </p>
        </div>
        """, unsafe_allow_html=True)

    # ── BOTÃO TOGGLE ───────────────────────────────────────────
    col_left, col_center, col_right = st.columns([1, 1, 1])
    with col_center:
        is_convergencia = render_toggle_button(
            label="✔️ Abrir Convergência Temática",
            session_key="analise5_convergencia_tematica",
            button_key="btn_analise5_convergencia_tematica"
        )

    st.markdown("---")

    if is_convergencia:

        if not df_quali_filt.empty:
            col_texto_c = 'TRANSCRIÇÃO DO CAUSADOR'
            col_texto_np = 'TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL'
            
            if col_texto_c in df_quali_filt.columns and col_texto_np in df_quali_filt.columns:
                try:
                    # Calcular convergência para CADA APA
                    convergencias_apas = []
                    
                    for idx, row in df_quali_filt.iterrows():
                        txt_c = str(row[col_texto_c]).strip()
                        txt_np = str(row[col_texto_np]).strip()
                        
                        if len(txt_c.split()) > 5 and len(txt_np.split()) > 5:
                            try:
                                temas_c = analise.extrair_temas_unicos(txt_c, resolucao_tipo='desconhecida')
                                temas_np = analise.extrair_temas_unicos(txt_np, resolucao_tipo='desconhecida')
                                
                                if temas_c and temas_np:
                                    conv = analise.calcular_convergencia_tematica(temas_c, temas_np)
                                    convergencias_apas.append({
                                        'APA': idx,
                                        'Convergencia': conv['convergencia_geral'],
                                        'Compartilhados': len(conv['temas_compartilhados']),
                                        'So_Causador': len(conv['temas_exclusivos_causador']),
                                        'So_Negociador': len(conv['temas_exclusivos_negociador'])
                                    })
                            except:
                                pass
                    
                    if convergencias_apas:
                        df_conv_agg = pd.DataFrame(convergencias_apas)
                        
                        # ════════════════════════════════════════════
                        # CÁLCULOS ESTATÍSTICOS
                        # ════════════════════════════════════════════
                        
                        dados_convergencia = df_conv_agg['Convergencia'].values
                        n_amostras = len(dados_convergencia)
                        
                        # Estatísticas básicas
                        media_conv = df_conv_agg['Convergencia'].mean()
                        mediana_conv = df_conv_agg['Convergencia'].median()
                        dp_conv = df_conv_agg['Convergencia'].std()
                        min_conv = df_conv_agg['Convergencia'].min()
                        max_conv = df_conv_agg['Convergencia'].max()
                        amplitude = max_conv - min_conv
                        
                        # Testes estatísticos
                        ic_95 = calcular_intervalo_confianca_95(dados_convergencia)
                        normalidade = testar_normalidade_shapiro(dados_convergencia)
                        cv = calcular_coeficiente_variacao(dados_convergencia)
                        outliers = detectar_outliers_iqr(dados_convergencia)
                        robustez = validar_robustez_amostral(n_amostras)
                        
                        # Média de temas compartilhados
                        media_compartilhados = df_conv_agg['Compartilhados'].mean()
                        
                        # ── SCORECARD PRINCIPAL ────────────────────────────────
                        st.markdown("### ✔️ Resumo da Convergência Temática")
                        
                        col_cv1, col_cv2, col_cv3, col_cv4 = st.columns(4)
                        
                        with col_cv1:
                            st.metric('Convergência Média', f'{media_conv:.1f}%')
                            st.caption(f'DP: ±{dp_conv:.1f}%')
                        
                        with col_cv2:
                            st.metric('Mediana', f'{mediana_conv:.1f}%')
                            st.caption(f'N = {n_amostras} APAs')
                        
                        with col_cv3:
                            st.metric('Temas Compartilhados (Média)', f'{media_compartilhados:.1f}')
                            st.caption('Média por APA')
                        
                        with col_cv4:
                            st.metric('Range', f'{min_conv:.1f}% - {max_conv:.1f}%')
                            st.caption(f'Amplitude: {amplitude:.1f}%')
                        
                        # ════════════════════════════════════════════
                        # 🔍 AUDITORIA ESTATÍSTICA (NOVO!)
                        # ════════════════════════════════════════════
                        
                        st.markdown("---")
                        st.markdown("### 🔍 Validação Estatística (Qualidade dos Dados)")
                        
                        # AVISO PRINCIPAL SOBRE ROBUSTEZ
                        st.markdown(f"""
                        <div style='
                            background-color: rgba(255, 174, 66, 0.1);
                            border-left: 4px solid #FFB84D;
                            padding: 15px;
                            border-radius: 5px;
                            margin-bottom: 20px;
                        '>
                        <h5 style='color: #FFB84D; margin-top: 0;'>
                        ⚠️ {robustez['nivel']} — Nível de Confiabilidade
                        </h5>
                        <p style='color: #ddd; margin-bottom: 10px;'>
                        <strong>Status:</strong> {robustez['descricao']}<br>
                        <strong>Confiança nos resultados:</strong> {robustez['confianca']}<br>
                        <strong>Progresso:</strong> {robustez['percentual_recomendacao']:.0f}% do recomendado ({n_amostras}/30 APAs)
                        </p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # TABELA DE VALIDAÇÃO
                        col_audit1, col_audit2 = st.columns(2)
                        
                        with col_audit1:
                            st.markdown("**📐 Distribuição dos Dados**")
                            
                            audit_data_1 = {
                                'Métrica': [
                                    'Intervalo de Confiança 95%',
                                    'Coeficiente de Variação',
                                    'Normalidade dos Dados'
                                ],
                                'Valor': [
                                    f"[{ic_95['limite_inferior']:.1f}% - {ic_95['limite_superior']:.1f}%]",
                                    f"{cv['valor']:.1f}% {cv['status'].split()[0]}",
                                    normalidade['interpretacao']
                                ]
                            }
                            
                            df_audit_1 = pd.DataFrame(audit_data_1)
                            st.dataframe(df_audit_1, use_container_width=True, hide_index=True)
                        
                        with col_audit2:
                            st.markdown("**🔎 Detecção de Anomalias**")
                            
                            outlier_status = (
                                f"🟢 Nenhum outlier" 
                                if not outliers['tem_outliers'] 
                                else f"🟡 {outliers['quantidade']} outlier(s) detectado(s)"
                            )
                            
                            audit_data_2 = {
                                'Métrica': [
                                    'Outliers (Valores Anômalos)',
                                    'Tamanho da Amostra',
                                    'Variabilidade'
                                ],
                                'Valor': [
                                    outlier_status,
                                    f"{n_amostras} APAs",
                                    cv['status']
                                ]
                            }
                            
                            df_audit_2 = pd.DataFrame(audit_data_2)
                            st.dataframe(df_audit_2, use_container_width=True, hide_index=True)
                        
                        # ════════════════════════════════════════════
                        # 📚 EXPLICAÇÕES EM LINGUAGEM LEIGA
                        # ════════════════════════════════════════════
                        
                        # Preparar interpretação do p-value
                        p_value_interpretation = (
                            f"✅ p = {normalidade['p_value']:.4f} - Dados aproximadamente normais"
                            if normalidade['eh_normal']
                            else f"⚠️ p = {normalidade['p_value']:.4f} - Dados não são normais"
                        )
                        
                        with st.expander("📚 O que significam esses números? (Clique para expandir)", expanded=False):
                            
                            st.markdown(f"""
                            ### ✔️ Explicação em Linguagem Simples
                            
                            ---
                            
                            **1️⃣ Intervalo de Confiança 95% (IC 95%)**
                            
                            <div style='background-color: rgba(100, 150, 255, 0.1); padding: 10px; border-radius: 5px; margin: 10px 0;'>
                            
                            **O que é:** Um "intervalo de segurança" onde a verdadeira média provavelmente está.
                            
                            **Analogia:** Imagine que você está tentando acertar o alvo de uma negociação. 
                            A média ({media_conv:.1f}%) é seu melhor palpite, mas o IC 95% é a "zona de segurança" onde você 
                            espera que o alvo realmente esteja em 95 de cada 100 tentativas.
                            
                            **Seu IC 95%:** [{ic_95['limite_inferior']:.1f}% - {ic_95['limite_superior']:.1f}%]
                            
                            **Interpretação:**
                            - Intervalo é MUITO AMPLO 🔴
                            - Significa: "Não temos certeza onde a verdadeira média está"
                            - Ação: Colete mais dados para diminuir esse intervalo
                            
                            **Analogia numérica:**
                            - Se N = 5 (seu caso): IC = [{ic_95['limite_inferior']:.1f}% - {ic_95['limite_superior']:.1f}%] (intervalo ENORME de ±{ic_95['margem_erro']:.1f}%)
                            - Se N = 100: IC seria [38% - 47.6%] (intervalo pequeno de ±5%)
                            → Mais dados = mais certeza
                            
                            </div>
                            
                            ---
                            
                            **2️⃣ Coeficiente de Variação (CV)**
                            
                            <div style='background-color: rgba(255, 150, 100, 0.1); padding: 10px; border-radius: 5px; margin: 10px 0;'>
                            
                            **O que é:** Uma medida de "quanto os dados variam em relação à média".
                            
                            **Analogia:** Imagine dois negociadores:
                            - Negociador A: Sempre consegue 40-45% de convergência (consistente)
                            - Negociador B: Às vezes 20%, às vezes 60% (imprevisível)
                            
                            O CV mostra qual é mais consistente.
                            
                            **Seu CV:** {cv['valor']:.1f}% → {cv['status']}
                            
                            **Interpretação:**
                            - CV < 15%: Dados muito consistentes ✅ (negociador confiável)
                            - CV 15-30%: Dados moderadamente variáveis ⚠️
                            - CV > 30%: Dados muito diferentes entre si 🔴 (imprevisível)
                            
                            **O que isso significa:**
                            Para cada 100% de convergência média, há ±{cv['valor']:.1f}% de "oscilação"
                            → Cada negociação é diferente da outra
                            
                            </div>
                            
                            ---
                            
                            **3️⃣ Teste de Normalidade (Shapiro-Wilk)**
                            
                            <div style='background-color: rgba(150, 255, 150, 0.1); padding: 10px; border-radius: 5px; margin: 10px 0;'>
                            
                            **O que é:** Um teste que verifica se os dados estão "bem distribuídos" 
                            (em forma de sino/normal).
                            
                            **Analogia:** Imagine a altura das pessoas em uma população:
                            - Normal: Poucas pessoas muito altas, poucas muito baixas, maioria no meio (sino)
                            - Não-normal: Todas com mesma altura (não há variação)
                            
                            **Seu resultado:** {p_value_interpretation}
                            
                            **Interpretação:**
                            - p-value > 0.05: Dados são aproximadamente normais ✅
                            - p-value < 0.05: Dados NÃO são normais ⚠️
                            
                            **Por que isso importa?**
                            Alguns testes estatísticos funcionam melhor com dados normais.
                            Se seus dados NÃO são normais, use testes "não-paramétricos" (mais seguros).
                            
                            </div>
                            
                            ---
                            
                            **4️⃣ Outliers (Valores Anômalos)**
                            
                            <div style='background-color: rgba(255, 100, 100, 0.1); padding: 10px; border-radius: 5px; margin: 10px 0;'>
                            
                            **O que é:** Valores que estão MUITO diferentes dos outros 
                            (aqueles pontinhos isolados no gráfico).
                            
                            **Analogia:** Imagine notas de uma turma:
                            - Normal: Maioria com notas entre 5-8
                            - Outlier: Um aluno com nota 2 (muito diferente)
                            
                            **Seu caso:** {'🟢 Nenhum outlier detectado' if not outliers['tem_outliers'] else f'🟡 {outliers["quantidade"]} outlier(s)'}
                            
                            **Ação recomendada:**
                            Se houver outliers, investigue:
                            - É um erro de coleta de dados?
                            - É uma negociação realmente diferente das outras?
                            - Deve ser mantida ou removida da análise?
                            
                            </div>
                            
                            ---
                            
                            **5️⃣ Tamanho da Amostra (N)**
                            
                            <div style='background-color: rgba(200, 100, 255, 0.1); padding: 10px; border-radius: 5px; margin: 10px 0;'>
                            
                            **O que é:** Quantas negociações você está analisando.
                            
                            **Recomendação:** N ≥ 30 para análises ROBUSTAS (confiáveis).
                            
                            **Seu N:** {n_amostras} → {robustez['nivel']}
                            
                            **Interpretação:**
                            - N < 10: 🔴 Exploratória (apenas para ideias iniciais)
                            - N 10-30: 🟡 Aceitável (colete mais para segurança)
                            - N > 30: ✅ Robusta (confiável para decisões)
                            
                            **Como melhorar?** Colete {robustez['deficit']:.0f} mais APAs para atingir N = 30
                            
                            </div>
                            
                            """, 
                            unsafe_allow_html=True
                        )
                        
                        # ── DISTRIBUIÇÃO ─────────────────────────────
                        st.markdown("---")
                        st.markdown("### ✔️ Distribuição da Convergência")
                        
                        st.markdown("""
                        **O que são esses gráficos?**
                        
                        Imagine 6 negociações diferentes. Em cada uma, calculamos quanto o negociador e o causador falam dos **mesmos temas** (convergência).
                        
                        - **Negociação 1:** 45% de sintonia temática
                        - **Negociação 2:** 52% de sintonia temática
                        - **Negociação 3:** 38% de sintonia temática
                        - ... e assim por diante
                        
                        Esses dois gráficos mostram como essas porcentagens se distribuem:
                        
                        **Gráfico da Esquerda (Histograma):** "Em quantas negociações tivemos cada nível de sintonia?"
                        - Se há uma barra alta em 45%, significa que muitas negociações tiveram ~45% de convergência
                        - Se a distribuição é espalhada, significa que a sintonia varia muito de ocorrência para ocorrência
                        
                        **Gráfico da Direita (Box Plot):** "Qual é a faixa típica de sintonia?"
                        - **A linha do meio (mediana):** 50% das negociações tiveram sintonia até esse valor
                        - **A caixa:** Mostra onde estão a maioria dos valores (do 25º ao 75º percentil)
                        - **Os pontinhos:** Ocorrências com sintonia muito diferente das outras (outliers)
                        """)
                        
                        col_cv_hist1, col_cv_hist2 = st.columns(2)
                        
                        with col_cv_hist1:
                            fig_conv_hist = px.histogram(
                                df_conv_agg,
                                x='Convergencia',
                                nbins=8,
                                title='Distribuição da Convergência Temática'
                            )
                            fig_conv_hist.update_traces(marker_color='#FF8C00')
                            fig_conv_hist.update_layout(
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font_color='#FFF',
                                height=300,
                                xaxis_title='Convergência (%)',
                                yaxis_title='Número de Negociações'
                            )
                            st.plotly_chart(fig_conv_hist, use_container_width=True)
                        
                        with col_cv_hist2:
                            fig_box_conv = px.box(
                                df_conv_agg,
                                y='Convergencia',
                                title='Faixa Típica de Convergência'
                            )
                            fig_box_conv.update_traces(marker_color='#FF8C00')
                            fig_box_conv.update_layout(
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font_color='#FFF',
                                height=300,
                                yaxis_title='Convergência (%)'
                            )
                            st.plotly_chart(fig_box_conv, use_container_width=True)
                        
                        # ── NOVO: GRÁFICO DE DISPERSÃO ─────────────────
                        st.markdown("---")
                        st.markdown("### 📍 Dispersão Individual (Cada APA)")
                        
                        st.markdown("""
                        **O que é esse gráfico?**
                        
                        Mostra **cada negociação individualmente** (cada ponto é uma APA).
                        
                        - **Eixo X (horizontal):** Número da APA (1ª, 2ª, 3ª... negociação)
                        - **Eixo Y (vertical):** Convergência dessa APA
                        - **Linha vermelha:** Média (42.8%)
                        - **Faixa cinzenta:** Intervalo de Confiança (esperado estar aqui em 95% dos casos)
                        
                        **Como ler:**
                        - Ponto ACIMA da faixa cinzenta = Convergência ACIMA da média (bom!)
                        - Ponto DENTRO da faixa = Convergência normal
                        - Ponto ABAIXO da faixa = Convergência ABAIXO da média (investigar)
                        
                        **Padrões a observar:**
                        - Todos os pontos espalhados? → Variabilidade alta (como é seu caso)
                        - Pontos juntos em uma linha? → Variabilidade baixa (consistência)
                        - Pontos isolados? → Outliers (anomalias)
                        """)
                        
                        # Preparar dados para scatter plot
                        df_scatter = df_conv_agg.copy()
                        df_scatter['APA_Num'] = range(1, len(df_scatter) + 1)
                        
                        fig_scatter = px.scatter(
                            df_scatter,
                            x='APA_Num',
                            y='Convergencia',
                            title='Convergência por Negociação (Scatter Plot)',
                            labels={'APA_Num': 'Número da APA', 'Convergencia': 'Convergência (%)'},
                            size='Compartilhados',  # Tamanho do ponto = número de temas compartilhados
                            hover_data={'APA': True, 'Convergencia': ':.1f', 'Compartilhados': True}
                        )
                        
                        # Adicionar linha de média
                        fig_scatter.add_hline(
                            y=media_conv,
                            line_dash="dash",
                            line_color="#FF0000",
                            annotation_text=f"Média: {media_conv:.1f}%",
                            annotation_position="right"
                        )
                        
                        # Adicionar faixa de IC 95%
                        fig_scatter.add_hrect(
                            y0=ic_95['limite_inferior'],
                            y1=ic_95['limite_superior'],
                            fillcolor="gray",
                            opacity=0.2,
                            layer="below",
                            annotation_text="IC 95%",
                            annotation_position="left"
                        )
                        
                        fig_scatter.update_traces(marker_color='#FF8C00', marker_size=10)
                        fig_scatter.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font_color='#FFF',
                            height=400,
                            xaxis_title='Número da APA',
                            yaxis_title='Convergência (%)',
                            hovermode='closest'
                        )
                        
                        st.plotly_chart(fig_scatter, use_container_width=True)
                        
                        st.markdown("""
                        **Dica de Interpretação:**
                        
                        - **Pontos maiores:** Mais temas compartilhados entre negociador e causador
                        - **Pontos menores:** Menos temas compartilhados
                        - **Padrão nos pontos maiores?** Se os maiores têm maior convergência, há correlação positiva
                        """)
                        
                        st.markdown("""
                        **Como interpretar os números na prática:**
                        
                        - **Convergência 40-60%:** Normal — há sempre alguma diferença de perspectiva entre negociador e causador
                        - **Convergência > 60%:** Excelente — o negociador está na "mesma frequência" que o causador
                        - **Convergência < 40%:** Alerta — há risco de desencontro de comunicação
                        
                        **Dica:** Se a maioria das suas negociações tem convergência > 50%, sua equipe está fazendo escuta ativa de forma consistente! 🎯
                        """)
                        
                        # ── ANÁLISE POR NEGOCIADOR (SE FILTRADO) ──────
                        if filtro_neg_g != "Todos":
                            st.markdown("---")
                            st.markdown("#### ✔️ Análise Específica do Negociador")
                            
                            conv_neg = df_conv_agg['Convergencia'].mean()
                            
                            if conv_neg >= 60:
                                status = "✅ Excelente — Alta sintonia temática com causadores"
                                cor = "🟢"
                            elif conv_neg >= 40:
                                status = "⚠️ Moderado — Alguns temas divergentes"
                                cor = "🟡"
                            else:
                                status = "❌ Fraco — Muita divergência temática. Recomendado reforço em escuta ativa"
                                cor = "🔴"
                            
                            st.markdown(f"""
                            **Negociador:** {filtro_neg_g}
                            
                            **Convergência média:** {conv_neg:.1f}%
                            
                            **Status:** {status}
                            
                            **Recomendação:**
                            - Se convergência < 40%: Investir em treinamento de escuta ativa
                            - Se convergência 40-60%: Consolidar técnicas de rapport
                            - Se convergência > 60%: Excelente! Usar como referência para equipe
                            """)
                        
                        # ── LEITURA OPERACIONAL ──────────────────────
                        st.markdown("---")
                        st.markdown("### ✔️ Leitura Operacional")
                        
                        st.markdown(f"""
                        **O que os dados mostram:**
                        
                        - **Convergência média de {media_conv:.1f}%:** Em média, há {media_conv:.0f}% de sincronização temática
                        - **Variação (DP ±{dp_conv:.1f}%):** Há oscilação significativa entre ocorrências
                        - **Temas compartilhados (média {media_compartilhados:.1f}):** Cada negociador-causador compartilha ~{media_compartilhados:.0f} temas em comum
                        
                        **Interpretação:**
                        - Convergência alta (> 60%) = Negociador e causador falam dos mesmos assuntos
                        - Convergência baixa (< 40%) = Universos temáticos diferentes = risco de desencontro
                        
                        **Ação Recomendada:**
                        Se convergência < 40%, implementar treinamento focado em:
                        1. **Escuta Ativa** — Entender os temas do causador antes de impor a agenda
                        2. **Validação Emocional** — Reconhecer as preocupações mesmo que diferentes
                        3. **Ponte Temática** — Conectar temas do causador aos temas da resolução
                        
                        ---
                        
                        **🔍 Qualidade Estatística desta Análise:**
                        
                        Nível de Robustez: **{robustez['nivel']}**
                        
                        {robustez['descricao']}
                        
                        **Recomendação final:** Colete {robustez['deficit']:.0f} mais APAs para atingir N = 30 e ter análise ROBUSTA.
                        """)
                    
                    else:
                        st.info('⚠️ Sem dados suficientes para calcular convergência temática nos filtros atuais.')
                
                except Exception as e:
                    st.warning(f'⚠️ Erro ao processar convergência: {str(e)[:80]}')
            else:
                st.warning('⚠️ Colunas de transcrição não encontradas.')
    # ──────────────────────────────────────────────────────────
    # ANÁLISE: REGRESSÃO LINEAR MULTIVARIADA
    # O que prediz queda de agressividade? Análise robusta e validada
    # ──────────────────────────────────────────────────────────

    st.markdown("""
    <div class='info-card'>
    <h5 style='color: #FFD700; margin-top: 0;'>O que Prediz Queda de Agressividade?</h5>
    <p style='font-size:1.1rem;color:#ddd;'>
    Análise multivariada com validação estatística.
    Identifica quais fatores realmente influenciam a redução de agressividade,
    controlando confundidores (viés de negociador, tipo de ocorrência, etc).
    </p>
    </div>
    """, unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────
    # BOTÃO TOGGLE
    # ──────────────────────────────────────────────────────────
    col_left, col_center, col_right = st.columns([1, 1, 1])
    with col_center:
        is_regressao = render_toggle_button(
            label="✔️ Abrir Análise Multivariada",
            session_key="analise_regressao",
            button_key="btn_analise_regressao"
        )

    st.markdown("---")

    # ──────────────────────────────────────────────────────────
    # CONTEÚDO (Dentro do if)
    # ──────────────────────────────────────────────────────────
    if is_regressao:
        
        # ═══════════════════════════════════════════════════════════
        # PASSO 1: PREPARAR DADOS
        # ═══════════════════════════════════════════════════════════
        
        with st.spinner("⏳ Preparando dados..."):
            # Encontrar colunas
            
            col_agr_princ_ch = analise.achar_coluna(df_quali_filt, "Principal", "Agressividade", "Chegada")
            col_agr_princ_en = analise.achar_coluna(df_quali_filt, "Principal", "Agressividade", "Encerramento")
            col_agr_sec_ch = analise.achar_coluna(df_quali_filt, "Secundário", "Agressividade", "Chegada")
            col_agr_sec_en = analise.achar_coluna(df_quali_filt, "Secundário", "Agressividade", "Encerramento")
            col_agr_lider_ch = analise.achar_coluna(df_quali_filt, "Líder", "Agressividade", "Chegada")
            col_agr_lider_en = analise.achar_coluna(df_quali_filt, "Líder", "Agressividade", "Encerramento")

            col_recep_princ_ch = analise.achar_coluna(df_quali_filt, "Principal", "Receptividade", "Chegada")
            
            # Validar colunas
            colunas_necessarias = [col_agr_princ_ch, col_agr_princ_en, col_agr_sec_ch, 
                                col_agr_sec_en, col_agr_lider_ch, col_agr_lider_en]
            
            if not all(colunas_necessarias):
                st.error("❌ Colunas de agressividade não encontradas. Verifique o formulário.")
            else:
                # Calcular deltas
                df_reg_prep = analise.calcular_delta_agressividade_consenso(
                    df_quali_filt,
                    col_agr_princ_ch, col_agr_princ_en,
                    col_agr_sec_ch, col_agr_sec_en,
                    col_agr_lider_ch, col_agr_lider_en
                )
                
                # Preparar para regressão
                df_modelo, erro = analise.preparar_dados_regressao(
                    df_reg_prep,
                    col_tempo="Tempo de Negociação Real",
                    col_negociador="Negociador Principal do incidente crítico",
                    col_tipologia="Tipologia",
                    col_modalidade="Modalidade",
                    col_resolucao="Resolução",
                    col_recep_chegada=col_recep_princ_ch
                )
                
                if erro:
                    st.warning(f"⚠️ {erro}")
                else:
                    # ═══════════════════════════════════════════════════════════
                    # PASSO 2: AJUSTAR MODELO
                    # ═══════════════════════════════════════════════════════════
                    
                    resultado_modelo, erro_modelo = analise.ajustar_regressao_linear(df_modelo)
                    
                    if erro_modelo:
                        st.error(f"❌ {erro_modelo}")
                    else:
                        
                        # ═══════════════════════════════════════════════════════════
                        # SEÇÃO 1: RESUMO DO MODELO
                        # ═══════════════════════════════════════════════════════════
                        
                        st.markdown("""
                        <div class='info-card'>
                        <h5 style='color: #FFD700;'>Qualidade do Modelo</h5>
                        """, unsafe_allow_html=True)
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("N (Ocorrências)", resultado_modelo['n'])
                        with col2:
                            st.metric("R² (Variância Explicada)", f"{resultado_modelo['r2']:.1%}")
                        with col3:
                            st.metric("R² Ajustado", f"{resultado_modelo['r2_adj']:.1%}")
                        with col4:
                            p_f = resultado_modelo['p_f']
                            sig = "✅ Significativo" if p_f < 0.05 else "❌ Não significativo"
                            st.metric("Modelo Global", sig)
                        
                        st.markdown("""
                        <div style='background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; margin-top: 10px;'>
                        <strong>Interpretação:</strong> O modelo explica <strong>{:.1%}</strong> da variação em queda de agressividade.
                        O p-value global é <strong>{:.4f}</strong> ({}).
                        </div>
                        """.format(
                            resultado_modelo['r2'],
                            resultado_modelo['p_f'],
                            "✅ Modelo válido (p < 0.05)" if resultado_modelo['p_f'] < 0.05 else "❌ Modelo fraco (p ≥ 0.05)"
                        ), unsafe_allow_html=True)
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        # ═══════════════════════════════════════════════════════════
                        # SEÇÃO 2: COEFICIENTES
                        # ═══════════════════════════════════════════════════════════
                        
                        st.markdown("""
                        <div class='info-card'>
                        <h5 style='color: #FFD700;'>🎯 Coeficientes do Modelo</h5>
                        """, unsafe_allow_html=True)
                        
                        df_coef = analise.extrair_coeficientes_significativos(resultado_modelo)
                        
                        # Tabela formatada
                        st.dataframe(
                            df_coef.style.format({
                                'Coeficiente': '{:.3f}',
                                'SE': '{:.3f}',
                                't-stat': '{:.2f}',
                                'p-value': '{:.4f}',
                                'IC_Lower': '{:.3f}',
                                'IC_Upper': '{:.3f}'
                            }).highlight_max(subset=['Coeficiente'], color='#10b981', axis=0)
                            .highlight_min(subset=['Coeficiente'], color='#f59e0b', axis=0),
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Gráfico de coeficientes com IC
                        df_plot = df_coef[df_coef['Variável'] != '(Intercept)'].copy()
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=df_plot['IC_Lower'],
                            y=df_plot['Variável'],
                            mode='markers',
                            marker=dict(size=1, color='rgba(0,0,0,0)'),
                            showlegend=False
                        ))
                        
                        fig.add_trace(go.Scatter(
                            x=df_plot['Coeficiente'],
                            y=df_plot['Variável'],
                            mode='markers',
                            marker=dict(
                                size=8,
                                color=['#10b981' if x > 0 else '#f59e0b' for x in df_plot['Coeficiente']]
                            ),
                            name='Coeficiente',
                            text=df_plot.apply(
                                lambda r: f"{r['Variável']}<br>β = {r['Coeficiente']:.3f}<br>p = {r['p-value']:.4f}",
                                axis=1
                            ),
                            hovertemplate='%{text}<extra></extra>'
                        ))
                        
                        for idx, row in df_plot.iterrows():
                            fig.add_trace(go.Scatter(
                                x=[row['IC_Lower'], row['IC_Upper']],
                                y=[row['Variável'], row['Variável']],
                                mode='lines',
                                line=dict(color='#888', width=2),
                                showlegend=False,
                                hoverinfo='skip'
                            ))
                        
                        fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
                        fig.update_layout(
                            title="Coeficientes com IC 95%",
                            xaxis_title="Coeficiente",
                            yaxis_title="Variável",
                            height=400,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font_color="#FFF",
                            hovermode='closest'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        # ═══════════════════════════════════════════════════════════
                        # SEÇÃO 3: COMPARAÇÃO DE PERCEPÇÕES
                        # ═══════════════════════════════════════════════════════════
                        
                        st.markdown("""
                        <div class='info-card'>
                        <h5 style='color: #FFD700;'>Triangulação: Consenso dos 3 Negociadores</h5>
                        """, unsafe_allow_html=True)
                        
                        col_tri1, col_tri2, col_tri3, col_tri4 = st.columns(4)
                        
                        delta_princ_mean = df_reg_prep['delta_princ'].dropna().mean()
                        delta_sec_mean = df_reg_prep['delta_sec'].dropna().mean()
                        delta_lider_mean = df_reg_prep['delta_lider'].dropna().mean()
                        delta_cons_mean = df_reg_prep['delta_consenso'].dropna().mean()
                        
                        with col_tri1:
                            st.metric("Principal (Média)", f"{delta_princ_mean:.2f}")
                        with col_tri2:
                            st.metric("Secundário (Média)", f"{delta_sec_mean:.2f}")
                        with col_tri3:
                            st.metric("Líder (Média)", f"{delta_lider_mean:.2f}")
                        with col_tri4:
                            st.metric("Consenso (Média)", f"{delta_cons_mean:.2f}")
                        
                        # Gráfico de distribuição
                        fig_dist = go.Figure()
                        
                        for label, dados, cor in [
                            ("Principal", df_reg_prep['delta_princ'].dropna(), '#F97316'),
                            ("Secundário", df_reg_prep['delta_sec'].dropna(), '#FB923C'),
                            ("Líder", df_reg_prep['delta_lider'].dropna(), '#FBBF24'),
                            ("Consenso", df_reg_prep['delta_consenso'].dropna(), '#10b981')
                        ]:
                            fig_dist.add_trace(go.Box(y=dados, name=label, marker_color=cor))
                        
                        fig_dist.update_layout(
                            title="Distribuição de Deltas por Negociador",
                            yaxis_title="Delta de Agressividade",
                            height=350,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font_color="#FFF",
                            boxmode='group'
                        )
                        st.plotly_chart(fig_dist, use_container_width=True)
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        # ═══════════════════════════════════════════════════════════
                        # SEÇÃO 4: DIAGNÓSTICOS
                        # ═══════════════════════════════════════════════════════════
                        
                        st.markdown("""
                        <div class='info-card'>
                        <h5 style='color: #FFD700;'>Diagnósticos do Modelo</h5>
                        <p style='font-size: 0.85rem; color: #aaa;'>
                        Validação de assumções estatísticas.
                        </p>
                        """, unsafe_allow_html=True)
                        
                        diags = analise.diagnosticos_qualidade(resultado_modelo)
                        
                        col_d1, col_d2, col_d3 = st.columns(3)
                        
                        with col_d1:
                            status = "✅" if diags['normalidade']['p_value'] > 0.05 else "⚠️"
                            st.markdown(f"""
                            **{status} Normalidade dos Resíduos**
                            
                            p-value: {diags['normalidade']['p_value']:.4f}
                            
                            {diags['normalidade']['interpretacao']}
                            
                            _{diags['normalidade']['implicacao']}_
                            """)
                        
                        with col_d2:
                            status = "✅" if diags['homocedasticidade']['p_value'] > 0.05 else "⚠️"
                            st.markdown(f"""
                            **{status} Homocedasticidade**
                            
                            p-value: {diags['homocedasticidade']['p_value']:.4f}
                            
                            {diags['homocedasticidade']['interpretacao']}
                            
                            _{diags['homocedasticidade']['implicacao']}_
                            """)
                        
                        with col_d3:
                            vif_max = diags['colinearidade']['vif_max']
                            status = "✅" if vif_max < 5 else "⚠️"
                            st.markdown(f"""
                            **{status} Colinearidade (VIF)**
                            
                            VIF máximo: {vif_max:.2f}
                            
                            {diags['colinearidade']['interpretacao']}
                            
                            _{diags['colinearidade']['implicacao']}_
                            """)
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        # ═══════════════════════════════════════════════════════════
                        # SEÇÃO 5: RESÍDUOS
                        # ═══════════════════════════════════════════════════════════
                        
                        st.markdown("""
                        <div class='info-card'>
                        <h5 style='color: #FFD700;'>Diagnóstico de Resíduos</h5>
                        """, unsafe_allow_html=True)
                        
                        col_res1, col_res2 = st.columns(2)
                        
                        with col_res1:
                            fig_res = go.Figure()
                            fig_res.add_trace(go.Scatter(
                                x=resultado_modelo['y_pred'],
                                y=resultado_modelo['residuos'],
                                mode='markers',
                                marker=dict(color='#F97316', size=6),
                                text=resultado_modelo['residuos'],
                                hovertemplate='Predito: %{x:.2f}<br>Resíduo: %{y:.2f}<extra></extra>'
                            ))
                            fig_res.add_hline(y=0, line_dash="dash", line_color="gray")
                            fig_res.update_layout(
                                title="Resíduos vs Preditos",
                                xaxis_title="Valores Preditos",
                                yaxis_title="Resíduos",
                                height=300,
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                font_color="#FFF"
                            )
                            st.plotly_chart(fig_res, use_container_width=True)
                        
                        with col_res2:
                            fig_qq = go.Figure()
                            res_sorted = np.sort(resultado_modelo['residuos'])
                            q_teorico = np.sort(np.random.normal(0, resultado_modelo['se_residuos'], 1000))
                            
                            fig_qq.add_trace(go.Scatter(
                                x=q_teorico,
                                y=res_sorted,
                                mode='markers',
                                marker=dict(color='#10b981', size=5),
                                name='Q-Q Plot'
                            ))
                            
                            # Linha diagonal
                            min_val = min(q_teorico.min(), res_sorted.min())
                            max_val = max(q_teorico.max(), res_sorted.max())
                            fig_qq.add_trace(go.Scatter(
                                x=[min_val, max_val],
                                y=[min_val, max_val],
                                mode='lines',
                                line=dict(color='gray', dash='dash'),
                                name='Normal',
                                showlegend=True
                            ))
                            
                            fig_qq.update_layout(
                                title="Q-Q Plot (Normalidade)",
                                xaxis_title="Quantis Teóricos",
                                yaxis_title="Quantis Observados",
                                height=300,
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                font_color="#FFF"
                            )
                            st.plotly_chart(fig_qq, use_container_width=True)
                        
                        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

                                        

    # ============================================================
    # ANÁLISE DE PERFIL DE NEGOCIADORES
    # (Adicionar na Série Histórica, ANTES da "Síntese Interpretativa por IA")
    # ============================================================

    st.markdown("""
    <div class='info-card'>
    <h5 style='color: #FFD700;'>Perfil de Negociadores: Escuta Ativa vs Persuasão</h5>
    <p style='font-size:1.1rem;color:#ddd;'>
    Análise estatística comparativa dos padrões de negociação por negociador.
    Identifica tendências, agrupa similares e testa significância estatística.
    </p>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 1, 1])

    with col_center:
        is_perfil_negociadores = render_toggle_button(
            label="✔️ Abrir Análise de Perfil",
            session_key="perfil_negociadores",
            button_key="btn_perfil_negociadores"
        )

    st.markdown("---")

    if is_perfil_negociadores:
        
        # ── CARREGAR DADOS ──────────────────────────────────────────
        try:
            # Importar função de análise
            from analise import (
                analisar_perfil_negociadores,
                gerar_grafo_palavras_com_estilo,
                gerar_legenda_negociadores_dinamica,
                gerar_tabela_score,
                gerar_scatter_score_efetividade,
                gerar_barras_grupos,
                classificar_tecnica
            )
            
            # Assumindo que df_tec está carregado (como nas análises anteriores)
            df_tec = st.session_state.get("df_tec", pd.DataFrame())
            
            if df_tec.empty:
                st.warning("⚠️ Tabela de técnicas não carregada.")
            else:
                
                # ── EXECUTAR ANÁLISE ────────────────────────────────────
                with st.spinner("⏳ Analisando perfis de negociadores..."):
                    resultado_analise = analisar_perfil_negociadores(df_tec)
                    
                    df_resultado = resultado_analise['df_resultado']
                    df_tec_classificado = resultado_analise['df_tecnicas_classificadas']
                    anova = resultado_analise['anova']
                    chi2 = resultado_analise['chi2']
                    kmeans = resultado_analise['kmeans']
                
                # Gerar paleta de cores para negociadores (dinâmica)
                negociadores_unicos = df_resultado['Negociador'].unique()
                paleta_cores = {
                    'laranja_forte': '#F97316',        # Laranja vibrante (principal)
                    'laranja_medio': '#FB923C',        # Laranja médio
                    'laranja_claro': '#FDBA74',        # Laranja claro
                    'laranja_muito_claro': '#FED7AA',  # Laranja pastel
                    'amarelo': '#FBBF24',              # Amarelo ouro
                    'amarelo_claro': '#FCD34D',        # Amarelo claro
                    'amber': '#F59E0B',                # Âmbar quente
                    'amber_claro': '#FDBF28',          # Âmbar claro
                    'preto': '#000000',                # Preto puro
                    'cinza_escuro': '#1F2937',         # Cinza escuro (neutro)
                    'cinza_medio': '#374151',          # Cinza médio
                    'laranja_escuro': '#EA580C',       # Laranja escuro
                    'vermelho_laranja': '#DC2626',     # Vermelho-laranja
                }
                
                # Converter para lista para melhor controle de alocação
                cores_lista = list(paleta_cores.values())
                
                # Alocar cores dinamicamente aos negociadores
                negociadores_cores = {
                    neg: cores_lista[i % len(cores_lista)]
                    for i, neg in enumerate(negociadores_unicos)
                }

                
                cores_lista = list(paleta_cores.values())
                negociadores_cores = {
                    neg: cores_lista[i % len(cores_lista)]
                    for i, neg in enumerate(negociadores_unicos)
                }
                
                # ── CRIAR TABS ──────────────────────────────────────────
                tab_score, tab_grafo, tab_stats, tab_kmeans = st.tabs([
                    "✔️ Scores e Efetividades",
                    "🕸️ Grafo de Palavras",
                    "✔️ Testes Estatísticos",
                    "✔️ Clusters (K-means)"
                ])
                
                # ── TAB 1: SCORES ───────────────────────────────────────
                with tab_score:
                    st.markdown("""
                    <div class='info-card'>
                    <h5 style='color: #FFD700; margin-top: 0;'>Score de Tendência</h5>
                    <p style='font-size:0.9rem;color:#aaa;'>
                    Score = -100 (100% Persuasão) a +100 (100% Escuta Ativa)
                    <br>Ponderado pela atitude do causador em cada técnica aplicada.
                    </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Tabela
                    st.markdown("### Tabela de Resultados")
                    df_display = gerar_tabela_score(df_resultado)
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                    
                    # Gráfico Scatter
                    st.markdown("---")
                    st.markdown("### Score vs Efetividade Média")
                    fig_scatter = gerar_scatter_score_efetividade(df_resultado)
                    st.plotly_chart(fig_scatter, use_container_width=True)
                    
                    # Gráfico Barras
                    st.markdown("---")
                    st.markdown("### Distribuição de Técnicas")
                    fig_barras = gerar_barras_grupos(df_resultado)
                    st.plotly_chart(fig_barras, use_container_width=True)
                
                # ── TAB 2: GRAFO ────────────────────────────────────────
                
                #

                with tab_grafo:
                    st.markdown("""
                    <div class='info-card'>
                    <h5 style='color: #FFD700; margin-top: 0;'>🕸️ Rede de Palavras</h5>
                    <p style='font-size:0.9rem;color:#aaa;'>
                    Palavras dos trechos de transcrição, coloridas por negociador.
                    Tamanho = Frequência | Conexões = Co-ocorrência
                    </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # ── LEGENDA DINÂMICA ──
                    
                    if negociadores_cores:
                        st.markdown("""
                        <div style='
                            background: rgba(30, 30, 30, 0.85);
                            backdrop-filter: blur(16px) saturate(180%);
                            -webkit-backdrop-filter: blur(16px) saturate(180%);
                            border: 1px solid rgba(255, 255, 255, 0.1);
                            border-radius: 12px;
                            padding: 15px;
                            margin-bottom: 20px;
                        '>
                        <h5 style='color: #FFD700; margin-top: 0; margin-bottom: 15px;'>🎨 Legenda de Negociadores</h5>
                        <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;'>
                        """, unsafe_allow_html=True)
                        
                        cols = st.columns(min(3, len(negociadores_cores)))
                        for i, (neg, cor) in enumerate(sorted(negociadores_cores.items())):
                            with cols[i % len(cols)]:
                                st.markdown(f"""
                                <div style='
                                    display: flex;
                                    align-items: center;
                                    background: rgba(255, 255, 255, 0.05);
                                    padding: 10px;
                                    border-radius: 8px;
                                    border-left: 4px solid {cor};
                                '>
                                    <div style='
                                        width: 24px;
                                        height: 24px;
                                        background-color: {cor};
                                        border-radius: 50%;
                                        margin-right: 10px;
                                    '></div>
                                    <span style='color: #FFF; font-weight: 500;'>{neg}</span>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        st.markdown("</div></div>", unsafe_allow_html=True)
                    
                    with st.spinner("✔️ Gerando grafo com glassmorphism..."):
                        try:
                            net = gerar_grafo_palavras_com_estilo(df_tec_classificado, negociadores_cores)
                            
                            if net is None:
                                st.warning("⚠️ Dados insuficientes para gerar o grafo (precisa de mais trechos de transcrição).")
                            else:
                                try:
                                    import tempfile
                                    import os
                                    
                                    # Usar arquivo temporário
                                    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                                        temp_file = f.name
                                    
                                    # Renderizar e salvar
                                    net.write_html(temp_file, notebook=False)
                
                                    # Ler arquivo
                                    with open(temp_file, 'r', encoding='utf-8') as f:
                                        html_content = f.read()
                                    
                                    # INJETAR CSS PARA FUNDO PRETO/GLASSMORPHISM
                                    html_content = html_content.replace(
                                        '<style type="text/css">',
                                        '''<style type="text/css">
                                        html, body {
                                            margin: 0;
                                            padding: 0;
                                            background: rgba(0, 0, 0, 0.95) !important;
                                            backdrop-filter: blur(16px) saturate(180%);
                                            -webkit-backdrop-filter: blur(16px) saturate(180%);
                                        }
                                        #mynetwork {
                                            background: rgba(30, 30, 30, 0.9) !important;
                                            backdrop-filter: blur(16px) saturate(180%);
                                            -webkit-backdrop-filter: blur(16px) saturate(180%);
                                        }
                                        '''
                                    )
                                    
                                    # Exibir grafo
                                    st.components.v1.html(html_content, height=800, scrolling=True)
                                    
                                    # Limpar arquivo temporário
                                    try:
                                        os.remove(temp_file)
                                    except:
                                        pass
                                    
                                    st.success("✅ Grafo gerado com sucesso!")
                                    
                                    # Informações sobre o grafo
                                    st.markdown("""
                                    ### 💡 Como interpretar:
                                    - **Bolinha GRANDE**: Palavra muito frequente
                                    - **Bolinha PEQUENA**: Palavra pouco frequente
                                    - **COR**: Qual negociador mais usou a palavra
                                    - **LINHAS**: Palavras que aparecem juntas nos trechos
                                    """)
                                    
                                except Exception as e:
                                    st.error(f"❌ Erro ao renderizar grafo: {str(e)[:80]}")
                        
                        except Exception as e:
                            st.error(f"❌ Erro geral: {str(e)[:100]}")
                
                # ── TAB 3: TESTES ESTATÍSTICOS ──────────────────────────
                with tab_stats:
                    st.markdown("""
                    <div class='info-card'>
                    <h5 style='color: #FFD700; margin-top: 0;'>Testes Estatísticos</h5>
                    <p style='font-size:0.9rem;color:#aaa;'>
                    Validação estatística das diferenças entre negociadores.
                    </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # ANOVA
                    if anova:
                        st.markdown("### 🧪 ANOVA - Efetividade entre Negociadores")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("F-statistic", anova['f_statistic'])
                        with col2:
                            st.metric("P-value", anova['p_value'])
                        with col3:
                            status = "✅ Significativo" if anova['significativo'] else "❌ Não significativo"
                            st.metric("Resultado", status)
                        
                        st.markdown(f"**Interpretação:** {anova['interpretacao']}")
                        st.markdown("---")
                    
                    # Chi-quadrado
                    if chi2:
                        st.markdown("### 🧪 Chi-Quadrado - Distribuição de Técnicas")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("χ²-statistic", chi2['chi2_statistic'])
                        with col2:
                            st.metric("P-value", chi2['p_value'])
                        with col3:
                            st.metric("Graus de Liberdade", chi2['df'])
                        with col4:
                            status = "✅ Significativo" if chi2['significativo'] else "❌ Não significativo"
                            st.metric("Resultado", status)
                        
                        st.markdown(f"**Interpretação:** {chi2['interpretacao']}")
                
                # ── TAB 4: K-MEANS ──────────────────────────────────────
                with tab_kmeans:
                    st.markdown("""
                    <div class='info-card'>
                    <h5 style='color: #FFD700; margin-top: 0;'>Clustering K-means (k=2)</h5>
                    <p style='font-size:0.9rem;color:#aaa;'>
                    Agrupa negociadores em 2 clusters: Escuta Ativa vs Persuasão/Influência.
                    </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Tabela com clusters
                    st.markdown("### ✔️ Atribuição de Clusters")
                    df_clusters = df_resultado[['Negociador', 'Score Tendência', 'Cluster']].copy()
                    
                    if 'Perfil_Cluster' in df_resultado.columns:
                        df_clusters['Perfil'] = df_resultado['Perfil_Cluster']
                    
                    st.dataframe(df_clusters, use_container_width=True, hide_index=True)
                    
                    # Visualizar clusters
                    st.markdown("---")
                    st.markdown("### ✔️ Visualização dos Clusters")
                    
                    fig_clusters = go.Figure()
                    
                    for cluster in sorted(df_resultado['Cluster'].unique()):
                        df_cluster = df_resultado[df_resultado['Cluster'] == cluster]
                        
                        perfil = df_cluster['Perfil_Cluster'].iloc[0] if 'Perfil_Cluster' in df_resultado.columns else f"Cluster {cluster}"
                        cor = '#10b981' if perfil == 'Escuta Ativa' else '#f59e0b'
                        
                        fig_clusters.add_trace(go.Scatter(
                            x=df_cluster['Score Tendência'],
                            y=df_cluster['Efetividade Escuta'],
                            mode='markers+text',
                            name=perfil,
                            text=df_cluster['Negociador'],
                            textposition='top center',
                            marker=dict(size=15, color=cor),
                        ))
                    
                    fig_clusters.update_layout(
                        title='Clustering de Negociadores',
                        xaxis_title='Score Tendência',
                        yaxis_title='Efetividade Escuta Ativa',
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#FFF",
                        height=500
                    )
                    
                    st.plotly_chart(fig_clusters, use_container_width=True)
                    
                    # Interpretação
                    st.markdown("---")
                    st.markdown("### 💡 Interpretação")
                    
                    for cluster in sorted(df_resultado['Cluster'].unique()):
                        df_clust = df_resultado[df_resultado['Cluster'] == cluster]
                        
                        perfil = df_clust['Perfil_Cluster'].iloc[0] if 'Perfil_Cluster' in df_resultado.columns else f"Cluster {cluster}"
                        negociadores = ', '.join(df_clust['Negociador'].tolist())
                        score_medio = df_clust['Score Tendência'].mean()
                        
                        if perfil == 'Escuta Ativa':
                            emoji = "🟢"
                            desc = "Tendem a usar mais **Escuta Ativa** (Paráfrase, Empatia, Resumo)"
                        else:
                            emoji = "🟠"
                            desc = "Tendem a usar mais **Persuasão/Influência** (Desconstrução, Reciprocidade, Medo)"
                        
                        st.markdown(f"""
                        {emoji} **{perfil}** (Score médio: {score_medio:.1f}%)
                        - Negociadores: {negociadores}
                        - Padrão: {desc}
                        """)
        
        except ImportError as e:
            st.error(f"❌ Erro ao importar módulo: {str(e)}")
        except Exception as e:
            st.error(f"❌ Erro na análise: {str(e)[:200]}")

    st.markdown("---")

    # ============================================================
    # SUMARIZAÇÃO DE FUNÇÕES E ENTRADA DE DADOS
    # ============================================================
    st.markdown("""
    <div class='info-card'>
    <h5 style='color: #FFD700; margin-top: 0;'>Sumarização de Funções e Entrada de Dados</h5>
    <p style='font-size:0.9rem; color:#bbb;'>
    Análise assistida por IA dos registros de funções, problemas identificados,
    ações corretivas e práticas promissoras das APAs filtradas.
    </p>
    </div>
    """, unsafe_allow_html=True)

    col_sum_left, col_sum_center, col_sum_right = st.columns([1, 1, 1])
    with col_sum_center:
        is_sum_funcoes = render_toggle_button(
            label="✔️ Abrir Sumarização de Funções",
            session_key="sum_funcoes_historico",
            button_key="btn_sum_funcoes_historico"
        )

    st.markdown("---")

    if is_sum_funcoes:
        cache_key_funcoes = f"sum_funcoes_{filtro_neg_g}_{len(df_quali_filt)}"

        if cache_key_funcoes not in st.session_state:
            with st.spinner("Analisando registros de funções com IA..."):
                try:
                    import ia_link

                    # Campos de funções a coletar
                    FUNCOES_CAMPOS = {
                        "Negociador Principal": {
                            "descricao":  "FUNÇÕES: NEGOCIADOR PRINCIPAL",
                            "problema":   "FUNÇÕES: NEGOCIADOR PRINCIPAL - PROBLEMA IDENTIFICADO",
                            "acoes":      "FUNÇÕES: NEGOCIADOR PRINCIPAL - AÇÕES CORRETIVAS ADOTADAS",
                            "praticas":   "FUNÇÕES: NEGOCIADOR PRINCIPAL - PRÁTICAS PROMISSORAS",
                        },
                        "Negociador Secundário": {
                            "descricao":  "FUNÇÕES: NEGOCIADOR SECUNDÁRIO",
                            "problema":   "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PROBLEMA IDENTIFICADO",
                            "acoes":      "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - AÇÕES CORRETIVAS ADOTADAS",
                            "praticas":   "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PRÁTICAS PROMISSORAS",
                        },
                        "Negociador Anotador": {
                            "descricao":  "FUNÇÕES: NEGOCIADOR ANOTADOR",
                            "problema":   "FUNÇÕES: NEGOCIADOR ANOTADOR - PROBLEMA IDENTIFICADO",
                            "acoes":      "FUNÇÕES: NEGOCIADOR ANOTADOR - AÇÕES CORRETIVAS ADOTADAS",
                            "praticas":   "FUNÇÕES: NEGOCIADOR ANOTADOR - PRÁTICAS PROMISSORAS",
                        },
                        "Negociador Líder": {
                            "descricao":  "FUNÇÕES: NEGOCIADOR LÍDER",
                            "problema":   "FUNÇÕES: NEGOCIADOR LÍDER - PROBLEMA IDENTIFICADO",
                            "acoes":      "FUNÇÕES: NEGOCIADOR LÍDER - AÇÕES CORRETIVAS ADOTADAS",
                            "praticas":   "FUNÇÕES: NEGOCIADOR LÍDER - PRÁTICAS PROMISSORAS",
                        },
                        "Auxiliar de Logística": {
                            "descricao":  "FUNÇÕES: NEGOCIADOR AUXILIAR DE LOGÍSTICA",
                            "problema":   "FUNÇÕES: AUXILIAR DE LOGÍSTICA - PROBLEMA IDENTIFICADO",
                            "acoes":      "FUNÇÕES: AUXILIAR DE LOGÍSTICA - AÇÕES CORRETIVAS",
                            "praticas":   "FUNÇÕES: AUXILIAR DE LOGÍSTICA - PRÁTICAS PROMISSORAS",
                        },
                        "Auxiliar de Informações": {
                            "descricao":  "FUNÇÕES: NEGOCIADOR AUXILIAR DE INFORMAÇÕES",
                            "problema":   "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PROBLEMA IDENTIFICADO",
                            "acoes":      "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - AÇÕES CORRETIVAS",
                            "praticas":   "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PRÁTICAS PROMISSORAS",
                        },
                        "Profissional de Saúde Mental": {
                            "descricao":  "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL",
                            "problema":   "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PROBLEMA IDENTIFICADO",
                            "acoes":      "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - AÇÕES CORRETIVAS ADOTADAS",
                            "praticas":   "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PRÁTICAS PROMISSORAS",
                        },
                    }

                    resumos_funcoes = {}

                    for funcao, campos in FUNCOES_CAMPOS.items():
                        textos = {"descricao": [], "problema": [], "acoes": [], "praticas": []}

                        for _, row in df_quali_filt.iterrows():
                            for chave, col in campos.items():
                                if col in df_quali_filt.columns:
                                    val = limpar_valor(row.get(col, ''))
                                    if val and val not in ['N/D', 'nan', '']:
                                        textos[chave].append(val)

                        # Só gera sumarização se houver conteúdo
                        tem_conteudo = any(len(v) > 0 for v in textos.values())
                        if not tem_conteudo:
                            resumos_funcoes[funcao] = None
                            continue

                        texto_consolidado = ""
                        if textos["descricao"]:
                            texto_consolidado += f"DESCRIÇÕES ({len(textos['descricao'])} registros):\n"
                            texto_consolidado += "\n".join(f"- {t}" for t in textos["descricao"]) + "\n\n"
                        if textos["problema"]:
                            texto_consolidado += f"PROBLEMAS IDENTIFICADOS ({len(textos['problema'])} registros):\n"
                            texto_consolidado += "\n".join(f"- {t}" for t in textos["problema"]) + "\n\n"
                        if textos["acoes"]:
                            texto_consolidado += f"AÇÕES CORRETIVAS ({len(textos['acoes'])} registros):\n"
                            texto_consolidado += "\n".join(f"- {t}" for t in textos["acoes"]) + "\n\n"
                        if textos["praticas"]:
                            texto_consolidado += f"PRÁTICAS PROMISSORAS ({len(textos['praticas'])} registros):\n"
                            texto_consolidado += "\n".join(f"- {t}" for t in textos["praticas"]) + "\n\n"

                        prompt = f"""Você é um analista especializado em negociação tática de alto risco (GATE/PMESP).
Analise os registros consolidados abaixo da função {funcao} em {len(df_quali_filt)} APAs.

{texto_consolidado}

Gere uma sumarização estruturada com:
1. **Padrão de Atuação** — como essa função tem sido desempenhada
2. **Problemas Recorrentes** — principais dificuldades identificadas
3. **Ações Corretivas Adotadas** — o que a equipe tem feito para corrigir
4. **Práticas Promissoras** — o que está funcionando bem
5. **Recomendação** — 1 ação prioritária para desenvolvimento desta função

Seja direto e objetivo. Use linguagem técnica operacional."""

                        try:
                            resumo = ia_link.chamar_openai_simples(prompt)
                            resumos_funcoes[funcao] = resumo
                        except Exception:
                            resumos_funcoes[funcao] = "⚠️ Não foi possível gerar sumarização para esta função."

                    st.session_state[cache_key_funcoes] = resumos_funcoes

                except Exception as e:
                    st.error(f"❌ Erro ao gerar sumarização: {str(e)[:100]}")
                    st.session_state[cache_key_funcoes] = {}

        resumos_funcoes = st.session_state.get(cache_key_funcoes, {})

        if resumos_funcoes:
            funcoes_com_dados = {k: v for k, v in resumos_funcoes.items() if v}

            if not funcoes_com_dados:
                st.warning("⚠️ Nenhuma função possui registros suficientes nas APAs filtradas.")
            else:
                tabs_funcoes = st.tabs([f"👤 {f}" for f in funcoes_com_dados.keys()])
                for tab, (funcao, resumo) in zip(tabs_funcoes, funcoes_com_dados.items()):
                    with tab:
                        st.markdown(f"""
                        <div class='info-card'>
                        <h5 style='color: #FFD700; margin-top: 0;'>👤 {funcao}</h5>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown(f"<div style='font-size:0.9rem; line-height:1.6'>{resumo}</div>",
                                    unsafe_allow_html=True)

        st.markdown("---")

    # ============================================================
    # SÍNTESE INTERPRETATIVA POR IA
    # ============================================================
    st.markdown("""
    <div class='info-card'>
    <h5 style='color: #FFD700; margin-top: 0;'>Síntese Interpretativa Assistida por Inteligência Artificial</h5>
    <p style='font-size:1.1rem;color:#ddd;'>
    A interpretação da IA é colaborativa e NÃO substitui a análise e compreensão do Avaliador/Negociador.
    Exige constante aprimoramento de instruções.
    </p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("✔ GERAR RELATÓRIO INTERPRETADO POR IA"):
        with st.spinner("✔️ Coletando dados reais e gerando interpretações..."):
            try:
                import ia_estatistica

                # ═══════════════════════════════════════════════════════
                # COLETA 1: METADADOS DA AMOSTRA
                # Por que: a IA precisa saber a composição da amostra
                #          (quantas ocorrências, tipos, modalidades, etc.)
                # Como:    lê diretamente do df_quali_filt com value_counts()
                # ═══════════════════════════════════════════════════════
                metadados = {"n_ocorrencias": len(df_quali_filt)}

                campos_meta = {
                    'Resolução': 'resolucoes',
                    'Tipologia': 'tipologias',
                    'Modalidade do incidente': 'modalidades',
                    'Sexo do Causador': 'sexo_causador',
                    'Uniforme Usado': 'uniforme',
                    'Forma de Transição': 'forma_transicao',
                }

                for col, chave in campos_meta.items():
                    if col in df_quali_filt.columns:
                        serie = df_quali_filt[col].apply(
                            lambda x: x[0] if isinstance(x, list) and len(x) > 0 else str(x)
                        )
                        serie = serie[~serie.isin(["N/D", "nan", "", "None"])]
                        if not serie.empty:
                            metadados[chave] = serie.value_counts().to_dict()

                # ═══════════════════════════════════════════════════════
                # COLETA 2: RANKING DE TÉCNICAS
                # Por que: a IA precisa saber quais técnicas são mais usadas
                # Como:    recria o df_tec filtrado com os mesmos filtros
                #          do painel e calcula value_counts()
                # ═══════════════════════════════════════════════════════
                ranking_tecnicas = {}
                _df_tec_ia = pd.DataFrame()

                try:
                    _df_tec_ia = df_tec.copy()

                    # Aplicar filtros de limpeza (mesma lógica do painel)
                    if "Negociador Principal do incidente crítico" in _df_tec_ia.columns:
                        _df_tec_ia["_Neg"] = _df_tec_ia["Negociador Principal do incidente crítico"].apply(limpar_valor)
                    if "Tipologia do incidente crítico" in _df_tec_ia.columns:
                        _df_tec_ia["_Tip"] = _df_tec_ia["Tipologia do incidente crítico"].apply(limpar_valor)
                    if "Modalidade do incidente crítico" in _df_tec_ia.columns:
                        _df_tec_ia["_Mod"] = _df_tec_ia["Modalidade do incidente crítico"].apply(limpar_valor)

                    # Aplicar mesmos filtros do painel
                    if filtro_neg_g != "Todos" and "_Neg" in _df_tec_ia.columns:
                        _df_tec_ia = _df_tec_ia[_df_tec_ia["_Neg"] == filtro_neg_g]
                    if filtro_tip_g != "Todas" and "_Tip" in _df_tec_ia.columns:
                        _df_tec_ia = _df_tec_ia[_df_tec_ia["_Tip"] == filtro_tip_g]
                    if filtro_mod_g != "Todas" and "_Mod" in _df_tec_ia.columns:
                        _df_tec_ia = _df_tec_ia[_df_tec_ia["_Mod"] == filtro_mod_g]

                    col_t = next(
                        (c for c in ["TÉCNICAS", "TECNICAS", "TÉCNICA", "TECNICA"]
                         if c in _df_tec_ia.columns),
                        None,
                    )

                    if col_t and not _df_tec_ia.empty:
                        freq = _df_tec_ia[col_t].value_counts()
                        ranking_tecnicas = {
                            "frequencias": freq.to_dict(),
                            "total_usos": int(freq.sum()),
                            "n_tecnicas_distintas": int(len(freq)),
                            "tecnica_mais_usada": str(freq.index[0]),
                            "frequencia_mais_usada": int(freq.iloc[0]),
                            "tecnica_menos_usada": str(freq.index[-1]),
                            "frequencia_menos_usada": int(freq.iloc[-1]),
                        }
                except Exception:
                    pass

                # ═══════════════════════════════════════════════════════
                # COLETA 3: EFETIVIDADE DAS TÉCNICAS
                # Por que: a IA precisa saber o score de cada técnica
                #          (positivas vs negativas = efetiva ou não)
                # Como:    classifica reações (-1, 0, +1) e calcula score
                # ═══════════════════════════════════════════════════════
                efetividade = {}

                try:
                    if col_t and not _df_tec_ia.empty:
                        col_reacao = next(
                            (c for c in _df_tec_ia.columns if 'ATITUDE' in c.upper()),
                            None,
                        )

                        if col_reacao:
                            def _norm_reacao(val):
                                if val is None:
                                    return None
                                s = str(val).strip()
                                if any(x in s for x in ["-1", "🔴", "Negativa", "negativa"]):
                                    return -1
                                elif any(x in s for x in ["0", "⚪", "Neutra", "neutra"]):
                                    return 0
                                elif any(x in s for x in ["1", "🟢", "Positiva", "positiva"]):
                                    return 1
                                return None

                            _df_ef = _df_tec_ia.copy()
                            _df_ef['_reacao'] = _df_ef[col_reacao].apply(_norm_reacao)

                            resumo_ef = []
                            for tecnica, grupo in _df_ef.groupby(col_t):
                                total = len(grupo)
                                pos = int((grupo['_reacao'] == 1).sum())
                                neu = int((grupo['_reacao'] == 0).sum())
                                neg = int((grupo['_reacao'] == -1).sum())
                                obs = pos + neu + neg
                                score = round(((pos - neg) / obs) * 100, 1) if obs > 0 else None
                                resumo_ef.append({
                                    "tecnica": str(tecnica),
                                    "total": total,
                                    "positivas": pos,
                                    "neutras": neu,
                                    "negativas": neg,
                                    "score": score,
                                })

                            resumo_ef.sort(
                                key=lambda x: x['score'] if x['score'] is not None else -999,
                                reverse=True
                            )

                            total_pos = sum(r['positivas'] for r in resumo_ef)
                            total_neg = sum(r['negativas'] for r in resumo_ef)
                            total_neu = sum(r['neutras'] for r in resumo_ef)
                            total_obs = total_pos + total_neg + total_neu
                            score_geral = round(
                                ((total_pos - total_neg) / max(1, total_obs)) * 100, 1
                            )

                            efetividade = {
                                "por_tecnica": resumo_ef,
                                "score_geral": score_geral,
                                "total_usos": sum(r['total'] for r in resumo_ef),
                                "total_positivas": total_pos,
                                "total_negativas": total_neg,
                                "total_neutras": total_neu,
                            }

                            if resumo_ef:
                                efetividade["tecnica_mais_efetiva"] = resumo_ef[0]["tecnica"]
                                efetividade["score_mais_efetiva"] = resumo_ef[0]["score"]
                                efetividade["tecnica_menos_efetiva"] = resumo_ef[-1]["tecnica"]
                                efetividade["score_menos_efetiva"] = resumo_ef[-1]["score"]
                except Exception:
                    pass

                # ═══════════════════════════════════════════════════════
                # COLETA 4: CONVERGÊNCIA TEMÁTICA
                # Por que: mede quanto negociador e causador falam dos
                #          mesmos temas (sincronização de comunicação)
                # Como:    usa funções do módulo analise para extrair
                #          temas e calcular convergência por APA
                # ═══════════════════════════════════════════════════════
                convergencia_dados = {}

                try:
                    col_texto_c = 'TRANSCRIÇÃO DO CAUSADOR'
                    col_texto_np = 'TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL'

                    if col_texto_c in df_quali_filt.columns and col_texto_np in df_quali_filt.columns:
                        convs = []
                        for _, row in df_quali_filt.iterrows():
                            txt_c = str(row[col_texto_c]).strip()
                            txt_np = str(row[col_texto_np]).strip()
                            if len(txt_c.split()) > 5 and len(txt_np.split()) > 5:
                                try:
                                    temas_c = analise.extrair_temas_unicos(txt_c, resolucao_tipo='desconhecida')
                                    temas_np = analise.extrair_temas_unicos(txt_np, resolucao_tipo='desconhecida')
                                    if temas_c and temas_np:
                                        conv = analise.calcular_convergencia_tematica(temas_c, temas_np)
                                        convs.append(conv['convergencia_geral'])
                                except Exception:
                                    pass

                        if convs:
                            convergencia_dados = {
                                "media": round(float(np.mean(convs)), 1),
                                "mediana": round(float(np.median(convs)), 1),
                                "desvio_padrao": round(float(np.std(convs)), 1),
                                "minimo": round(float(min(convs)), 1),
                                "maximo": round(float(max(convs)), 1),
                                "amplitude": round(float(max(convs) - min(convs)), 1),
                                "n_apas_analisadas": len(convs),
                            }
                except Exception:
                    pass

                # ═══════════════════════════════════════════════════════
                # COLETA 5: REGRESSÃO MULTIVARIADA
                # Por que: identifica quais fatores predizem redução
                #          de agressividade (controle estatístico)
                # Como:    usa funções do módulo analise para calcular
                #          deltas, ajustar modelo e extrair diagnósticos
                # ═══════════════════════════════════════════════════════
                regressao_dados = {}

                try:
                    col_agr_princ_ch = analise.achar_coluna(df_quali_filt, "Principal", "Agressividade", "Chegada")
                    col_agr_princ_en = analise.achar_coluna(df_quali_filt, "Principal", "Agressividade", "Encerramento")
                    col_agr_sec_ch = analise.achar_coluna(df_quali_filt, "Secundário", "Agressividade", "Chegada")
                    col_agr_sec_en = analise.achar_coluna(df_quali_filt, "Secundário", "Agressividade", "Encerramento")
                    col_agr_lider_ch = analise.achar_coluna(df_quali_filt, "Líder", "Agressividade", "Chegada")
                    col_agr_lider_en = analise.achar_coluna(df_quali_filt, "Líder", "Agressividade", "Encerramento")
                    col_recep_princ_ch = analise.achar_coluna(df_quali_filt, "Principal", "Receptividade", "Chegada")

                    colunas_reg = [col_agr_princ_ch, col_agr_princ_en, col_agr_sec_ch,
                                   col_agr_sec_en, col_agr_lider_ch, col_agr_lider_en]

                    if all(colunas_reg):
                        df_reg = analise.calcular_delta_agressividade_consenso(
                            df_quali_filt,
                            col_agr_princ_ch, col_agr_princ_en,
                            col_agr_sec_ch, col_agr_sec_en,
                            col_agr_lider_ch, col_agr_lider_en
                        )

                        df_modelo, erro = analise.preparar_dados_regressao(
                            df_reg,
                            col_tempo="Tempo de Negociação Real",
                            col_negociador="Negociador Principal do incidente crítico",
                            col_tipologia="Tipologia",
                            col_modalidade="Modalidade",
                            col_resolucao="Resolução",
                            col_recep_chegada=col_recep_princ_ch
                        )

                        if not erro:
                            resultado_mod, erro_mod = analise.ajustar_regressao_linear(df_modelo)

                            if not erro_mod:
                                diags = analise.diagnosticos_qualidade(resultado_mod)
                                df_coef = analise.extrair_coeficientes_significativos(resultado_mod)

                                regressao_dados = {
                                    "n": int(resultado_mod['n']),
                                    "r2": round(float(resultado_mod['r2']), 4),
                                    "r2_adj": round(float(resultado_mod['r2_adj']), 4),
                                    "p_f": round(float(resultado_mod['p_f']), 6),
                                    "modelo_significativo": bool(resultado_mod['p_f'] < 0.05),
                                    "coeficientes": df_coef.to_dict('records'),
                                    "diagnosticos": {
                                        "normalidade_p": round(float(diags['normalidade']['p_value']), 4),
                                        "normalidade_ok": bool(diags['normalidade']['p_value'] > 0.05),
                                        "normalidade_texto": diags['normalidade']['interpretacao'],
                                        "homocedasticidade_p": round(float(diags['homocedasticidade']['p_value']), 4),
                                        "homocedasticidade_ok": bool(diags['homocedasticidade']['p_value'] > 0.05),
                                        "homocedasticidade_texto": diags['homocedasticidade']['interpretacao'],
                                        "vif_max": round(float(diags['colinearidade']['vif_max']), 2),
                                        "vif_ok": bool(diags['colinearidade']['vif_max'] < 5),
                                        "vif_texto": diags['colinearidade']['interpretacao'],
                                    },
                                    "deltas_medios": {
                                        "principal": round(float(df_reg['delta_princ'].dropna().mean()), 2),
                                        "secundario": round(float(df_reg['delta_sec'].dropna().mean()), 2),
                                        "lider": round(float(df_reg['delta_lider'].dropna().mean()), 2),
                                        "consenso": round(float(df_reg['delta_consenso'].dropna().mean()), 2),
                                    }
                                }
                except Exception:
                    pass

                # ═══════════════════════════════════════════════════════
                # COLETA 6: PERFIL DE NEGOCIADORES
                # Por que: compara estilos (Escuta Ativa vs Persuasão),
                #          testes estatísticos e agrupamento K-means
                # Como:    usa analisar_perfil_negociadores() do módulo
                # ═══════════════════════════════════════════════════════
                perfil_dados = {}

                try:
                    from analise import analisar_perfil_negociadores

                    _df_tec_perfil = st.session_state.get("df_tec", pd.DataFrame())
                    if _df_tec_perfil.empty and not df_tec.empty:
                        _df_tec_perfil = df_tec.copy()

                    if not _df_tec_perfil.empty:
                        res_perfil = analisar_perfil_negociadores(_df_tec_perfil)

                        df_res = res_perfil['df_resultado']
                        _anova = res_perfil['anova']
                        _chi2 = res_perfil['chi2']

                        perfil_por_negociador = []
                        for _, row in df_res.iterrows():
                            entry = {
                                "negociador": str(row.get('Negociador', 'N/D')),
                                "score_tendencia": round(float(row.get('Score Tendência', 0)), 1),
                                "cluster": int(row.get('Cluster', 0)),
                            }
                            if 'Perfil_Cluster' in row.index:
                                entry["perfil_cluster"] = str(row['Perfil_Cluster'])
                            if 'Efetividade Escuta' in row.index:
                                entry["efetividade_escuta"] = round(float(row['Efetividade Escuta']), 1)
                            if 'Efetividade Persuasão' in row.index:
                                entry["efetividade_persuasao"] = round(float(row['Efetividade Persuasão']), 1)
                            perfil_por_negociador.append(entry)

                        perfil_dados = {
                            "negociadores": perfil_por_negociador,
                            "n_clusters": 2,
                        }

                        if _anova:
                            perfil_dados["anova"] = {
                                "f_statistic": _anova.get('f_statistic', 'N/D'),
                                "p_value": _anova.get('p_value', 'N/D'),
                                "significativo": _anova.get('significativo', False),
                                "interpretacao": _anova.get('interpretacao', ''),
                            }

                        if _chi2:
                            perfil_dados["chi2"] = {
                                "chi2_statistic": _chi2.get('chi2_statistic', 'N/D'),
                                "p_value": _chi2.get('p_value', 'N/D'),
                                "df": _chi2.get('df', 'N/D'),
                                "significativo": _chi2.get('significativo', False),
                                "interpretacao": _chi2.get('interpretacao', ''),
                            }
                except Exception:
                    pass

                # ═══════════════════════════════════════════════════════
                # MONTAR PAYLOAD E CHAMAR IA
                # ═══════════════════════════════════════════════════════
                payload_ia = ia_estatistica.coletar_payload_serie_historica(
                    n_ocorrencias=len(df_quali_filt),
                    metadados=metadados,
                    ranking_tecnicas=ranking_tecnicas,
                    efetividade=efetividade,
                    convergencia=convergencia_dados,
                    regressao=regressao_dados,
                    perfil_negociadores=perfil_dados,
                )

                relatorio = ia_estatistica.gerar_relatorio_com_ia(payload_ia)

                # ═══════════════════════════════════════════════════════
                # RENDERIZAR RESULTADO
                # ═══════════════════════════════════════════════════════
                if "erro" in relatorio:
                    st.error(f"Erro na geração do relatório: {relatorio['erro']}")
                    with st.expander("🔍 Ver dados enviados para a IA"):
                        st.json(payload_ia)
                else:
                    st.success("✔ Relatório gerado com sucesso!")

                    # ── 6 SEÇÕES DA IA ────────────────────────────
                    st.markdown(relatorio.get("panorama_amostra", "N/D"))
                    st.markdown("---")

                    st.markdown(relatorio.get("ranking_efetividade", "N/D"))
                    st.markdown("---")

                    st.markdown(relatorio.get("convergencia_tematica", "N/D"))
                    st.markdown("---")

                    st.markdown(relatorio.get("analise_multivariada", "N/D"))
                    st.markdown("---")

                    st.markdown(relatorio.get("perfil_negociadores", "N/D"))
                    st.markdown("---")

                    st.markdown(relatorio.get("sintese_limitacoes", "N/D"))

                    # ── EXPANDER COM PAYLOAD (DEBUG) ──────────────
                    with st.expander("🔍 Ver dados enviados para a IA"):
                        st.json(payload_ia)

                    # ── EXPORTAR PDF ──────────────────────────────
                    st.markdown("---")
                    st.markdown("### 📥 Exportar Relatório em PDF")

                    try:
                        from fpdf import FPDF
                        import unicodedata as _ud

                        pdf_hist = FPDF()
                        pdf_hist.add_page()

                        # Cabeçalho
                        pdf_hist.set_fill_color(249, 115, 22)
                        pdf_hist.rect(0, 0, 210, 35, 'F')
                        pdf_hist.set_font("Arial", "B", 14)
                        pdf_hist.set_text_color(255, 255, 255)
                        pdf_hist.cell(0, 12, "ANALISE ESTATISTICA - SERIE HISTORICA", ln=True, align="C")
                        pdf_hist.set_font("Arial", "I", 10)
                        pdf_hist.cell(0, 8, "Relatório Assistido por Inteligencia Artificial para Apoio Decisorio", ln=True, align="C")

                        # Conteúdo — cada seção vira um bloco no PDF
                        secoes_pdf = [
                            ("Panorama da Amostra", "panorama_amostra"),
                            ("Ranking e Efetividade", "ranking_efetividade"),
                            ("Convergencia Tematica", "convergencia_tematica"),
                            ("Analise Multivariada", "analise_multivariada"),
                            ("Perfil dos Negociadores", "perfil_negociadores"),
                            ("Sintese Final e Limitacoes", "sintese_limitacoes"),
                        ]

                        pdf_hist.ln(10)
                        pdf_hist.set_text_color(0, 0, 0)

                        for titulo_secao, chave_secao in secoes_pdf:
                            pdf_hist.set_font("Arial", "B", 12)
                            pdf_hist.cell(0, 8, titulo_secao, ln=True)
                            pdf_hist.set_font("Arial", "", 9)

                            texto_bruto = relatorio.get(chave_secao, "N/D")
                            # Remove markdown e normaliza para ASCII (compatível com FPDF)
                            texto_limpo = texto_bruto.replace("###", "").replace("**", "").replace("- ", "  * ")
                            texto_limpo = _ud.normalize('NFKD', texto_limpo).encode('ASCII', 'ignore').decode('ASCII')
                            pdf_hist.multi_cell(0, 5, txt=texto_limpo)
                            pdf_hist.ln(3)

                        pdf_saida = pdf_hist.output(dest="S")
                        if isinstance(pdf_saida, str):
                            pdf_bytes = pdf_saida.encode('latin-1', errors='replace')
                        else:
                            pdf_bytes = bytes(pdf_saida)

                        st.download_button(
                            label="📥 Baixar Relatório (PDF)",
                            data=pdf_bytes,
                            file_name="Relatorio_Serie_Historica_GATE.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.warning(f"⚠️ Erro ao gerar PDF: {str(e)[:100]}")

            except ImportError as e:
                st.error(f"⚠️ Módulo não encontrado: {str(e)}")
            except Exception as e:
                st.error(f"🚨 Erro na geração do relatório: {str(e)[:200]}")

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='margin-top:20px; margin-bottom:100px; padding:15px; background-color:#111; border-radius:8px;'>
    <p style="color:#bbb; font-size:13px; line-height:1.7; text-align:left;">

    <span style="color:#ffae42; font-weight:700; font-size:14px; letter-spacing:1px;">
    DELTA-NEGOCIAÇÃO — GATE/PMESP
    </span>


    "O maior inimigo do conhecimento não é a ignorância, mas a ilusão do conhecimento."
    — Stephen Hawking.


    “Sem dados, você é apenas mais uma pessoa com opinião.”
    — W. Edwards Deming.


    Empenhados no desenvolvimento de treinamentos e na avaliação dos Negociadores, alicerçados no pensamento técnico-científico e no valor humano, guiados por dados.

    <br>

    <span style="color:#ffae42; font-weight:600;">
    NEGOCIAÇÃO!
    </span>

    <br>

    <span style="color:#777; font-size:11px;">
    Dados confidenciais, de uso exclusivo da equipe de Negociação do Grupo de Ações Táticas Especiais.
    </span>

    </p>

    <hr style="border:none; height:1px; background:linear-gradient(to right, transparent, rgba(255,174,66,0.6), transparent); margin-top:18px; margin-bottom:12px;">

    <div style="text-align:center; font-size:11px; color:#666; line-height:1.5;">
    © 2026 AXIOM - Strategic Intelligence Ltda — Todos os direitos reservados.<br>
    Este sistema é protegido por direitos autorais e legislação aplicável. Reprodução, distribuição, engenharia reversa, modificação ou utilização não autorizada são proibidas.
    </div>
    """, unsafe_allow_html=True)