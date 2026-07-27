# ============================================================
# database.py — conexão Supabase + consultas cacheadas (Streamlit)
# ============================================================

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from supabase import Client, create_client

ROOT_DIR = Path(__file__).resolve().parent
ENV_LOCAL_PATH = ROOT_DIR / ".env.local"

TABELA_APAS = "apas"
TABELA_TECNICAS = "tecnicas"
CACHE_TTL = 300

# PostgreSQL (snake_case) → nomes legados esperados pelo app (ex-Airtable)
MAPA_APA_PARA_LEGADO: dict[str, str] = {
    "id_numero": "ID",
    "data_ocorrencia": "Data da ocorrência",
    "modalidade_incidente": "Modalidade do incidente",
    "tipologia": "Tipologia",
    "motivacao": "Motivação",
    "forma_transicao": "Forma de Transição",
    "resolucao": "Resolução",
    "negociador_principal": "Negociador Principal",
    "negociador_secundario": "Negociador Secundário",
    "negociador_anotador": "Negociador Anotador",
    "negociador_lider": "Negociador Líder",
    "negociador_aux_info": "Negociador Auxiliar de Informações",
    "negociador_aux_log": "Negociador Auxiliar de Logística",
    "prof_saude_mental": "Profissional de Saúde Mental",
    "percep_agr_principal_chegada": "12 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A AGRESSIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA",
    "percep_agr_secundario_chegada": "12 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A AGRESSIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA",
    "percep_agr_terceiro_chegada": "12 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A AGRESSIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA",
    "percep_rec_principal_chegada": "13 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A RECEPTIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA",
    "percep_rec_secundario_chegada": "13 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A RECEPTIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA",
    "percep_rec_terceiro_chegada": "13 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A RECEPTIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA",
    "percep_agr_principal_encerramento": "24 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A AGRESSIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA",
    "percep_agr_secundario_encerramento": "24 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A AGRESSIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA",
    "percep_agr_terceiro_encerramento": "24 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A AGRESSIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA",
    "percep_rec_principal_encerramento": "25 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A RECEPTIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA",
    "percep_rec_secundario_encerramento": "25 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A RECEPTIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA",
    "percep_rec_terceiro_encerramento": "25 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A RECEPTIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA",
    "transcricao_causador": "TRANSCRIÇÃO DO CAUSADOR",
    "transcricao_principal": "TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL",
    "transcricao_secundario": "TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO",
    "tempo_negociacao_real_seg": "Tempo de Negociação Real",
    "tempo_negociacao_tatica_seg": "Tempo de Negociação Tática",
    "uniforme_usado": "Uniforme Usado",
    "sexo_causador": "Sexo do Causador",
}


def _carregar_env_local() -> None:
    if not ENV_LOCAL_PATH.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(ENV_LOCAL_PATH)
    except ImportError:
        pass


def _secret(key: str) -> str | None:
    try:
        val = st.secrets.get(key)
        if val:
            return str(val).strip()
    except Exception:
        pass
    return None


def _env(key: str) -> str | None:
    val = os.getenv(key)
    return str(val).strip() if val else None


