# ============================================================
# form_apa_v2.py - VERSÃO MELHORADA
# ENTRADA DE DADOS COMPLETA - 3 ABAS INDEPENDENTES
# Aba 1: Criar Nova APA
# Aba 2: Upload Técnicas (INDEPENDENTE)
# Aba 3: Visualizar & Editar (COM FORMULÁRIO DE EDIÇÃO)
# ============================================================

import streamlit as st
import pandas as pd
import io
from datetime import datetime
import airtable_link


# ════════════════════════════════════════════════════════════
# OPÇÕES (EXATAS DO AIRTABLE)
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

PERCEPCOES_AGRESSIVIDADE = [
    "Não observado",
    "Não agressivo",
    "Neutro",
    "Parcialmente agressivo",
    "Agressivo",
    "Muito agressivo"
]

PERCEPCOES_RECEPTIVIDADE = [
    "Não observado",
    "Não receptivo",
    "Neutro",
    "Parcialmente receptivo",
    "Receptivo",
    "Muito receptivo"
]

PERCEPCOES = PERCEPCOES_AGRESSIVIDADE


def validar_excel_tecnicas(df):
    """Valida Excel de técnicas"""
    df.columns = df.columns.str.strip()
    
    colunas_esperadas = {
        'tecnicas': ['TÉCNICAS', 'A_TÉCNICAS'],
        'atitude': ['ATITUDE DO CAUSADOR'],
        'trecho': ['TRECHO DA TRANSCRIÇÃO', 'TRECHO DA TRANSCRICAO']
    }
    
    colunas_encontradas = {}
    erros = []
    
    for chave, nomes_possiveis in colunas_esperadas.items():
        encontrado = False
        for col in df.columns:
            if col.upper() in [n.upper() for n in nomes_possiveis]:
                colunas_encontradas[chave] = col
                encontrado = True
                break
        
        if not encontrado:
            erros.append(f"❌ Coluna faltando: {nomes_possiveis[0]}")
    
    if erros:
        return False, erros, None
    
    # Validar ATITUDE
    col_atitude = colunas_encontradas['atitude']
    atitudes_invalidas = df[~df[col_atitude].isin([-1, 0, 1])].index.tolist()
    
    validacoes = []
    if atitudes_invalidas:
        validacoes.append(f"⚠️ Linhas com ATITUDE inválida: {atitudes_invalidas}")
    
    return True, validacoes, colunas_encontradas


