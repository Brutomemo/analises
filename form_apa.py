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
import database
import separador_apa
import utils


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

# Nomes exatos das colunas no Supabase / CSV (atenção aos espaços duplos)
CAMPOS_CHEGADA = {
    "agr_np": "12 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A AGRESSIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA",
    "agr_ns": "12 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A AGRESSIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA",
    "agr_nl": "12 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A AGRESSIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA",
    "rec_np": "13 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A RECEPTIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA",
    "rec_ns": "13 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A RECEPTIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA",
    "rec_nl": "13 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A RECEPTIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA",
}
CAMPOS_ENCERRAMENTO = {
    "agr_np": "24 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A AGRESSIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA",
    "agr_ns": "24 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A AGRESSIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA",
    "agr_nl": "24 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A AGRESSIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA",
    "rec_np": "25 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A RECEPTIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA",
    "rec_ns": "25 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A RECEPTIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA",
    "rec_nl": "25 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A RECEPTIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA",
}


def _converter_tempo_para_segundos(valor_str):
    """Converte HH:MM para segundos. Retorna None se vazio."""
    if not valor_str or str(valor_str).strip() == "":
        return None
    try:
        partes = str(valor_str).strip().split(":")
        h = int(partes[0])
        m = int(partes[1]) if len(partes) > 1 else 0
        return (h * 3600) + (m * 60)
    except:
        return None

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


def _formatar_lista_apas(df_apas):
    if df_apas is None or df_apas.empty:
        return ""
    partes = []
    for _, row in df_apas.iterrows():
        id_a = _vinculo_id_apa(row) or _normalizar_id_apa(row.get("ID")) or "?"
        neg = row.get("Negociador Principal")
        sufixo = f" — {neg}" if neg is not None and not (isinstance(neg, float) and pd.isna(neg)) and str(neg).strip() else ""
        partes.append(f"**{id_a}**{sufixo}")
    return ", ".join(partes)


def _payload_funcoes_criar():
    """Lê campos de funções do session_state (chaves c_func_*)."""
    mapa = {
        "FUNÇÕES: NEGOCIADOR PRINCIPAL": "c_func_np",
        "FUNÇÕES: NEGOCIADOR PRINCIPAL - PROBLEMA IDENTIFICADO": "c_func_np_problema",
        "FUNÇÕES: NEGOCIADOR PRINCIPAL - AÇÕES CORRETIVAS ADOTADAS": "c_func_np_acoes",
        "FUNÇÕES: NEGOCIADOR PRINCIPAL - PRÁTICAS PROMISSORAS": "c_func_np_praticas",
        "FUNÇÕES: NEGOCIADOR SECUNDÁRIO": "c_func_ns",
        "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PROBLEMA IDENTIFICADO": "c_func_ns_problema",
        "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - AÇÕES CORRETIVAS ADOTADAS": "c_func_ns_acoes",
        "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PRÁTICAS PROMISSORAS": "c_func_ns_praticas",
        "FUNÇÕES: NEGOCIADOR ANOTADOR": "c_func_na",
        "FUNÇÕES: NEGOCIADOR ANOTADOR - PROBLEMA IDENTIFICADO": "c_func_na_problema",
        "FUNÇÕES: NEGOCIADOR ANOTADOR - AÇÕES CORRETIVAS ADOTADAS": "c_func_na_acoes",
        "FUNÇÕES: NEGOCIADOR ANOTADOR - PRÁTICAS PROMISSORAS": "c_func_na_praticas",
        "FUNÇÕES: NEGOCIADOR LÍDER": "c_func_nl",
        "FUNÇÕES: NEGOCIADOR LÍDER - PROBLEMA IDENTIFICADO": "c_func_nl_problema",
        "FUNÇÕES: NEGOCIADOR LÍDER - AÇÕES CORRETIVAS ADOTADAS": "c_func_nl_acoes",
        "FUNÇÕES: NEGOCIADOR LÍDER - PRÁTICAS PROMISSORAS": "c_func_nl_praticas",
        "FUNÇÕES: NEGOCIADOR AUXILIAR DE LOGÍSTICA": "c_func_al",
        "FUNÇÕES: AUXILIAR DE LOGÍSTICA - PROBLEMA IDENTIFICADO": "c_func_al_problema",
        "FUNÇÕES: AUXILIAR DE LOGÍSTICA - AÇÕES CORRETIVAS": "c_func_al_acoes",
        "FUNÇÕES: AUXILIAR DE LOGÍSTICA - PRÁTICAS PROMISSORAS": "c_func_al_praticas",
        "FUNÇÕES: NEGOCIADOR AUXILIAR DE INFORMAÇÕES": "c_func_ai",
        "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PROBLEMA IDENTIFICADO": "c_func_ai_problema",
        "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - AÇÕES CORRETIVAS": "c_func_ai_acoes",
        "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PRÁTICAS PROMISSORAS": "c_func_ai_praticas",
        "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL": "c_func_psm",
        "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PROBLEMA IDENTIFICADO": "c_func_psm_problema",
        "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - AÇÕES CORRETIVAS ADOTADAS": "c_func_psm_acoes",
        "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PRÁTICAS PROMISSORAS": "c_func_psm_praticas",
    }
    return {campo: (st.session_state.get(_criar_key(chave)) or "") for campo, chave in mapa.items()}


def _invalidar_dados_app():
    """Força recarga dos DataFrames e indicadores após gravação."""
    database.invalidar_cache_completo()
    st.session_state.pop("df_quali", None)
    st.session_state.pop("df_tec", None)
    st.session_state.pop("status_q", None)
    st.session_state.pop("status_t", None)


def _resolver_record_id_apa(apa, df_quali=None):
    """Obtém o UUID da APA no Supabase."""
    for campo in ('Airtable_Record_ID', 'record_id_airtable', 'id'):
        valor = apa.get(campo)
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            continue
        valor_str = str(valor).strip()
        if valor_str and valor_str.lower() != 'nan':
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
                if valor_str and valor_str.lower() != 'nan':
                    return valor_str

    id_ref = _normalizar_id_apa(id_campo) or id_campo
    return database.buscar_apa_uuid(id_ref)


def _vinculo_id_apa(apa):
    """ID usado no campo Vinculo_APA (mesmo formato da aba de análise: ID_Busca)."""
    return utils.limpar_id(apa.get('ID'))


def _texto_campo(val) -> str:
    """Normaliza valor de campo textual (evita 'nan' / None / NaN no formulário)."""
    if val is None:
        return ""
    try:
        if isinstance(val, float) and pd.isna(val):
            return ""
    except (TypeError, ValueError):
        pass
    texto = str(val).strip()
    if not texto or texto.lower() in {"nan", "none", "null"}:
        return ""
    return texto


def _indice_opcao(opcoes, valor, com_vazio=False):
    """Índice seguro para selectbox a partir do valor atual da APA."""
    texto = _texto_campo(valor)
    base = ([""] + list(opcoes)) if com_vazio else list(opcoes)
    if texto in base:
        return base.index(texto)
    return 0


def _criar_tecnica_supabase(apa_uuid, payload):
    """Grava uma técnica no Supabase vinculada à APA."""
    return database.criar_tecnica(payload, apa_id=apa_uuid)