def resolve_credentials() -> tuple[str, str]:
    """
    Prioridade: st.secrets → variáveis de ambiente (.env.local).
    """
    _carregar_env_local()

    url = (
        _secret("SUPABASE_URL")
        or _secret("NEXT_PUBLIC_SUPABASE_URL")
        or _secret("SUPABASE_PROJECT_URL")
        or _env("SUPABASE_URL")
        or _env("NEXT_PUBLIC_SUPABASE_URL")
        or _env("SUPABASE_PROJECT_URL")
    )
    key = (
        _secret("SUPABASE_KEY")
        or _secret("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or _secret("SUPABASE_SERVICE_ROLE_KEY")
        or _env("SUPABASE_KEY")
        or _env("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or _env("SUPABASE_SERVICE_ROLE_KEY")
    )

    if not url or not key:
        raise RuntimeError(
            "Credenciais Supabase não configuradas. "
            "Defina SUPABASE_URL e SUPABASE_KEY (ou NEXT_PUBLIC_*) em st.secrets ou .env.local."
        )
    return url, key


@st.cache_resource
def get_supabase_client() -> Client:
    url, key = resolve_credentials()
    return create_client(url, key)


def limpar_cache() -> None:
    fetch_apas.clear()
    fetch_tecnicas.clear()
    fetch_tecnicas_com_apa.clear()


@st.cache_data(ttl=CACHE_TTL)
def fetch_apas() -> pd.DataFrame:
    """Retorna todas as APAs registradas (colunas snake_case do PostgreSQL)."""
    client = get_supabase_client()
    response = client.table(TABELA_APAS).select("*").execute()
    return pd.DataFrame(response.data or [])


@st.cache_data(ttl=CACHE_TTL)
def fetch_tecnicas() -> pd.DataFrame:
    """Retorna todas as técnicas gravadas (colunas snake_case)."""
    client = get_supabase_client()
    response = client.table(TABELA_TECNICAS).select("*").execute()
    return pd.DataFrame(response.data or [])


@st.cache_data(ttl=CACHE_TTL)
def fetch_tecnicas_com_apa() -> pd.DataFrame:
    """Técnicas com dados da APA associada (join via apa_id)."""
    df_tec = fetch_tecnicas()
    df_apa = fetch_apas()

    if df_tec.empty:
        return df_tec
    if df_apa.empty:
        return df_tec

    cols_apa = [
        c
        for c in df_apa.columns
        if c not in ("created_at", "updated_at", "funcoes_dados")
    ]
    df_join = df_tec.merge(
        df_apa[cols_apa],
        left_on="apa_id",
        right_on="id",
        how="left",
        suffixes=("", "_apa"),
    )

    if "negociador_principal" in df_join.columns:
        df_join["NEGOCIADOR PRINCIPAL"] = df_join["negociador_principal"]
        df_join["Negociador Principal do incidente crítico"] = df_join["negociador_principal"]
    if "tipologia" in df_join.columns:
        df_join["Tipologia do incidente crítico"] = df_join["tipologia"]
    if "modalidade_incidente" in df_join.columns:
        df_join["Modalidade do incidente crítico"] = df_join["modalidade_incidente"]
    if "id_numero" in df_join.columns:
        df_join["Vinculo_APA"] = df_join["id_numero"]

    return df_join


def test_connection() -> tuple[bool, int, int, str]:
    """
    Testa a conexão e retorna (ok, total_apas, total_tecnicas, mensagem).
    """
    try:
        client = get_supabase_client()
        apas = client.table(TABELA_APAS).select("id", count="exact").limit(1).execute()
        tecs = client.table(TABELA_TECNICAS).select("id", count="exact").limit(1).execute()
        n_apas = apas.count if apas.count is not None else len(fetch_apas())
        n_tecs = tecs.count if tecs.count is not None else len(fetch_tecnicas())
        return True, int(n_apas), int(n_tecs), "Conexão Supabase OK"
    except Exception as exc:
        return False, 0, 0, str(exc)


def _expandir_funcoes_dados(row: pd.Series, destino: dict[str, Any]) -> None:
    bruto = row.get("funcoes_dados")
    if bruto is None or (isinstance(bruto, float) and pd.isna(bruto)):
        return
    if isinstance(bruto, str):
        try:
            bruto = json.loads(bruto)
        except json.JSONDecodeError:
            return
    if isinstance(bruto, dict):
        for chave, valor in bruto.items():
            if valor is not None and str(valor).strip():
                destino[str(chave)] = valor


def apas_para_formato_app(df: pd.DataFrame) -> pd.DataFrame:
    """Converte APAs do Supabase para o formato legado consumido pelo app."""
    if df.empty:
        return pd.DataFrame()

    registros: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        item: dict[str, Any] = {}

        record_id = row.get("id")
        if record_id is not None and not pd.isna(record_id):
            rec_str = str(record_id)
            item["Airtable_Record_ID"] = rec_str
            item["record_id_airtable"] = rec_str

        id_num = row.get("id_numero")
        if id_num is not None and not pd.isna(id_num):
            item["ID"] = f"APA {int(id_num):03d}"

        for col_db, col_legacy in MAPA_APA_PARA_LEGADO.items():
            if col_db == "id_numero":
                continue
            if col_db in row.index and not pd.isna(row[col_db]):
                item[col_legacy] = row[col_db]

        _expandir_funcoes_dados(row, item)
        registros.append(item)

    return pd.DataFrame(registros)


def tecnicas_para_formato_app(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Converte técnicas (com join APA) para o formato legado consumido pelo app."""
    if df is None:
        df = fetch_tecnicas_com_apa()
    if df.empty:
        return pd.DataFrame()

    registros: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        item: dict[str, Any] = {}

        record_id = row.get("id")
        if record_id is not None and not pd.isna(record_id):
            item["Airtable_Record_ID"] = str(record_id)

        if "tecnica" in row.index and not pd.isna(row["tecnica"]):
            item["TÉCNICAS"] = row["tecnica"]
        if "trecho_transcricao" in row.index and not pd.isna(row["trecho_transcricao"]):
            item["TRECHO DA TRANSCRIÇÃO"] = row["trecho_transcricao"]
        if "atitude_causador" in row.index and not pd.isna(row["atitude_causador"]):
            item["ATITUDE DO CAUSADOR"] = row["atitude_causador"]

        vinculo = row.get("Vinculo_APA", row.get("id_numero"))
        if vinculo is not None and not pd.isna(vinculo):
            item["Vinculo_APA"] = int(vinculo)

        apa_uuid = row.get("apa_id")
        if apa_uuid is not None and not pd.isna(apa_uuid):
            item["apa_id"] = str(apa_uuid)

        for col in (
            "NEGOCIADOR PRINCIPAL",
            "Negociador Principal do incidente crítico",
            "Tipologia do incidente crítico",
            "Modalidade do incidente crítico",
        ):
            if col in row.index and not pd.isna(row[col]):
                item[col] = row[col]

        registros.append(item)

    return pd.DataFrame(registros)


def buscar_dados_apa() -> tuple[pd.DataFrame, str]:
    """Compatível com airtable_link.buscar_dados_apa()."""
    try:
        df = apas_para_formato_app(fetch_apas())
        if df.empty:
            return df, "Nenhuma APA encontrada no Supabase"
        return df, f"{len(df)} APAs carregadas (Supabase)"
    except Exception as exc:
        return pd.DataFrame(), f"Erro ao carregar APAs do Supabase: {exc}"


def buscar_todas_tecnicas() -> tuple[pd.DataFrame, str]:
    """Compatível com airtable_link.buscar_todas_tecnicas()."""
    try:
        df = tecnicas_para_formato_app(fetch_tecnicas_com_apa())
        if df.empty:
            return df, "Nenhuma técnica encontrada no Supabase"
        return df, f"{len(df)} técnicas carregadas (Supabase)"
    except Exception as exc:
        return pd.DataFrame(), f"Erro ao carregar técnicas do Supabase: {exc}"