def render(df_quali, df_tec):
    """
    Interface principal de Entrada de Dados com 3 abas:
    1. Criar Nova APA
    2. Upload de Técnicas (INDEPENDENTE)
    3. Visualizar & Editar (COM FORMULÁRIO)
    """
    
    st.markdown("### 📋 Entrada de Dados — GATE/PMESP")
    st.markdown("""
    <p style='color: #aaa; font-size: 0.9rem;'>
    Crie novas APAs, faça upload de técnicas e edite dados existentes.
    </p>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ════════════════════════════════════════════════════════════
    # 3 ABAS PRINCIPAIS
    # ════════════════════════════════════════════════════════════
    
    tab1, tab2, tab3 = st.tabs([
        "➕ Criar Nova APA",
        "📊 Upload de Técnicas",
        "✏️ Visualizar & Editar"
    ])
    
    # ─────────────────────────────────────────────────────────────
    # ABA 1: CRIAR NOVA APA
    # ─────────────────────────────────────────────────────────────
    
    with tab1:
        st.markdown("### Preencha os Dados da Nova APA")
        
        # 7 ABAS DO FORMULÁRIO
        tab_meta, tab_equipe, tab_chegada, tab_enc, tab_trans, tab_func, tab_obs = st.tabs([
            "✔️ Metadados",
            "✔️ Equipe",
            "✔️ Chegada",
            "✔️ Encerramento",
            "✔️ Transcrições",
            "✔️ Funções",
            "✔️ Info Adicionais"
        ])
        
        # ─── METADADOS ───
        with tab_meta:
            col1, col2 = st.columns(2)
            with col1:
                data_oca = st.date_input("Data da Ocorrência *", key="c_data")
            with col2:
                modalidade = st.selectbox("Modalidade do Incidente *", [""] + MODALIDADES, key="c_modalidade")
            
            col3, col4 = st.columns(2)
            with col3:
                tipologia = st.selectbox("Tipologia *", [""] + TIPOLOGIAS, key="c_tipologia")
            with col4:
                forma_transicao = st.selectbox("Forma de Transição", [""] + FORMAS_TRANSICAO, key="c_forma_transicao")
            
            motivacao = st.text_area("Motivação", placeholder="...", height=80, key="c_motivacao")
            resolucao = st.selectbox("Resolução *", [""] + RESOLUCOES, key="c_resolucao")
        
        # ─── EQUIPE ───
        with tab_equipe:
            col1, col2 = st.columns(2)
            with col1:
                neg_principal = st.selectbox("Negociador Principal *", [""] + NEGOCIADORES, key="c_neg_principal")
            with col2:
                neg_secundario = st.selectbox("Negociador Secundário", [""] + NEGOCIADORES, key="c_neg_secundario")
            
            col3, col4 = st.columns(2)
            with col3:
                neg_anotador = st.selectbox("Negociador Anotador", [""] + NEGOCIADORES, key="c_neg_anotador")
            with col4:
                neg_lider = st.selectbox("Negociador Líder", [""] + NEGOCIADORES, key="c_neg_lider")
            
            col5, col6 = st.columns(2)
            with col5:
                aux_info = st.selectbox("Auxiliar de Informações", [""] + NEGOCIADORES, key="c_aux_info")
            with col6:
                aux_log = st.selectbox("Auxiliar de Logística", [""] + NEGOCIADORES, key="c_aux_log")
            
            prof_saude = st.selectbox("Profissional de Saúde Mental", [""] + SAUDE_MENTAL, key="c_prof_saude")
        
        # ─── PERCEPÇÃO CHEGADA ───
        with tab_chegada:
            st.markdown("**Negociador Principal**")
            col1, col2 = st.columns(2)
            with col1:
                agr_principal_chegada = st.selectbox("12 - Agressividade", PERCEPCOES_AGRESSIVIDADE, key="c_agr_principal_chegada")
            with col2:
                rec_principal_chegada = st.selectbox("13 - Receptividade", PERCEPCOES_RECEPTIVIDADE, key="c_rec_principal_chegada")
            
            st.markdown("**Negociador Secundário**")
            col3, col4 = st.columns(2)
            with col3:
                agr_secundario_chegada = st.selectbox("12 - Agressividade", PERCEPCOES_AGRESSIVIDADE, key="c_agr_secundario_chegada")
            with col4:
                rec_secundario_chegada = st.selectbox("13 - Receptividade", PERCEPCOES_RECEPTIVIDADE, key="c_rec_secundario_chegada")
            
            st.markdown("**Negociador Líder**")
            col5, col6 = st.columns(2)
            with col5:
                agr_lider_chegada = st.selectbox("12 - Agressividade", PERCEPCOES_AGRESSIVIDADE, key="c_agr_lider_chegada")
            with col6:
                rec_lider_chegada = st.selectbox("13 - Receptividade", PERCEPCOES_RECEPTIVIDADE, key="c_rec_lider_chegada")
        
        # ─── PERCEPÇÃO ENCERRAMENTO ───
        with tab_enc:
            st.markdown("**Negociador Principal**")
            col1, col2 = st.columns(2)
            with col1:
                agr_principal_enc = st.selectbox("24 - Agressividade", PERCEPCOES_AGRESSIVIDADE, key="c_agr_principal_enc")
            with col2:
                rec_principal_enc = st.selectbox("25 - Receptividade", PERCEPCOES_RECEPTIVIDADE, key="c_rec_principal_enc")
            
            st.markdown("**Negociador Secundário**")
            col3, col4 = st.columns(2)
            with col3:
                agr_secundario_enc = st.selectbox("24 - Agressividade", PERCEPCOES_AGRESSIVIDADE, key="c_agr_secundario_enc")
            with col4:
                rec_secundario_enc = st.selectbox("25 - Receptividade", PERCEPCOES_RECEPTIVIDADE, key="c_rec_secundario_enc")
            
            st.markdown("**Negociador Líder**")
            col5, col6 = st.columns(2)
            with col5:
                agr_lider_enc = st.selectbox("24 - Agressividade", PERCEPCOES_AGRESSIVIDADE, key="c_agr_lider_enc")
            with col6:
                rec_lider_enc = st.selectbox("25 - Receptividade", PERCEPCOES_RECEPTIVIDADE, key="c_rec_lider_enc")
        
        # ─── TRANSCRIÇÕES ───
        with tab_trans:
            trans_causador = st.text_area("Transcrição do Causador", placeholder="...", height=100, key="c_trans_causador")
            trans_principal = st.text_area("Transcrição do Negociador Principal", placeholder="...", height=100, key="c_trans_principal")
            trans_secundario = st.text_area("Transcrição do Negociador Secundário", placeholder="...", height=100, key="c_trans_secundario")
        
        # ─── FUNÇÕES ───
        with tab_func:
            st.markdown("**NEGOCIADOR PRINCIPAL**")
            func_np = st.text_area("Descrição", placeholder="...", height=60, key="c_func_np")
            func_np_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="c_func_np_problema")
            func_np_acoes = st.text_area("Ações Corretivas", placeholder="...", height=60, key="c_func_np_acoes")
            func_np_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="c_func_np_praticas")
            
            st.markdown("**NEGOCIADOR SECUNDÁRIO**")
            func_ns = st.text_area("Descrição", placeholder="...", height=60, key="c_func_ns")
            func_ns_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="c_func_ns_problema")
            func_ns_acoes = st.text_area("Ações Corretivas", placeholder="...", height=60, key="c_func_ns_acoes")
            func_ns_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="c_func_ns_praticas")
            
            st.markdown("**NEGOCIADOR ANOTADOR**")
            func_na = st.text_area("Descrição", placeholder="...", height=60, key="c_func_na")
            func_na_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="c_func_na_problema")
            func_na_acoes = st.text_area("Ações Corretivas", placeholder="...", height=60, key="c_func_na_acoes")
            func_na_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="c_func_na_praticas")
            
            st.markdown("**NEGOCIADOR LÍDER**")
            func_nl = st.text_area("Descrição", placeholder="...", height=60, key="c_func_nl")
            func_nl_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="c_func_nl_problema")
            func_nl_acoes = st.text_area("Ações Corretivas", placeholder="...", height=60, key="c_func_nl_acoes")
            func_nl_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="c_func_nl_praticas")
            
            st.markdown("**AUXILIAR DE LOGÍSTICA**")
            func_al = st.text_area("Descrição", placeholder="...", height=60, key="c_func_al")
            func_al_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="c_func_al_problema")
            func_al_acoes = st.text_area("Ações Corretivas", placeholder="...", height=60, key="c_func_al_acoes")
            func_al_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="c_func_al_praticas")
            
            st.markdown("**AUXILIAR DE INFORMAÇÕES**")
            func_ai = st.text_area("Descrição", placeholder="...", height=60, key="c_func_ai")
            func_ai_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="c_func_ai_problema")
            func_ai_acoes = st.text_area("Ações Corretivas", placeholder="...", height=60, key="c_func_ai_acoes")
            func_ai_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="c_func_ai_praticas")
            
            st.markdown("**PROFISSIONAL DE SAÚDE MENTAL**")
            func_psm = st.text_area("Descrição", placeholder="...", height=60, key="c_func_psm")
            func_psm_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="c_func_psm_problema")
            func_psm_acoes = st.text_area("Ações Corretivas", placeholder="...", height=60, key="c_func_psm_acoes")
            func_psm_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="c_func_psm_praticas")
        
        # ─── INFO ADICIONAIS ───
        with tab_obs:
            col1, col2 = st.columns(2)
            with col1:
                tempo_real = st.text_input("Tempo de Negociação Real (HH:MM)", placeholder="Ex: 01:30", key="c_tempo_real")
            with col2:
                tempo_tatica = st.text_input("Tempo de Negociação Tática (HH:MM)", placeholder="Ex: 00:45", key="c_tempo_tatica")
            
            col3, col4 = st.columns(2)
            with col3:
                uniforme = st.selectbox("Uniforme Usado", [""] + UNIFORMES, key="c_uniforme")
            with col4:
                sexo = st.selectbox("Sexo do Causador", [""] + SEXOS, key="c_sexo")
            
            validador_nome = st.selectbox("Seu Nome/Identificação *", [""] + NEGOCIADORES, key="c_validador")
        
        # BOTÕES DE AÇÃO
        st.markdown("---")
        col_save, col_preview, col_clear = st.columns(3)

        with col_save:
            if st.button("✅ CRIAR APA", use_container_width=True, type="secondary", key="btn_criar_aba1"):
                
                with st.spinner("💾 Criando novo registro..."):
                    try:
                        payload = {
                            "Data da ocorrência": data_oca.isoformat() if data_oca else "",
                            "Modalidade do incidente": modalidade or "",
                            "Tipologia": tipologia or "",
                            "Forma de Transição": forma_transicao or "",
                            "Resolução": resolucao or "",
                            "Motivação": motivacao or "",
                            "Negociador Principal": neg_principal or "",
                            "Negociador Secundário": neg_secundario or "",
                            "Negociador Anotador": neg_anotador or "",
                            "Negociador Líder": neg_lider or "",
                            "Negociador Auxiliar de Informações": aux_info or "",
                            "Negociador Auxiliar de Logística": aux_log or "",
                            "Profissional de Saúde Mental": prof_saude or "",
                            "12 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A AGRESSIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": agr_principal_chegada,
                            "12 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A AGRESSIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": agr_secundario_chegada,
                            "12 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A AGRESSIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": agr_lider_chegada,
                            "13 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A RECEPTIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": rec_principal_chegada,
                            "13 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A RECEPTIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": rec_secundario_chegada,
                            "13 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A RECEPTIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": rec_lider_chegada,
                            "24 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A AGRESSIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": agr_principal_enc,
                            "24 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A AGRESSIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": agr_secundario_enc,
                            "24 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A AGRESSIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": agr_lider_enc,
                            "25 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A RECEPTIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": rec_principal_enc,
                            "25 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A RECEPTIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": rec_secundario_enc,
                            "25 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A RECEPTIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": rec_lider_enc,
                            "TRANSCRIÇÃO DO CAUSADOR": trans_causador or "",
                            "TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL": trans_principal or "",
                            "TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO": trans_secundario or "",
                            "FUNÇÕES: NEGOCIADOR PRINCIPAL": func_np or "",
                            "FUNÇÕES: NEGOCIADOR PRINCIPAL - PROBLEMA IDENTIFICADO": func_np_problema or "",
                            "FUNÇÕES: NEGOCIADOR PRINCIPAL - AÇÕES CORRETIVAS ADOTADAS": func_np_acoes or "",
                            "FUNÇÕES: NEGOCIADOR PRINCIPAL - PRÁTICAS PROMISSORAS": func_np_praticas or "",
                            "FUNÇÕES: NEGOCIADOR SECUNDÁRIO": func_ns or "",
                            "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PROBLEMA IDENTIFICADO": func_ns_problema or "",
                            "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - AÇÕES CORRETIVAS ADOTADAS": func_ns_acoes or "",
                            "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PRÁTICAS PROMISSORAS": func_ns_praticas or "",
                            "FUNÇÕES: NEGOCIADOR ANOTADOR": func_na or "",
                            "FUNÇÕES: NEGOCIADOR ANOTADOR - PROBLEMA IDENTIFICADO": func_na_problema or "",
                            "FUNÇÕES: NEGOCIADOR ANOTADOR - AÇÕES CORRETIVAS ADOTADAS": func_na_acoes or "",
                            "FUNÇÕES: NEGOCIADOR ANOTADOR - PRÁTICAS PROMISSORAS": func_na_praticas or "",
                            "FUNÇÕES: NEGOCIADOR LÍDER": func_nl or "",
                            "FUNÇÕES: NEGOCIADOR LÍDER - PROBLEMA IDENTIFICADO": func_nl_problema or "",
                            "FUNÇÕES: NEGOCIADOR LÍDER - AÇÕES CORRETIVAS ADOTADAS": func_nl_acoes or "",
                            "FUNÇÕES: NEGOCIADOR LÍDER - PRÁTICAS PROMISSORAS": func_nl_praticas or "",
                            "FUNÇÕES: NEGOCIADOR AUXILIAR DE LOGÍSTICA": func_al or "",
                            "FUNÇÕES: AUXILIAR DE LOGÍSTICA - PROBLEMA IDENTIFICADO": func_al_problema or "",
                            "FUNÇÕES: AUXILIAR DE LOGÍSTICA - AÇÕES CORRETIVAS": func_al_acoes or "",
                            "FUNÇÕES: AUXILIAR DE LOGÍSTICA - PRÁTICAS PROMISSORAS": func_al_praticas or "",
                            "FUNÇÕES: NEGOCIADOR AUXILIAR DE INFORMAÇÕES": func_ai or "",
                            "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PROBLEMA IDENTIFICADO": func_ai_problema or "",
                            "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - AÇÕES CORRETIVAS": func_ai_acoes or "",
                            "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PRÁTICAS PROMISSORAS": func_ai_praticas or "",
                            "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL": func_psm or "",
                            "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PROBLEMA IDENTIFICADO": func_psm_problema or "",
                            "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - AÇÕES CORRETIVAS ADOTADAS": func_psm_acoes or "",
                            "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PRÁTICAS PROMISSORAS": func_psm_praticas or "",
                            "Tempo de Negociação Real": tempo_real or "",
                            "Tempo de Negociação Tática": tempo_tatica or "",
                            "Uniforme Usado": uniforme or "",
                            "Sexo do Causador": sexo or "",
                            "VALIDADOR": validador_nome or "",
                        }
                        
                        # Remover campos vazios
                        payload = {k: v for k, v in payload.items() if v != ""}
                        
                        print(f"📤 Enviando para Airtable: {payload}")
                        resultado = airtable_link.criar_nova_apa(payload)
                        print(f"📥 Resultado: {resultado}")
                        
                        if resultado:
                            st.session_state.id_apa_criado = resultado if isinstance(resultado, str) else payload.get("ID", "APA criada")
                            st.success(f"✅ APA CRIADA COM SUCESSO! ID: {st.session_state.id_apa_criado}")
                            st.balloons()
                        else:
                            st.error("❌ Falha ao criar APA. Verifique o console para detalhes.")
                    
                    except Exception as e:
                        st.error(f"❌ Erro: {str(e)}")
                        import traceback
                        traceback.print_exc()

        with col_preview:
            if st.button("👁️ Pré-visualizar", use_container_width=True, key="btn_prev_aba1"):
                st.json({
                    "Data": str(data_oca),
                    "Negociador": neg_principal,
                    "Tipologia": tipologia,
                    "Validador": validador_nome
                })

        with col_clear:
            if st.button("❌ Limpar Tudo", use_container_width=True, key="btn_clear_aba1"):
                for key in list(st.session_state.keys()):
                    if key.startswith("c_"):
                        del st.session_state[key]
                st.info("✨ Formulário limpo!")
    
    # ─────────────────────────────────────────────────────────────
    # ABA 2: UPLOAD DE TÉCNICAS (INDEPENDENTE)
    # ─────────────────────────────────────────────────────────────
    
    with tab2:
        st.markdown("### 📊 Upload de Técnicas")
        st.markdown("Faça upload de técnicas para qualquer APA existente, em qualquer momento.")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            id_apa_upload = st.text_input(
                "ID da APA *",
                placeholder="Ex: APA 001",
                key="upload_id_apa_tab2"
            )
        with col2:
            st.markdown("#### ")  # Espaço vazio
            uploaded_file = st.file_uploader(
                "Selecione arquivo Excel",
                type=['xlsx', 'xls'],
                key="upload_excel_tab2"
            )
        
        if uploaded_file is not None and id_apa_upload:
            try:
                df_excel = pd.read_excel(uploaded_file)
                valido, mensagens, colunas = validar_excel_tecnicas(df_excel)

                if not valido:
                    st.error("### ❌ Erro na Validação")
                    for msg in mensagens:
                        st.error(msg)
                else:
                    st.success(f"✅ Excel validado! {len(df_excel)} técnicas prontas")

                    if mensagens:
                        for msg in mensagens:
                            st.warning(msg)

                    st.dataframe(df_excel.head(5), use_container_width=True, hide_index=True)

                    if st.button(f"✅ INSERIR {len(df_excel)} TÉCNICAS", use_container_width=True, type="primary", key="btn_insert_tech_tab2"):
                        with st.spinner(f"💾 Inserindo {len(df_excel)} técnicas..."):
                            sucesso_count = 0
                            erro_count = 0

                            col_tecnicas = colunas['tecnicas']
                            col_atitude = colunas['atitude']
                            col_trecho = colunas['trecho']

                            progress_bar = st.progress(0)

                            for idx, row in df_excel.iterrows():
                                try:
                                    payload = {
                                        "TÉCNICAS": str(row[col_tecnicas]).strip(),
                                        "ATITUDE DO CAUSADOR": int(row[col_atitude]),
                                        "TRECHO DA TRANSCRIÇÃO": str(row[col_trecho]).strip(),
                                        "Vínculo_APA": id_apa_upload.strip().upper()
                                    }

                                    if airtable_link.criar_tecnica(payload):
                                        sucesso_count += 1
                                    else:
                                        erro_count += 1
                                except:
                                    erro_count += 1

                                progress_bar.progress((idx + 1) / len(df_excel))

                            st.success(f"""
                            ✅ TÉCNICAS INSERIDAS!
                            - Sucesso: {sucesso_count}
                            - Erros: {erro_count}
                            """)
                            st.balloons()

            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
    
    # ─────────────────────────────────────────────────────────────
    # ABA 3: VISUALIZAR & EDITAR (COM FORMULÁRIO)
    # ─────────────────────────────────────────────────────────────
    
    with tab3:
        st.markdown("### ✏️ Visualizar & Editar APA")
        
        col_id, col_btn = st.columns([3, 1])
        with col_id:
            id_busca = st.text_input(
                "ID da APA",
                placeholder="Ex: APA 001",
                key="vis_id_busca_tab3"
            )
        with col_btn:
            btn_buscar = st.button("🔍 Buscar", key="btn_buscar_vis_tab3")
        
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
                    apa = registros.iloc[0]
                    
                    st.success("✅ APA encontrada!")
                    
                    # Mostrar resumo em cards
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Data", str(apa.get('Data da ocorrência', 'N/D'))[:12])
                    with col2:
                        st.metric("Negociador", str(apa.get('Negociador Principal', 'N/D'))[:15])
                    with col3:
                        st.metric("Tipologia", str(apa.get('Tipologia', 'N/D'))[:15])
                    with col4:
                        st.metric("Resolução", str(apa.get('Resolução', 'N/D'))[:12])
                    
                    st.markdown("---")
                    
                    # FORMULÁRIO DE EDIÇÃO
                    st.markdown("### ✏️ Editar Dados")
                    
                    with st.form(f"form_edit_{id_limpo}", clear_on_submit=False):
                        # Metadados
                        st.markdown("#### 📋 Metadados")
                        col1, col2 = st.columns(2)
                        with col1:
                            data_edit = st.date_input("Data da Ocorrência", value=pd.to_datetime(apa.get('Data da ocorrência')) if pd.notna(apa.get('Data da ocorrência')) else None, key=f"edit_data_{id_limpo}")
                        with col2:
                            modalidade_edit = st.selectbox("Modalidade", [""] + MODALIDADES, index=MODALIDADES.index(apa.get('Modalidade do incidente')) + 1 if apa.get('Modalidade do incidente') in MODALIDADES else 0, key=f"edit_mod_{id_limpo}")
                        
                        col3, col4 = st.columns(2)
                        with col3:
                            tipologia_edit = st.selectbox("Tipologia", [""] + TIPOLOGIAS, index=TIPOLOGIAS.index(apa.get('Tipologia')) + 1 if apa.get('Tipologia') in TIPOLOGIAS else 0, key=f"edit_tip_{id_limpo}")
                        with col4:
                            resolucao_edit = st.selectbox("Resolução", [""] + RESOLUCOES, index=RESOLUCOES.index(apa.get('Resolução')) + 1 if apa.get('Resolução') in RESOLUCOES else 0, key=f"edit_res_{id_limpo}")
                        
                        motivacao_edit = st.text_area("Motivação", value=apa.get('Motivação', ''), key=f"edit_mot_{id_limpo}", height=80)
                        
                        # Equipe
                        st.markdown("#### 👥 Equipe Principal")
                        col5, col6 = st.columns(2)
                        with col5:
                            neg_principal_edit = st.selectbox("Negociador Principal", [""] + NEGOCIADORES, index=NEGOCIADORES.index(apa.get('Negociador Principal')) + 1 if apa.get('Negociador Principal') in NEGOCIADORES else 0, key=f"edit_np_{id_limpo}")
                        with col6:
                            neg_secundario_edit = st.selectbox("Negociador Secundário", [""] + NEGOCIADORES, index=NEGOCIADORES.index(apa.get('Negociador Secundário')) + 1 if apa.get('Negociador Secundário') in NEGOCIADORES else 0, key=f"edit_ns_{id_limpo}")
                        
                        # Botões
                        col_salvar, col_cancelar = st.columns(2)
                        with col_salvar:
                            btn_salvar = st.form_submit_button("💾 SALVAR ALTERAÇÕES", use_container_width=True, type="primary")
                        with col_cancelar:
                            btn_cancelar = st.form_submit_button("❌ CANCELAR", use_container_width=True)
                        
                        if btn_salvar:
                            # Preparar payload de atualização
                            payload_update = {
                                "Data da ocorrência": data_edit.isoformat() if data_edit else "",
                                "Modalidade do incidente": modalidade_edit or "",
                                "Tipologia": tipologia_edit or "",
                                "Resolução": resolucao_edit or "",
                                "Motivação": motivacao_edit or "",
                                "Negociador Principal": neg_principal_edit or "",
                                "Negociador Secundário": neg_secundario_edit or "",
                            }
                            
                            # Remover vazios
                            payload_update = {k: v for k, v in payload_update.items() if v != ""}
                            
                            # Atualizar no Airtable
                            try:
                                if airtable_link.atualizar_apa_validacao(id_limpo, payload_update):
                                    st.success("✅ Dados atualizados com sucesso!")
                                    st.balloons()
                                else:
                                    st.error("❌ Falha ao atualizar. Verifique o ID.")
                            except Exception as e:
                                st.error(f"❌ Erro: {str(e)}")
            
            except Exception as e:
                st.error(f"Erro: {str(e)}")