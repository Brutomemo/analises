# ============================================================
# form_apa_v2.py - VERSÃO MELHORADA
# ENTRADA DE DADOS COMPLETA - 3 ABAS INDEPENDENTES
# Aba 1: Criar Nova APA
# Aba 2: Upload Técnicas (INDEPENDENTE)
# Aba 3: Visualizar & Editar (COM FORMULÁRIO DE EDIÇÃO)
# ============================================================

import re
import streamlit as st
import pandas as pd
import io
from datetime import datetime, date
import airtable_link
import separador_apa


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
    "Ten PM Carolina",
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
    "Cb PM Edson"    
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
    """Valida Excel de técnicas - PERMITE ATITUDE vazia (será "Inaudível/Não Observado")"""
    df.columns = df.columns.str.strip()
    
    colunas_esperadas = {
        'tecnicas': ['TÉCNICAS', 'A_TÉCNICAS'],
        'atitude': ['ATITUDE DO CAUSADOR'],
        'trecho': ['TRECHO DA TRANSCRIÇÃO', 'TRECHO DA TRANSCRIÇÃO']
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
    
    # Validar ATITUDE - PERMITE VAZIO (será "Inaudível/Não Observado")
    col_atitude = colunas_encontradas['atitude']
    
    # Marcar como inválido APENAS se:
    # - Não é vazio (NaN/None/''/"") E
    # - Não é um dos valores válidos (-1, 0, 1)
    atitudes_invalidas = []
    for idx, valor in enumerate(df[col_atitude]):
        # Se está vazio (NaN ou ""), é válido - será "Inaudível/Não Observado"
        if pd.isna(valor) or valor == "" or str(valor).strip() == "":
            continue
        
        # Se não está vazio, deve ser -1, 0 ou 1
        try:
            val_num = int(valor)
            if val_num not in [-1, 0, 1]:
                atitudes_invalidas.append(idx)
        except (ValueError, TypeError):
            # Se não consegue converter para número, é inválido
            atitudes_invalidas.append(idx)
    
    validacoes = []
    if atitudes_invalidas:
        validacoes.append(f"⚠️ Linhas com ATITUDE inválida (não são -1, 0, 1 ou vazio): {atitudes_invalidas}")
    else:
        validacoes.append(f"✅ ATITUDE validada - valores vazios serão interpretados como 'Inaudível/Não Observado'")
    
    return True, validacoes, colunas_encontradas


def _normalizar_data_ocorrencia(valor):
    """Normaliza datas do Airtable e do formulário para comparação/busca."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)) or valor == "":
        return None
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, pd.Timestamp):
        return valor.date()

    s = str(valor).strip()
    if not s:
        return None

    # ISO YYYY-MM-DD (gravado pelo formulário via isoformat)
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return pd.to_datetime(s[:10], format="%Y-%m-%d").date()

    # Datas com barra: Airtable exibe no formato M/D/YYYY
    if "/" in s:
        return pd.to_datetime(s, dayfirst=False).date()

    try:
        return pd.to_datetime(s, dayfirst=False).date()
    except (ValueError, TypeError):
        return None


def _id_apa_coincide(id_a, id_b):
    """Compara IDs de APA (31, 31.0, 'APA 031', etc.)."""
    if id_a is None or id_b is None:
        return False
    if isinstance(id_a, float) and pd.isna(id_a):
        return False
    if isinstance(id_b, float) and pd.isna(id_b):
        return False
    fmt_a = _normalizar_id_apa(id_a)
    fmt_b = _normalizar_id_apa(id_b)
    if fmt_a and fmt_b:
        return fmt_a == fmt_b
    return str(id_a).strip() == str(id_b).strip()


def _chave_registro_apa(row, df_quali=None):
    rec = _resolver_record_id_apa(row, df_quali)
    if rec:
        return rec
    id_fmt = _normalizar_id_apa(row.get('ID'))
    return f"apa-{id_fmt or row.get('ID')}"


def _rotulo_ocorrencia_apa(row):
    partes = []
    if pd.notna(row.get('ID')):
        partes.append(str(row.get('ID')))
    if pd.notna(row.get('Negociador Principal')):
        partes.append(str(row.get('Negociador Principal')))
    if pd.notna(row.get('Tipologia')):
        partes.append(str(row.get('Tipologia')))
    if pd.notna(row.get('Modalidade do incidente')):
        partes.append(str(row.get('Modalidade do incidente'))[:30])
    return " — ".join(partes) if partes else "Ocorrência sem identificação"


def _normalizar_id_apa(valor_id):
    if valor_id is None or (isinstance(valor_id, float) and pd.isna(valor_id)):
        return None
    if isinstance(valor_id, (int, float)) and not isinstance(valor_id, bool):
        return f"APA {int(valor_id):03d}"
    campo_id = str(valor_id).strip()
    if campo_id.endswith('.0'):
        campo_id = campo_id[:-2]
    try:
        num = int(campo_id.replace("APA", "").strip())
        return f"APA {num:03d}"
    except (ValueError, TypeError):
        return campo_id.upper()


def _garantir_coluna_data_busca(df_quali):
    df_quali['Data_Busca'] = df_quali['Data da ocorrência'].apply(_normalizar_data_ocorrencia)
    return df_quali


def _buscar_registros_por_data(df_quali, data_filtro):
    df_quali = _garantir_coluna_data_busca(df_quali)
    data_cmp = data_filtro if isinstance(data_filtro, date) else _normalizar_data_ocorrencia(data_filtro)
    if data_cmp is None:
        return df_quali.iloc[0:0].copy()
    return df_quali[df_quali['Data_Busca'] == data_cmp].copy().reset_index(drop=True)


def _resolver_record_id_apa(apa, df_quali=None):
    """Obtém o record_id interno do Airtable (rec...) para a APA selecionada."""
    for campo in ('Airtable_Record_ID', 'record_id_airtable', 'id'):
        valor = apa.get(campo)
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            continue
        valor_str = str(valor).strip()
        if valor_str.startswith('rec'):
            return valor_str

    id_campo = apa.get('ID')
    if df_quali is not None and not df_quali.empty and id_campo is not None:
        for _, linha in df_quali.iterrows():
            if not _id_apa_coincide(linha.get('ID'), id_campo):
                continue
            for campo in ('Airtable_Record_ID', 'record_id_airtable', 'id'):
                valor = linha.get(campo)
                if valor is None or (isinstance(valor, float) and pd.isna(valor)):
                    continue
                valor_str = str(valor).strip()
                if valor_str.startswith('rec'):
                    return valor_str

    id_ref = _normalizar_id_apa(id_campo) or id_campo
    return airtable_link.buscar_record_id_por_id_apa(id_ref)


def _criar_tecnica_airtable(payload, vinculo_record_id=None):
    """Compatível com criar_tecnica retornando bool (legado) ou (bool, erro)."""
    resultado = airtable_link.criar_tecnica(payload, vinculo_record_id=vinculo_record_id)
    if isinstance(resultado, tuple):
        return resultado
    return bool(resultado), None if resultado else "Falha ao criar técnica no Airtable."


def _inserir_tecnicas_extraidas(df_tecnicas, apa, df_quali=None, progress_bar=None):
    """Insere técnicas extraídas do .docx no Airtable, vinculadas à APA selecionada."""
    vinculo_record_id = _resolver_record_id_apa(apa, df_quali)
    id_apa_normalizado = _normalizar_id_apa(apa.get('ID'))
    if not vinculo_record_id:
        return 0, len(df_tecnicas), [
            f"Não foi possível localizar o record_id (rec...) da APA "
            f"{id_apa_normalizado or apa.get('ID')}. Recarregue os dados do Airtable."
        ]

    sucesso_count = 0
    erro_count = 0
    detalhes_erros = []
    total = len(df_tecnicas)

    for n, (_, row) in enumerate(df_tecnicas.iterrows()):
        tecnica = str(row.get('TÉCNICAS', '')).strip()
        trecho = str(row.get('TRECHO DA TRANSCRIÇÃO', '')).strip()

        if not tecnica:
            erro_count += 1
            detalhes_erros.append(f"Linha {n + 1}: técnica vazia.")
            if progress_bar is not None and total:
                progress_bar.progress((n + 1) / total)
            continue

        if not trecho:
            trecho = "[Trecho não extraído do documento — revise a tabela no .docx]"

        payload = {
            "TÉCNICAS": tecnica,
            "TRECHO DA TRANSCRIÇÃO": trecho,
            "Vinculo_APA": id_apa_normalizado or str(apa.get('ID', '')).strip(),
        }

        atitude = row.get('ATITUDE DO CAUSADOR')
        if atitude is not None and not (isinstance(atitude, float) and pd.isna(atitude)):
            if str(atitude).strip() != "":
                try:
                    payload["ATITUDE DO CAUSADOR"] = int(atitude)
                except (ValueError, TypeError):
                    detalhes_erros.append(f"{tecnica}: atitude inválida ({atitude!r}).")

        ok, erro = _criar_tecnica_airtable(payload, vinculo_record_id=vinculo_record_id)
        if ok:
            sucesso_count += 1
        else:
            erro_count += 1
            detalhes_erros.append(f"{tecnica}: {erro or 'erro desconhecido'}")

        if progress_bar is not None and total:
            progress_bar.progress((n + 1) / total)

    return sucesso_count, erro_count, detalhes_erros


def _render_envio_tecnicas_docx(apa, df_quali, key_prefix):
    """Upload .docx, extração e envio das técnicas para a APA já selecionada."""
    id_apa = str(apa.get('ID', 'N/D')).strip()
    id_apa_normalizado = _normalizar_id_apa(apa.get('ID'))
    record_id_apa = _resolver_record_id_apa(apa, df_quali)

    st.markdown("##### Enviar Técnicas Extraídas do .docx")

    if record_id_apa:
        st.info(f"🔗 APA **{id_apa_normalizado or id_apa}** vinculada: `{record_id_apa}`")
    else:
        st.error(
            "❌ Não foi possível obter o `record_id` (rec...) desta APA. "
            "Recarregue a página para atualizar os dados do Airtable e tente novamente."
        )

    df_tec_cache = st.session_state.get('tecnicas_extraidas_apa')

    arq_tec = st.file_uploader(
        "Upload do .docx da APA (extrai técnicas automaticamente)",
        type=["docx", "docm"],
        key=f"uploader_tec_{key_prefix}",
    )
    if arq_tec:
        with st.spinner("Extraindo técnicas..."):
            res = separador_apa.processar_apa(arq_tec.read())
        if res['erro']:
            st.error(f"❌ {res['erro']}")
        elif res['tecnicas'].empty:
            st.warning("⚠️ Nenhuma técnica encontrada no arquivo.")
        else:
            st.session_state['tecnicas_extraidas_apa'] = res['tecnicas']
            df_tec_cache = res['tecnicas']
            st.success(f"✅ {len(df_tec_cache)} técnicas extraídas e prontas para envio.")

    if df_tec_cache is None or df_tec_cache.empty:
        st.info(
            "Faça upload do .docx acima ou extraia técnicas na aba **Criar Novo Registro** "
            "(subaba Transcrições) — elas ficam em cache até o envio."
        )
        return

    st.metric("Técnicas prontas para envio", len(df_tec_cache))
    sem_trecho = int((df_tec_cache['TRECHO DA TRANSCRIÇÃO'].fillna('').astype(str).str.strip() == '').sum())
    if sem_trecho:
        st.warning(
            f"⚠️ {sem_trecho} técnica(s) sem trecho extraído — serão enviadas com aviso no campo trecho. "
            "Reenvie o .docx após conferir a tabela de técnicas."
        )
    st.dataframe(df_tec_cache, use_container_width=True, hide_index=True)

    if st.button(
        f"✔️ Enviar {len(df_tec_cache)} técnicas para {id_apa}",
        key=f"btn_enviar_tec_{key_prefix}",
        use_container_width=True,
        type="secondary",
        disabled=not record_id_apa,
    ):
        with st.spinner(f"💾 Enviando {len(df_tec_cache)} técnicas..."):
            progress = st.progress(0)
            sucesso, erros, detalhes = _inserir_tecnicas_extraidas(
                df_tec_cache, apa, df_quali=df_quali, progress_bar=progress
            )
            progress.empty()

        if erros == 0:
            st.success(f"✅ {sucesso} técnicas enviadas para {id_apa}!")
            st.session_state.pop('tecnicas_extraidas_apa', None)
            st.session_state.pop('df_tec', None)
        else:
            st.warning(f"⚠️ {sucesso} enviadas, {erros} com erro.")
            with st.expander("Detalhes dos erros", expanded=True):
                for msg in detalhes[:20]:
                    st.write(f"- {msg}")


def render(df_quali, df_tec):
    """
    Interface principal de Entrada de Dados com 2 abas:
    1. Criar Nova APA
    2. Visualizar & Editar (COM FORMULÁRIO)
    """
    
    st.markdown("### Entrada de Dados")
    st.markdown("""
    <p style='color: #aaa; font-size: 0.9rem;'>
    Crie novas APAs, extraia técnicas do .docx e edite dados existentes.
    </p>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ════════════════════════════════════════════════════════════
    # 2 ABAS PRINCIPAIS
    # ════════════════════════════════════════════════════════════
    
    tab1, tab2 = st.tabs([
        "✔️ Criar Novo Registro de APA",
        "🔎 Visualizar & Editar"
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
            separador_apa.render_separador()
            st.markdown("---")
            trans_causador = st.text_area("Transcrição do Causador", placeholder="...", height=100, key="c_trans_causador")
            trans_principal = st.text_area("Transcrição do Negociador Principal", placeholder="...", height=100, key="c_trans_principal")
            trans_secundario = st.text_area("Transcrição do Negociador Secundário", placeholder="...", height=100, key="c_trans_secundario")
        
        # ─── FUNÇÕES ───
        with tab_func:
            for funcao, prefixo in [
                ("NEGOCIADOR PRINCIPAL",        "c_func_np"),
                ("NEGOCIADOR SECUNDÁRIO",        "c_func_ns"),
                ("NEGOCIADOR ANOTADOR",          "c_func_na"),
                ("NEGOCIADOR LÍDER",             "c_func_nl"),
                ("AUXILIAR DE LOGÍSTICA",        "c_func_al"),
                ("AUXILIAR DE INFORMAÇÕES",      "c_func_ai"),
                ("PROFISSIONAL DE SAÚDE MENTAL", "c_func_psm"),
            ]:
                st.markdown(f"**{funcao}**")
                locals()[f"{prefixo}"] = st.text_area(
                    "Descrição", placeholder="...", height=68, key=f"{prefixo}"
                )
                with st.expander("📋 Problema / Ações / Práticas"):
                    locals()[f"{prefixo}_problema"] = st.text_area(
                        "Problema Identificado", placeholder="...", height=68, key=f"{prefixo}_problema"
                    )
                    locals()[f"{prefixo}_acoes"] = st.text_area(
                        "Ações Corretivas", placeholder="...", height=68, key=f"{prefixo}_acoes"
                    )
                    locals()[f"{prefixo}_praticas"] = st.text_area(
                        "Práticas Promissoras", placeholder="...", height=68, key=f"{prefixo}_praticas"
                    )
                st.markdown("---")
        
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
        
        # BOTÕES DE AÇÃO
        st.markdown("---")
        col_save, col_clear = st.columns(2)

        with col_save:
            if st.button("✅ CRIAR REGISTRO DE APA", use_container_width=True, type="secondary", key="btn_criar_aba1"):
                
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
                        }
                        
                        # Remover campos vazios
                        payload = {k: v for k, v in payload.items() if v != ""}

                        resultado = airtable_link.criar_nova_apa(payload)
                        id_apa = resultado.get("id") if isinstance(resultado, dict) else resultado
                        erro = resultado.get("erro") if isinstance(resultado, dict) else None

                        if id_apa:
                            st.session_state.id_apa_criado = id_apa
                            st.success(f"✅ APA CRIADA COM SUCESSO! ID: {st.session_state.id_apa_criado}")
                        else:
                            st.error(f"❌ Falha ao criar APA: {erro or 'Erro desconhecido.'}")
                    
                    except Exception as e:
                        st.error(f"❌ Erro: {str(e)}")
                        import traceback
                        traceback.print_exc()

        with col_clear:
            if st.button("❌ Limpar Tudo", use_container_width=True, key="btn_clear_aba1"):
                for key in list(st.session_state.keys()):
                    if key.startswith("c_"):
                        del st.session_state[key]
                st.info("✨ Formulário limpo!")
    
    # ─────────────────────────────────────────────────────────────
    # ABA 2: VISUALIZAR & EDITAR (COM FORMULÁRIO)
    # ─────────────────────────────────────────────────────────────
    
    with tab2:
        st.markdown("### Visualizar & Editar APA")

        def _on_edit_data_change():
            st.session_state['_edit_data_ativo'] = st.session_state['vis_data_busca_tab3']
            st.session_state.pop('_edit_registro_key', None)

        if 'vis_data_busca_tab3' not in st.session_state:
            st.session_state['vis_data_busca_tab3'] = st.session_state.get('_edit_data_ativo', date.today())

        col_data_busca, col_btn = st.columns([3, 1])
        with col_data_busca:
            data_busca = st.date_input(
                "Data da Ocorrência",
                key="vis_data_busca_tab3",
                on_change=_on_edit_data_change,
            )
        with col_btn:
            st.write("")
            st.write("")
            btn_buscar = st.button("🔍 Buscar", key="btn_buscar_vis_tab3")

        # Persiste a data buscada no session_state para que o formulário de edição
        # permaneça visível após o submit (no rerun, btn_buscar volta a False).
        if btn_buscar and data_busca:
            st.session_state['_edit_data_ativo'] = data_busca
            st.session_state.pop('_edit_registro_key', None)

        data_ativa = st.session_state.get('_edit_data_ativo')

        if data_ativa:
            try:
                data_filtro = data_ativa if isinstance(data_ativa, date) else pd.to_datetime(data_ativa).date()
                registros = _buscar_registros_por_data(df_quali, data_filtro)

                if registros.empty:
                    st.error(f"❌ Nenhuma APA encontrada para {data_filtro.strftime('%d/%m/%Y')}")
                    st.session_state.pop('_edit_data_ativo', None)
                    st.session_state.pop('_edit_registro_key', None)
                else:
                    chaves_registros = [
                        _chave_registro_apa(registros.iloc[i], df_quali) for i in range(len(registros))
                    ]

                    if len(registros) > 1:
                        indice_atual = 0
                        registro_ativo = st.session_state.get('_edit_registro_key')
                        if registro_ativo in chaves_registros:
                            indice_atual = chaves_registros.index(registro_ativo)

                        indice_selecionado = st.selectbox(
                            f" {len(registros)} ocorrências nesta data — selecione qual editar",
                            options=list(range(len(registros))),
                            format_func=lambda i: _rotulo_ocorrencia_apa(registros.iloc[i]),
                            index=indice_atual,
                            key="vis_sel_ocorrencia_tab3"
                        )
                        apa = registros.iloc[indice_selecionado]
                        st.session_state['_edit_registro_key'] = chaves_registros[indice_selecionado]
                    else:
                        apa = registros.iloc[0]
                        st.session_state['_edit_registro_key'] = chaves_registros[0]

                    id_limpo = st.session_state.get('_edit_registro_key', 'edit')
                    id_apa = _normalizar_id_apa(apa.get('ID')) or str(apa.get('ID', 'N/D')).strip()

                    st.success(f"✅ APA encontrada! ({id_apa})")

                    st.markdown("---")
                    _render_envio_tecnicas_docx(apa, df_quali, key_prefix=f"edit_{id_limpo}")
                    st.markdown("---")

                    # Mostrar resumo em cards
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("ID", id_apa[:15])
                    with col2:
                        st.metric("Negociador", str(apa.get('Negociador Principal', 'N/D'))[:15])
                    with col3:
                        st.metric("Tipologia", str(apa.get('Tipologia', 'N/D'))[:15])
                    with col4:
                        st.metric("Resolução", str(apa.get('Resolução', 'N/D'))[:12])
                    
                    st.markdown("---")
                    
                    # FORMULÁRIO DE EDIÇÃO
                    st.markdown("### Editar Dados")
                    
                    with st.form(f"form_edit_{id_limpo}", clear_on_submit=False):
                        # Metadados
                        st.markdown("#### Metadados")
                        col1, col2 = st.columns(2)
                        with col1:
                            data_edit = st.date_input(
                                "Data da Ocorrência",
                                value=_normalizar_data_ocorrencia(apa.get('Data da ocorrência')),
                                key=f"edit_data_{id_limpo}",
                            )
                        with col2:
                            modalidade_edit = st.selectbox("Modalidade", [""] + MODALIDADES, index=MODALIDADES.index(apa.get('Modalidade do incidente')) + 1 if apa.get('Modalidade do incidente') in MODALIDADES else 0, key=f"edit_mod_{id_limpo}")
                        
                        col3, col4 = st.columns(2)
                        with col3:
                            tipologia_edit = st.selectbox("Tipologia", [""] + TIPOLOGIAS, index=TIPOLOGIAS.index(apa.get('Tipologia')) + 1 if apa.get('Tipologia') in TIPOLOGIAS else 0, key=f"edit_tip_{id_limpo}")
                        with col4:
                            resolucao_edit = st.selectbox("Resolução", [""] + RESOLUCOES, index=RESOLUCOES.index(apa.get('Resolução')) + 1 if apa.get('Resolução') in RESOLUCOES else 0, key=f"edit_res_{id_limpo}")
                        
                        motivacao_edit = st.text_area("Motivação", value=apa.get('Motivação', ''), key=f"edit_mot_{id_limpo}", height=80)
                        
                        # Equipe
                        st.markdown("#### Equipe de Negociação")
                        col5, col6 = st.columns(2)
                        with col5:
                            neg_principal_edit = st.selectbox("Negociador Principal", [""] + NEGOCIADORES, index=NEGOCIADORES.index(apa.get('Negociador Principal')) + 1 if apa.get('Negociador Principal') in NEGOCIADORES else 0, key=f"edit_np_{id_limpo}")
                        with col6:
                            neg_secundario_edit = st.selectbox("Negociador Secundário", [""] + NEGOCIADORES, index=NEGOCIADORES.index(apa.get('Negociador Secundário')) + 1 if apa.get('Negociador Secundário') in NEGOCIADORES else 0, key=f"edit_ns_{id_limpo}")
                        
                        col7, col8 = st.columns(2)
                        with col7:
                            neg_anotador_edit = st.selectbox("Negociador Anotador", [""] + NEGOCIADORES, index=NEGOCIADORES.index(apa.get('Negociador Anotador')) + 1 if apa.get('Negociador Anotador') in NEGOCIADORES else 0, key=f"edit_na_{id_limpo}")
                        with col8:
                            neg_lider_edit = st.selectbox("Negociador Líder", [""] + NEGOCIADORES, index=NEGOCIADORES.index(apa.get('Negociador Líder')) + 1 if apa.get('Negociador Líder') in NEGOCIADORES else 0, key=f"edit_nl_{id_limpo}")
                        
                        # Transcrições
                        st.markdown("#### Transcrições")
                        trans_causador_edit = st.text_area("Transcrição do Causador", value=apa.get('TRANSCRIÇÃO DO CAUSADOR', ''), key=f"edit_tc_{id_limpo}", height=100)
                        trans_principal_edit = st.text_area("Transcrição do Negociador Principal", value=apa.get('TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL', ''), key=f"edit_tp_{id_limpo}", height=100)
                        trans_secundario_edit = st.text_area("Transcrição do Negociador Secundário", value=apa.get('TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO', ''), key=f"edit_ts_{id_limpo}", height=100)
                        
                        # Info Adicionais
                        st.markdown("#### ℹ️ Informações Adicionais")
                        col9, col10 = st.columns(2)
                        with col9:
                            tempo_real_edit = st.text_input("Tempo de Negociação Real (HH:MM)", value=apa.get('Tempo de Negociação Real', ''), key=f"edit_tr_{id_limpo}")
                        with col10:
                            tempo_tatica_edit = st.text_input("Tempo de Negociação Tática (HH:MM)", value=apa.get('Tempo de Negociação Tática', ''), key=f"edit_tt_{id_limpo}")
                        
                        col11, col12 = st.columns(2)
                        with col11:
                            uniforme_edit = st.selectbox("Uniforme Usado", [""] + UNIFORMES, index=UNIFORMES.index(apa.get('Uniforme Usado')) + 1 if apa.get('Uniforme Usado') in UNIFORMES else 0, key=f"edit_unif_{id_limpo}")
                        with col12:
                            sexo_edit = st.selectbox("Sexo do Causador", [""] + SEXOS, index=SEXOS.index(apa.get('Sexo do Causador')) + 1 if apa.get('Sexo do Causador') in SEXOS else 0, key=f"edit_sex_{id_limpo}")
                        
                        # Funções (em expander para não ficar gigante)
                        with st.expander(" FUNÇÕES - Clique para Expandir", expanded=False):
                            st.markdown("#### NEGOCIADOR PRINCIPAL")
                            col_f1a, col_f1b = st.columns(2)
                            with col_f1a:
                                func_np_edit = st.text_area("Descrição", value=apa.get('FUNÇÕES: NEGOCIADOR PRINCIPAL', ''), key=f"edit_func_np_{id_limpo}", height=80)
                                func_np_problema_edit = st.text_area("Problema Identificado", value=apa.get('FUNÇÕES: NEGOCIADOR PRINCIPAL - PROBLEMA IDENTIFICADO', ''), key=f"edit_func_np_prob_{id_limpo}", height=80)
                            with col_f1b:
                                func_np_acoes_edit = st.text_area("Ações Corretivas", value=apa.get('FUNÇÕES: NEGOCIADOR PRINCIPAL - AÇÕES CORRETIVAS ADOTADAS', ''), key=f"edit_func_np_acao_{id_limpo}", height=80)
                                func_np_praticas_edit = st.text_area("Práticas Promissoras", value=apa.get('FUNÇÕES: NEGOCIADOR PRINCIPAL - PRÁTICAS PROMISSORAS', ''), key=f"edit_func_np_prat_{id_limpo}", height=80)
                            
                            st.markdown("#### NEGOCIADOR SECUNDÁRIO")
                            col_f2a, col_f2b = st.columns(2)
                            with col_f2a:
                                func_ns_edit = st.text_area("Descrição", value=apa.get('FUNÇÕES: NEGOCIADOR SECUNDÁRIO', ''), key=f"edit_func_ns_{id_limpo}", height=80)
                                func_ns_problema_edit = st.text_area("Problema Identificado", value=apa.get('FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PROBLEMA IDENTIFICADO', ''), key=f"edit_func_ns_prob_{id_limpo}", height=80)
                            with col_f2b:
                                func_ns_acoes_edit = st.text_area("Ações Corretivas", value=apa.get('FUNÇÕES: NEGOCIADOR SECUNDÁRIO - AÇÕES CORRETIVAS ADOTADAS', ''), key=f"edit_func_ns_acao_{id_limpo}", height=80)
                                func_ns_praticas_edit = st.text_area("Práticas Promissoras", value=apa.get('FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PRÁTICAS PROMISSORAS', ''), key=f"edit_func_ns_prat_{id_limpo}", height=80)
                            
                            st.markdown("#### NEGOCIADOR ANOTADOR")
                            col_f3a, col_f3b = st.columns(2)
                            with col_f3a:
                                func_na_edit = st.text_area("Descrição", value=apa.get('FUNÇÕES: NEGOCIADOR ANOTADOR', ''), key=f"edit_func_na_{id_limpo}", height=80)
                                func_na_problema_edit = st.text_area("Problema Identificado", value=apa.get('FUNÇÕES: NEGOCIADOR ANOTADOR - PROBLEMA IDENTIFICADO', ''), key=f"edit_func_na_prob_{id_limpo}", height=80)
                            with col_f3b:
                                func_na_acoes_edit = st.text_area("Ações Corretivas", value=apa.get('FUNÇÕES: NEGOCIADOR ANOTADOR - AÇÕES CORRETIVAS ADOTADAS', ''), key=f"edit_func_na_acao_{id_limpo}", height=80)
                                func_na_praticas_edit = st.text_area("Práticas Promissoras", value=apa.get('FUNÇÕES: NEGOCIADOR ANOTADOR - PRÁTICAS PROMISSORAS', ''), key=f"edit_func_na_prat_{id_limpo}", height=80)
                            
                            st.markdown("#### NEGOCIADOR LÍDER")
                            col_f4a, col_f4b = st.columns(2)
                            with col_f4a:
                                func_nl_edit = st.text_area("Descrição", value=apa.get('FUNÇÕES: NEGOCIADOR LÍDER', ''), key=f"edit_func_nl_{id_limpo}", height=80)
                                func_nl_problema_edit = st.text_area("Problema Identificado", value=apa.get('FUNÇÕES: NEGOCIADOR LÍDER - PROBLEMA IDENTIFICADO', ''), key=f"edit_func_nl_prob_{id_limpo}", height=80)
                            with col_f4b:
                                func_nl_acoes_edit = st.text_area("Ações Corretivas", value=apa.get('FUNÇÕES: NEGOCIADOR LÍDER - AÇÕES CORRETIVAS ADOTADAS', ''), key=f"edit_func_nl_acao_{id_limpo}", height=80)
                                func_nl_praticas_edit = st.text_area("Práticas Promissoras", value=apa.get('FUNÇÕES: NEGOCIADOR LÍDER - PRÁTICAS PROMISSORAS', ''), key=f"edit_func_nl_prat_{id_limpo}", height=80)
                            
                            st.markdown("#### AUXILIAR DE LOGÍSTICA")
                            col_f5a, col_f5b = st.columns(2)
                            with col_f5a:
                                func_al_edit = st.text_area("Descrição", value=apa.get('FUNÇÕES: NEGOCIADOR AUXILIAR DE LOGÍSTICA', ''), key=f"edit_func_al_{id_limpo}", height=80)
                                func_al_problema_edit = st.text_area("Problema Identificado", value=apa.get('FUNÇÕES: AUXILIAR DE LOGÍSTICA - PROBLEMA IDENTIFICADO', ''), key=f"edit_func_al_prob_{id_limpo}", height=80)
                            with col_f5b:
                                func_al_acoes_edit = st.text_area("Ações Corretivas", value=apa.get('FUNÇÕES: AUXILIAR DE LOGÍSTICA - AÇÕES CORRETIVAS', ''), key=f"edit_func_al_acao_{id_limpo}", height=80)
                                func_al_praticas_edit = st.text_area("Práticas Promissoras", value=apa.get('FUNÇÕES: AUXILIAR DE LOGÍSTICA - PRÁTICAS PROMISSORAS', ''), key=f"edit_func_al_prat_{id_limpo}", height=80)
                            
                            st.markdown("#### AUXILIAR DE INFORMAÇÕES")
                            col_f6a, col_f6b = st.columns(2)
                            with col_f6a:
                                func_ai_edit = st.text_area("Descrição", value=apa.get('FUNÇÕES: NEGOCIADOR AUXILIAR DE INFORMAÇÕES', ''), key=f"edit_func_ai_{id_limpo}", height=80)
                                func_ai_problema_edit = st.text_area("Problema Identificado", value=apa.get('FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PROBLEMA IDENTIFICADO', ''), key=f"edit_func_ai_prob_{id_limpo}", height=80)
                            with col_f6b:
                                func_ai_acoes_edit = st.text_area("Ações Corretivas", value=apa.get('FUNÇÕES: AUXILIAR DE INFORMAÇÕES - AÇÕES CORRETIVAS', ''), key=f"edit_func_ai_acao_{id_limpo}", height=80)
                                func_ai_praticas_edit = st.text_area("Práticas Promissoras", value=apa.get('FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PRÁTICAS PROMISSORAS', ''), key=f"edit_func_ai_prat_{id_limpo}", height=80)
                            
                            st.markdown("#### PROFISSIONAL DE SAÚDE MENTAL")
                            col_f7a, col_f7b = st.columns(2)
                            with col_f7a:
                                func_psm_edit = st.text_area("Descrição", value=apa.get('FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL', ''), key=f"edit_func_psm_{id_limpo}", height=80)
                                func_psm_problema_edit = st.text_area("Problema Identificado", value=apa.get('FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PROBLEMA IDENTIFICADO', ''), key=f"edit_func_psm_prob_{id_limpo}", height=80)
                            with col_f7b:
                                func_psm_acoes_edit = st.text_area("Ações Corretivas", value=apa.get('FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - AÇÕES CORRETIVAS ADOTADAS', ''), key=f"edit_func_psm_acao_{id_limpo}", height=80)
                                func_psm_praticas_edit = st.text_area("Práticas Promissoras", value=apa.get('FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PRÁTICAS PROMISSORAS', ''), key=f"edit_func_psm_prat_{id_limpo}", height=80)
                        
                        # Botões
                        col_salvar, col_cancelar = st.columns(2)
                        with col_salvar:
                            btn_salvar = st.form_submit_button("💾 SALVAR ALTERAÇÕES", use_container_width=True, type="secondary")
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
                                "Negociador Anotador": neg_anotador_edit or "",
                                "Negociador Líder": neg_lider_edit or "",
                                "TRANSCRIÇÃO DO CAUSADOR": trans_causador_edit or "",
                                "TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL": trans_principal_edit or "",
                                "TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO": trans_secundario_edit or "",
                                "Tempo de Negociação Real": tempo_real_edit or "",
                                "Tempo de Negociação Tática": tempo_tatica_edit or "",
                                "Uniforme Usado": uniforme_edit or "",
                                "Sexo do Causador": sexo_edit or "",
                                # Funções - Negociador Principal
                                "FUNÇÕES: NEGOCIADOR PRINCIPAL": func_np_edit or "",
                                "FUNÇÕES: NEGOCIADOR PRINCIPAL - PROBLEMA IDENTIFICADO": func_np_problema_edit or "",
                                "FUNÇÕES: NEGOCIADOR PRINCIPAL - AÇÕES CORRETIVAS ADOTADAS": func_np_acoes_edit or "",
                                "FUNÇÕES: NEGOCIADOR PRINCIPAL - PRÁTICAS PROMISSORAS": func_np_praticas_edit or "",
                                # Funções - Negociador Secundário
                                "FUNÇÕES: NEGOCIADOR SECUNDÁRIO": func_ns_edit or "",
                                "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PROBLEMA IDENTIFICADO": func_ns_problema_edit or "",
                                "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - AÇÕES CORRETIVAS ADOTADAS": func_ns_acoes_edit or "",
                                "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PRÁTICAS PROMISSORAS": func_ns_praticas_edit or "",
                                # Funções - Negociador Anotador
                                "FUNÇÕES: NEGOCIADOR ANOTADOR": func_na_edit or "",
                                "FUNÇÕES: NEGOCIADOR ANOTADOR - PROBLEMA IDENTIFICADO": func_na_problema_edit or "",
                                "FUNÇÕES: NEGOCIADOR ANOTADOR - AÇÕES CORRETIVAS ADOTADAS": func_na_acoes_edit or "",
                                "FUNÇÕES: NEGOCIADOR ANOTADOR - PRÁTICAS PROMISSORAS": func_na_praticas_edit or "",
                                # Funções - Negociador Líder
                                "FUNÇÕES: NEGOCIADOR LÍDER": func_nl_edit or "",
                                "FUNÇÕES: NEGOCIADOR LÍDER - PROBLEMA IDENTIFICADO": func_nl_problema_edit or "",
                                "FUNÇÕES: NEGOCIADOR LÍDER - AÇÕES CORRETIVAS ADOTADAS": func_nl_acoes_edit or "",
                                "FUNÇÕES: NEGOCIADOR LÍDER - PRÁTICAS PROMISSORAS": func_nl_praticas_edit or "",
                                # Funções - Auxiliar de Logística
                                "FUNÇÕES: NEGOCIADOR AUXILIAR DE LOGÍSTICA": func_al_edit or "",
                                "FUNÇÕES: AUXILIAR DE LOGÍSTICA - PROBLEMA IDENTIFICADO": func_al_problema_edit or "",
                                "FUNÇÕES: AUXILIAR DE LOGÍSTICA - AÇÕES CORRETIVAS": func_al_acoes_edit or "",
                                "FUNÇÕES: AUXILIAR DE LOGÍSTICA - PRÁTICAS PROMISSORAS": func_al_praticas_edit or "",
                                # Funções - Auxiliar de Informações
                                "FUNÇÕES: NEGOCIADOR AUXILIAR DE INFORMAÇÕES": func_ai_edit or "",
                                "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PROBLEMA IDENTIFICADO": func_ai_problema_edit or "",
                                "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - AÇÕES CORRETIVAS": func_ai_acoes_edit or "",
                                "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PRÁTICAS PROMISSORAS": func_ai_praticas_edit or "",
                                # Funções - Profissional de Saúde Mental
                                "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL": func_psm_edit or "",
                                "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PROBLEMA IDENTIFICADO": func_psm_problema_edit or "",
                                "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - AÇÕES CORRETIVAS ADOTADAS": func_psm_acoes_edit or "",
                                "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PRÁTICAS PROMISSORAS": func_psm_praticas_edit or "",
                            }
                            
                            # Remover vazios e None (campos não preenchidos não devem sobrescrever dados)
                            payload_update = {
                                k: v for k, v in payload_update.items()
                                if v is not None and v != "" and not (isinstance(v, float) and pd.isna(v))
                            }

                            record_id_interno = _resolver_record_id_apa(apa, df_quali)

                            # Diagnóstico visível para facilitar depuração
                            with st.expander("🔍 Diagnóstico (expandir se houver erro)", expanded=False):
                                st.write(f"**record_id_interno:** `{record_id_interno}`")
                                st.write(f"**id_apa:** `{id_apa}`")
                                st.write(f"**data_busca:** `{data_filtro.strftime('%d/%m/%Y')}`")
                                st.write(f"**Campos no payload:** {list(payload_update.keys())}")

                            if not payload_update:
                                st.warning("⚠️ Nenhum campo foi alterado. Não há dados para salvar.")
                            else:
                                # Atualizar no Airtable
                                try:
                                    resultado = airtable_link.atualizar_apa_validacao(
                                        id_apa,
                                        payload_update,
                                        record_id_interno=record_id_interno
                                    )
                                    if resultado:
                                        st.success("✅ Dados atualizados com sucesso!")
                                        # Invalida cache para forçar recarga na próxima navegação
                                        st.session_state.pop("df_quali", None)
                                        st.balloons()
                                    else:
                                        st.error(
                                            "❌ APA não encontrada na base de dados. "
                                            "Expanda o diagnóstico acima e verifique o record_id_interno."
                                        )
                                except (RuntimeError, ValueError) as e:
                                    st.error(f"❌ Erro do Airtable: {str(e)}")
                                except Exception as e:
                                    st.error(f"❌ Erro inesperado: {type(e).__name__}: {str(e)}")
            
            except Exception as e:
                st.error(f"Erro: {str(e)}")

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
    </div>
    """, unsafe_allow_html=True)