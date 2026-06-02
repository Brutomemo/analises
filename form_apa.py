# ============================================================
# form_apa.py
# FORMULÁRIO COMPLETO - TODOS OS CAMPOS DO AIRTABLE
# GATE/PMESP - Delta Negociação
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime
import airtable_link


def limpar_valor(val):
    """Limpa valores vindos do Airtable"""
    if isinstance(val, list):
        return val[0] if len(val) > 0 else "N/D"
    return str(val) if pd.notna(val) else "N/D"


# ════════════════════════════════════════════════════════════
# OPÇÕES EXATAS DO AIRTABLE
# ════════════════════════════════════════════════════════════

MODALIDADES = [
    "Ocorrência com refém",
    "Pessoa armada com propósito suicida",
    "Pessoa com propósito suicida com terceiro em risco",
    "Pessoa embarricada",
    "Pessoa em surto (embarricada ou não)",
    "Criminoso com propósito suicida",
    "Criminoso embarricado",
    "Criminoso homiziado"
]

TIPOLOGIAS = [
    "Emocionalmente perturbado",
    "Mentalmente perturbado",
    "Criminoso",
    "Terrorista"
]

FORMAS_TRANSICAO = [
    "Controlada",
    "Emergencial",
    "Não houve - Primeiro Interventor ausente"
]

RESOLUCOES = [
    "Negociação Real",
    "Negociação Tática",
    "Intervenção"
]

NEGOCIADORES = [
    "Cap PM Pavão",
    "Ten PM Cupka",
    "Sub Ten PM Silva",
    "Sgt PM Vanessa",
    "Sgt PM Penna",
    "Sgt PM Cabral",
    "Sgt PM Ketlin",
    "Cb PM Edson",
    "Cb PM Bastos",
    "Cb PM Gabriel",
    "Cb PM Helena",
    "Cb PM Luiz",
    "Cb PM Gustavo",
    "Sd PM Stefany",
    "Sd PM Santim",
    "Sd PM Lima",
    "Sd PM Krapp",
    "Sd PM Granso",
    "Sd PM Samara"
]

SAUDE_MENTAL = [
    "Sub Ten PM Silva",
    "Cb PM Edson",
    "Sd PM Krapp"
]

UNIFORMES = [
    "Combat Shirt azul escura",
    "Camiseta Polo azul claro",
    "Paisano"
]

SEXOS = ["Homem", "Mulher"]

PERCEPCOES = [
    "Não observado",
    "Não agressivo",
    "Neutro",
    "Parcialmente agressivo",
    "Agressivo",
    "Muito agressivo"
]


