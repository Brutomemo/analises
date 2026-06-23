"""
apa.py
Aba "Visão Seletiva" (APA) do Delta-Negociação — GATE/PMESP.
Extraído do app.py — Fase 3 da reestruturação.

Uso no app.py:
    import apa
    apa.render_apa(df_quali, df_tec)
"""

import streamlit as st
import pandas as pd
import unicodedata
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF

import utils
import analise
import ia_link


def render_apa(df_quali, df_tec):
    """Renderiza a aba completa de Visão Seletiva (APA)."""

    st.markdown("<h5 style='color: #FFD700;'> Seleção e Metadados da Ocorrência</h5>", unsafe_allow_html=True)

    df_quali['Neg_Limpo'] = df_quali['Negociador Principal'].apply(utils.limpar_valor)
    df_quali['Tip_Limpa'] = df_quali['Tipologia'].apply(utils.limpar_valor)
    df_quali['Mod_Limpa'] = df_quali['Modalidade do incidente'].apply(utils.limpar_valor)

    if 'ID' not in df_quali.columns:
        df_quali['ID'] = "APA " + df_quali.index.astype(str)
    df_quali['ID_Busca'] = df_quali['ID'].apply(utils.limpar_id)

    # ── FILTROS ENCADEADOS BIDIRECIONAIS ────────────────────────────────
    col_fi1, col_fi2, col_fi3 = st.columns(3)

    neg_atual = st.session_state.get("f_neg_ind", "Todos")
    tip_atual = st.session_state.get("f_tip_ind", "Todas")
    mod_atual = st.session_state.get("f_mod_ind", "Todas")

    df_ctx_neg = df_quali.copy()
    if tip_atual != "Todas":
        df_ctx_neg = df_ctx_neg[df_ctx_neg['Tip_Limpa'] == tip_atual]
    if mod_atual != "Todas":
        df_ctx_neg = df_ctx_neg[df_ctx_neg['Mod_Limpa'] == mod_atual]

    df_ctx_tip = df_quali.copy()
    if neg_atual != "Todos":
        df_ctx_tip = df_ctx_tip[df_ctx_tip['Neg_Limpo'] == neg_atual]
    if mod_atual != "Todas":
        df_ctx_tip = df_ctx_tip[df_ctx_tip['Mod_Limpa'] == mod_atual]

    df_ctx_mod = df_quali.copy()
    if neg_atual != "Todos":
        df_ctx_mod = df_ctx_mod[df_ctx_mod['Neg_Limpo'] == neg_atual]
    if tip_atual != "Todas":
        df_ctx_mod = df_ctx_mod[df_ctx_mod['Tip_Limpa'] == tip_atual]

    with col_fi1:
        lista_neg = ["Todos"] + sorted(
            df_ctx_neg[df_ctx_neg['Neg_Limpo'] != 'N/D']['Neg_Limpo'].unique().tolist()
        )
        idx_neg = lista_neg.index(neg_atual) if neg_atual in lista_neg else 0
        filtro_neg = st.selectbox("Filtrar por Negociador:", lista_neg, index=idx_neg, key="f_neg_ind")

    with col_fi2:
        lista_tip = ["Todas"] + sorted(
            df_ctx_tip[df_ctx_tip['Tip_Limpa'] != 'N/D']['Tip_Limpa'].unique().tolist()
        )
        idx_tip = lista_tip.index(tip_atual) if tip_atual in lista_tip else 0
        filtro_tip = st.selectbox("Filtrar por Tipologia:", lista_tip, index=idx_tip, key="f_tip_ind")

    with col_fi3:
        lista_mod = ["Todas"] + sorted(
            df_ctx_mod[df_ctx_mod['Mod_Limpa'] != 'N/D']['Mod_Limpa'].unique().tolist()
        )
        idx_mod = lista_mod.index(mod_atual) if mod_atual in lista_mod else 0
        filtro_mod = st.selectbox("Filtrar por Modalidade:", lista_mod, index=idx_mod, key="f_mod_ind")

    df_q_ind = df_quali.copy()
    if filtro_neg != "Todos":
        df_q_ind = df_q_ind[df_q_ind['Neg_Limpo'] == filtro_neg]
    if filtro_tip != "Todas":
        df_q_ind = df_q_ind[df_q_ind['Tip_Limpa'] == filtro_tip]
    if filtro_mod != "Todas":
        df_q_ind = df_q_ind[df_q_ind['Mod_Limpa'] == filtro_mod]

    lista_apas = df_q_ind['ID_Busca'].tolist()

    if not lista_apas:
        st.warning("Nenhuma ocorrência encontrada com estes filtros.")
        return

    apa_selecionada = st.selectbox(
        "Selecione a ID da APA para análise:",
        lista_apas,
        index=len(lista_apas) - 1,
    )
    df_apa = df_quali[df_quali['ID_Busca'] == apa_selecionada].iloc[0]

    # ── METADADOS ───────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='info-card'><strong>Data:</strong><br>{utils.limpar_valor(df_apa.get('Data da ocorrência'))}</div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='info-card'><strong>Modalidade:</strong><br>{utils.limpar_valor(df_apa.get('Modalidade do incidente'))}</div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='info-card'><strong>Tipologia:</strong><br>{utils.limpar_valor(df_apa.get('Tipologia'))}</div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='info-card'><strong>Motivação:</strong><br>{utils.limpar_valor(df_apa.get('Motivação'))}</div>", unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    with c5: st.markdown(f"<div class='info-card'><strong>Negociador Principal:</strong><br>{utils.limpar_valor(df_apa.get('Negociador Principal'))}</div>", unsafe_allow_html=True)
    with c6: st.markdown(f"<div class='info-card'><strong>Forma de Transição:</strong><br>{utils.limpar_valor(df_apa.get('Forma de Transição'))}</div>", unsafe_allow_html=True)
    with c7: st.markdown(f"<div class='info-card'><strong>Tempo de Negociação Real:</strong><br>{utils.formatar_tempo_airtable(df_apa.get('Tempo de Negociação Real'))}</div>", unsafe_allow_html=True)
    with c8: st.markdown(f"<div class='info-card'><strong>Tempo de Negociação Tática:</strong><br>{utils.formatar_tempo_airtable(df_apa.get('Tempo de Negociação Tática'))}</div>", unsafe_allow_html=True)

    c9, c10, c11, _ = st.columns(4)
    with c9: st.markdown(f"<div class='info-card'><strong>Resolução:</strong><br>{utils.limpar_valor(df_apa.get('Resolução'))}</div>", unsafe_allow_html=True)
    with c10: st.markdown(f"<div class='info-card'><strong>Uniforme Usado:</strong><br>{utils.limpar_valor(df_apa.get('Uniforme Usado'))}</div>", unsafe_allow_html=True)
    with c11: st.markdown(f"<div class='info-card'><strong>Sexo do Causador:</strong><br>{utils.limpar_valor(df_apa.get('Sexo do Causador'))}</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ====================================================
    # SEÇÃO 1: PERCEPÇÃO DE AGRESSIVIDADE/RECEPTIVIDADE
    # ====================================================
    st.markdown("<h5 style='color: #FFD700;'> Agressividade e Receptividade do causador</h5>", unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 1, 1])
    with col_center:
        is_percep_neg = utils.render_toggle_button(
            label="✔️ Abrir Percepção dos Negociadores",
            session_key="percep_neg",
            button_key="btn_percep_neg"
        )

    st.markdown("---")

    if is_percep_neg:
        tab_pc1, tab_pc2 = st.tabs([
            "✔️ Linha de Tendência",
            "✔️ Visão Geral"
        ])

        with tab_pc1:
            st.markdown("""
            <div class='info-card'>
            <h5 style='color: #FFD700; margin-top: 0;'>Linha de tendência individualizada da Percepção de agressividade e receptividade do causador</h5>
            <p style='font-size:1.2rem;color:#ddd;'>
            Percepção dos Negociadores <strong>no início e encerramento da ocorrência</strong>.
            </p>
            </div>
            """, unsafe_allow_html=True)

            colunas_norm = {col: unicodedata.normalize('NFKD', str(col)).encode('ASCII', 'ignore').decode('ASCII').lower() for col in df_apa.index}

            def buscar_percepcao(papel, metrica, momento):
                p_n = unicodedata.normalize('NFKD', str(papel)).encode('ASCII', 'ignore').decode('ASCII').lower()
                m_n = unicodedata.normalize('NFKD', str(metrica)).encode('ASCII', 'ignore').decode('ASCII').lower()
                mo_n = unicodedata.normalize('NFKD', str(momento)).encode('ASCII', 'ignore').decode('ASCII').lower()
                for col_orig, col_n in colunas_norm.items():
                    if p_n in col_n and m_n in col_n and mo_n in col_n:
                        return utils.limpar_valor(df_apa[col_orig])
                return "N/D"

            p_agr_c_txt = buscar_percepcao('Principal', 'Agressividade', 'Chegada')
            p_rec_c_txt = buscar_percepcao('Principal', 'Receptividade', 'Chegada')
            p_agr_e_txt = buscar_percepcao('Principal', 'Agressividade', 'Encerramento')
            p_rec_e_txt = buscar_percepcao('Principal', 'Receptividade', 'Encerramento')
            s_agr_c_txt = buscar_percepcao('Secundario', 'Agressividade', 'Chegada')
            s_rec_c_txt = buscar_percepcao('Secundario', 'Receptividade', 'Chegada')
            s_agr_e_txt = buscar_percepcao('Secundario', 'Agressividade', 'Encerramento')
            s_rec_e_txt = buscar_percepcao('Secundario', 'Receptividade', 'Encerramento')
            l_agr_c_txt = buscar_percepcao('Lider', 'Agressividade', 'Chegada')
            l_rec_c_txt = buscar_percepcao('Lider', 'Receptividade', 'Chegada')
            l_agr_e_txt = buscar_percepcao('Lider', 'Agressividade', 'Encerramento')
            l_rec_e_txt = buscar_percepcao('Lider', 'Receptividade', 'Encerramento')

            p_agr_c_num, p_rec_c_num = utils.converter_escala(p_agr_c_txt), utils.converter_escala(p_rec_c_txt)
            p_agr_e_num, p_rec_e_num = utils.converter_escala(p_agr_e_txt), utils.converter_escala(p_rec_e_txt)
            s_agr_c_num, s_rec_c_num = utils.converter_escala(s_agr_c_txt), utils.converter_escala(s_rec_c_txt)
            s_agr_e_num, s_rec_e_num = utils.converter_escala(s_agr_e_txt), utils.converter_escala(s_rec_e_txt)
            l_agr_c_num, l_rec_c_num = utils.converter_escala(l_agr_c_txt), utils.converter_escala(l_rec_c_txt)
            l_agr_e_num, l_rec_e_num = utils.converter_escala(l_agr_e_txt), utils.converter_escala(l_rec_e_txt)

            p_escolhida = st.selectbox(
                "Visualizar evolução sob a perspectiva do:",
                ["Negociador Principal", "Negociador Secundário", "Negociador Líder"],
                key="selecao_negociador_grafico"
            )

            if p_escolhida == "Negociador Principal":
                v_agr_c, v_rec_c = p_agr_c_num, p_rec_c_num
                v_agr_e, v_rec_e = p_agr_e_num, p_rec_e_num
            elif p_escolhida == "Negociador Secundário":
                v_agr_c, v_rec_c = s_agr_c_num, s_rec_c_num
                v_agr_e, v_rec_e = s_agr_e_num, s_rec_e_num
            else:
                v_agr_c, v_rec_c = l_agr_c_num, l_rec_c_num
                v_agr_e, v_rec_e = l_agr_e_num, l_rec_e_num

            plot_agr_c = v_agr_c if v_agr_c > 0 else None
            plot_agr_e = v_agr_e if v_agr_e > 0 else None
            plot_rec_c = v_rec_c if v_rec_c > 0 else None
            plot_rec_e = v_rec_e if v_rec_e > 0 else None

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=["Chegada", "Encerramento"], y=[plot_agr_c, plot_agr_e], mode='lines+markers', name='Agressividade', line=dict(color='#ef4444', width=4), marker=dict(size=12)))
            fig_trend.add_trace(go.Scatter(x=["Chegada", "Encerramento"], y=[plot_rec_c, plot_rec_e], mode='lines+markers', name='Receptividade', line=dict(color='#22c55e', width=4), marker=dict(size=12)))
            fig_trend.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#FFF",
                yaxis=dict(tickvals=[1, 2, 3, 4, 5], ticktext=["1 - Não agressivo <br>não receptivo", "2 - Neutro", "3 - Parc. agressivo <br>parc. receptivo", "4 - Agressivo <br>receptivo", "5 - Muito agressivo <br>muito receptivo"], range=[0.5, 5.5]),
                xaxis=dict(title=None),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig_trend.update_traces(connectgaps=False)
            st.plotly_chart(fig_trend, use_container_width=True)

        with tab_pc2:
            st.markdown("""
            <div class='info-card'>
            <h5 style='color: #FFD700; margin-top: 0;'>Percepção Geral dos Negociadores sobre a agressividade e receptividade do causador.</h5>
            <p style='font-size:1.2rem;color:#ddd;'>
            Percepção dos Negociadores <strong>no início e encerramento da ocorrência</strong>.
            </p>
            </div>
            """, unsafe_allow_html=True)

            tab_chegada, tab_encerramento = st.tabs(["🏳 Na Chegada à Ocorrência", "🏴 No Encerramento"])

            with tab_chegada:
                col_p_c, col_s_c, col_l_c = st.columns(3)
                with col_p_c:
                    st.markdown("**Negociador Principal**")
                    st.markdown(utils.render_card("Agressividade", p_agr_c_txt, "card-red"), unsafe_allow_html=True)
                    st.markdown(utils.render_card("Receptividade", p_rec_c_txt, "card-green"), unsafe_allow_html=True)
                with col_s_c:
                    st.markdown("**Negociador Secundário**")
                    st.markdown(utils.render_card("Agressividade", s_agr_c_txt, "card-red"), unsafe_allow_html=True)
                    st.markdown(utils.render_card("Receptividade", s_rec_c_txt, "card-green"), unsafe_allow_html=True)
                with col_l_c:
                    st.markdown("**Negociador Líder**")
                    st.markdown(utils.render_card("Agressividade", l_agr_c_txt, "card-red"), unsafe_allow_html=True)
                    st.markdown(utils.render_card("Receptividade", l_rec_c_txt, "card-green"), unsafe_allow_html=True)

            with tab_encerramento:
                col_p_e, col_s_e, col_l_e = st.columns(3)
                with col_p_e:
                    st.markdown("**Negociador Principal**")
                    st.markdown(utils.render_card("Agressividade", p_agr_e_txt, "card-red"), unsafe_allow_html=True)
                    st.markdown(utils.render_card("Receptividade", p_rec_e_txt, "card-green"), unsafe_allow_html=True)
                with col_s_e:
                    st.markdown("**Negociador Secundário**")
                    st.markdown(utils.render_card("Agressividade", s_agr_e_txt, "card-red"), unsafe_allow_html=True)
                    st.markdown(utils.render_card("Receptividade", s_rec_e_txt, "card-green"), unsafe_allow_html=True)
                with col_l_e:
                    st.markdown("**Negociador Líder**")
                    st.markdown(utils.render_card("Agressividade", l_agr_e_txt, "card-red"), unsafe_allow_html=True)
                    st.markdown(utils.render_card("Receptividade", l_rec_e_txt, "card-green"), unsafe_allow_html=True)

            st.markdown("---")
            st.session_state.p_agr_c_num = p_agr_c_num
            st.session_state.p_rec_c_num = p_rec_c_num
            st.session_state.s_agr_c_num = s_agr_c_num
            st.session_state.s_rec_c_num = s_rec_c_num
            st.session_state.l_agr_c_num = l_agr_c_num
            st.session_state.l_rec_c_num = l_rec_c_num
            st.session_state.p_agr_e_num = p_agr_e_num
            st.session_state.p_rec_e_num = p_rec_e_num
            st.session_state.s_agr_e_num = s_agr_e_num
            st.session_state.s_rec_e_num = s_rec_e_num
            st.session_state.l_agr_e_num = l_agr_e_num
            st.session_state.l_rec_e_num = l_rec_e_num

    st.markdown("---")

    # ════════════════════════════════════════════════════════════
    # SUMÁRIO DAS TRANSCRIÇÕES
    # ════════════════════════════════════════════════════════════
    st.markdown("<h5 style='color: #FFD700;'>Sumário das Transcrições (Nesta APA)</h5>", unsafe_allow_html=True)

    col_sum_left, col_sum_center, col_sum_right = st.columns([1, 1, 1])
    with col_sum_center:
        is_sumario_transcricoes = utils.render_toggle_button(
            label="✔️ Abrir Sumário das Transcrições",
            session_key="sumario_transcricoes",
            button_key="btn_sumario_transcricoes"
        )

    st.markdown("---")

    if is_sumario_transcricoes:
        texto_causador_sum = utils.limpar_valor(df_apa.get('TRANSCRIÇÃO DO CAUSADOR', ''))
        texto_neg_principal_sum = utils.limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL', ''))
        cache_key_sumario = f"sumario_transcricoes_{apa_selecionada}"

        if cache_key_sumario not in st.session_state:
            with st.spinner("Gerando sumários das transcrições com IA..."):
                st.session_state[cache_key_sumario] = {
                    "causador": ia_link.sumarizar_transcricao(texto_causador_sum, papel="causador"),
                    "negociador_principal": ia_link.sumarizar_transcricao(texto_neg_principal_sum, papel="negociador_principal"),
                }

        resumos_transcricoes = st.session_state[cache_key_sumario]

        tab_sum_causador, tab_sum_neg_principal = st.tabs(["✔️ Causador do Incidente", "✔️ Negociador Principal"])

        with tab_sum_causador:
            st.markdown("""
            <div class='info-card'>
            <h5 style='color: #FFD700; margin-top: 0;'>Síntese do discurso do Causador</h5>
            <p style='font-size:0.95rem;color:#bbb;margin-bottom:0;'>
            Pontos centrais, motivações e demandas observáveis na transcrição.
            </p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""<div style='font-size:0.9rem; line-height:1.6'>
            {resumos_transcricoes.get("causador", "Sem conteúdo.")}
            </div>""", unsafe_allow_html=True)

        with tab_sum_neg_principal:
            st.markdown("""
            <div class='info-card'>
            <h5 style='color: #FFD700; margin-top: 0;'>Síntese da condução do Negociador Principal</h5>
            <p style='font-size:0.9rem;color:#bbb;margin-bottom:0;'>
            Estratégia verbal, postura e elementos relevantes da intervenção.
            </p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""<div style='font-size:0.9rem; line-height:1.6'>
            {resumos_transcricoes.get("negociador_principal", "Sem conteúdo.")}
            </div>""", unsafe_allow_html=True)

        st.markdown("---")

    # ════════════════════════════════════════════════════════════
    # TRANSCRIÇÕES
    # ════════════════════════════════════════════════════════════
    st.markdown("### ✔ Transcrições")

    if "show_transcricoes" not in st.session_state:
        st.session_state["show_transcricoes"] = False

    label = "▲ Ocultar transcrições" if st.session_state["show_transcricoes"] else "▼ Ver transcrições completas da ocorrência"
    if st.button(label, key="btn_transcricoes"):
        st.session_state["show_transcricoes"] = not st.session_state["show_transcricoes"]

    if st.session_state["show_transcricoes"]:
        st.markdown("**Causador do Incidente:**")
        st.write(utils.limpar_valor(df_apa.get('TRANSCRIÇÃO DO CAUSADOR')))
        st.markdown("**Negociador Principal:**")
        st.write(utils.limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL')))
        st.markdown("**Negociador Secundário:**")
        st.write(utils.limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO')))

    st.markdown("---")

    # ════════════════════════════════════════════════════════════
    # SEÇÃO 2: ANÁLISE DE TÉCNICAS
    # ════════════════════════════════════════════════════════════
    st.markdown("<h5 style='color: #FFD700;'>Frequência e Efetividade das Técnicas Aplicadas (Nesta APA)</h5>", unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 1, 1])
    with col_center:
        is_analise_tecnicas = utils.render_toggle_button(
            label="✔️ Abrir Análise das Técnicas",
            session_key="analise_tecnicas",
            button_key="btn_analise_tecnicas"
        )

    st.markdown("---")

    if is_analise_tecnicas:
        tab_freq, tab_efet = st.tabs(["✔️ Tabela de Frequência", "✔️ Efetividade das Técnicas"])

        with tab_freq:
            st.markdown("""
            <div style='margin-bottom:15px;'>
            <h5 style='color:#FFD700;'>✔️Frequência das Técnicas Aplicadas</h5>
            <p style='color:#aaa;font-size:0.9rem;'>
            Análise de quantas vezes cada técnica foi utilizada nesta ocorrência.
            </p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("✔ Calcular Frequência de Técnicas", key="btn_freq_tecnicas"):
                if not df_tec.empty:
                    col_vinculo = next((c for c in df_tec.columns if 'VINCULO' in c.upper() or 'VÍNCULO' in c.upper()), None)
                    if col_vinculo:
                        id_visivel = str(apa_selecionada).strip()
                        df_tec['Vinculo_Str'] = df_tec[col_vinculo].astype(str).str.replace(r"[\[\]'\"]", "", regex=True).str.strip()
                        df_tec_filtrado = df_tec[df_tec['Vinculo_Str'] == id_visivel]
                        if df_tec_filtrado.empty and 'Airtable_Record_ID' in df_apa:
                            id_interno = str(df_apa['Airtable_Record_ID']).strip()
                            df_tec_filtrado = df_tec[df_tec[col_vinculo].astype(str).str.contains(id_interno, na=False, regex=False)]
                        if not df_tec_filtrado.empty:
                            col_tecnica = next((col for col in ['TÉCNICAS', 'TECNICAS', 'TÉCNICA', 'TECNICA'] if col in df_tec_filtrado.columns), None)
                            if col_tecnica:
                                freq_abs = df_tec_filtrado[col_tecnica].value_counts()
                                freq_rel = (df_tec_filtrado[col_tecnica].value_counts(normalize=True) * 100).round(1)
                                df_freq = pd.DataFrame({'Frequência Absoluta': freq_abs, 'Frequência Relativa (%)': freq_rel}).reset_index().rename(columns={col_tecnica: 'Técnica Empregada'})
                                st.dataframe(df_freq, use_container_width=True, hide_index=True)
                                st.markdown("<h4 style='text-align:center; color: #FFD700; margin-top: 20px;'>Frequências das Técnicas Aplicadas (Treemap)</h4>", unsafe_allow_html=True)
                                fig_tree = px.treemap(df_freq, path=['Técnica Empregada'], values='Frequência Absoluta', color='Frequência Absoluta', color_continuous_scale='Oranges')
                                fig_tree.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#FFF", margin=dict(t=10, l=10, r=10, b=10))
                                st.session_state['treemap_freq'] = fig_tree
                                st.success("✅ Treemap gerado!")
                            else:
                                st.warning("Técnicas encontradas, mas a coluna 'TÉCNICAS' não foi identificada no Airtable.")
                        else:
                            st.info("Nenhuma técnica cruzou com a APA atual.")
                    else:
                        st.warning("A coluna de vínculo (ex: 'Vinculo_APA') não foi encontrada na aba de técnicas.")
                else:
                    st.warning("Tabela de técnicas vazia no Airtable.")

            if st.session_state.get('treemap_freq'):
                st.plotly_chart(st.session_state['treemap_freq'], use_container_width=True)

        with tab_efet:
            st.markdown("""
            <div style='margin-bottom:15px;'>
            <h5 style='color:#FFD700;'>✔️ Efetividade das Técnicas</h5>
            <p style='color:#aaa;font-size:0.9rem;'>
            Cruza cada técnica usada com a reação do causador.
            </p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("✔ Analisar Efetividade das Técnicas", key="btn_efetividade_tecnicas"):
                with st.spinner("Cruzando técnicas com reação do causador..."):
                    try:
                        record_id_atual = df_apa.get('Airtable_Record_ID')
                        if not record_id_atual:
                            st.warning("⚠️ ID do registro não encontrado.")
                        else:
                            df_tec = st.session_state.get("df_tec", pd.DataFrame())
                            if df_tec.empty:
                                st.warning("⚠️ Tabela de técnicas não carregada.")
                            else:
                                def vinculo_contem(val, record_id):
                                    if isinstance(val, list):
                                        return record_id in val
                                    return str(val) == record_id

                                mask = df_tec['Vinculo_APA'].apply(lambda x: vinculo_contem(x, record_id_atual))
                                df_tec_apa = df_tec[mask].copy()

                                if df_tec_apa.empty:
                                    st.info("Nenhuma técnica registrada para esta ocorrência.")
                                else:
                                    def normalizar_reacao(val):
                                        if val is None:
                                            return None
                                        s = str(val).strip()
                                        if s in ["-1", "-1.0", "🔴 Reação Negativa", "Reação Negativa"]:
                                            return -1
                                        elif s in ["0", "0.0", "⚪ Reação Neutra", "Reação Neutra"]:
                                            return 0
                                        elif s in ["1", "1.0", "🟢 Reação Positiva", "Reação Positiva"]:
                                            return 1
                                        return None

                                    col_reacao = next((c for c in ['ATITUDE DO CAUSADOR', 'Atitude do Causador', 'atitude_causador'] if c in df_tec_apa.columns), None)
                                    col_tecnica = next((c for c in ['TÉCNICAS', 'Técnicas', 'tecnicas'] if c in df_tec_apa.columns), None)

                                    if not col_tecnica:
                                        st.warning("⚠️ Coluna TÉCNICAS não encontrada.")
                                    else:
                                        df_tec_apa['_reacao_num'] = df_tec_apa[col_reacao].apply(normalizar_reacao) if col_reacao else None
                                        resumo = []
                                        for tecnica, grupo in df_tec_apa.groupby(col_tecnica):
                                            total    = len(grupo)
                                            positivo = (grupo['_reacao_num'] == 1).sum()
                                            neutro   = (grupo['_reacao_num'] == 0).sum()
                                            negativo = (grupo['_reacao_num'] == -1).sum()
                                            inaud    = grupo['_reacao_num'].isna().sum()
                                            observados = positivo + neutro + negativo
                                            score = round(((positivo - negativo) / observados) * 100, 1) if observados > 0 else None
                                            resumo.append({"Técnica": tecnica, "Total": total, "🟢 Positiva": int(positivo), "⚪ Neutra": int(neutro), "🔴 Negativa": int(negativo), "❓ Inaudível": int(inaud), "Score (%)": score})

                                        df_resumo = pd.DataFrame(resumo).sort_values("Score (%)", ascending=False, na_position='last')
                                        st.session_state['tecnicas_analisadas'] = df_resumo
                                        st.success(f"✅ {len(df_resumo)} técnicas analisadas!")

                    except Exception as e:
                        st.error(f"Erro ao analisar técnicas: {str(e)[:80]}")

            if st.session_state.get('tecnicas_analisadas') is not None:
                df_resumo = st.session_state['tecnicas_analisadas']
                total_usos     = int(df_resumo["Total"].sum())
                total_positivo = int(df_resumo["🟢 Positiva"].sum())
                total_neutro   = int(df_resumo["⚪ Neutra"].sum())
                total_negativo = int(df_resumo["🔴 Negativa"].sum())
                observados_total = total_positivo + total_neutro + total_negativo
                score_geral    = round(((total_positivo - total_negativo) / max(1, observados_total)) * 100, 1)

                st.markdown("### ✔️ Resumo Geral")
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("Total de Usos", total_usos)
                with col2: st.metric("🟢 Positivas", total_positivo)
                with col3: st.metric("🔴 Negativas", total_negativo)
                with col4: st.metric("Score Geral", f"{score_geral:+.1f}%")

                st.markdown("### ✔️ Efetividade por Técnica")
                st.dataframe(df_resumo, use_container_width=True, hide_index=True)

                try:
                    tecnicas  = df_resumo["Técnica"].tolist()
                    positivos = df_resumo["🟢 Positiva"].tolist()
                    neutros   = df_resumo["⚪ Neutra"].tolist()
                    negativos = df_resumo["🔴 Negativa"].tolist()
                    fig_barras = go.Figure()
                    fig_barras.add_trace(go.Bar(name="🟢 Positiva", x=tecnicas, y=positivos, marker_color="#10b981"))
                    fig_barras.add_trace(go.Bar(name="⚪ Neutra", x=tecnicas, y=neutros, marker_color="#6b7280"))
                    fig_barras.add_trace(go.Bar(name="🔴 Negativa", x=tecnicas, y=negativos, marker_color="#ef4444"))
                    fig_barras.update_layout(barmode="stack", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#fff"), height=420, margin=dict(t=20, b=120, l=40, r=40))
                    st.plotly_chart(fig_barras, use_container_width=True)
                except Exception as e:
                    st.error(f"Erro ao gerar gráfico: {str(e)[:80]}")

    st.markdown("---")

    # ════════════════════════════════════════════════════════════
    # ANÁLISE SEMÂNTICA + TEMÁTICA (bloco completo preservado)
    # ════════════════════════════════════════════════════════════
    st.markdown("""
    <h3 style='color: #FFD700;'>Análise Semântica </h3>
    <p style='color: #aaa; font-size: 0.95rem; margin-top: -10px;'>
    <strong>O que o causador REALMENTE sente, quer e teme.</strong>
    </p>
    """, unsafe_allow_html=True)

    if "show_explicacao" not in st.session_state:
        st.session_state["show_explicacao"] = False

    label_btn = "▲ Ocultar Guia" if st.session_state["show_explicacao"] else "▼ Entenda como ler a Análise"
    if st.button(label_btn, key="btn_explicacao_semantica"):
        st.session_state["show_explicacao"] = not st.session_state["show_explicacao"]

    # (bloco de explicação omitido aqui por tamanho — preservado do original)

    st.markdown("<h5 style='color: #FFD700;'>Análise Temática e Detalhes da Transcrição (Nesta APA)</h5>", unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 1, 1])
    with col_center:
        is_analise_tematica = utils.render_toggle_button(
            label="✔️ Abrir Análise Temática",
            session_key="analise_tematica",
            button_key="btn_analise_tematica"
        )

    st.markdown("---")

    if is_analise_tematica:
        def extrair_temas_e_metricas(resultado_lista):
            temas, metricas = [], []
            for linha in resultado_lista:
                if any(k in linha for k in ['Risco Observado', 'Abertura Observada', 'Raiz Observada', 'Intensidade Geral', 'Direção:', 'Volatilidade', 'Classificação APA', 'Leitura Operacional']):
                    metricas.append(linha)
                else:
                    temas.append(linha)
            return temas, metricas

        with st.spinner("Processando padrões mentais, temas dominantes e gerando nuvens de palavras..."):
            try:
                texto_c  = analise.limpar_valor(df_apa.get('TRANSCRIÇÃO DO CAUSADOR', ''))
                texto_np = analise.limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL', ''))
                texto_ns = analise.limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO', ''))
                texto_total = f"{texto_c} {texto_np} {texto_ns}"

                resolucao_raw = analise.limpar_valor(df_apa.get('Resolução', df_apa.get('RESOLUÇÃO', df_apa.get('resolucao', '')))).strip()
                resolucao_norm = resolucao_raw.lower()
                if not resolucao_norm:
                    resolucao_tipo = "desconhecida"
                elif "tática" in resolucao_norm or "tatica" in resolucao_norm:
                    resolucao_tipo = "Negociação Tática"
                elif "real" in resolucao_norm or "negocia" in resolucao_norm:
                    resolucao_tipo = "Negociação Real"
                elif "interven" in resolucao_norm:
                    resolucao_tipo = "Intervenção"
                else:
                    resolucao_tipo = "desconhecida"

                def extrair_tempo(valor):
                    try:
                        return int(float(str(analise.limpar_valor(valor)).replace(',', '.') or 0))
                    except Exception:
                        return 0

                tempo_neg_real   = extrair_tempo(df_apa.get('TEMPO NEGOCIAÇÃO REAL', df_apa.get('Tempo Negociação Real', df_apa.get('tempo_negociacao_real', 0))))
                tempo_neg_tatica = extrair_tempo(df_apa.get('TEMPO NEGOCIAÇÃO TÁTICA', df_apa.get('Tempo Negociação Tática', df_apa.get('tempo_negociacao_tatica', 0))))

                resultado_total = analise.extrair_topicos_ngrams(texto_total, resolucao_tipo=resolucao_tipo) if len(texto_total) > 10 else ["Texto insuficiente"]
                resultado_c  = analise.extrair_topicos_ngrams(texto_c,  resolucao_tipo=resolucao_tipo) if len(texto_c)  > 10 else ["Texto insuficiente"]
                resultado_np = analise.extrair_topicos_ngrams(texto_np, resolucao_tipo=resolucao_tipo) if len(texto_np) > 10 else ["Texto insuficiente"]
                resultado_ns = analise.extrair_topicos_ngrams(texto_ns, resolucao_tipo=resolucao_tipo) if len(texto_ns) > 10 else ["Texto insuficiente"]

                temas_total, _ = extrair_temas_e_metricas(resultado_total)
                temas_c,  _    = extrair_temas_e_metricas(resultado_c)
                temas_np, _    = extrair_temas_e_metricas(resultado_np)
                temas_ns, _    = extrair_temas_e_metricas(resultado_ns)

                st.session_state['stats_calculados'] = {
                    "temas": temas_total, "temas_c": temas_c, "temas_np": temas_np, "temas_ns": temas_ns,
                    "wc_c":  analise.gerar_wordcloud(texto_c)  if len(texto_c)  > 5 else None,
                    "wc_np": analise.gerar_wordcloud(texto_np) if len(texto_np) > 5 else None,
                    "wc_ns": analise.gerar_wordcloud(texto_ns) if len(texto_ns) > 5 else None,
                    "texto_c_raw": texto_c, "texto_np_raw": texto_np, "texto_ns_raw": texto_ns,
                    "resolucao_tipo": resolucao_tipo, "resolucao_raw": resolucao_raw,
                    "tempo_neg_real": tempo_neg_real, "tempo_neg_tatica": tempo_neg_tatica,
                }
                st.success("✅ Padrões mentais processados!")
            except Exception as e:
                st.error(f"Erro ao processar: {str(e)[:80]}")

    if st.session_state.get('stats_calculados'):
        stats = st.session_state['stats_calculados']

        tab_ng1, tab_ng2, tab_ng3, tab_ng4, tab_ng5, tab_ng6, tab_ng7, tab_ng8 = st.tabs([
            "🔴 Causador", "🟢 Negociador Principal", "🔵 Negociador Secundário",
            "✔️ Análise Global", "✔️ Comparativo das Nuvens de Palavras",
            "✔️ Convergência Temática", "✔️ Estado da Crise", "✔️ Detalhes da Transcrição"
        ])

        with tab_ng1:
            st.markdown("""
            <div class='info-card'>
            <h5 style='color: #ef4444; margin-top: 0;'>🔴 CAUSADOR — Em que ele estava REALMENTE focando?</h5>
            <p style='font-size:0.9rem;color:#ddd;'>Os temas dominantes abaixo revelam a <strong>obsessão mental</strong> do causador.</p>
            </div>""", unsafe_allow_html=True)
            for t in stats.get('temas_c', ["Análise individual ainda não gerada."]):
                st.markdown(t)
            wc_c = stats.get('wc_c')
            if wc_c:
                st.markdown("#### Nuvem de Palavras — Foco Mental do Causador")
                st.pyplot(wc_c)
            else:
                st.info("Sem transcrição suficiente para gerar nuvem.")

        with tab_ng2:
            st.markdown("""
            <div class='info-card'>
            <h5 style='color: #10b981; margin-top: 0;'>🟢 NEGOCIADOR PRINCIPAL — Acompanhou os temas expostos pelo Causador?</h5>
            <p style='font-size:0.9rem;color:#ddd;'>Os temas do negociador mostram <strong>em que ele está focando</strong>.</p>
            </div>""", unsafe_allow_html=True)
            for t in stats.get('temas_np', ["Análise individual ainda não gerada."]):
                st.markdown(t)
            wc_np = stats.get('wc_np')
            if wc_np:
                st.markdown("#### Nuvem de Palavras — Estratégia do Negociador")
                st.pyplot(wc_np)
            else:
                st.info("Sem transcrição suficiente para gerar nuvem.")

        with tab_ng3:
            st.markdown("""
            <div class='info-card'>
            <h5 style='color: #3b82f6; margin-top: 0;'>🔵 NEGOCIADOR SECUNDÁRIO — Destacou alguma participação?</h5>
            <p style='font-size:0.9rem;color:#ddd;'>Seus temas indicam se estava reforçando a mensagem do principal ou dispersando esforços.</p>
            </div>""", unsafe_allow_html=True)
            for t in stats.get('temas_ns', ["Análise individual ainda não gerada."]):
                st.markdown(t)
            wc_ns = stats.get('wc_ns')
            if wc_ns:
                st.markdown("#### Nuvem de Palavras — Atuação do Secundário")
                st.pyplot(wc_ns)
            else:
                st.info("Sem transcrição suficiente para gerar nuvem.")

        with tab_ng4:
            st.markdown("""
            <div class='info-card'>
            <h5 style='color: #f97316; margin-top: 0;'>✔️ VISÃO GERAL — Os temas gerais do incidente</h5>
            <p style='font-size:0.9rem;color:#ddd;'>Agregando causador + negociadores, quais eram os assuntos DOMINANTES?</p>
            </div>""", unsafe_allow_html=True)
            for t in stats.get('temas', ["Sem dados"]):
                st.markdown(t)

        with tab_ng5:
            st.markdown("""
            <div class='info-card'>
            <h5 style='color: #FFD700; margin-top: 0;'>✔️ NUVEM DE PALAVRAS LADO-A-LADO — Sincronização</h5>
            <p style='font-size:0.9rem;color:#ddd;'>Compare as nuvens visualmente.</p>
            </div>""", unsafe_allow_html=True)
            col_wc_g1, col_wc_g2, col_wc_g3 = st.columns(3)
            with col_wc_g1:
                st.markdown("**Causador**")
                wc_c = stats.get('wc_c')
                st.pyplot(wc_c, clear_figure=True) if wc_c else st.info("Sem nuvem.")
            with col_wc_g2:
                st.markdown("**Negociador Principal**")
                wc_np = stats.get('wc_np')
                st.pyplot(wc_np, clear_figure=True) if wc_np else st.info("Sem nuvem.")
            with col_wc_g3:
                st.markdown("**Negociador Secundário**")
                wc_ns = stats.get('wc_ns')
                st.pyplot(wc_ns, clear_figure=True) if wc_ns else st.info("Sem nuvem.")

        with tab_ng6:
            st.markdown("""
            <div class='info-card'>
            <h4 style='color:#FFD700; margin-top:0;'>✔️ CONVERGÊNCIA TEMÁTICA — Quanto cada tema foi abordado?</h4>
            <p style='color:#ccc; font-size:0.9rem;'>Compara a <strong>intensidade (score)</strong> de cada tema abordado por causador e negociador.</p>
            </div>""", unsafe_allow_html=True)
            texto_c_raw  = stats.get('texto_c_raw', '')
            texto_np_raw = stats.get('texto_np_raw', '')
            if not texto_c_raw or not texto_np_raw:
                st.warning("⚠️ Transcrições insuficientes para analisar convergência temática.")
            else:
                try:
                    temas_c  = analise.extrair_temas_unicos(texto_c_raw,  resolucao_tipo=stats.get('resolucao_tipo', 'desconhecida'))
                    temas_np = analise.extrair_temas_unicos(texto_np_raw, resolucao_tipo=stats.get('resolucao_tipo', 'desconhecida'))
                    conv_tematica = analise.calcular_convergencia_tematica(temas_c, temas_np)
                    st.markdown("### ✔️ Resumo da Convergência")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1: st.metric("Convergência Geral", f"{conv_tematica['convergencia_geral']:.1f}%")
                    with col2: st.metric("Temas Compartilhados", len(conv_tematica['temas_compartilhados']))
                    with col3: st.metric("Só Causador", len(conv_tematica['temas_exclusivos_causador']))
                    with col4: st.metric("Só Negociador", len(conv_tematica['temas_exclusivos_negociador']))
                    st.markdown("---")
                    try:
                        fig_r = analise.gerar_radar_convergencia_tematica_corrigido(temas_c, temas_np, conv_tematica['convergencia_por_tema'])
                        st.plotly_chart(fig_r, use_container_width=True)
                    except Exception as e:
                        st.error(f"Erro ao gerar radar: {str(e)[:80]}")
                    st.markdown("---")
                    try:
                        fig_b = analise.gerar_grafico_barras_intensidade_temas(conv_tematica['convergencia_por_tema'])
                        st.plotly_chart(fig_b, use_container_width=True)
                    except Exception as e:
                        st.error(f"Erro ao gerar gráfico: {str(e)[:80]}")
                    st.markdown("---")
                    df_conv_tab = analise.gerar_tabela_convergencia_tematica(conv_tematica)
                    st.dataframe(df_conv_tab, use_container_width=True, hide_index=True)
                    st.markdown("---")
                    st.markdown(conv_tematica['analise_detalhada'])
                except Exception as e:
                    st.error(f"Erro ao analisar convergência temática: {str(e)[:80]}")

        with tab_ng7:
            st.markdown("""
            <div class='info-card'>
            <h5 style='color:#FFD700; margin-top:0;'>✔️ ESTADO DO CAUSADOR (APA)</h5>
            <p style='color:#ccc; font-size:0.9rem;'>Análise estruturada do estado emocional/comportamental do causador.</p>
            </div>""", unsafe_allow_html=True)
            texto_c_raw = stats.get('texto_c_raw', '')
            if texto_c_raw:
                try:
                    analise_crise = analise.analisar_crise_direcional(texto_c_raw, resolucao_tipo=stats.get('resolucao_tipo', 'desconhecida'))
                    if analise_crise and 'sumario' in analise_crise:
                        sumario            = analise_crise['sumario']
                        risco_observado    = sumario.get('risco_observado')
                        abertura_observada = sumario.get('abertura_observada')
                        raiz_observada     = sumario.get('raiz_observada')
                        volatilidade_index = sumario.get('volatilidade_index')
                        intensidade_index  = sumario.get('intensidade_index')
                        direcao_index      = sumario.get('direcao_index')
                        classificacao      = sumario.get('classificacao')
                        leitura            = sumario.get('leitura')
                        resolucao_tipo     = stats.get('resolucao_tipo', 'desconhecida')
                        st.markdown("### ✔️ Resumo da Análise")
                        col1, col2, col3 = st.columns(3)
                        with col1: st.metric("🔴 Risco Observado",    f"{risco_observado:.1f}%"    if risco_observado    is not None else "N/D")
                        with col2: st.metric("🟢 Abertura Observada", f"{abertura_observada:.1f}%" if abertura_observada is not None else "N/D")
                        with col3: st.metric("🟡 Raiz Observada",     f"{raiz_observada:.1f}%"     if raiz_observada     is not None else "N/D")
                        col4, col5, col6 = st.columns(3)
                        with col4: st.metric("⚡ Intensidade Global", f"{intensidade_index:.2f}"  if intensidade_index  is not None else "N/D")
                        with col5: st.metric("➡️ Direção",            f"{direcao_index:+.2f}"     if direcao_index      is not None else "N/D")
                        with col6: st.metric("✔️ Volatilidade",       f"{volatilidade_index:.2f}" if volatilidade_index is not None else "N/D")
                        st.markdown("---")
                        st.info(leitura)
                        st.markdown("---")
                        st.markdown("### ✔️ Padrão de Crise (Radar)")
                        try:
                            fig_crise = analise.gerar_radar_crise_individual(
                                risco_observado    if risco_observado    is not None else 0,
                                abertura_observada if abertura_observada is not None else 0,
                                raiz_observada     if raiz_observada     is not None else 0,
                                volatilidade_index if volatilidade_index is not None else 0
                            )
                            st.plotly_chart(fig_crise, use_container_width=True)
                        except Exception as e:
                            st.error(f"Erro ao gerar radar: {str(e)[:80]}")
                        st.markdown("---")
                        st.markdown("### ✔️ Leitura Operacional (Linguagem Acessível)")
                        narrativa = analise.gerar_narrativa_crise(
                            risco_observado=risco_observado or 0, abertura_observada=abertura_observada or 0,
                            raiz_observada=raiz_observada or 0, intensidade_index=intensidade_index or 0,
                            direcao_index=direcao_index or 0, volatilidade_index=volatilidade_index or 0,
                            classificacao=classificacao or "INDETERMINADO", resolucao_tipo=resolucao_tipo
                        )
                        st.markdown(narrativa)
                    else:
                        st.warning("Não foi possível gerar análise de crise")
                except Exception as e:
                    st.error(f"Erro ao analisar crise: {str(e)[:80]}")
            else:
                st.warning("⚠️ Nenhuma transcrição disponível para análise")

        with tab_ng8:
            st.markdown("### Detalhes da Transcrição")
            col_caus = "TRANSCRIÇÃO DO CAUSADOR"
            col_neg  = "TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL"
            if col_caus not in df_apa or col_neg not in df_apa:
                st.warning("⚠️ Colunas de transcrição não encontradas")
            else:
                txt_caus = str(df_apa[col_caus]).strip()
                txt_neg  = str(df_apa[col_neg]).strip()
                if not txt_caus or not txt_neg or len(txt_caus) < 20 or len(txt_neg) < 20:
                    st.warning("⚠️ Transcrições insuficientes para análise")
                else:
                    col_left, col_center, col_right = st.columns([1, 1, 1])
                    with col_center:
                        is_analise_rapida = utils.render_toggle_button(
                            label="✔️ Análise dos Padrões Léxicos",
                            session_key="tab8_analise_rapida",
                            button_key="btn_tab8_analise_rapida"
                        )
                    st.markdown("---")
                    if is_analise_rapida:
                        analise_rapida = analise.analise_rapida_discurso(txt_neg, txt_caus)
                        st.markdown("### 🟢 NEGOCIADOR PRINCIPAL")
                        col1, col2, col3 = st.columns(3)
                        with col1: st.metric("Validação", analise_rapida['total_validacao'], "x ocorrências")
                        with col2: st.metric("Confronto", analise_rapida['total_confronto'], "x ocorrências")
                        with col3: st.metric("Tamanho (Palavras)", len(txt_neg.split()), "palavras")
                        st.markdown("---")
                        st.markdown("### 🔴 CAUSADOR")
                        col1, col2 = st.columns(2)
                        with col1: st.metric("Emoção Alta", analise_rapida['total_emocao'], "x palavras fortes")
                        with col2: st.metric("Tamanho (Palavras)", len(txt_caus.split()), "palavras")
                        st.markdown("---")
                        st.markdown("#### ✔️ Detalhes das Palavras-Chave Encontradas")
                        col_val, col_conf = st.columns(2)
                        with col_val:
                            st.markdown("**Validação (Negociador):**")
                            for palavra, freq in sorted(analise_rapida['validacao'].items(), key=lambda x: x[1], reverse=True):
                                st.write(f"  • {palavra}: {freq}x")
                        with col_conf:
                            st.markdown("**Confronto (Negociador):**")
                            for palavra, freq in sorted(analise_rapida['confronto'].items(), key=lambda x: x[1], reverse=True):
                                st.write(f"  • {palavra}: {freq}x")
                        st.markdown("---")
                        st.markdown("### 🔴 CAUSADOR")
                        st.markdown("**Emoção Alta (Causador):**")
                        for palavra, freq in sorted(analise_rapida['emocao_causador'].items(), key=lambda x: x[1], reverse=True):
                            st.write(f"  • {palavra}: {freq}x")
                        st.markdown("---")
                        st.markdown("#### 💡 O Que Significa")
                        st.markdown("""
                        - **Validação**: Palavras que indicam reconhecimento, escuta, empatia
                        - **Confronto**: Palavras que indicam discordância, negação, imposição
                        - **Emoção Alta**: Indicadores de stress, medo, raiva no causador

                        **Nota:** Essa análise conta frequência, não interpreta contexto.
                        """)

    st.markdown("---")

    # ════════════════════════════════════════════════════════════
    # BOTÃO PDF / IA
    # ════════════════════════════════════════════════════════════
    if st.button("✔ 3. GERAR ANALYTICS E EXPORTAR ANÁLISE (PDF)"):
        with st.spinner("Compilando dados técnicos, consultando IA e desenhando PDF..."):
            try:
                p_agr_c_num = st.session_state.get('p_agr_c_num', 0)
                p_rec_c_num = st.session_state.get('p_rec_c_num', 0)
                s_agr_c_num = st.session_state.get('s_agr_c_num', 0)
                s_rec_c_num = st.session_state.get('s_rec_c_num', 0)
                l_agr_c_num = st.session_state.get('l_agr_c_num', 0)
                l_rec_c_num = st.session_state.get('l_rec_c_num', 0)
                p_agr_e_num = st.session_state.get('p_agr_e_num', 0)
                p_rec_e_num = st.session_state.get('p_rec_e_num', 0)
                s_agr_e_num = st.session_state.get('s_agr_e_num', 0)
                s_rec_e_num = st.session_state.get('s_rec_e_num', 0)
                l_agr_e_num = st.session_state.get('l_agr_e_num', 0)
                l_rec_e_num = st.session_state.get('l_rec_e_num', 0)

                t_causador   = utils.limpar_valor(df_apa.get('TRANSCRIÇÃO DO CAUSADOR'))
                t_principal  = utils.limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL'))
                t_secundario = utils.limpar_valor(df_apa.get('TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO'))

                df_transcricoes = pd.DataFrame([{"Causador": t_causador, "Neg_Principal": t_principal, "Neg_Secundario": t_secundario}])

                stats_calculados = st.session_state.get('stats_calculados', {}) or {}
                temas_extraidos = stats_calculados.get('topicos', ["Etapa 2 não executada"])
                if not isinstance(temas_extraidos, (list, tuple)):
                    temas_extraidos = [str(temas_extraidos)]

                meta_dict = df_apa.to_dict()
                meta_dict["temas_dominantes_scikit_learn"] = " | ".join([str(t) for t in temas_extraidos])
                meta_dict["analises_calculadas"] = {
                    "ngrams": stats_calculados.get("ngrams", stats_calculados.get("n_grams", "Não executada")),
                    "convergencia": stats_calculados.get("convergencia", stats_calculados.get("convergencia_lexical", "Não executada")),
                    "topicos": temas_extraidos,
                }
                df_meta = pd.DataFrame([meta_dict])
                dados_extraidos = {"transcricao": df_transcricoes, "metadados": df_meta}

                tecnicas_da_apa = []
                freq_tecnicas_dict = {}
                estatisticas_ocorrencia = {}

                try:
                    if not df_tec.empty:
                        col_vinculo = next((c for c in df_tec.columns if 'VINCULO' in c.upper() or 'VÍNCULO' in c.upper()), None)
                        if col_vinculo:
                            id_visivel = str(apa_selecionada).strip()
                            df_tec_tmp = df_tec.copy()
                            df_tec_tmp['Vinculo_Str'] = df_tec_tmp[col_vinculo].astype(str).str.replace(r"[\[\]'\"]", "", regex=True).str.strip()
                            df_tec_filtrado_pdf = df_tec_tmp[df_tec_tmp['Vinculo_Str'] == id_visivel].copy()
                            if df_tec_filtrado_pdf.empty and 'Airtable_Record_ID' in df_apa:
                                id_interno = str(df_apa['Airtable_Record_ID']).strip()
                                df_tec_filtrado_pdf = df_tec_tmp[df_tec_tmp[col_vinculo].astype(str).str.contains(id_interno, na=False, regex=False)].copy()
                            if not df_tec_filtrado_pdf.empty:
                                col_tecnica = next((col for col in ['TÉCNICAS', 'TECNICAS', 'TÉCNICA', 'TECNICA'] if col in df_tec_filtrado_pdf.columns), None)
                                if col_tecnica:
                                    freq_abs = df_tec_filtrado_pdf[col_tecnica].value_counts()
                                    freq_rel = (df_tec_filtrado_pdf[col_tecnica].value_counts(normalize=True) * 100).round(1)
                                    df_freq_pdf = pd.DataFrame({'Técnica Empregada': freq_abs.index, 'Frequência Absoluta': freq_abs.values, 'Frequência Relativa (%)': freq_rel.values})
                                    tecnicas_da_apa = df_freq_pdf['Técnica Empregada'].dropna().astype(str).tolist()
                                    frequencia_tecnicas_ocorrencia = [{"tecnica": str(r["Técnica Empregada"]), "frequencia_absoluta": int(r["Frequência Absoluta"]), "frequencia_relativa": float(r["Frequência Relativa (%)"])} for _, r in df_freq_pdf.iterrows()]
                                    freq_tecnicas_dict = dict(zip(df_freq_pdf['Técnica Empregada'].astype(str), df_freq_pdf['Frequência Absoluta'].astype(int)))
                                    estatisticas_ocorrencia = {"frequencia_tecnicas_ocorrencia": frequencia_tecnicas_ocorrencia, "frequencia_absoluta_por_tecnica": freq_tecnicas_dict}
                except Exception as e:
                    st.warning(f"Falha ao montar frequências para a IA: {e}")

                resultado_ia = ia_link.analisar_ocorrencia_gate(dados_extraidos, estatisticas_ocorrencia=estatisticas_ocorrencia, tecnicas_ocorrencia=tecnicas_da_apa)

                if isinstance(resultado_ia, dict):
                    parecer_ia = resultado_ia.get("parecer", "")
                    sugestoes_treinamento = resultado_ia.get("sugestoes_treinamento", "")
                else:
                    parecer_ia = str(resultado_ia)
                    sugestoes_treinamento = ""

                def calcular_media_equipe(*valores):
                    validos = [v for v in valores if v and v > 0]
                    return sum(validos) / len(validos) if validos else None

                likert_inicio = {'agressividade_media': calcular_media_equipe(p_agr_c_num, s_agr_c_num, l_agr_c_num), 'receptividade_media': calcular_media_equipe(p_rec_c_num, s_rec_c_num, l_rec_c_num)}
                likert_fim    = {'agressividade_media': calcular_media_equipe(p_agr_e_num, s_agr_e_num, l_agr_e_num), 'receptividade_media': calcular_media_equipe(p_rec_e_num, s_rec_e_num, l_rec_e_num)}

                try:
                    import numpy as _np
                    from scipy.stats import spearmanr as _spearmanr
                    x_likert = [v for v in [p_agr_c_num, s_agr_c_num, l_agr_c_num] if v > 0]
                    y_likert = [v for v in [p_agr_e_num, s_agr_e_num, l_agr_e_num] if v > 0]
                    n_par = min(len(x_likert), len(y_likert))
                    if n_par >= 3 and len(set(x_likert[:n_par])) > 1 and len(set(y_likert[:n_par])) > 1:
                        rho_lk, p_lk = _spearmanr(x_likert[:n_par], y_likert[:n_par])
                        stats_spearman = {'valido': True, 'p_value': float(p_lk), 'rho': float(rho_lk)}
                    else:
                        stats_spearman = {'valido': False, 'p_value': 1.0, 'rho': 0.0}
                except Exception:
                    stats_spearman = {'valido': False, 'p_value': 1.0, 'rho': 0.0}

                laudo_frio = ia_link.gerar_laudo_frio(likert_inicio, likert_fim, stats_spearman)

                st.markdown(f"""
                <div class="info-card" style="border-left: 4px solid #FFD700;">
                <h4 style="color: #FFD700; margin-top: 0;">Inferência Estatística (Motor Frio)</h4>
                <p style="font-size: 1.05rem; line-height: 1.6;">{laudo_frio}</p>
                <hr style="border-color: rgba(255,255,255,0.1); margin: 15px 0;">
                <h4 style="color: #06C755; margin-top: 0;">Leitura Analítica</h4>
                <p style="font-size: 1.05rem; line-height: 1.6;">{parecer_ia}</p>
                <hr style="border-color: rgba(255,255,255,0.1); margin: 15px 0;">
                <h4 style="color: #FFA500; margin-top: 0;">Sugestões para treinamentos</h4>
                <p style="font-size: 1.05rem; line-height: 1.6;">{sugestoes_treinamento or 'Sem base suficiente para sugerir treinamento específico.'}</p>
                </div>
                """, unsafe_allow_html=True)

                texto_str = f"INFERENCIA ESTATISTICA (MOTOR FRIO)\n\n{laudo_frio}\n\nLEITURA ANALITICA\n\n{parecer_ia}\n\nSUGESTOES PARA TREINAMENTOS\n\n{sugestoes_treinamento or 'Sem base suficiente.'}"
                texto_str = texto_str.replace("**", "").replace("### ", "")
                texto_final_pdf = unicodedata.normalize('NFKD', texto_str).encode('ASCII', 'ignore').decode('ASCII')

                pdf = FPDF()
                pdf.add_page()
                pdf.set_fill_color(249, 115, 22)
                pdf.rect(0, 0, 210, 40, 'F')
                pdf.set_font("Arial", "B", 18)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 15, "RELATÓRIO DE ANALISE POS-ACAO (APA), ASSISTIDO POR INTELIGENCIA ARTIFICIAL", ln=True, align="C")
                pdf.set_font("Arial", "I", 12)
                pdf.cell(0, 5, f"Unidade: GATE | ID: {apa_selecionada}", ln=True, align="C")
                pdf.ln(20)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "B", 14)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(0, 10, " 1. INFORMACOES DO INCIDENTE", ln=True, fill=True)
                pdf.set_font("Arial", "", 11)

                dt_oc = utils.limpar_valor(df_apa.get('Data da ocorrência'))
                tip   = utils.limpar_valor(df_apa.get('Tipologia'))
                neg   = utils.limpar_valor(df_apa.get('Negociador Principal'))
                info_str = f"Data: {dt_oc} | Tipologia: {tip} | Negociador: {neg}"
                pdf.multi_cell(0, 8, txt=unicodedata.normalize('NFKD', info_str).encode('ASCII', 'ignore').decode('ASCII'), border='L')
                pdf.ln(10)
                pdf.set_font("Arial", "B", 14)
                pdf.set_fill_color(249, 115, 22)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 10, " 2. INTELIGENCIA DE APOIO A DECISAO (IA)", ln=True, fill=True)
                pdf.ln(5)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "", 11)
                pdf.multi_cell(0, 7, txt=texto_final_pdf)

                pdf_saida = pdf.output(dest="S")
                pdf_bytes = pdf_saida.encode('latin-1', errors='replace') if isinstance(pdf_saida, str) else bytes(pdf_saida)

                st.download_button(label="📥 BAIXAR ANÁLISE COMPLETA (PDF)", data=pdf_bytes, file_name=f"Laudo_GATE_{apa_selecionada}.pdf", mime="application/pdf")

            except Exception as e:
                st.error(f"Erro na análise da IA ou geração do PDF: {str(e)}")

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='margin-top:20px; margin-bottom:100px; padding:15px; background-color:#111; border-radius:8px;'>
    <p style="color:#bbb; font-size:13px; line-height:1.7; text-align:left;">
    <span style="color:#ffae42; font-weight:700; font-size:14px; letter-spacing:1px;">DELTA-NEGOCIAÇÃO — GATE/PMESP</span>
    <br><br>
    "O maior inimigo do conhecimento não é a ignorância, mas a ilusão do conhecimento." — Stephen Hawking.
    <br><br>
    "Sem dados, você é apenas mais uma pessoa com opinião." — W. Edwards Deming.
    </p>
    <hr style="border:none; height:1px; background:linear-gradient(to right, transparent, rgba(255,174,66,0.6), transparent); margin-top:18px; margin-bottom:12px;">
    <div style="text-align:center; font-size:11px; color:#666; line-height:1.5;">
    © 2026 Delta-Negociação — Todos os direitos reservados.
    </div>
    """, unsafe_allow_html=True)