def _inserir_tecnicas_extraidas(
    df_tecnicas,
    apa,
    df_quali=None,
    progress_bar=None,
    substituir=True,
):
    """
    Insere técnicas extraídas do .docx no Supabase, vinculadas à APA selecionada.

    Se substituir=True e já houver técnicas, remove as existentes antes de inserir
    (evita duplicar o primeiro registro ao reenviar o .docx).
    """
    vinculo_id = _vinculo_id_apa(apa)
    if not vinculo_id:
        return 0, len(df_tecnicas), [
            "Não foi possível identificar o ID da APA para o vínculo. Recarregue os dados do Supabase."
        ]

    apa_uuid = _resolver_record_id_apa(apa, df_quali)
    if not apa_uuid:
        return 0, len(df_tecnicas), [
            f"APA {vinculo_id}: registro não encontrado no Supabase. "
            "Recarregue a página (F5) e selecione a APA novamente."
        ]

    detalhes_erros = []
    if substituir:
        removidas, erro_del = database.deletar_tecnicas_por_apa(apa_uuid)
        if erro_del:
            return 0, len(df_tecnicas), [f"Falha ao substituir técnicas anteriores: {erro_del}"]
        if removidas:
            detalhes_erros.append(f"Removidas {removidas} técnica(s) anterior(es) antes do reenvio.")

    sucesso_count = 0
    erro_count = 0
    total = len(df_tecnicas)

    for n, (_, row) in enumerate(df_tecnicas.iterrows()):
        tecnica = str(row.get('TÉCNICAS', '')).strip()
        trecho = str(row.get('TRECHO DA TRANSCRIÇÃO', '')).strip()

        if not tecnica or re.match(r'^escolher\s+um\s+item\.?$', tecnica, re.I):
            # Linha placeholder do Word — não grava
            if progress_bar is not None and total:
                progress_bar.progress((n + 1) / total)
            continue

        if not trecho:
            trecho = "[Trecho não extraído do documento — revise a tabela no .docx]"

        payload = {
            "TÉCNICAS": tecnica,
            "TRECHO DA TRANSCRIÇÃO": trecho,
        }

        atitude = row.get('ATITUDE DO CAUSADOR')
        if atitude is not None and not (isinstance(atitude, float) and pd.isna(atitude)):
            if str(atitude).strip() != "":
                try:
                    payload["ATITUDE DO CAUSADOR"] = int(atitude)
                except (ValueError, TypeError):
                    detalhes_erros.append(f"{tecnica}: atitude inválida ({atitude!r}).")

        ok, erro = _criar_tecnica_supabase(apa_uuid, payload)
        if ok:
            sucesso_count += 1
        else:
            erro_count += 1
            detalhes_erros.append(f"{tecnica}: {erro or 'erro desconhecido'}")

        if progress_bar is not None and total:
            progress_bar.progress((n + 1) / total)

    return sucesso_count, erro_count, detalhes_erros


def _aplicar_transcricoes_nos_campos_edit(id_limpo, transcricoes, sobrescrever=False):
    """
    Preenche os text_area de edição com falas extraídas do .docx.
    Por padrão só preenche campos ainda vazios (não carregados anteriormente).
    """
    mapa = {
        "causador": f"edit_tc_{id_limpo}",
        "negociador_principal": f"edit_tp_{id_limpo}",
        "negociador_secundario": f"edit_ts_{id_limpo}",
    }
    labels = {
        "causador": "TRANSCRIÇÃO DO CAUSADOR",
        "negociador_principal": "TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL",
        "negociador_secundario": "TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO",
    }
    aplicados = {}
    for papel, key in mapa.items():
        novo = _texto_campo((transcricoes or {}).get(papel, ""))
        if not novo:
            continue
        atual = _texto_campo(st.session_state.get(key, ""))
        if sobrescrever or not atual:
            st.session_state[key] = novo
            aplicados[labels[papel]] = novo
    return aplicados


def _limpar_cache_tecnicas_docx():
    """Remove técnicas/transcrições em cache e força reset do file_uploader no próximo render."""
    st.session_state.pop("tecnicas_extraidas_apa", None)
    st.session_state.pop("transcricoes_extraidas_apa", None)
    st.session_state["_tecnicas_uploader_reset"] = st.session_state.get("_tecnicas_uploader_reset", 0) + 1


def _limpar_tela_visualizar_editar():
    """Limpa busca, formulário de edição e cache de técnicas .docx da aba Visualizar & Editar."""
    for key in (
        "_edit_data_ativo",
        "_edit_registro_key",
        "vis_sel_ocorrencia_tab3",
    ):
        st.session_state.pop(key, None)
    # Libera widgets de transcrição / seed para a próxima busca hidratar do Supabase
    for key in list(st.session_state.keys()):
        if (
            key.startswith("edit_tc_")
            or key.startswith("edit_tp_")
            or key.startswith("edit_ts_")
            or key.startswith("_trans_seeded_")
        ):
            st.session_state.pop(key, None)
    _limpar_cache_tecnicas_docx()


def _criar_form_rev():
    return st.session_state.get("_criar_apa_form_rev", 0)


def _criar_key(nome):
    """Chave versionada do formulário Criar — nova revisão = widgets novos no navegador."""
    return f"{nome}__{_criar_form_rev()}"


def _limpar_formulario_criar():
    """Limpa todos os campos da aba Criar Novo Registro."""
    for key in list(st.session_state.keys()):
        if (
            key.startswith("c_")
            or key.startswith("ext_")
            or key.startswith("uploader_apa")
        ):
            st.session_state.pop(key, None)
    _limpar_cache_tecnicas_docx()
    st.session_state["_criar_apa_form_rev"] = _criar_form_rev() + 1


