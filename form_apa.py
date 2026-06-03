# ============================================================
# form_apa_completo.py
# ENTRADA DE DADOS COMPLETA - INTEGRADA
# Sub-aba 1: Criar Nova APA + Upload Técnicas
# Sub-aba 2: Visualizar & Editar (link para Airtable)
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

PERCEPCOES = [
    "Não observado",
    "Não agressivo",
    "Neutro",
    "Parcialmente agressivo",
    "Agressivo",
    "Muito agressivo"
]


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
    Interface principal de Entrada de Dados com 2 sub-abas:
    1. Criar Nova APA + Upload Técnicas
    2. Visualizar & Editar
    """
    
    st.markdown("### 📋 Entrada de Dados — GATE/PMESP")
    st.markdown("""
    <p style='color: #aaa; font-size: 0.9rem;'>
    Crie novas APAs, faça upload de técnicas e visualize dados existentes.
    </p>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ════════════════════════════════════════════════════════════
    # 2 SUB-ABAS PRINCIPAIS
    # ════════════════════════════════════════════════════════════
    
    sub_tab1, sub_tab2 = st.tabs([
        "➕ Criar Nova APA",
        "✏️ Visualizar & Editar"
    ])
    
    # ─────────────────────────────────────────────────────────────
    # SUB-ABA 1: CRIAR NOVA APA + UPLOAD TÉCNICAS
    # ─────────────────────────────────────────────────────────────
    
    with sub_tab1:
        
        # Container para o formulário
        container_form = st.container()
        
        with container_form:
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
                st.markdown("**Principal**")
                col1, col2 = st.columns(2)
                with col1:
                    agr_principal_chegada = st.selectbox("12 - Agressividade", PERCEPCOES, key="c_agr_principal_chegada")
                with col2:
                    rec_principal_chegada = st.selectbox("13 - Receptividade", PERCEPCOES, key="c_rec_principal_chegada")
                
                st.markdown("**Secundário**")
                col3, col4 = st.columns(2)
                with col3:
                    agr_secundario_chegada = st.selectbox("12 - Agressividade", PERCEPCOES, key="c_agr_secundario_chegada")
                with col4:
                    rec_secundario_chegada = st.selectbox("13 - Receptividade", PERCEPCOES, key="c_rec_secundario_chegada")
                
                st.markdown("**Líder**")
                col5, col6 = st.columns(2)
                with col5:
                    agr_lider_chegada = st.selectbox("12 - Agressividade", PERCEPCOES, key="c_agr_lider_chegada")
                with col6:
                    rec_lider_chegada = st.selectbox("13 - Receptividade", PERCEPCOES, key="c_rec_lider_chegada")
            
            # ─── PERCEPÇÃO ENCERRAMENTO ───
            with tab_enc:
                st.markdown("**Principal**")
                col1, col2 = st.columns(2)
                with col1:
                    agr_principal_enc = st.selectbox("24 - Agressividade", PERCEPCOES, key="c_agr_principal_enc")
                with col2:
                    rec_principal_enc = st.selectbox("25 - Receptividade", PERCEPCOES, key="c_rec_principal_enc")
                
                st.markdown("**Secundário**")
                col3, col4 = st.columns(2)
                with col3:
                    agr_secundario_enc = st.selectbox("24 - Agressividade", PERCEPCOES, key="c_agr_secundario_enc")
                with col4:
                    rec_secundario_enc = st.selectbox("25 - Receptividade", PERCEPCOES, key="c_rec_secundario_enc")
                
                st.markdown("**Líder**")
                col5, col6 = st.columns(2)
                with col5:
                    agr_lider_enc = st.selectbox("24 - Agressividade", PERCEPCOES, key="c_agr_lider_enc")
                with col6:
                    rec_lider_enc = st.selectbox("25 - Receptividade", PERCEPCOES, key="c_rec_lider_enc")
            
            # ─── TRANSCRIÇÕES ───
            with tab_trans:
                st.markdown("**TRANSCRIÇÃO DO CAUSADOR**")
                trans_causador = st.text_area("", placeholder="...", height=80, key="c_trans_causador")
                
                st.markdown("**TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL**")
                trans_principal = st.text_area("", placeholder="...", height=80, key="c_trans_principal")
                
                st.markdown("**TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO**")
                trans_secundario = st.text_area("", placeholder="...", height=80, key="c_trans_secundario")
                
                st.markdown("**TABELA DE FREQUÊNCIAS DAS TÉCNICAS**")
                tabela_tecnicas = st.text_area("", placeholder="(Será preenchido via upload na próxima etapa)", height=80, key="c_tabela_tecnicas")
            
            # ─── FUNÇÕES ───
            with tab_func:
                st.markdown("**Negociador Principal**")
                col1, col2 = st.columns(2)
                with col1:
                    func_np = st.text_area("Funções", placeholder="...", height=60, key="c_func_np")
                with col2:
                    func_np_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="c_func_np_problema")
                
                col3, col4 = st.columns(2)
                with col3:
                    func_np_acoes = st.text_area("Ações Corretivas Adotadas", placeholder="...", height=60, key="c_func_np_acoes")
                with col4:
                    func_np_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="c_func_np_praticas")
                
                st.markdown("---")
                st.markdown("**Negociador Secundário**")
                col5, col6 = st.columns(2)
                with col5:
                    func_ns = st.text_area("Funções", placeholder="...", height=60, key="c_func_ns")
                with col6:
                    func_ns_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="c_func_ns_problema")
                
                col7, col8 = st.columns(2)
                with col7:
                    func_ns_acoes = st.text_area("Ações Corretivas Adotadas", placeholder="...", height=60, key="c_func_ns_acoes")
                with col8:
                    func_ns_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="c_func_ns_praticas")
                
                st.markdown("---")
                st.markdown("**Negociador Anotador**")
                col9, col10 = st.columns(2)
                with col9:
                    func_na = st.text_area("Funções", placeholder="...", height=60, key="c_func_na")
                with col10:
                    func_na_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="c_func_na_problema")
                
                col11, col12 = st.columns(2)
                with col11:
                    func_na_acoes = st.text_area("Ações Corretivas Adotadas", placeholder="...", height=60, key="c_func_na_acoes")
                with col12:
                    func_na_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="c_func_na_praticas")
                
                st.markdown("---")
                st.markdown("**Negociador Líder**")
                col13, col14 = st.columns(2)
                with col13:
                    func_nl = st.text_area("Funções", placeholder="...", height=60, key="c_func_nl")
                with col14:
                    func_nl_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="c_func_nl_problema")
                
                col15, col16 = st.columns(2)
                with col15:
                    func_nl_acoes = st.text_area("Ações Corretivas Adotadas", placeholder="...", height=60, key="c_func_nl_acoes")
                with col16:
                    func_nl_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="c_func_nl_praticas")
                
                st.markdown("---")
                st.markdown("**Auxiliar de Logística**")
                col17, col18 = st.columns(2)
                with col17:
                    func_al = st.text_area("Funções", placeholder="...", height=60, key="c_func_al")
                with col18:
                    func_al_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="c_func_al_problema")
                
                col19, col20 = st.columns(2)
                with col19:
                    func_al_acoes = st.text_area("Ações Corretivas", placeholder="...", height=60, key="c_func_al_acoes")
                with col20:
                    func_al_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="c_func_al_praticas")
                
                st.markdown("---")
                st.markdown("**Auxiliar de Informações**")
                col21, col22 = st.columns(2)
                with col21:
                    func_ai = st.text_area("Funções", placeholder="...", height=60, key="c_func_ai")
                with col22:
                    func_ai_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="c_func_ai_problema")
                
                col23, col24 = st.columns(2)
                with col23:
                    func_ai_acoes = st.text_area("Ações Corretivas", placeholder="...", height=60, key="c_func_ai_acoes")
                with col24:
                    func_ai_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="c_func_ai_praticas")
                
                st.markdown("---")
                st.markdown("**Profissional de Saúde Mental**")
                col25, col26 = st.columns(2)
                with col25:
                    func_psm = st.text_area("Funções", placeholder="...", height=60, key="c_func_psm")
                with col26:
                    func_psm_problema = st.text_area("Problema Identificado", placeholder="...", height=60, key="c_func_psm_problema")
                
                col27, col28 = st.columns(2)
                with col27:
                    func_psm_acoes = st.text_area("Ações Corretivas Adotadas", placeholder="...", height=60, key="c_func_psm_acoes")
                with col28:
                    func_psm_praticas = st.text_area("Práticas Promissoras", placeholder="...", height=60, key="c_func_psm_praticas")
            
            # ─── INFO ADICIONAIS ───
            with tab_obs:
                col1, col2 = st.columns(2)
                with col1:
                    tempo_real = st.text_input("Tempo de Negociação Real (HH:MM)", placeholder="00:00", key="c_tempo_real")
                with col2:
                    tempo_tatica = st.text_input("Tempo de Negociação Tática (HH:MM)", placeholder="00:00", key="c_tempo_tatica")
                
                col3, col4 = st.columns(2)
                with col3:
                    uniforme = st.selectbox("Uniforme Usado", UNIFORMES, key="c_uniforme")
                with col4:
                    sexo = st.selectbox("Sexo do Causador", SEXOS, key="c_sexo")
                
                validador_nome = st.text_input("Seu Nome/Identificação *", placeholder="Ex: Cap PM Pavão", key="c_validador")
        
        
        # BOTÕES DE AÇÃO
        st.markdown("---")
        col_save, col_preview, col_clear = st.columns(3)

        with col_save:
            if st.button("✅ CRIAR APA", use_container_width=True, type="secondary", key="btn_criar_aba1"):
                
                with st.spinner("💾 Criando novo registro..."):
                    try:
                        # MÍNIMO NECESSÁRIO PARA TESTE
                        payload = {
                            "Data da ocorrência": data_oca.isoformat() if data_oca else "",
                            "Modalidade do incidente": modalidade or "N/D",
                            "Tipologia": tipologia or "N/D",
                            "Negociador Principal": neg_principal or "N/D",
                            "Resolução": resolucao or "N/D",
                            "Criado Por": validador_nome or "Teste",
                            "Data Criação": datetime.now().isoformat(),
                            "Status": "Novo"
                        }
                        
                        print(f"📤 Enviando para Airtable: {payload}")
                        resultado = airtable_link.criar_nova_apa(payload)
                        print(f"📥 Resultado: {resultado}")
                        
                        if resultado:
                            st.session_state.id_apa_criado = resultado if isinstance(resultado, str) else payload.get("ID", "APA criada")
                            st.success(f"✅ APA CRIADA COM SUCESSO! ID: {st.session_state.id_apa_criado}")
                            st.balloons()
                            
                            st.markdown("---")
                            st.markdown("### 📊 PRÓXIMO PASSO: Upload de Técnicas")
                            st.markdown("Você pode fazer upload das técnicas agora!")
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

        # ════════════════════════════════════════════════════════════
        # UPLOAD DE TÉCNICAS (após APA criada)
        # ════════════════════════════════════════════════════════════

        if "id_apa_criado" in st.session_state:
            st.markdown("---")
            st.markdown("### 📊 Upload de Técnicas")

            id_apa = st.text_input(
                "ID da APA para vincular",
                value=st.session_state.get("id_apa_criado", ""),
                placeholder="Ex: APA 001",
                key="upload_id_apa_aba1"
            )

            uploaded_file = st.file_uploader(
                "Selecione arquivo Excel com técnicas",
                type=['xlsx', 'xls'],
                key="upload_excel_aba1"
            )

            if uploaded_file is not None and id_apa:
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

                        if st.button(f"✅ INSERIR {len(df_excel)} TÉCNICAS", use_container_width=True, type="primary", key="btn_insert_tech"):
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
                                            "Vínculo_APA": id_apa.strip().upper()
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
    # SUB-ABA 2: VISUALIZAR & EDITAR
    # ─────────────────────────────────────────────────────────────
    
    with sub_tab2:
        st.markdown("#### Visualizar Dados da APA")
        
        col_id, col_btn = st.columns([3, 1])
        with col_id:
            id_busca = st.text_input(
                "ID da APA",
                placeholder="Ex: APA 001",
                key="vis_id_busca"
            )
        with col_btn:
            btn_buscar = st.button("🔍 Buscar", key="btn_buscar_vis")
        
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
                    
                    # Mostrar dados em cards
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
                    st.markdown("### Dados Completos")
                    
                    # Mostrar todos os dados
                    dados_dict = apa.to_dict()
                    st.json({k: str(v)[:100] for k, v in dados_dict.items() if pd.notna(v)})
                    
                    st.markdown("---")
                    st.markdown("### ✏️ Editar no Airtable")
                    
                    st.info("""
                    Para editar os dados desta APA, clique no botão abaixo para abrir no Airtable.
                    Você será redirecionado para a base de dados onde pode fazer alterações.
                    """)
                    
                    # Construir URL do Airtable (formato genérico)
                    airtable_url = f"https://airtable.com/appVS2d7sGlsXlKKA/tblP2cddxBzKYUVU2/viwIzDvLfNTNLwGBe/{id_limpo}"
                    
                    col_edit, col_close = st.columns(2)
                    with col_edit:
                        st.markdown(f"[🔗 Abrir no Airtable](https://airtable.com)")
                    with col_close:
                        if st.button("❌ Fechar", use_container_width=True):
                            st.info("Busca fechada")
            
            except Exception as e:
                st.error(f"Erro: {str(e)}")