def render_form_apa(df_quali, df_tec):
    """
    FORMULÁRIO COMPLETO COM TODOS OS CAMPOS EXATOS DO AIRTABLE
    7 Abas principais com todos os 40+ campos mapeados
    """
    
    st.markdown("### ✔️Entrada de Dados-APA")
    st.markdown("""
    <p style='color: #aaa; font-size: 0.9rem; margin-bottom: 1rem;'>
    Preencha todos os campos com os dados da ocorrência. Campos com * são obrigatórios.
    </p>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ════════════════════════════════════════════════════════════
    # 7 ABAS PRINCIPAIS
    # ════════════════════════════════════════════════════════════
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "✔️ Metadados",
        "✔️ Equipe",
        "✔️ Chegada",
        "✔️ Encerramento",
        "✔️ Transcrições",
        "✔️ Funções",
        "✔️ Info Adicionais"
    ])
    
    # ─────────────────────────────────────────────────────────────
    # ABA 1: METADADOS
    # ─────────────────────────────────────────────────────────────
    
    with tab1:
        st.markdown("### Informações Básicas da Ocorrência")
        
        col1, col2 = st.columns(2)
        with col1:
            data_oca = st.date_input(
                "Data da Ocorrência *",
                key="f_data"
            )
        with col2:
            modalidade = st.selectbox(
                "Modalidade do Incidente *",
                [""] + MODALIDADES,
                key="f_modalidade"
            )
        
        col3, col4 = st.columns(2)
        with col3:
            tipologia = st.selectbox(
                "Tipologia *",
                [""] + TIPOLOGIAS,
                key="f_tipologia"
            )
        with col4:
            forma_transicao = st.selectbox(
                "Forma de Transição",
                [""] + FORMAS_TRANSICAO,
                key="f_forma_transicao"
            )
        
        st.markdown("**Motivação**")
        motivacao = st.text_area(
            "Descreva a motivação do incidente",
            placeholder="...",
            height=100,
            key="f_motivacao"
        )
        
        resolucao = st.selectbox(
            "Resolução *",
            [""] + RESOLUCOES,
            key="f_resolucao"
        )
    
    # ─────────────────────────────────────────────────────────────
    # ABA 2: EQUIPE
    # ─────────────────────────────────────────────────────────────
    
    with tab2:
        st.markdown("## Negociadores")
        
        col1, col2 = st.columns(2)
        with col1:
            neg_principal = st.selectbox(
                "Negociador Principal *",
                [""] + NEGOCIADORES,
                key="f_neg_principal"
            )
        with col2:
            neg_secundario = st.selectbox(
                "Negociador Secundário",
                [""] + NEGOCIADORES,
                key="f_neg_secundario"
            )
        
        col3, col4 = st.columns(2)
        with col3:
            neg_anotador = st.selectbox(
                "Negociador Anotador",
                [""] + NEGOCIADORES,
                key="f_neg_anotador"
            )
        with col4:
            neg_lider = st.selectbox(
                "Negociador Líder",
                [""] + NEGOCIADORES,
                key="f_neg_lider"
            )
        
        col5, col6 = st.columns(2)
        with col5:
            aux_info = st.selectbox(
                "Negociador Auxiliar de Informações",
                [""] + NEGOCIADORES,
                key="f_aux_info"
            )
        with col6:
            aux_log = st.selectbox(
                "Negociador Auxiliar de Logística",
                [""] + NEGOCIADORES,
                key="f_aux_log"
            )
        
        prof_saude = st.selectbox(
            "Profissional de Saúde Mental",
            [""] + SAUDE_MENTAL,
            key="f_prof_saude"
        )
    
    # ─────────────────────────────────────────────────────────────
    # ABA 3: PERCEPÇÃO NA CHEGADA
    # ─────────────────────────────────────────────────────────────
    
    with tab3:
        st.markdown("## Percepções do Negociador Principal")
        col1, col2 = st.columns(2)
        with col1:
            agr_principal_chegada = st.selectbox(
                "12 - Agressividade",
                PERCEPCOES,
                key="f_agr_principal_chegada"
            )
        with col2:
            rec_principal_chegada = st.selectbox(
                "13 - Receptividade",
                PERCEPCOES,
                key="f_rec_principal_chegada"
            )
        
        st.markdown("## Percepções do Negociador Secundário")
        col3, col4 = st.columns(2)
        with col3:
            agr_secundario_chegada = st.selectbox(
                "12 - Agressividade",
                PERCEPCOES,
                key="f_agr_secundario_chegada"
            )
        with col4:
            rec_secundario_chegada = st.selectbox(
                "13 - Receptividade",
                PERCEPCOES,
                key="f_rec_secundario_chegada"
            )
        
        st.markdown("## Percepções do Negociador Líder")
        col5, col6 = st.columns(2)
        with col5:
            agr_lider_chegada = st.selectbox(
                "12 - Agressividade",
                PERCEPCOES,
                key="f_agr_lider_chegada"
            )
        with col6:
            rec_lider_chegada = st.selectbox(
                "13 - Receptividade",
                PERCEPCOES,
                key="f_rec_lider_chegada"
            )
    
    # ─────────────────────────────────────────────────────────────
    # ABA 4: PERCEPÇÃO NO ENCERRAMENTO
    # ─────────────────────────────────────────────────────────────
    
    with tab4:
        st.markdown("## Percepções do Negociador Principal")
        col1, col2 = st.columns(2)
        with col1:
            agr_principal_enc = st.selectbox(
                "24 - Agressividade",
                PERCEPCOES,
                key="f_agr_principal_enc"
            )
        with col2:
            rec_principal_enc = st.selectbox(
                "25 - Receptividade",
                PERCEPCOES,
                key="f_rec_principal_enc"
            )
        
        st.markdown("## Percepções do Negociador Secundário")
        col3, col4 = st.columns(2)
        with col3:
            agr_secundario_enc = st.selectbox(
                "24 - Agressividade",
                PERCEPCOES,
                key="f_agr_secundario_enc"
            )
        with col4:
            rec_secundario_enc = st.selectbox(
                "25 - Receptividade",
                PERCEPCOES,
                key="f_rec_secundario_enc"
            )
        
        st.markdown("## Percepções do Negociador Líder")
        col5, col6 = st.columns(2)
        with col5:
            agr_lider_enc = st.selectbox(
                "24 - Agressividade",
                PERCEPCOES,
                key="f_agr_lider_enc"
            )
        with col6:
            rec_lider_enc = st.selectbox(
                "25 - Receptividade",
                PERCEPCOES,
                key="f_rec_lider_enc"
            )
    
    # ─────────────────────────────────────────────────────────────
    # ABA 5: TRANSCRIÇÕES
    # ─────────────────────────────────────────────────────────────
    
    with tab5:
        st.markdown("## Transcrições da Ocorrência")
        
        st.markdown("**TRANSCRIÇÃO DO CAUSADOR**")
        trans_causador = st.text_area(
            "Digitação da fala do causador",
            placeholder="...",
            height=100,
            key="f_trans_causador"
        )
        
        st.markdown("**TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL**")
        trans_principal = st.text_area(
            "Digitação da fala do negociador principal",
            placeholder="...",
            height=100,
            key="f_trans_principal"
        )
        
        st.markdown("**TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO**")
        trans_secundario = st.text_area(
            "Digitação da fala do negociador secundário (opcional)",
            placeholder="...",
            height=100,
            key="f_trans_secundario"
        )
        
        st.markdown("**TABELA DE FREQUÊNCIAS DAS TÉCNICAS**")
        tabela_tecnicas = st.text_area(
            "Técnicas aplicadas e suas frequências",
            placeholder="Cole a tabela aqui...",
            height=100,
            key="f_tabela_tecnicas"
        )
    
    # ─────────────────────────────────────────────────────────────
    # ABA 6: FUNÇÕES (20 CAMPOS DETALHADOS)
    # ─────────────────────────────────────────────────────────────
    
    with tab6:
        st.markdown("## FUNÇÕES: NEGOCIADOR PRINCIPAL")
        col1, col2 = st.columns(2)
        with col1:
            func_np = st.text_area("Funções", placeholder="...", height=60, key="f_func_np")
        with col2:
            func_np_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="f_func_np_problema")
        
        col3, col4 = st.columns(2)
        with col3:
            func_np_acoes = st.text_area("Ações Corretivas Adotadas", placeholder="...", height=60, key="f_func_np_acoes")
        with col4:
            func_np_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="f_func_np_praticas")
        
        st.markdown("---")
        st.markdown("## FUNÇÕES: NEGOCIADOR SECUNDÁRIO")
        col5, col6 = st.columns(2)
        with col5:
            func_ns = st.text_area("Funções", placeholder="...", height=60, key="f_func_ns")
        with col6:
            func_ns_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="f_func_ns_problema")
        
        col7, col8 = st.columns(2)
        with col7:
            func_ns_acoes = st.text_area("Ações Corretivas Adotadas", placeholder="...", height=60, key="f_func_ns_acoes")
        with col8:
            func_ns_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="f_func_ns_praticas")
        
        st.markdown("---")
        st.markdown("## FUNÇÕES: NEGOCIADOR ANOTADOR")
        col9, col10 = st.columns(2)
        with col9:
            func_na = st.text_area("Funções", placeholder="...", height=60, key="f_func_na")
        with col10:
            func_na_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="f_func_na_problema")
        
        col11, col12 = st.columns(2)
        with col11:
            func_na_acoes = st.text_area("Ações Corretivas Adotadas", placeholder="...", height=60, key="f_func_na_acoes")
        with col12:
            func_na_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="f_func_na_praticas")
        
        st.markdown("---")
        st.markdown("## FUNÇÕES: NEGOCIADOR LÍDER")
        col13, col14 = st.columns(2)
        with col13:
            func_nl = st.text_area("Funções", placeholder="...", height=60, key="f_func_nl")
        with col14:
            func_nl_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="f_func_nl_problema")
        
        col15, col16 = st.columns(2)
        with col15:
            func_nl_acoes = st.text_area("Ações Corretivas Adotadas", placeholder="...", height=60, key="f_func_nl_acoes")
        with col16:
            func_nl_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="f_func_nl_praticas")
        
        st.markdown("---")
        st.markdown("## FUNÇÕES: AUXILIAR DE LOGÍSTICA")
        col17, col18 = st.columns(2)
        with col17:
            func_al = st.text_area("Funções", placeholder="...", height=60, key="f_func_al")
        with col18:
            func_al_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="f_func_al_problema")
        
        col19, col20 = st.columns(2)
        with col19:
            func_al_acoes = st.text_area("Ações Corretivas", placeholder="...", height=60, key="f_func_al_acoes")
        with col20:
            func_al_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="f_func_al_praticas")
        
        st.markdown("---")
        st.markdown("## FUNÇÕES: AUXILIAR DE INFORMAÇÕES")
        col21, col22 = st.columns(2)
        with col21:
            func_ai = st.text_area("Funções", placeholder="...", height=60, key="f_func_ai")
        with col22:
            func_ai_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="f_func_ai_problema")
        
        col23, col24 = st.columns(2)
        with col23:
            func_ai_acoes = st.text_area("Ações Corretivas", placeholder="...", height=60, key="f_func_ai_acoes")
        with col24:
            func_ai_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="f_func_ai_praticas")
        
        st.markdown("---")
        st.markdown("## FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL")
        col25, col26 = st.columns(2)
        with col25:
            func_psm = st.text_area("Funções", placeholder="...", height=60, key="f_func_psm")
        with col26:
            func_psm_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="f_func_psm_problema")
        
        col27, col28 = st.columns(2)
        with col27:
            func_psm_acoes = st.text_area("Ações Corretivas Adotadas", placeholder="...", height=60, key="f_func_psm_acoes")
        with col28:
            func_psm_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="f_func_psm_praticas")
    
    # ─────────────────────────────────────────────────────────────
    # ABA 7: INFORMAÇÕES ADICIONAIS
    # ─────────────────────────────────────────────────────────────
    
    with tab7:
        st.markdown("## Tempos")
        col1, col2 = st.columns(2)
        with col1:
            tempo_real = st.text_input(
                "Tempo de Negociação Real (HH:MM)",
                placeholder="00:00",
                key="f_tempo_real"
            )
        with col2:
            tempo_tatica = st.text_input(
                "Tempo de Negociação Tática (HH:MM)",
                placeholder="00:00",
                key="f_tempo_tatica"
            )
        
        st.markdown("## Características")
        col3, col4 = st.columns(2)
        with col3:
            uniforme = st.selectbox(
                "Uniforme Usado",
                UNIFORMES,
                key="f_uniforme"
            )
        with col4:
            sexo = st.selectbox(
                "Sexo do Causador",
                SEXOS,
                key="f_sexo"
            )
        
        st.markdown("## Validação")
        validador_nome = st.text_input(
            "Seu Nome/Identificação *",
            placeholder="Ex: Cap PM Pavão",
            key="f_validador"
        )
    
    # ════════════════════════════════════════════════════════════
    # BOTÕES DE AÇÃO
    # ════════════════════════════════════════════════════════════
    
    st.markdown("---")
    col_save, col_preview, col_clear = st.columns(3)
    
    with col_save:
        if st.button("✅ REGISTRAR APA", use_container_width=True, type="secondary", key="btn_criar_final"):
            
            # Validações obrigatórias
            erros = []
            if not data_oca:
                erros.append("Data obrigatória")
            if not modalidade:
                erros.append("Modalidade obrigatória")
            if not tipologia:
                erros.append("Tipologia obrigatória")
            if not neg_principal:
                erros.append("Negociador Principal obrigatório")
            if not resolucao:
                erros.append("Resolução obrigatória")
            if len(str(trans_causador).split()) < 10:
                erros.append("Transcrição Causador deve ter no mínimo 10 palavras")
            if len(str(trans_principal).split()) < 10:
                erros.append("Transcrição Principal deve ter no mínimo 10 palavras")
            if not validador_nome:
                erros.append("Seu Nome obrigatório")
            
            if erros:
                st.error("### ❌ Erros na validação:")
                for erro in erros:
                    st.error(f"• {erro}")
            else:
                with st.spinner("💾 Criando novo registro no Airtable..."):
                    try:
                        # Preparar payload com TODOS os campos EXATOS do Airtable
                        payload = {
                            "Data da ocorrência": data_oca.isoformat(),
                            "Modalidade do incidente": modalidade,
                            "Tipologia": tipologia,
                            "Forma de Transição": forma_transicao,
                            "Resolução": resolucao,
                            "Motivação": motivacao,
                            "Negociador Principal": neg_principal,
                            "Negociador Secundário": neg_secundario,
                            "Negociador Anotador": neg_anotador,
                            "Negociador Líder": neg_lider,
                            "Negociador Auxiliar de Informações": aux_info,
                            "Negociador Auxiliar de Logística": aux_log,
                            "Profissional de Saúde Mental": prof_saude,
                            
                            # Percepção Chegada
                            "12 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A AGRESSIVIDADE DO CAUSADOR NA CHEGADA À OCORRÊNCIA": agr_principal_chegada,
                            "12 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A AGRESSIVIDADE DO CAUSADOR NA CHEGADA À OCORRÊNCIA": agr_secundario_chegada,
                            "12 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A AGRESSIVIDADE DO CAUSADOR NA CHEGADA À OCORRÊNCIA": agr_lider_chegada,
                            "13 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A RECEPTIVIDADE DO CAUSADOR NA CHEGADA À OCORRÊNCIA": rec_principal_chegada,
                            "13 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A RECEPTIVIDADE DO CAUSADOR NA CHEGADA À OCORRÊNCIA": rec_secundario_chegada,
                            "13 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A RECEPTIVIDADE DO CAUSADOR NA CHEGADA À OCORRÊNCIA": rec_lider_chegada,
                            
                            # Percepção Encerramento
                            "24 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A AGRESSIVIDADE DO CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": agr_principal_enc,
                            "24 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A AGRESSIVIDADE DO CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": agr_secundario_enc,
                            "24 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A AGRESSIVIDADE DO CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": agr_lider_enc,
                            "25 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A RECEPTIVIDADE DO CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": rec_principal_enc,
                            "25 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A RECEPTIVIDADE DO CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": rec_secundario_enc,
                            "25 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A RECEPTIVIDADE DO CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": rec_lider_enc,
                            
                            # Transcrições
                            "TRANSCRIÇÃO DO CAUSADOR": trans_causador,
                            "TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL": trans_principal,
                            "TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO": trans_secundario,
                            "TABELA DE FREQUÊNCIAS DAS TÉCNICAS": tabela_tecnicas,
                            
                            # Funções - Principal
                            "FUNÇÕES: NEGOCIADOR PRINCIPAL": func_np,
                            "FUNÇÕES: NEGOCIADOR PRINCIPAL - PROBLEMA IDENTIFICADO": func_np_problema,
                            "FUNÇÕES: NEGOCIADOR PRINCIPAL - AÇÕES CORRETIVAS ADOTADAS": func_np_acoes,
                            "FUNÇÕES: NEGOCIADOR PRINCIPAL - PRÁTICAS PROMISSORAS": func_np_praticas,
                            
                            # Funções - Secundário
                            "FUNÇÕES: NEGOCIADOR SECUNDÁRIO": func_ns,
                            "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PROBLEMA IDENTIFICADO": func_ns_problema,
                            "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - AÇÕES CORRETIVAS ADOTADAS": func_ns_acoes,
                            "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PRÁTICAS PROMISSORAS": func_ns_praticas,
                            
                            # Funções - Anotador
                            "FUNÇÕES: NEGOCIADOR ANOTADOR": func_na,
                            "FUNÇÕES: NEGOCIADOR ANOTADOR - PROBLEMA IDENTIFICADO": func_na_problema,
                            "FUNÇÕES: NEGOCIADOR ANOTADOR - AÇÕES CORRETIVAS ADOTADAS": func_na_acoes,
                            "FUNÇÕES: NEGOCIADOR ANOTADOR - PRÁTICAS PROMISSORAS": func_na_praticas,
                            
                            # Funções - Líder
                            "FUNÇÕES: NEGOCIADOR LÍDER": func_nl,
                            "FUNÇÕES: NEGOCIADOR LÍDER - PROBLEMA IDENTIFICADO": func_nl_problema,
                            "FUNÇÕES: NEGOCIADOR LÍDER - AÇÕES CORRETIVAS ADOTADAS": func_nl_acoes,
                            "FUNÇÕES: NEGOCIADOR LÍDER - PRÁTICAS PROMISSORAS": func_nl_praticas,
                            
                            # Funções - Auxiliar Logística
                            "FUNÇÕES: NEGOCIADOR AUXILIAR DE LOGÍSTICA": func_al,
                            "FUNÇÕES: AUXILIAR DE LOGÍSTICA - PROBLEMA IDENTIFICADO": func_al_problema,
                            "FUNÇÕES: AUXILIAR DE LOGÍSTICA - AÇÕES CORRETIVAS": func_al_acoes,
                            "FUNÇÕES: AUXILIAR DE LOGÍSTICA - PRÁTICAS PROMISSORAS": func_al_praticas,
                            
                            # Funções - Auxiliar Informações
                            "FUNÇÕES: NEGOCIADOR AUXILIAR DE INFORMAÇÕES": func_ai,
                            "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PROBLEMA IDENTIFICADO": func_ai_problema,
                            "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - AÇÕES CORRETIVAS": func_ai_acoes,
                            "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PRÁTICAS PROMISSORAS": func_ai_praticas,
                            
                            # Funções - Saúde Mental
                            "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL": func_psm,
                            "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PROBLEMA IDENTIFICADO": func_psm_problema,
                            "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - AÇÕES CORRETIVAS ADOTADAS": func_psm_acoes,
                            "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PRÁTICAS PROMISSORAS": func_psm_praticas,
                            
                            # Info Adicionais
                            "Tempo de Negociação Real": tempo_real,
                            "Tempo de Negociação Tática": tempo_tatica,
                            "Uniforme Usado": uniforme,
                            "Sexo do Causador": sexo,
                            
                            # Metadados
                            "Criado Por": validador_nome,
                            "Data Criação": datetime.now().isoformat(),
                            "Status": "Novo"
                        }
                        
                        # Criar registro
                        sucesso = airtable_link.criar_nova_apa(payload)
                        
                        if sucesso:
                            st.success(f"""
                            ✅ **APA CRIADA COM SUCESSO!**
                            
                            **Resumo:**
                            • Data: {data_oca}
                            • Negociador Principal: {neg_principal}
                            • Tipologia: {tipologia}
                            • Modalidade: {modalidade}
                            • Resolução: {resolucao}
                            • Criado por: {validador_nome}
                            • Timestamp: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
                            """)
                            st.balloons()
                            
                            # Limpar formulário
                            for key in list(st.session_state.keys()):
                                if key.startswith("f_"):
                                    del st.session_state[key]
                        else:
                            st.error("❌ Erro ao criar APA no Airtable")
                    
                    except Exception as e:
                        st.error(f"❌ Erro: {str(e)[:200]}")
    
    with col_preview:
        if st.button("✔️Pré-visualizar dados inseridos", use_container_width=True, key="btn_preview_final"):
            st.info("**Pré-visualização dos dados principais:**")
            st.json({
                "Data": str(data_oca),
                "Negociador Principal": neg_principal,
                "Tipologia": tipologia,
                "Modalidade": modalidade,
                "Resolução": resolucao,
                "Uniforme": uniforme,
                "Validador": validador_nome,
                "Transcrições": {
                    "Causador": trans_causador[:80] + "...",
                    "Principal": trans_principal[:80] + "..."
                }
            })
    
    with col_clear:
        if st.button("❌ Limpar Tudo", use_container_width=True, key="btn_clear_final"):
            for key in list(st.session_state.keys()):
                if key.startswith("f_"):
                    del st.session_state[key]
            st.info("✨ Formulário limpo!")