def _render_envio_tecnicas_docx(apa, df_quali, key_prefix):
    """
    Upload .docx na Visualizar & Editar:
    - extrai técnicas e transcrições
    - preenche campos de transcrição vazios (sem apagar o que já existe)
    - permite reenviar técnicas substituindo as anteriores (sem duplicar)
    """
    id_apa = str(apa.get('ID', 'N/D')).strip()
    id_limpo = key_prefix.replace("edit_", "", 1) if key_prefix.startswith("edit_") else key_prefix
    vinculo_id = _vinculo_id_apa(apa)
    apa_uuid = _resolver_record_id_apa(apa, df_quali)

    st.markdown("##### Upload do .docx — Técnicas e Transcrições")

    if vinculo_id and apa_uuid:
        st.info(f"🔗 Vínculo confirmado: APA **{vinculo_id}** → `{apa_uuid}`")
    elif vinculo_id:
        st.error(
            f"❌ APA **{vinculo_id}** encontrada, mas o UUID não foi localizado "
            "no Supabase. Recarregue os dados e confira se a APA existe na base."
        )
    else:
        st.error(
            "❌ Não foi possível identificar o ID desta APA. "
            "Recarregue a página para atualizar os dados do Supabase e tente novamente."
        )

    # Sanitiza 'nan' já presente nos widgets de transcrição desta APA
    for key in (f"edit_tc_{id_limpo}", f"edit_tp_{id_limpo}", f"edit_ts_{id_limpo}"):
        if key in st.session_state:
            st.session_state[key] = _texto_campo(st.session_state.get(key))

    df_tec_cache = st.session_state.get('tecnicas_extraidas_apa')
    trans_cache = st.session_state.get('transcricoes_extraidas_apa') or {}
    uploader_reset = st.session_state.get("_tecnicas_uploader_reset", 0)
    sig_key = f"_docx_sig_{key_prefix}"
    applied_key = f"_docx_trans_applied_{key_prefix}"

    arq_tec = st.file_uploader(
        "Upload do .docx da APA (extrai técnicas e transcrições)",
        type=["docx", "docm"],
        key=f"uploader_tec_{key_prefix}_{uploader_reset}",
    )
    if arq_tec:
        file_sig = f"{arq_tec.name}:{arq_tec.size}"
        if st.session_state.get(sig_key) != file_sig:
            with st.spinner("Extraindo técnicas e transcrições..."):
                res = separador_apa.processar_apa(arq_tec.read())

            if res['erro']:
                st.error(f"❌ {res['erro']}")
                st.session_state.pop(sig_key, None)
            else:
                st.session_state[sig_key] = file_sig
                st.session_state[applied_key] = None

                df_res = res.get('tecnicas')
                if df_res is not None and not df_res.empty:
                    st.session_state['tecnicas_extraidas_apa'] = df_res
                else:
                    st.session_state.pop('tecnicas_extraidas_apa', None)
                    st.warning("⚠️ Nenhuma técnica encontrada no arquivo.")

                st.session_state['transcricoes_extraidas_apa'] = res.get('transcricoes') or {}

        df_tec_cache = st.session_state.get('tecnicas_extraidas_apa')
        trans_cache = st.session_state.get('transcricoes_extraidas_apa') or {}

        n_palavras = {
            k: len(_texto_campo(v).split())
            for k, v in (trans_cache or {}).items()
            if _texto_campo(v)
        }
        if n_palavras:
            st.success(
                "✅ Transcrições extraídas: "
                + ", ".join(f"{k} ({n} palavras)" for k, n in n_palavras.items())
            )
        elif st.session_state.get(sig_key) == file_sig:
            st.warning(
                "⚠️ Nenhuma fala colorida encontrada na seção Transcrição. "
                "Confira o .docx (causador=vermelho, principal=azul, secundário=verde)."
            )

        if df_tec_cache is not None and not getattr(df_tec_cache, "empty", True):
            st.success(f"✅ {len(df_tec_cache)} técnicas extraídas e prontas para envio.")

        sobrescrever_trans = st.checkbox(
            "Sobrescrever transcrições já preenchidas nesta APA",
            value=True,
            key=f"chk_overwrite_trans_{key_prefix}",
            help="Marcado: substitui o texto atual pelo diálogo extraído do .docx.",
        )
        apply_sig = f"{st.session_state.get(sig_key)}:{sobrescrever_trans}"
        if (
            st.session_state.get(sig_key)
            and st.session_state.get(applied_key) != apply_sig
            and any(_texto_campo(v) for v in (trans_cache or {}).values())
        ):
            # Sempre limpa as chaves dos widgets antes de injetar (Streamlit
            # restaura valor antigo do text_area e bloqueia o texto novo).
            for k in (f"edit_tc_{id_limpo}", f"edit_tp_{id_limpo}", f"edit_ts_{id_limpo}"):
                atual = _texto_campo(st.session_state.get(k))
                if sobrescrever_trans or not atual:
                    st.session_state.pop(k, None)

            aplicados = _aplicar_transcricoes_nos_campos_edit(
                id_limpo, trans_cache, sobrescrever=sobrescrever_trans
            )
            # Permite o bloco de UI re-hidratar/aceitar o texto injetado no próximo rerun
            st.session_state.pop(f"_trans_seeded_{id_limpo}", None)
            campos_ok = any(
                _texto_campo(st.session_state.get(k))
                for k in (f"edit_tc_{id_limpo}", f"edit_tp_{id_limpo}", f"edit_ts_{id_limpo}")
            )
            if aplicados or campos_ok:
                st.session_state[applied_key] = apply_sig

            if aplicados and apa_uuid:
                atuais_db = {
                    "TRANSCRIÇÃO DO CAUSADOR": _texto_campo(apa.get("TRANSCRIÇÃO DO CAUSADOR")),
                    "TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL": _texto_campo(
                        apa.get("TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL")
                    ),
                    "TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO": _texto_campo(
                        apa.get("TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO")
                    ),
                }
                payload_trans = {
                    campo: texto
                    for campo, texto in aplicados.items()
                    if sobrescrever_trans or not atuais_db.get(campo)
                }
                if payload_trans:
                    try:
                        database.atualizar_apa_validacao(
                            id_apa, payload_trans, record_id_interno=apa_uuid
                        )
                        st.session_state["_trans_gravadas_msg"] = (
                            "💾 Transcrições gravadas na APA: "
                            + ", ".join(payload_trans.keys())
                        )
                        # Recarrega df_quali para os campos refletirem o banco
                        _invalidar_dados_app()
                    except Exception as exc:
                        st.session_state["_trans_gravadas_msg"] = (
                            f"Transcrições nos campos, mas falha ao gravar: {exc}"
                        )
                st.rerun()

        msg_trans = st.session_state.pop("_trans_gravadas_msg", None)
        if msg_trans:
            st.info(msg_trans)

    if (df_tec_cache is None or getattr(df_tec_cache, "empty", True)) and not any(
        _texto_campo(v) for v in (trans_cache or {}).values()
    ):
        st.info(
            "Faça upload do .docx acima para carregar **técnicas** e **transcrições** "
            "nesta APA já registrada."
        )
        return

    if df_tec_cache is not None and not getattr(df_tec_cache, "empty", True):
        st.metric("Técnicas prontas para envio", len(df_tec_cache))
        sem_trecho = int(
            (df_tec_cache['TRECHO DA TRANSCRIÇÃO'].fillna('').astype(str).str.strip() == '').sum()
        )
        if sem_trecho:
            st.warning(
                f"⚠️ {sem_trecho} técnica(s) sem trecho extraído — serão enviadas com aviso no campo trecho. "
                "Reenvie o .docx após conferir a tabela de técnicas."
            )
        st.dataframe(df_tec_cache, use_container_width=True, hide_index=True)

        n_existentes = 0
        if apa_uuid:
            try:
                n_existentes = len(database.buscar_tecnicas_por_apa(apa_uuid))
            except Exception:
                n_existentes = 0

        substituir = st.checkbox(
            "Substituir técnicas já cadastradas (recomendado — evita duplicar)",
            value=True,
            key=f"chk_subst_tec_{key_prefix}",
            help=(
                "Marcado: remove as técnicas atuais desta APA e grava as do .docx. "
                "Desmarcado: apenas adiciona (pode duplicar)."
            ),
        )
        if n_existentes and substituir:
            st.caption(
                f"Serão removidas **{n_existentes}** técnica(s) já cadastrada(s) antes do novo envio."
            )

        rotulo_btn = (
            f"✔️ Substituir por {len(df_tec_cache)} técnicas em {id_apa}"
            if substituir
            else f"✔️ Enviar {len(df_tec_cache)} técnicas para {id_apa}"
        )
        if st.button(
            rotulo_btn,
            key=f"btn_enviar_tec_{key_prefix}",
            use_container_width=True,
            type="secondary",
            disabled=not (vinculo_id and apa_uuid),
        ):
            with st.spinner(f"💾 Gravando {len(df_tec_cache)} técnicas..."):
                progress = st.progress(0)
                sucesso, erros, detalhes = _inserir_tecnicas_extraidas(
                    df_tec_cache,
                    apa,
                    df_quali=df_quali,
                    progress_bar=progress,
                    substituir=substituir,
                )
                progress.empty()

            if erros == 0:
                st.session_state["_tecnicas_enviadas_msg"] = (
                    f"✅ {sucesso} técnicas gravadas e vinculadas à APA **{vinculo_id}** "
                    f"(`{apa_uuid}`)."
                )
                st.session_state.pop(sig_key, None)
                st.session_state.pop(applied_key, None)
                _invalidar_dados_app()
                _limpar_cache_tecnicas_docx()
                st.rerun()
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
        st.caption(
            "Esta aba **sempre cria um registro novo** no Supabase (ID autonumérico). "
            "Para alterar uma APA existente, use **Visualizar & Editar**."
        )

        _, col_clear_top = st.columns([4, 1])
        with col_clear_top:
            st.button(
                "❌ Limpar Tudo",
                use_container_width=True,
                key="btn_clear_aba1",
                on_click=_limpar_formulario_criar,
            )
        
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
                data_oca = st.date_input("Data da Ocorrência *", key=_criar_key("c_data"))
            with col2:
                modalidade = st.selectbox("Modalidade do Incidente *", [""] + MODALIDADES, key=_criar_key("c_modalidade"))
            
            col3, col4 = st.columns(2)
            with col3:
                tipologia = st.selectbox("Tipologia *", [""] + TIPOLOGIAS, key=_criar_key("c_tipologia"))
            with col4:
                forma_transicao = st.selectbox("Forma de Transição", [""] + FORMAS_TRANSICAO, key=_criar_key("c_forma_transicao"))
            
            motivacao = st.text_area("Motivação", placeholder="...", height=80, key=_criar_key("c_motivacao"))
            resolucao = st.selectbox("Resolução *", [""] + RESOLUCOES, key=_criar_key("c_resolucao"))
        
        # ─── EQUIPE ───
        with tab_equipe:
            col1, col2 = st.columns(2)
            with col1:
                neg_principal = st.selectbox("Negociador Principal *", [""] + NEGOCIADORES, key=_criar_key("c_neg_principal"))
            with col2:
                neg_secundario = st.selectbox("Negociador Secundário", [""] + NEGOCIADORES, key=_criar_key("c_neg_secundario"))
            
            col3, col4 = st.columns(2)
            with col3:
                neg_anotador = st.selectbox("Negociador Anotador", [""] + NEGOCIADORES, key=_criar_key("c_neg_anotador"))
            with col4:
                neg_lider = st.selectbox("Negociador Líder", [""] + NEGOCIADORES, key=_criar_key("c_neg_lider"))
            
            col5, col6 = st.columns(2)
            with col5:
                aux_info = st.selectbox("Auxiliar de Informações", [""] + NEGOCIADORES, key=_criar_key("c_aux_info"))
            with col6:
                aux_log = st.selectbox("Auxiliar de Logística", [""] + NEGOCIADORES, key=_criar_key("c_aux_log"))
            
            prof_saude = st.selectbox("Profissional de Saúde Mental", [""] + SAUDE_MENTAL, key=_criar_key("c_prof_saude"))
        
        # ─── PERCEPÇÃO CHEGADA ───
        with tab_chegada:
            st.markdown("**Negociador Principal**")
            col1, col2 = st.columns(2)
            with col1:
                agr_principal_chegada = st.selectbox("12 - Agressividade", PERCEPCOES_AGRESSIVIDADE, key=_criar_key("c_agr_principal_chegada"))
            with col2:
                rec_principal_chegada = st.selectbox("13 - Receptividade", PERCEPCOES_RECEPTIVIDADE, key=_criar_key("c_rec_principal_chegada"))
            
            st.markdown("**Negociador Secundário**")
            col3, col4 = st.columns(2)
            with col3:
                agr_secundario_chegada = st.selectbox("12 - Agressividade", PERCEPCOES_AGRESSIVIDADE, key=_criar_key("c_agr_secundario_chegada"))
            with col4:
                rec_secundario_chegada = st.selectbox("13 - Receptividade", PERCEPCOES_RECEPTIVIDADE, key=_criar_key("c_rec_secundario_chegada"))
            
            st.markdown("**Negociador Líder**")
            col5, col6 = st.columns(2)
            with col5:
                agr_lider_chegada = st.selectbox("12 - Agressividade", PERCEPCOES_AGRESSIVIDADE, key=_criar_key("c_agr_lider_chegada"))
            with col6:
                rec_lider_chegada = st.selectbox("13 - Receptividade", PERCEPCOES_RECEPTIVIDADE, key=_criar_key("c_rec_lider_chegada"))
        
        # ─── PERCEPÇÃO ENCERRAMENTO ───
        with tab_enc:
            st.markdown("**Negociador Principal**")
            col1, col2 = st.columns(2)
            with col1:
                agr_principal_enc = st.selectbox("24 - Agressividade", PERCEPCOES_AGRESSIVIDADE, key=_criar_key("c_agr_principal_enc"))
            with col2:
                rec_principal_enc = st.selectbox("25 - Receptividade", PERCEPCOES_RECEPTIVIDADE, key=_criar_key("c_rec_principal_enc"))
            
            st.markdown("**Negociador Secundário**")
            col3, col4 = st.columns(2)
            with col3:
                agr_secundario_enc = st.selectbox("24 - Agressividade", PERCEPCOES_AGRESSIVIDADE, key=_criar_key("c_agr_secundario_enc"))
            with col4:
                rec_secundario_enc = st.selectbox("25 - Receptividade", PERCEPCOES_RECEPTIVIDADE, key=_criar_key("c_rec_secundario_enc"))
            
            st.markdown("**Negociador Líder**")
            col5, col6 = st.columns(2)
            with col5:
                agr_lider_enc = st.selectbox("24 - Agressividade", PERCEPCOES_AGRESSIVIDADE, key=_criar_key("c_agr_lider_enc"))
            with col6:
                rec_lider_enc = st.selectbox("25 - Receptividade", PERCEPCOES_RECEPTIVIDADE, key=_criar_key("c_rec_lider_enc"))
        
        # ─── TRANSCRIÇÕES ───
        with tab_trans:
            separador_apa.render_separador()
            st.markdown("---")
            trans_causador = st.text_area("Transcrição do Causador", placeholder="...", height=100, key=_criar_key("c_trans_causador"))
            trans_principal = st.text_area("Transcrição do Negociador Principal", placeholder="...", height=100, key=_criar_key("c_trans_principal"))
            trans_secundario = st.text_area("Transcrição do Negociador Secundário", placeholder="...", height=100, key=_criar_key("c_trans_secundario"))
        
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
                    "Descrição", placeholder="...", height=68, key=_criar_key(f"{prefixo}")
                )
                with st.expander("📋 Problema / Ações / Práticas"):
                    locals()[f"{prefixo}_problema"] = st.text_area(
                        "Problema Identificado", placeholder="...", height=68, key=_criar_key(f"{prefixo}_problema")
                    )
                    locals()[f"{prefixo}_acoes"] = st.text_area(
                        "Ações Corretivas", placeholder="...", height=68, key=_criar_key(f"{prefixo}_acoes")
                    )
                    locals()[f"{prefixo}_praticas"] = st.text_area(
                        "Práticas Promissoras", placeholder="...", height=68, key=_criar_key(f"{prefixo}_praticas")
                    )
                st.markdown("---")
        
        # ─── INFO ADICIONAIS ───
        with tab_obs:
            col1, col2 = st.columns(2)
            with col1:
                tempo_real = st.text_input("Tempo de Negociação Real (HH:MM)", placeholder="Ex: 01:30", key=_criar_key("c_tempo_real"))
            with col2:
                tempo_tatica = st.text_input("Tempo de Negociação Tática (HH:MM)", placeholder="Ex: 00:45", key=_criar_key("c_tempo_tatica"))
            
            col3, col4 = st.columns(2)
            with col3:
                uniforme = st.selectbox("Uniforme Usado", [""] + UNIFORMES, key=_criar_key("c_uniforme"))
            with col4:
                sexo = st.selectbox("Sexo do Causador", [""] + SEXOS, key=_criar_key("c_sexo"))
        
        # BOTÕES DE AÇÃO
        st.markdown("---")

        existentes_na_data = (
            _buscar_registros_por_data(df_quali, data_oca) if data_oca else pd.DataFrame()
        )
        if not existentes_na_data.empty:
            st.warning(
                f"⚠️ Já existe(m) APA(s) em **{data_oca.strftime('%d/%m/%Y')}**: "
                f"{_formatar_lista_apas(existentes_na_data)}. "
                "Se a intenção é **atualizar** uma delas, vá em **Visualizar & Editar**. "
                "Clicar em **Criar** abaixo gera outro registro (novo ID no Supabase), "
                "mesmo com os mesmos dados — isso parece duplicata."
            )
            st.checkbox(
                "Confirmo: quero criar um **novo** registro nesta data (não editar o existente)",
                key=_criar_key("c_confirmar_nova_apa_duplicada"),
            )

        col_save, _ = st.columns(2)

        with col_save:
            if st.button("✅ CRIAR REGISTRO DE APA", use_container_width=True, type="secondary", key="btn_criar_aba1"):

                if not existentes_na_data.empty and not st.session_state.get(_criar_key("c_confirmar_nova_apa_duplicada")):
                    st.error(
                        "Marque a confirmação acima antes de criar outro registro na mesma data."
                    )
                elif st.session_state.get("_apa_create_lock"):
                    st.warning("Aguarde — a criação anterior ainda está em processamento.")
                else:
                    st.session_state["_apa_create_lock"] = True
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
                                **_payload_funcoes_criar(),
                                "Tempo de Negociação Real": tempo_real or "",
                                "Tempo de Negociação Tática": tempo_tatica or "",
                                "Uniforme Usado": uniforme or "",
                                "Sexo do Causador": sexo or "",
                            }

                            payload = {k: v for k, v in payload.items() if v is not None and v != ""}

                            resultado = database.criar_nova_apa(payload)
                            id_apa = resultado.get("id") if isinstance(resultado, dict) else resultado
                            erro = resultado.get("erro") if isinstance(resultado, dict) else None

                            if id_apa:
                                st.session_state.id_apa_criado = id_apa
                                _invalidar_dados_app()
                                st.session_state.pop(_criar_key("c_confirmar_nova_apa_duplicada"), None)
                                rec_novo = resultado.get("record_id") if isinstance(resultado, dict) else None
                                msg = f"✅ NOVO registro criado: **{st.session_state.id_apa_criado}**"
                                if rec_novo:
                                    msg += f" (`{rec_novo}`)"
                                st.success(msg)
                                st.caption(
                                    "Este é um ID novo no Supabase. "
                                    "Para enviar técnicas, use **Visualizar & Editar** e selecione esta APA."
                                )
                            else:
                                st.error(f"❌ Falha ao criar APA: {erro or 'Erro desconhecido.'}")

                        except Exception as e:
                            st.error(f"❌ Erro: {str(e)}")
                            import traceback
                            traceback.print_exc()
                        finally:
                            st.session_state.pop("_apa_create_lock", None)
    
    # ─────────────────────────────────────────────────────────────
    # ABA 2: VISUALIZAR & EDITAR (COM FORMULÁRIO)
    # ─────────────────────────────────────────────────────────────
    
    with tab2:
        st.markdown("### Visualizar & Editar APA")

        msg_tecnicas_ok = st.session_state.pop("_tecnicas_enviadas_msg", None)
        if msg_tecnicas_ok:
            st.success(msg_tecnicas_ok)

        def _on_edit_data_change():
            st.session_state['_edit_data_ativo'] = st.session_state['vis_data_busca_tab3']
            st.session_state.pop('_edit_registro_key', None)

        if 'vis_data_busca_tab3' not in st.session_state:
            st.session_state['vis_data_busca_tab3'] = st.session_state.get('_edit_data_ativo', date.today())

        col_data_busca, col_btn_buscar, col_btn_limpar = st.columns([3, 1, 1])
        with col_data_busca:
            data_busca = st.date_input(
                "Data da Ocorrência",
                key="vis_data_busca_tab3",
                on_change=_on_edit_data_change,
            )
        with col_btn_buscar:
            st.write("")
            st.write("")
            btn_buscar = st.button("🔍 Buscar", key="btn_buscar_vis_tab3", use_container_width=True)
        with col_btn_limpar:
            st.write("")
            st.write("")
            btn_limpar = st.button("🧹 Limpar", key="btn_limpar_vis_tab3", use_container_width=True)

        if btn_limpar:
            _limpar_tela_visualizar_editar()
            st.rerun()

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

                    tecnicas_apa = database.buscar_tecnicas_por_apa(
                        _resolver_record_id_apa(apa, df_quali) or id_apa
                    )
                    st.caption(
                        f"**{len(tecnicas_apa)}** técnica(s) cadastrada(s) no Supabase para esta APA."
                    )

                    st.markdown("---")
                    _render_envio_tecnicas_docx(apa, df_quali, key_prefix=f"edit_{id_limpo}")
                    st.markdown("---")

                    # Mostrar resumo em cards
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("ID", id_apa[:15])
                    with col2:
                        st.metric(
                            "Negociador",
                            (_texto_campo(apa.get('Negociador Principal')) or 'N/D')[:15],
                        )
                    with col3:
                        st.metric(
                            "Tipologia",
                            (_texto_campo(apa.get('Tipologia')) or 'N/D')[:15],
                        )
                    with col4:
                        st.metric(
                            "Resolução",
                            (_texto_campo(apa.get('Resolução')) or 'N/D')[:12],
                        )
                    
                    st.markdown("---")

                    # Hidrata session_state das transcrições ANTES dos widgets
                    # (fora do form para o upload .docx conseguir injetar texto).
                    _mapa_trans_edit = (
                        (f"edit_tc_{id_limpo}", "TRANSCRIÇÃO DO CAUSADOR", "causador"),
                        (f"edit_tp_{id_limpo}", "TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL", "negociador_principal"),
                        (f"edit_ts_{id_limpo}", "TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO", "negociador_secundario"),
                    )
                    _trans_cache_ui = st.session_state.get("transcricoes_extraidas_apa") or {}
                    _chk_overwrite = f"chk_overwrite_trans_edit_{id_limpo}"
                    _sobrescrever_ui = bool(st.session_state.get(_chk_overwrite, False))
                    _seed_key = f"_trans_seeded_{id_limpo}"

                    def _injetar_trans_widget(chave_widget: str, texto: str) -> None:
                        """Pop + set: Streamlit ignora assignment se a key do widget já veio vazia do browser."""
                        texto = _texto_campo(texto)
                        st.session_state.pop(chave_widget, None)
                        st.session_state[chave_widget] = texto

                    for _k, _campo, _papel in _mapa_trans_edit:
                        db_val = _texto_campo(apa.get(_campo))
                        extraido = _texto_campo(_trans_cache_ui.get(_papel, ""))
                        atual = _texto_campo(st.session_state.get(_k)) if _k in st.session_state else ""

                        if extraido and _sobrescrever_ui:
                            _injetar_trans_widget(_k, extraido)
                        elif (not st.session_state.get(_seed_key)) or (not atual):
                            preenchimento = db_val or extraido
                            if preenchimento and preenchimento != atual:
                                _injetar_trans_widget(_k, preenchimento)
                            elif _k not in st.session_state:
                                st.session_state[_k] = ""
                    st.session_state[_seed_key] = True

                    # FORMULÁRIO DE EDIÇÃO (mesma sequência do Criar, sem editar o nº da APA)
                    st.markdown("### Editar Dados")
                    st.caption(f"APA **{id_apa}** (número somente leitura)")
                    
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
                            modalidade_edit = st.selectbox(
                                "Modalidade",
                                [""] + MODALIDADES,
                                index=_indice_opcao(MODALIDADES, apa.get('Modalidade do incidente'), com_vazio=True),
                                key=f"edit_mod_{id_limpo}",
                            )
                        
                        col3, col4 = st.columns(2)
                        with col3:
                            tipologia_edit = st.selectbox(
                                "Tipologia",
                                [""] + TIPOLOGIAS,
                                index=_indice_opcao(TIPOLOGIAS, apa.get('Tipologia'), com_vazio=True),
                                key=f"edit_tip_{id_limpo}",
                            )
                        with col4:
                            forma_transicao_edit = st.selectbox(
                                "Forma de Transição",
                                [""] + FORMAS_TRANSICAO,
                                index=_indice_opcao(FORMAS_TRANSICAO, apa.get('Forma de Transição'), com_vazio=True),
                                key=f"edit_ft_{id_limpo}",
                            )

                        motivacao_edit = st.text_area(
                            "Motivação",
                            value=_texto_campo(apa.get('Motivação')),
                            key=f"edit_mot_{id_limpo}",
                            height=80,
                        )
                        resolucao_edit = st.selectbox(
                            "Resolução",
                            [""] + RESOLUCOES,
                            index=_indice_opcao(RESOLUCOES, apa.get('Resolução'), com_vazio=True),
                            key=f"edit_res_{id_limpo}",
                        )
                        
                        # Equipe
                        st.markdown("#### Equipe de Negociação")
                        col5, col6 = st.columns(2)
                        with col5:
                            neg_principal_edit = st.selectbox(
                                "Negociador Principal",
                                [""] + NEGOCIADORES,
                                index=_indice_opcao(NEGOCIADORES, apa.get('Negociador Principal'), com_vazio=True),
                                key=f"edit_np_{id_limpo}",
                            )
                        with col6:
                            neg_secundario_edit = st.selectbox(
                                "Negociador Secundário",
                                [""] + NEGOCIADORES,
                                index=_indice_opcao(NEGOCIADORES, apa.get('Negociador Secundário'), com_vazio=True),
                                key=f"edit_ns_{id_limpo}",
                            )
                        
                        col7, col8 = st.columns(2)
                        with col7:
                            neg_anotador_edit = st.selectbox(
                                "Negociador Anotador",
                                [""] + NEGOCIADORES,
                                index=_indice_opcao(NEGOCIADORES, apa.get('Negociador Anotador'), com_vazio=True),
                                key=f"edit_na_{id_limpo}",
                            )
                        with col8:
                            neg_lider_edit = st.selectbox(
                                "Negociador Líder",
                                [""] + NEGOCIADORES,
                                index=_indice_opcao(NEGOCIADORES, apa.get('Negociador Líder'), com_vazio=True),
                                key=f"edit_nl_{id_limpo}",
                            )

                        col_eq5, col_eq6 = st.columns(2)
                        with col_eq5:
                            aux_info_edit = st.selectbox(
                                "Auxiliar de Informações",
                                [""] + NEGOCIADORES,
                                index=_indice_opcao(
                                    NEGOCIADORES, apa.get('Negociador Auxiliar de Informações'), com_vazio=True
                                ),
                                key=f"edit_ai_{id_limpo}",
                            )
                        with col_eq6:
                            aux_log_edit = st.selectbox(
                                "Auxiliar de Logística",
                                [""] + NEGOCIADORES,
                                index=_indice_opcao(
                                    NEGOCIADORES, apa.get('Negociador Auxiliar de Logística'), com_vazio=True
                                ),
                                key=f"edit_al_{id_limpo}",
                            )
                        prof_saude_edit = st.selectbox(
                            "Profissional de Saúde Mental",
                            [""] + SAUDE_MENTAL,
                            index=_indice_opcao(
                                SAUDE_MENTAL, apa.get('Profissional de Saúde Mental'), com_vazio=True
                            ),
                            key=f"edit_psm_sel_{id_limpo}",
                        )

                        # Chegada (percepções 12/13)
                        st.markdown("#### Chegada")
                        st.markdown("**Negociador Principal**")
                        c_ch1, c_ch2 = st.columns(2)
                        with c_ch1:
                            agr_np_cheg = st.selectbox(
                                "12 - Agressividade",
                                PERCEPCOES_AGRESSIVIDADE,
                                index=_indice_opcao(
                                    PERCEPCOES_AGRESSIVIDADE, apa.get(CAMPOS_CHEGADA["agr_np"])
                                ),
                                key=f"edit_agr_np_ch_{id_limpo}",
                            )
                        with c_ch2:
                            rec_np_cheg = st.selectbox(
                                "13 - Receptividade",
                                PERCEPCOES_RECEPTIVIDADE,
                                index=_indice_opcao(
                                    PERCEPCOES_RECEPTIVIDADE, apa.get(CAMPOS_CHEGADA["rec_np"])
                                ),
                                key=f"edit_rec_np_ch_{id_limpo}",
                            )
                        st.markdown("**Negociador Secundário**")
                        c_ch3, c_ch4 = st.columns(2)
                        with c_ch3:
                            agr_ns_cheg = st.selectbox(
                                "12 - Agressividade",
                                PERCEPCOES_AGRESSIVIDADE,
                                index=_indice_opcao(
                                    PERCEPCOES_AGRESSIVIDADE, apa.get(CAMPOS_CHEGADA["agr_ns"])
                                ),
                                key=f"edit_agr_ns_ch_{id_limpo}",
                            )
                        with c_ch4:
                            rec_ns_cheg = st.selectbox(
                                "13 - Receptividade",
                                PERCEPCOES_RECEPTIVIDADE,
                                index=_indice_opcao(
                                    PERCEPCOES_RECEPTIVIDADE, apa.get(CAMPOS_CHEGADA["rec_ns"])
                                ),
                                key=f"edit_rec_ns_ch_{id_limpo}",
                            )
                        st.markdown("**Negociador Líder**")
                        c_ch5, c_ch6 = st.columns(2)
                        with c_ch5:
                            agr_nl_cheg = st.selectbox(
                                "12 - Agressividade",
                                PERCEPCOES_AGRESSIVIDADE,
                                index=_indice_opcao(
                                    PERCEPCOES_AGRESSIVIDADE, apa.get(CAMPOS_CHEGADA["agr_nl"])
                                ),
                                key=f"edit_agr_nl_ch_{id_limpo}",
                            )
                        with c_ch6:
                            rec_nl_cheg = st.selectbox(
                                "13 - Receptividade",
                                PERCEPCOES_RECEPTIVIDADE,
                                index=_indice_opcao(
                                    PERCEPCOES_RECEPTIVIDADE, apa.get(CAMPOS_CHEGADA["rec_nl"])
                                ),
                                key=f"edit_rec_nl_ch_{id_limpo}",
                            )

                        # Encerramento (percepções 24/25)
                        st.markdown("#### Encerramento")
                        st.markdown("**Negociador Principal**")
                        c_en1, c_en2 = st.columns(2)
                        with c_en1:
                            agr_np_enc = st.selectbox(
                                "24 - Agressividade",
                                PERCEPCOES_AGRESSIVIDADE,
                                index=_indice_opcao(
                                    PERCEPCOES_AGRESSIVIDADE, apa.get(CAMPOS_ENCERRAMENTO["agr_np"])
                                ),
                                key=f"edit_agr_np_en_{id_limpo}",
                            )
                        with c_en2:
                            rec_np_enc = st.selectbox(
                                "25 - Receptividade",
                                PERCEPCOES_RECEPTIVIDADE,
                                index=_indice_opcao(
                                    PERCEPCOES_RECEPTIVIDADE, apa.get(CAMPOS_ENCERRAMENTO["rec_np"])
                                ),
                                key=f"edit_rec_np_en_{id_limpo}",
                            )
                        st.markdown("**Negociador Secundário**")
                        c_en3, c_en4 = st.columns(2)
                        with c_en3:
                            agr_ns_enc = st.selectbox(
                                "24 - Agressividade",
                                PERCEPCOES_AGRESSIVIDADE,
                                index=_indice_opcao(
                                    PERCEPCOES_AGRESSIVIDADE, apa.get(CAMPOS_ENCERRAMENTO["agr_ns"])
                                ),
                                key=f"edit_agr_ns_en_{id_limpo}",
                            )
                        with c_en4:
                            rec_ns_enc = st.selectbox(
                                "25 - Receptividade",
                                PERCEPCOES_RECEPTIVIDADE,
                                index=_indice_opcao(
                                    PERCEPCOES_RECEPTIVIDADE, apa.get(CAMPOS_ENCERRAMENTO["rec_ns"])
                                ),
                                key=f"edit_rec_ns_en_{id_limpo}",
                            )
                        st.markdown("**Negociador Líder**")
                        c_en5, c_en6 = st.columns(2)
                        with c_en5:
                            agr_nl_enc = st.selectbox(
                                "24 - Agressividade",
                                PERCEPCOES_AGRESSIVIDADE,
                                index=_indice_opcao(
                                    PERCEPCOES_AGRESSIVIDADE, apa.get(CAMPOS_ENCERRAMENTO["agr_nl"])
                                ),
                                key=f"edit_agr_nl_en_{id_limpo}",
                            )
                        with c_en6:
                            rec_nl_enc = st.selectbox(
                                "25 - Receptividade",
                                PERCEPCOES_RECEPTIVIDADE,
                                index=_indice_opcao(
                                    PERCEPCOES_RECEPTIVIDADE, apa.get(CAMPOS_ENCERRAMENTO["rec_nl"])
                                ),
                                key=f"edit_rec_nl_en_{id_limpo}",
                            )
                        
                        # Info Adicionais
                        st.markdown("#### Informações Adicionais")
                        col9, col10 = st.columns(2)
                        with col9:
                            tempo_real_edit = st.text_input(
                                "Tempo de Negociação Real (HH:MM)",
                                value=utils.tempo_para_exibicao_hhmm(apa.get("Tempo de Negociação Real", "")),
                                key=f"edit_tr_{id_limpo}",
                            )
                        with col10:
                            tempo_tatica_edit = st.text_input(
                                "Tempo de Negociação Tática (HH:MM)",
                                value=utils.tempo_para_exibicao_hhmm(apa.get("Tempo de Negociação Tática", "")),
                                key=f"edit_tt_{id_limpo}",
                            )
                        
                        col11, col12 = st.columns(2)
                        with col11:
                            uniforme_edit = st.selectbox(
                                "Uniforme Usado",
                                [""] + UNIFORMES,
                                index=_indice_opcao(UNIFORMES, apa.get('Uniforme Usado'), com_vazio=True),
                                key=f"edit_unif_{id_limpo}",
                            )
                        with col12:
                            sexo_edit = st.selectbox(
                                "Sexo do Causador",
                                [""] + SEXOS,
                                index=_indice_opcao(SEXOS, apa.get('Sexo do Causador'), com_vazio=True),
                                key=f"edit_sex_{id_limpo}",
                            )

                        # Transcrições (após Info Adicionais; valores hidratados antes do form)
                        st.markdown("#### Transcrições")
                        _n_chars = {
                            "Causador": len(_texto_campo(st.session_state.get(f"edit_tc_{id_limpo}"))),
                            "Principal": len(_texto_campo(st.session_state.get(f"edit_tp_{id_limpo}"))),
                            "Secundário": len(_texto_campo(st.session_state.get(f"edit_ts_{id_limpo}"))),
                        }
                        if any(_n_chars.values()):
                            st.caption(
                                "Carregado do Supabase — "
                                + ", ".join(f"{k}: {n:,} caracteres" for k, n in _n_chars.items() if n)
                            )
                        else:
                            st.caption(
                                "Nenhuma transcrição no Supabase para esta APA. "
                                "Envie o .docx acima ou preencha manualmente."
                            )
                        st.text_area(
                            "Transcrição do Causador",
                            key=f"edit_tc_{id_limpo}",
                            height=180,
                        )
                        st.text_area(
                            "Transcrição do Negociador Principal",
                            key=f"edit_tp_{id_limpo}",
                            height=180,
                        )
                        st.text_area(
                            "Transcrição do Negociador Secundário",
                            key=f"edit_ts_{id_limpo}",
                            height=180,
                        )
                        
                        # Funções (em expander para não ficar gigante)
                        with st.expander("Funções — clique para expandir", expanded=False):
                            st.markdown("#### NEGOCIADOR PRINCIPAL")
                            col_f1a, col_f1b = st.columns(2)
                            with col_f1a:
                                func_np_edit = st.text_area("Descrição", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR PRINCIPAL')), key=f"edit_func_np_{id_limpo}", height=80)
                                func_np_problema_edit = st.text_area("Problema Identificado", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR PRINCIPAL - PROBLEMA IDENTIFICADO')), key=f"edit_func_np_prob_{id_limpo}", height=80)
                            with col_f1b:
                                func_np_acoes_edit = st.text_area("Ações Corretivas", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR PRINCIPAL - AÇÕES CORRETIVAS ADOTADAS')), key=f"edit_func_np_acao_{id_limpo}", height=80)
                                func_np_praticas_edit = st.text_area("Práticas Promissoras", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR PRINCIPAL - PRÁTICAS PROMISSORAS')), key=f"edit_func_np_prat_{id_limpo}", height=80)
                            
                            st.markdown("#### NEGOCIADOR SECUNDÁRIO")
                            col_f2a, col_f2b = st.columns(2)
                            with col_f2a:
                                func_ns_edit = st.text_area("Descrição", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR SECUNDÁRIO')), key=f"edit_func_ns_{id_limpo}", height=80)
                                func_ns_problema_edit = st.text_area("Problema Identificado", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PROBLEMA IDENTIFICADO')), key=f"edit_func_ns_prob_{id_limpo}", height=80)
                            with col_f2b:
                                func_ns_acoes_edit = st.text_area("Ações Corretivas", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR SECUNDÁRIO - AÇÕES CORRETIVAS ADOTADAS')), key=f"edit_func_ns_acao_{id_limpo}", height=80)
                                func_ns_praticas_edit = st.text_area("Práticas Promissoras", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PRÁTICAS PROMISSORAS')), key=f"edit_func_ns_prat_{id_limpo}", height=80)
                            
                            st.markdown("#### NEGOCIADOR ANOTADOR")
                            col_f3a, col_f3b = st.columns(2)
                            with col_f3a:
                                func_na_edit = st.text_area("Descrição", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR ANOTADOR')), key=f"edit_func_na_{id_limpo}", height=80)
                                func_na_problema_edit = st.text_area("Problema Identificado", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR ANOTADOR - PROBLEMA IDENTIFICADO')), key=f"edit_func_na_prob_{id_limpo}", height=80)
                            with col_f3b:
                                func_na_acoes_edit = st.text_area("Ações Corretivas", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR ANOTADOR - AÇÕES CORRETIVAS ADOTADAS')), key=f"edit_func_na_acao_{id_limpo}", height=80)
                                func_na_praticas_edit = st.text_area("Práticas Promissoras", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR ANOTADOR - PRÁTICAS PROMISSORAS')), key=f"edit_func_na_prat_{id_limpo}", height=80)
                            
                            st.markdown("#### NEGOCIADOR LÍDER")
                            col_f4a, col_f4b = st.columns(2)
                            with col_f4a:
                                func_nl_edit = st.text_area("Descrição", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR LÍDER')), key=f"edit_func_nl_{id_limpo}", height=80)
                                func_nl_problema_edit = st.text_area("Problema Identificado", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR LÍDER - PROBLEMA IDENTIFICADO')), key=f"edit_func_nl_prob_{id_limpo}", height=80)
                            with col_f4b:
                                func_nl_acoes_edit = st.text_area("Ações Corretivas", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR LÍDER - AÇÕES CORRETIVAS ADOTADAS')), key=f"edit_func_nl_acao_{id_limpo}", height=80)
                                func_nl_praticas_edit = st.text_area("Práticas Promissoras", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR LÍDER - PRÁTICAS PROMISSORAS')), key=f"edit_func_nl_prat_{id_limpo}", height=80)
                            
                            st.markdown("#### AUXILIAR DE LOGÍSTICA")
                            col_f5a, col_f5b = st.columns(2)
                            with col_f5a:
                                func_al_edit = st.text_area("Descrição", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR AUXILIAR DE LOGÍSTICA')), key=f"edit_func_al_{id_limpo}", height=80)
                                func_al_problema_edit = st.text_area("Problema Identificado", value=_texto_campo(apa.get('FUNÇÕES: AUXILIAR DE LOGÍSTICA - PROBLEMA IDENTIFICADO')), key=f"edit_func_al_prob_{id_limpo}", height=80)
                            with col_f5b:
                                func_al_acoes_edit = st.text_area("Ações Corretivas", value=_texto_campo(apa.get('FUNÇÕES: AUXILIAR DE LOGÍSTICA - AÇÕES CORRETIVAS')), key=f"edit_func_al_acao_{id_limpo}", height=80)
                                func_al_praticas_edit = st.text_area("Práticas Promissoras", value=_texto_campo(apa.get('FUNÇÕES: AUXILIAR DE LOGÍSTICA - PRÁTICAS PROMISSORAS')), key=f"edit_func_al_prat_{id_limpo}", height=80)
                            
                            st.markdown("#### AUXILIAR DE INFORMAÇÕES")
                            col_f6a, col_f6b = st.columns(2)
                            with col_f6a:
                                func_ai_edit = st.text_area("Descrição", value=_texto_campo(apa.get('FUNÇÕES: NEGOCIADOR AUXILIAR DE INFORMAÇÕES')), key=f"edit_func_ai_{id_limpo}", height=80)
                                func_ai_problema_edit = st.text_area("Problema Identificado", value=_texto_campo(apa.get('FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PROBLEMA IDENTIFICADO')), key=f"edit_func_ai_prob_{id_limpo}", height=80)
                            with col_f6b:
                                func_ai_acoes_edit = st.text_area("Ações Corretivas", value=_texto_campo(apa.get('FUNÇÕES: AUXILIAR DE INFORMAÇÕES - AÇÕES CORRETIVAS')), key=f"edit_func_ai_acao_{id_limpo}", height=80)
                                func_ai_praticas_edit = st.text_area("Práticas Promissoras", value=_texto_campo(apa.get('FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PRÁTICAS PROMISSORAS')), key=f"edit_func_ai_prat_{id_limpo}", height=80)
                            
                            st.markdown("#### PROFISSIONAL DE SAÚDE MENTAL")
                            col_f7a, col_f7b = st.columns(2)
                            with col_f7a:
                                func_psm_edit = st.text_area("Descrição", value=_texto_campo(apa.get('FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL')), key=f"edit_func_psm_{id_limpo}", height=80)
                                func_psm_problema_edit = st.text_area("Problema Identificado", value=_texto_campo(apa.get('FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PROBLEMA IDENTIFICADO')), key=f"edit_func_psm_prob_{id_limpo}", height=80)
                            with col_f7b:
                                func_psm_acoes_edit = st.text_area("Ações Corretivas", value=_texto_campo(apa.get('FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - AÇÕES CORRETIVAS ADOTADAS')), key=f"edit_func_psm_acao_{id_limpo}", height=80)
                                func_psm_praticas_edit = st.text_area("Práticas Promissoras", value=_texto_campo(apa.get('FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PRÁTICAS PROMISSORAS')), key=f"edit_func_psm_prat_{id_limpo}", height=80)
                        
                        # Botões
                        col_salvar, col_cancelar = st.columns(2)
                        with col_salvar:
                            btn_salvar = st.form_submit_button("💾 SALVAR ALTERAÇÕES", use_container_width=True, type="secondary")
                        with col_cancelar:
                            btn_cancelar = st.form_submit_button("❌ CANCELAR", use_container_width=True)
                        
                        if btn_salvar:
                            # Preparar payload de atualização (mesmos campos do Criar, exceto nº da APA)
                            payload_update = {
                                "Data da ocorrência": data_edit.isoformat() if data_edit else "",
                                "Modalidade do incidente": modalidade_edit or "",
                                "Tipologia": tipologia_edit or "",
                                "Forma de Transição": forma_transicao_edit or "",
                                "Resolução": resolucao_edit or "",
                                "Motivação": motivacao_edit or "",
                                "Negociador Principal": neg_principal_edit or "",
                                "Negociador Secundário": neg_secundario_edit or "",
                                "Negociador Anotador": neg_anotador_edit or "",
                                "Negociador Líder": neg_lider_edit or "",
                                "Negociador Auxiliar de Informações": aux_info_edit or "",
                                "Negociador Auxiliar de Logística": aux_log_edit or "",
                                "Profissional de Saúde Mental": prof_saude_edit or "",
                                CAMPOS_CHEGADA["agr_np"]: agr_np_cheg,
                                CAMPOS_CHEGADA["agr_ns"]: agr_ns_cheg,
                                CAMPOS_CHEGADA["agr_nl"]: agr_nl_cheg,
                                CAMPOS_CHEGADA["rec_np"]: rec_np_cheg,
                                CAMPOS_CHEGADA["rec_ns"]: rec_ns_cheg,
                                CAMPOS_CHEGADA["rec_nl"]: rec_nl_cheg,
                                CAMPOS_ENCERRAMENTO["agr_np"]: agr_np_enc,
                                CAMPOS_ENCERRAMENTO["agr_ns"]: agr_ns_enc,
                                CAMPOS_ENCERRAMENTO["agr_nl"]: agr_nl_enc,
                                CAMPOS_ENCERRAMENTO["rec_np"]: rec_np_enc,
                                CAMPOS_ENCERRAMENTO["rec_ns"]: rec_ns_enc,
                                CAMPOS_ENCERRAMENTO["rec_nl"]: rec_nl_enc,
                                "TRANSCRIÇÃO DO CAUSADOR": _texto_campo(
                                    st.session_state.get(f"edit_tc_{id_limpo}")
                                ),
                                "TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL": _texto_campo(
                                    st.session_state.get(f"edit_tp_{id_limpo}")
                                ),
                                "TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO": _texto_campo(
                                    st.session_state.get(f"edit_ts_{id_limpo}")
                                ),
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
                                # Atualizar no Supabase
                                try:
                                    resultado = database.atualizar_apa_validacao(
                                        id_apa,
                                        payload_update,
                                        record_id_interno=record_id_interno
                                    )
                                    if resultado:
                                        st.success("✅ Dados atualizados com sucesso!")
                                        _invalidar_dados_app()
                                    else:
                                        st.error(
                                            "❌ APA não encontrada na base de dados. "
                                            "Expanda o diagnóstico acima e verifique o record_id_interno."
                                        )
                                except (RuntimeError, ValueError) as e:
                                    st.error(f"❌ Erro do Supabase: {str(e)}")
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