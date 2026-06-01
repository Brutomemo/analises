# ============================================================
# form_apa.py (V2)
# ABA: ENTRADA DE DADOS — MODO HÍBRIDO
# Criar novos registros OU enriquecer existentes
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import unicodedata
import airtable_link


def limpar_valor(val):
    """Limpa valores vindos do Airtable"""
    if isinstance(val, list):
        return val[0] if len(val) > 0 else "N/D"
    return str(val) if pd.notna(val) else "N/D"


def converter_escala_texto_numero(texto):
    """Converte descrição Likert para número"""
    escala_map = {
        "❓ inaudível / não observado": 0,
        "não agressivo": 1,
        "não receptivo": 1,
        "neutro": 2,
        "parcialmente agressivo": 3,
        "parcialmente receptivo": 3,
        "agressivo": 4,
        "receptivo": 4,
        "muito agressivo": 5,
        "muito receptivo": 5,
    }
    
    v = str(texto).lower().strip()
    return escala_map.get(v, 0)


def render_form_apa(df_quali, df_tec):
    """
    Página de Entrada de Dados com 2 modos:
    MODO 1: Criar nova APA
    MODO 2: Enriquecer APA existente
    """
    
    st.markdown("### 📋 Entrada de Dados — Nova APA ou Enriquecimento")
    st.markdown("""
    <p style='color: #aaa; font-size: 0.9rem; margin-bottom: 1rem;'>
    <strong>Escolha:</strong> Criar uma nova ocorrência OU enriquecer dados já existentes na base.
    </p>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ════════════════════════════════════════════════════════════════
    # SELETOR DE MODO
    # ════════════════════════════════════════════════════════════════
    
    modo = st.radio(
        "Escolha o modo de operação:",
        ["➕ Criar Nova APA", "✏️ Enriquecer APA Existente"],
        horizontal=True,
        key="modo_entrada"
    )
    
    st.markdown("---")
    
    # ════════════════════════════════════════════════════════════════
    # MODO 1: CRIAR NOVA APA
    # ════════════════════════════════════════════════════════════════
    
    if modo == "➕ Criar Nova APA":
        render_modo_criar_nova(df_quali, df_tec)
    
    # ════════════════════════════════════════════════════════════════
    # MODO 2: ENRIQUECER EXISTENTE
    # ════════════════════════════════════════════════════════════════
    
    else:
        render_modo_enriquecer(df_quali, df_tec)


def render_modo_criar_nova(df_quali, df_tec):
    """
    MODO 1: Formulário completo para criar nova APA
    Todos os campos necessários para um registro completo
    """
    
    st.markdown("#### ➕ CRIAR NOVA APA")
    st.markdown("""
    <p style='font-size: 0.9rem; color: #aaa;'>
    Preencha todos os campos para criar um novo registro na base.
    </p>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Dividir em abas por tema
    tab_metadata, tab_transcricoes, tab_percepcao, tab_observacoes = st.tabs([
        "📊 Metadados",
        "📝 Transcrições",
        "👁️ Percepção",
        "📋 Observações"
    ])
    
    # ─────────────────────────────────────────────────────────────
    # TAB 1: METADADOS
    # ─────────────────────────────────────────────────────────────
    
    with tab_metadata:
        st.markdown("**Data & Identificação**")
        
        col_dt, col_tip = st.columns(2)
        with col_dt:
            data_oca = st.date_input(
                "Data da Ocorrência",
                key="criar_data"
            )
        with col_tip:
            tipologia = st.selectbox(
                "Tipologia",
                ["Ameaça de Suicídio", "Reféns", "Perturbado Psíquico",
                 "Agressão", "Outros"],
                key="criar_tipologia"
            )
        
        st.markdown("**Incidente**")
        
        col_mod, col_mot = st.columns(2)
        with col_mod:
            modalidade = st.selectbox(
                "Modalidade do Incidente",
                ["Pessoa armada com propósito suicida",
                 "Pessoa armada com propósito de agressão",
                 "Pessoa desarmada",
                 "Outros"],
                key="criar_modalidade"
            )
        with col_mot:
            motivacao = st.text_input(
                "Motivação (breve)",
                placeholder="Ex: Desemprego, desentendimento familiar",
                key="criar_motivacao"
            )
        
        st.markdown("**Responsáveis**")
        
        col_neg, col_sec = st.columns(2)
        with col_neg:
            negociador_principal = st.text_input(
                "Negociador Principal",
                placeholder="Nome ou Identificação",
                key="criar_neg_principal"
            )
        with col_sec:
            negociador_secundario = st.text_input(
                "Negociador Secundário (opcional)",
                placeholder="Nome ou Identificação",
                key="criar_neg_secundario"
            )
    
    # ─────────────────────────────────────────────────────────────
    # TAB 2: TRANSCRIÇÕES
    # ─────────────────────────────────────────────────────────────
    
    with tab_transcricoes:
        st.markdown("**Causador**")
        trans_causador = st.text_area(
            "Transcrição do Causador",
            placeholder="Digite ou cole a transcrição completa...",
            height=120,
            key="criar_trans_causador"
        )
        
        st.markdown("**Negociador Principal**")
        trans_neg_principal = st.text_area(
            "Transcrição do Negociador Principal",
            placeholder="Digite ou cole a transcrição completa...",
            height=120,
            key="criar_trans_neg_principal"
        )
        
        st.markdown("**Negociador Secundário (opcional)**")
        trans_neg_secundario = st.text_area(
            "Transcrição do Negociador Secundário",
            placeholder="Digite ou cole a transcrição (deixe em branco se não houver)",
            height=100,
            key="criar_trans_neg_secundario"
        )
    
    # ─────────────────────────────────────────────────────────────
    # TAB 3: PERCEPÇÃO
    # ─────────────────────────────────────────────────────────────
    
    with tab_percepcao:
        st.markdown("**Percepção na Chegada**")
        
        col_agr_c, col_rec_c = st.columns(2)
        with col_agr_c:
            agr_chegada = st.selectbox(
                "Agressividade",
                ["❓ Não observado", "Não agressivo", "Neutro",
                 "Parcialmente agressivo", "Agressivo", "Muito agressivo"],
                key="criar_agr_chegada"
            )
        with col_rec_c:
            rec_chegada = st.selectbox(
                "Receptividade",
                ["❓ Não observado", "Não receptivo", "Neutro",
                 "Parcialmente receptivo", "Receptivo", "Muito receptivo"],
                key="criar_rec_chegada"
            )
        
        st.markdown("**Percepção no Encerramento**")
        
        col_agr_e, col_rec_e = st.columns(2)
        with col_agr_e:
            agr_encerramento = st.selectbox(
                "Agressividade",
                ["❓ Não observado", "Não agressivo", "Neutro",
                 "Parcialmente agressivo", "Agressivo", "Muito agressivo"],
                key="criar_agr_enc"
            )
        with col_rec_e:
            rec_encerramento = st.selectbox(
                "Receptividade",
                ["❓ Não observado", "Não receptivo", "Neutro",
                 "Parcialmente receptivo", "Receptivo", "Muito receptivo"],
                key="criar_rec_enc"
            )
        
        st.markdown("**Resultado**")
        
        col_res, col_uni = st.columns(2)
        with col_res:
            resolucao = st.selectbox(
                "Forma de Resolução",
                ["Negociação Real", "Negociação Tática", "Intervenção", "Outros"],
                key="criar_resolucao"
            )
        with col_uni:
            uniforme = st.selectbox(
                "Uniforme Usado",
                ["Farda", "Encoberto", "Traje Civil", "N/A"],
                key="criar_uniforme"
            )
    
    # ─────────────────────────────────────────────────────────────
    # TAB 4: OBSERVAÇÕES
    # ─────────────────────────────────────────────────────────────
    
    with tab_observacoes:
        st.markdown("**Tempos**")
        
        col_tr, col_tt = st.columns(2)
        with col_tr:
            tempo_real = st.number_input(
                "Tempo de Negociação Real (segundos)",
                min_value=0,
                value=0,
                key="criar_tempo_real"
            )
        with col_tt:
            tempo_tatica = st.number_input(
                "Tempo de Negociação Tática (segundos)",
                min_value=0,
                value=0,
                key="criar_tempo_tatica"
            )
        
        st.markdown("**Qualidade & Flags**")
        
        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            transcrição_completa = st.checkbox(
                "Transcrição Completa?",
                value=True,
                key="criar_trans_completa"
            )
        with col_q2:
            tem_anomalia = st.checkbox(
                "Tem Anomalia/Flag?",
                value=False,
                key="criar_anomalia"
            )
        with col_q3:
            sexo_causador = st.selectbox(
                "Sexo do Causador",
                ["Masculino", "Feminino", "N/D"],
                key="criar_sexo"
            )
        
        st.markdown("**Observações do Criador**")
        
        observacoes = st.text_area(
            "Notas Adicionais",
            placeholder="Contexto, pontos de atenção, recomendações...",
            height=100,
            key="criar_observacoes"
        )
        
        validador_nome = st.text_input(
            "Seu Nome/ID",
            placeholder="Ex: Cap PM Pavão",
            key="criar_validador"
        )
    
    # ─────────────────────────────────────────────────────────────
    # BOTÕES
    # ─────────────────────────────────────────────────────────────
    
    st.markdown("---")
    
    col_save, col_preview, col_cancel = st.columns(3)
    
    with col_save:
        if st.button("✅ Criar APA", use_container_width=True, type="primary", key="btn_criar_apa"):
            
            # Validações obrigatórias
            erros = []
            if not negociador_principal:
                erros.append("Negociador Principal obrigatório")
            if len(str(trans_causador).split()) < 10:
                erros.append("Transcrição do Causador muito curta (mín. 10 palavras)")
            if len(str(trans_neg_principal).split()) < 10:
                erros.append("Transcrição do Negociador muito curta (mín. 10 palavras)")
            if not validador_nome:
                erros.append("Seu Nome/ID obrigatório")
            
            if erros:
                for erro in erros:
                    st.error(f"❌ {erro}")
            else:
                with st.spinner("💾 Criando novo registro no Airtable..."):
                    try:
                        # Preparar payload
                        payload = {
                            "Data da ocorrência": data_oca.isoformat(),
                            "Tipologia": tipologia,
                            "Modalidade do incidente": modalidade,
                            "Motivação": motivacao,
                            "Negociador Principal": negociador_principal,
                            "Negociador Secundário": negociador_secundario,
                            "TRANSCRIÇÃO DO CAUSADOR": trans_causador,
                            "TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL": trans_neg_principal,
                            "TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO": trans_neg_secundario,
                            "Percepção Principal Agressividade Chegada": agr_chegada,
                            "Percepção Principal Receptividade Chegada": rec_chegada,
                            "Percepção Principal Agressividade Encerramento": agr_encerramento,
                            "Percepção Principal Receptividade Encerramento": rec_encerramento,
                            "Resolução": resolucao,
                            "Uniforme Usado": uniforme,
                            "Tempo de Negociação Real": int(tempo_real),
                            "Tempo de Negociação Tática": int(tempo_tatica),
                            "Transcrição Completa": "Sim" if transcrição_completa else "Não",
                            "Tem Anomalia": "Sim" if tem_anomalia else "Não",
                            "Sexo do Causador": sexo_causador,
                            "Observações": observacoes,
                            "Criado Por": validador_nome,
                            "Data Criação": datetime.now().isoformat(),
                            "Status": "Novo"
                        }
                        
                        # Criar novo registro
                        sucesso = airtable_link.criar_nova_apa(payload)
                        
                        if sucesso:
                            st.success(f"""
                            ✅ **NOVA APA CRIADA COM SUCESSO!**
                            
                            - Negociador: {negociador_principal}
                            - Data: {data_oca}
                            - Tipologia: {tipologia}
                            - Criado por: {validador_nome}
                            """)
                            st.balloons()
                            
                            # Limpar formulário
                            for key in list(st.session_state.keys()):
                                if key.startswith("criar_"):
                                    del st.session_state[key]
                        else:
                            st.error("❌ Erro ao criar APA no Airtable")
                    
                    except Exception as e:
                        st.error(f"❌ Erro: {str(e)[:150]}")
    
    with col_preview:
        if st.button("👁️ Pré-visualizar", use_container_width=True, key="btn_preview_criar"):
            st.json({
                "Negociador": negociador_principal,
                "Data": str(data_oca),
                "Tipologia": tipologia,
                "Transcrição Causador": trans_causador[:100] + "...",
                "Transcrição Negociador": trans_neg_principal[:100] + "...",
                "Agressividade (Chegada)": agr_chegada,
                "Receptividade (Chegada)": rec_chegada,
                "Resolução": resolucao,
                "Criado Por": validador_nome,
                "Data/Hora": datetime.now().isoformat()
            })
    
    with col_cancel:
        if st.button("❌ Limpar", use_container_width=True, key="btn_limpar_criar"):
            for key in list(st.session_state.keys()):
                if key.startswith("criar_"):
                    del st.session_state[key]
            st.info("Formulário limpo")


def render_modo_enriquecer(df_quali, df_tec):
    """
    MODO 2: Buscar APA existente e enriquecer dados
    """
    
    st.markdown("#### ✏️ ENRIQUECER APA EXISTENTE")
    st.markdown("""
    <p style='font-size: 0.9rem; color: #aaa;'>
    Busque uma APA já criada, complete campos faltantes e adicione observações.
    </p>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Buscar APA
    st.markdown("**Etapa 1: Buscar APA**")
    
    col_id, col_btn = st.columns([3, 1])
    with col_id:
        id_busca = st.text_input(
            "ID da APA",
            placeholder="Ex: APA 001, APA 015",
            key="enriq_id_busca"
        )
    with col_btn:
        btn_buscar = st.button("🔍 Buscar", key="btn_buscar_enriq")
    
    apa_encontrada = None
    if btn_buscar and id_busca:
        try:
            id_limpo = str(id_busca).strip().upper()
            if 'ID_Busca' not in df_quali.columns:
                df_quali['ID_Busca'] = df_quali['ID'].apply(
                    lambda x: str(x).strip().upper() if pd.notna(x) else "N/D"
                )
            
            registros = df_quali[df_quali['ID_Busca'].str.contains(id_limpo, case=False, na=False)]
            
            if registros.empty:
                st.error(f"❌ APA {id_busca} não encontrada")
            else:
                apa_encontrada = registros.iloc[0]
                st.success("✅ APA encontrada!")
        except Exception as e:
            st.error(f"Erro: {str(e)}")
    
    # Mostrar dados encontrados
    if apa_encontrada is not None:
        
        st.markdown("---")
        st.markdown("**Etapa 2: Dados Atuais**")
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Data", limpar_valor(apa_encontrada.get('Data da ocorrência', 'N/D')))
        with col_m2:
            st.metric("Negociador", limpar_valor(apa_encontrada.get('Negociador Principal', 'N/D'))[:15])
        with col_m3:
            st.metric("Tipologia", limpar_valor(apa_encontrada.get('Tipologia', 'N/D'))[:12])
        with col_m4:
            st.metric("Status", limpar_valor(apa_encontrada.get('Status', 'Novo')))
        
        st.markdown("---")
        st.markdown("**Etapa 3: Enriquecer Dados**")
        
        # Formulário simples para enriquecimento
        with st.form("form_enriquecimento"):
            
            col_agr, col_rec = st.columns(2)
            with col_agr:
                agr_chegada = st.selectbox(
                    "Agressividade (Chegada)",
                    ["❓ Não observado", "Não agressivo", "Neutro",
                     "Parcialmente agressivo", "Agressivo", "Muito agressivo"],
                    key="enriq_agr"
                )
            with col_rec:
                rec_chegada = st.selectbox(
                    "Receptividade (Chegada)",
                    ["❓ Não observado", "Não receptivo", "Neutro",
                     "Parcialmente receptivo", "Receptivo", "Muito receptivo"],
                    key="enriq_rec"
                )
            
            st.markdown("**Observações**")
            observacoes = st.text_area(
                "Adicione observações",
                placeholder="Insights, pontos de melhoria, contexto adicional...",
                key="enriq_obs"
            )
            
            validador = st.text_input(
                "Seu Nome/ID",
                key="enriq_validador"
            )
            
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                submitted = st.form_submit_button("✅ Salvar Enriquecimento", use_container_width=True)
            with col_s2:
                preview = st.form_submit_button("👁️ Pré-visualizar", use_container_width=True)
            
            if submitted:
                if not validador:
                    st.error("Nome/ID obrigatório")
                else:
                    with st.spinner("Salvando..."):
                        try:
                            payload = {
                                "Percepção Principal Agressividade Chegada": agr_chegada,
                                "Percepção Principal Receptividade Chegada": rec_chegada,
                                "Observações Enriquecimento": observacoes,
                                "Enriquecido Por": validador,
                                "Data Enriquecimento": datetime.now().isoformat(),
                                "Status": "Enriquecido"
                            }
                            
                            sucesso = airtable_link.atualizar_apa_validacao(id_busca, payload)
                            
                            if sucesso:
                                st.success(f"✅ APA {id_busca} enriquecida com sucesso!")
                                st.balloons()
                            else:
                                st.error("Erro ao salvar")
                        except Exception as e:
                            st.error(f"Erro: {str(e)[:100]}")
            
            if preview:
                st.json({
                    "APA ID": id_busca,
                    "Agressividade": agr_chegada,
                    "Receptividade": rec_chegada,
                    "Observações": observacoes[:80] + "..." if len(observacoes) > 80 else observacoes,
                    "Validador": validador
                })
    
    # Rodapé
    st.markdown("---")
    st.markdown("""
    <div style='padding:12px; background:rgba(255,215,0,0.03); border-radius:8px;'>
    <p style='font-size:0.85rem; color:#aaa; margin:0;'>
    💡 Use este modo para completar dados de APAs já criadas. 
    Campos já preenchidos serão mantidos.
    </p>
    </div>
    """, unsafe_allow_html=True)