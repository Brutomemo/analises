# ============================================================
# form_apa.py
# ABA 3: FORMULÁRIO DE ENTRADA & VALIDAÇÃO DE APA
# Entrada de dados + Enriquecimento + Validações
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


def validar_apa(registro):
    """
    Valida um registro de APA
    Retorna: dict com status e mensagens
    """
    validacoes = {
        "erros": [],
        "avisos": [],
        "ok": True
    }
    
    # --- VALIDAÇÕES OBRIGATÓRIAS ---
    
    # Transcrição do causador
    trans_c = limpar_valor(registro.get('TRANSCRIÇÃO DO CAUSADOR', ''))
    if trans_c == 'N/D' or len(str(trans_c).split()) < 10:
        validacoes["erros"].append("❌ Transcrição do Causador: muito curta ou vazia (mín. 10 palavras)")
    
    # Transcrição do negociador principal
    trans_np = limpar_valor(registro.get('TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL', ''))
    if trans_np == 'N/D' or len(str(trans_np).split()) < 10:
        validacoes["erros"].append("❌ Transcrição do Negociador: muito curta ou vazia (mín. 10 palavras)")
    
    # Tipologia
    tip = limpar_valor(registro.get('Tipologia', ''))
    if tip == 'N/D':
        validacoes["erros"].append("❌ Tipologia: não preenchida")
    
    # Modalidade
    mod = limpar_valor(registro.get('Modalidade do incidente', ''))
    if mod == 'N/D':
        validacoes["erros"].append("❌ Modalidade: não preenchida")
    
    # Data
    data = limpar_valor(registro.get('Data da ocorrência', ''))
    if data == 'N/D':
        validacoes["erros"].append("❌ Data da ocorrência: não preenchida")
    
    # --- VALIDAÇÕES DE AVISO ---
    
    # Agressividade/Receptividade na chegada
    agr_c = converter_escala_texto_numero(
        limpar_valor(registro.get('Percepção Principal Agressividade Chegada', ''))
    )
    rec_c = converter_escala_texto_numero(
        limpar_valor(registro.get('Percepção Principal Receptividade Chegada', ''))
    )
    
    if agr_c == 0 and rec_c == 0:
        validacoes["avisos"].append("⚠️ Percepção de Agressividade/Receptividade não preenchida")
    
    # Resolução
    res = limpar_valor(registro.get('Resolução', ''))
    if res == 'N/D':
        validacoes["avisos"].append("⚠️ Resolução não preenchida")
    
    # Atualizar status
    validacoes["ok"] = len(validacoes["erros"]) == 0
    
    return validacoes


def render_form_apa(df_quali, df_tec):
    """
    Página de Formulário: Entrada + Validação de APAs
    """
    
    st.markdown("### Validação & Enriquecimento de APA")
    st.markdown("""
    <p style='color: #aaa; font-size: 0.9rem; margin-bottom: 1rem;'>
    <strong>Fluxo:</strong> Busque uma APA bruta do Airtable, valide os dados, enriqueça com observações, e salve as validações.
    </p>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ════════════════════════════════════════════════════════════════
    # SEÇÃO 1: BUSCAR REGISTRO
    # ════════════════════════════════════════════════════════════════
    
    st.markdown("#### 🔍 Etapa 1: Buscar APA")
    
    col_search_1, col_search_2, col_search_3 = st.columns([2, 1, 1])
    
    with col_search_1:
        id_apa_busca = st.text_input(
            "ID da APA para validar",
            placeholder="Ex: APA 001, APA 042, etc",
            key="form_id_apa"
        )
    
    with col_search_2:
        btn_buscar = st.button("🔍 Buscar", use_container_width=True, key="btn_buscar_apa")
    
    with col_search_3:
        st.markdown("")  # Espaçamento
    
    # Buscar e mostrar registro
    apa_encontrada = None
    if btn_buscar and id_apa_busca:
        
        with st.spinner("Buscando APA no Airtable..."):
            try:
                # Limpar ID
                id_busca_limpo = str(id_apa_busca).strip().upper()
                
                # Buscar no df_quali
                if 'ID_Busca' not in df_quali.columns:
                    df_quali['ID_Busca'] = df_quali['ID'].apply(
                        lambda x: str(x).strip().upper() if pd.notna(x) else "N/D"
                    )
                
                registros = df_quali[
                    df_quali['ID_Busca'].str.contains(id_busca_limpo, case=False, na=False)
                ]
                
                if registros.empty:
                    st.error(f"❌ Nenhuma APA encontrada com ID: {id_apa_busca}")
                elif len(registros) > 1:
                    st.warning(f"⚠️ Múltiplas APAs encontradas. Usando a primeira.")
                    apa_encontrada = registros.iloc[0]
                else:
                    apa_encontrada = registros.iloc[0]
                    st.success(f"✅ APA encontrada!")
            
            except Exception as e:
                st.error(f"Erro ao buscar: {str(e)[:100]}")
    
    # ════════════════════════════════════════════════════════════════
    # SEÇÃO 2: EXIBIR METADADOS DA APA
    # ════════════════════════════════════════════════════════════════
    
    if apa_encontrada is not None:
        
        st.markdown("---")
        st.markdown("#### Etapa 2: Revisar Metadados")
        
        # Metadados em cards
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        
        with col_m1:
            st.markdown(f"""
            <div class='info-card' style='padding: 10px;'>
            <strong style='color: #FFD700; font-size: 0.85rem;'>DATA</strong><br>
            <span style='font-size: 0.9rem;'>{limpar_valor(apa_encontrada.get('Data da ocorrência'))}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col_m2:
            st.markdown(f"""
            <div class='info-card' style='padding: 10px;'>
            <strong style='color: #FFD700; font-size: 0.85rem;'>TIPOLOGIA</strong><br>
            <span style='font-size: 0.9rem;'>{limpar_valor(apa_encontrada.get('Tipologia'))}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col_m3:
            st.markdown(f"""
            <div class='info-card' style='padding: 10px;'>
            <strong style='color: #FFD700; font-size: 0.85rem;'>NEGOCIADOR</strong><br>
            <span style='font-size: 0.9rem;'>{limpar_valor(apa_encontrada.get('Negociador Principal'))}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col_m4:
            st.markdown(f"""
            <div class='info-card' style='padding: 10px;'>
            <strong style='color: #FFD700; font-size: 0.85rem;'>MODALIDADE</strong><br>
            <span style='font-size: 0.9rem;'>{limpar_valor(apa_encontrada.get('Modalidade do incidente'))}</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # ════════════════════════════════════════════════════════════════
        # SEÇÃO 3: VALIDAÇÕES AUTOMÁTICAS
        # ════════════════════════════════════════════════════════════════
        
        st.markdown("#### ✔️ Etapa 3: Validações Automáticas")
        
        validacoes = validar_apa(apa_encontrada)
        
        # Mostrar erros
        if validacoes["erros"]:
            for erro in validacoes["erros"]:
                st.error(erro)
        
        # Mostrar avisos
        if validacoes["avisos"]:
            for aviso in validacoes["avisos"]:
                st.warning(aviso)
        
        # Status geral
        if validacoes["ok"]:
            st.success("✅ Todas as validações obrigatórias passaram!")
        else:
            st.error("❌ Há erros que precisam ser corrigidos antes de validar.")
        
        st.markdown("---")
        
        # ════════════════════════════════════════════════════════════════
        # SEÇÃO 4: FORMULÁRIO DE ENRIQUECIMENTO
        # ════════════════════════════════════════════════════════════════
        
        st.markdown("#### Etapa 4: Enriquecimento & Observações")
        
        with st.form("form_validacao_apa", border=True):
            
            # --- PERCEPÇÃO (escala Likert) ---
            st.markdown("**Percepção do Causador (Se não preenchido na ocorrência)**")
            
            col_per1, col_per2 = st.columns(2)
            
            with col_per1:
                agr_chegada = st.selectbox(
                    "Agressividade na Chegada",
                    ["❓ Não observado", "Não agressivo", "Neutro", 
                     "Parcialmente agressivo", "Agressivo", "Muito agressivo"],
                    key="form_agr_chegada"
                )
            
            with col_per2:
                rec_chegada = st.selectbox(
                    "Receptividade na Chegada",
                    ["❓ Não observado", "Não receptivo", "Neutro",
                     "Parcialmente receptivo", "Receptivo", "Muito receptivo"],
                    key="form_rec_chegada"
                )
            
            col_per3, col_per4 = st.columns(2)
            
            with col_per3:
                agr_encerramento = st.selectbox(
                    "Agressividade no Encerramento",
                    ["❓ Não observado", "Não agressivo", "Neutro",
                     "Parcialmente agressivo", "Agressivo", "Muito agressivo"],
                    key="form_agr_enc"
                )
            
            with col_per4:
                rec_encerramento = st.selectbox(
                    "Receptividade no Encerramento",
                    ["❓ Não observado", "Não receptivo", "Neutro",
                     "Parcialmente receptivo", "Receptivo", "Muito receptivo"],
                    key="form_rec_enc"
                )
            
            st.markdown("---")
            
            # --- QUALIDADE DA OCORRÊNCIA ---
            st.markdown("**Qualidade & Integridade**")
            
            col_qual1, col_qual2, col_qual3 = st.columns(3)
            
            with col_qual1:
                duplicata = st.checkbox(
                    "Marcar como Duplicata?",
                    value=False,
                    key="form_duplicata"
                )
            
            with col_qual2:
                transcrição_completa = st.checkbox(
                    "Transcrição Completa?",
                    value=True,
                    key="form_trans_completa"
                )
            
            with col_qual3:
                anomalia = st.checkbox(
                    "Há Anomalia/Flag?",
                    value=False,
                    key="form_anomalia"
                )
            
            st.markdown("---")
            
            # --- OBSERVAÇÕES ---
            st.markdown("**Notas e Observações**")
            
            observacoes = st.text_area(
                "Observações do Validador",
                placeholder="""Escreva observações relevantes:
- Pontos de melhoria
- Padrões observados
- Contexto adicional
- Anomalias encontradas
- Recomendações para treinamento""",
                height=120,
                key="form_observacoes"
            )
            
            st.markdown("---")
            
            # --- IDENTIFICAÇÃO DO VALIDADOR ---
            col_valid1, col_valid2 = st.columns(2)
            
            with col_valid1:
                validador_nome = st.text_input(
                    "Seu Nome/Identificação",
                    placeholder="Ex: Cap PM Pavão",
                    key="form_validador"
                )
            
            with col_valid2:
                validador_funcao = st.selectbox(
                    "Sua Função",
                    ["Supervisor", "Instrutor", "Analista", "Auditor", "Outro"],
                    key="form_funcao"
                )
            
            st.markdown("---")
            
            # --- SUBMIT ---
            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
            
            with col_btn1:
                submitted = st.form_submit_button(
                    "✅ Salvar Validações",
                    use_container_width=True,
                    type="primary"
                )
            
            with col_btn2:
                preview = st.form_submit_button(
                    "Pré-visualizar",
                    use_container_width=True
                )
            
            with col_btn3:
                cancelar = st.form_submit_button(
                    "❌ Cancelar",
                    use_container_width=True
                )
            
            # ─────────────────────────────────────────────
            # PROCESSAR SUBMIT
            # ─────────────────────────────────────────────
            
            if preview:
                st.markdown("#### Pré-visualização dos Dados")
                
                preview_data = {
                    "APA ID": id_apa_busca,
                    "Agressividade (Chegada)": agr_chegada,
                    "Receptividade (Chegada)": rec_chegada,
                    "Agressividade (Encerramento)": agr_encerramento,
                    "Receptividade (Encerramento)": rec_encerramento,
                    "É Duplicata": duplicata,
                    "Transcrição Completa": transcrição_completa,
                    "Há Anomalia": anomalia,
                    "Observações": observacoes[:100] + "..." if len(observacoes) > 100 else observacoes,
                    "Validador": validador_nome,
                    "Função": validador_funcao,
                    "Data/Hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                }
                
                st.json(preview_data)
            
            if submitted:
                
                # Validar campos obrigatórios
                if not validador_nome:
                    st.error("❌ Nome do validador é obrigatório")
                elif duplicata and not observacoes:
                    st.error("❌ Se marcar como duplicata, explique o motivo nas observações")
                else:
                    
                    with st.spinner("💾 Salvando validações no Airtable..."):
                        try:
                            # Preparar payload
                            payload_validacao = {
                                "Percepção Principal Agressividade Chegada": agr_chegada,
                                "Percepção Principal Receptividade Chegada": rec_chegada,
                                "Percepção Principal Agressividade Encerramento": agr_encerramento,
                                "Percepção Principal Receptividade Encerramento": rec_encerramento,
                                "É Duplicata": "Sim" if duplicata else "Não",
                                "Transcrição Completa": "Sim" if transcrição_completa else "Não",
                                "Tem Anomalia": "Sim" if anomalia else "Não",
                                "Observações Validador": observacoes,
                                "Validado Por": validador_nome,
                                "Função Validador": validador_funcao,
                                "Data Validação": datetime.now().isoformat(),
                                "Status Validação": "Validado"
                            }
                            
                            # Atualizar Airtable (você vai implementar isso no airtable_link)
                            sucesso = airtable_link.atualizar_apa_validacao(
                                id_apa=id_apa_busca,
                                payload=payload_validacao
                            )
                            
                            if sucesso:
                                st.success(f"""
                                ✅ **APA {id_apa_busca} validada com sucesso!**
                                
                                - ✓ Percepção registrada
                                - ✓ Observações salvas
                                - ✓ Rastreabilidade: {validador_nome} ({validador_funcao})
                                """)
                                
                                # Limpar session state
                                for key in st.session_state:
                                    if key.startswith("form_"):
                                        del st.session_state[key]
                                
                                st.balloons()
                            
                            else:
                                st.error("❌ Erro ao salvar no Airtable. Verifique a conexão.")
                        
                        except Exception as e:
                            st.error(f"❌ Erro: {str(e)[:150]}")
            
            if cancelar:
                st.info("❌ Operação cancelada")
    
    # ════════════════════════════════════════════════════════════════
    # RODAPÉ
    # ════════════════════════════════════════════════════════════════
    
    st.markdown("---")
    st.markdown("""
    <div style='padding:15px; background:rgba(255,215,0,0.03); border-radius:8px; border-left:3px solid #FFD700;'>
    <p style='font-size:0.85rem; color:#aaa; margin:0; line-height:1.6;'>
    <strong>ℹ️ Como usar este formulário:</strong><br>
    1. Busque uma APA recém-capturada pelo Airtable Form<br>
    2. Revise os metadados automaticamente extraídos<br>
    3. Valide os dados contra regras de negócio<br>
    4. Enriqueça com percepção, observações e flags<br>
    5. Salve para que a IA possa gerar análises<br><br>
    <strong>Resultado:</strong> Dados validados, rastreáveis e prontos para análise estatística.
    </p>
    </div>
    """, unsafe_allow_html=True)