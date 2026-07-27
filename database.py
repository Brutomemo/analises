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

import utils

ROOT_DIR = Path(__file__).resolve().parent
ENV_LOCAL_PATH = ROOT_DIR / ".env.local"

TABELA_APAS = "apas"
TABELA_TECNICAS = "tecnicas"
CACHE_TTL = 300
PREFIXO_FUNCOES = "FUNÇÕES:"

MAPA_LEGADO_PARA_APA: dict[str, str] = {
    legacy: db for db, legacy in {
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
    }.items()
}

# PostgreSQL (snake_case) → nomes legados esperados pelo app (ex-Airtable)
MAPA_APA_PARA_LEGADO: dict[str, str] = {db: leg for leg, db in MAPA_LEGADO_PARA_APA.items()}


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


def invalidar_cache_completo() -> None:
    """Limpa cache Supabase e session caches do Streamlit."""
    limpar_cache()
    st.cache_data.clear()


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


# ============================================================
# Escrita (insert / update / delete)
# ============================================================

def _vazio(val: Any) -> bool:
    if val is None:
        return True
    try:
        if pd.isna(val):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(val, str) and not val.strip()


def _normalizar_id_numero(val: Any) -> int | None:
    if _vazio(val):
        return None
    s = str(val).strip()
    if s.upper().startswith("APA"):
        s = s.upper().replace("APA", "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _proximo_id_numero(client: Client) -> int:
    resp = (
        client.table(TABELA_APAS)
        .select("id_numero")
        .order("id_numero", desc=True)
        .limit(1)
        .execute()
    )
    if resp.data:
        return int(resp.data[0]["id_numero"]) + 1
    return 1


def buscar_apa_uuid(id_apa: Any) -> str | None:
    """Resolve UUID da APA a partir de id_numero, 'APA 031' ou UUID."""
    if _vazio(id_apa):
        return None

    bruto = str(id_apa).strip()
    if len(bruto) == 36 and bruto.count("-") == 4:
        return bruto

    id_num = _normalizar_id_numero(bruto)
    if id_num is None:
        return None

    client = get_supabase_client()
    resp = (
        client.table(TABELA_APAS)
        .select("id")
        .eq("id_numero", id_num)
        .limit(1)
        .execute()
    )
    if resp.data:
        return str(resp.data[0]["id"])
    return None


def _preparar_payload_apa(
    dados_apa: dict[str, Any],
    apa_id: str | None = None,
) -> dict[str, Any]:
    """Converte payload legado (formulário) para colunas snake_case do Supabase."""
    bruto = dict(dados_apa)
    bruto.pop("ID", None)
    bruto.pop("id", None)

    try:
        utils.validar_tempos_payload_airtable(bruto)
    except ValueError:
        raise

    payload: dict[str, Any] = {}
    funcoes: dict[str, str] = {}

    for chave, valor in bruto.items():
        if _vazio(valor):
            continue

        if str(chave).startswith(PREFIXO_FUNCOES):
            funcoes[str(chave)] = str(valor).strip()
            continue

        if chave in MAPA_LEGADO_PARA_APA:
            col_db = MAPA_LEGADO_PARA_APA[chave]
        elif chave in MAPA_APA_PARA_LEGADO:
            col_db = chave
        else:
            continue

        if col_db == "id_numero":
            payload[col_db] = _normalizar_id_numero(valor)
        elif col_db == "data_ocorrencia":
            s = str(valor).strip()
            payload[col_db] = s[:10] if len(s) >= 10 else s
        else:
            payload[col_db] = valor

    if funcoes:
        if apa_id:
            client = get_supabase_client()
            atual = (
                client.table(TABELA_APAS)
                .select("funcoes_dados")
                .eq("id", apa_id)
                .limit(1)
                .execute()
            )
            existente: dict[str, Any] = {}
            if atual.data:
                bruto_func = atual.data[0].get("funcoes_dados")
                if isinstance(bruto_func, dict):
                    existente = bruto_func
                elif isinstance(bruto_func, str):
                    try:
                        existente = json.loads(bruto_func)
                    except json.JSONDecodeError:
                        existente = {}
            existente.update(funcoes)
            payload["funcoes_dados"] = existente
        else:
            payload["funcoes_dados"] = funcoes

    return payload


def _formatar_id_apa(id_numero: Any) -> str | None:
    if id_numero is None or _vazio(id_numero):
        return None
    return f"APA {int(id_numero):03d}"


def salvar_apa(dados_apa: dict[str, Any], apa_id: str | None = None) -> dict[str, Any]:
    """
    Insere ou atualiza uma APA na tabela `apas`.

    Retorno compatível com airtable_link.criar_nova_apa():
      {"id": "APA 031", "record_id": "<uuid>", "erro": None}
    """
    try:
        client = get_supabase_client()
        payload = _preparar_payload_apa(dados_apa, apa_id=apa_id)

        if not payload:
            return {"id": None, "record_id": apa_id, "erro": "Nenhum dado para salvar."}

        if apa_id:
            resp = client.table(TABELA_APAS).update(payload).eq("id", apa_id).execute()
        else:
            if "id_numero" not in payload:
                payload["id_numero"] = _proximo_id_numero(client)
            resp = client.table(TABELA_APAS).insert(payload).execute()

        if not resp.data:
            return {"id": None, "record_id": apa_id, "erro": "Supabase não retornou dados."}

        row = resp.data[0]
        uuid = str(row["id"])
        id_fmt = _formatar_id_apa(row.get("id_numero"))

        invalidar_cache_completo()
        return {"id": id_fmt, "record_id": uuid, "erro": None}

    except ValueError as exc:
        return {"id": None, "record_id": apa_id, "erro": str(exc)}
    except Exception as exc:
        return {"id": None, "record_id": apa_id, "erro": str(exc)}


def _preparar_payload_tecnica(item: dict[str, Any], apa_id: str) -> dict[str, Any]:
    tecnica = item.get("tecnica") or item.get("TÉCNICAS")
    trecho = item.get("trecho_transcricao") or item.get("TRECHO DA TRANSCRIÇÃO")
    atitude = item.get("atitude_causador", item.get("ATITUDE DO CAUSADOR"))

    if _vazio(tecnica):
        raise ValueError("Campo TÉCNICAS/tecnica obrigatório.")
    if _vazio(trecho):
        trecho = "(trecho nao informado)"

    payload: dict[str, Any] = {
        "apa_id": apa_id,
        "tecnica": str(tecnica).strip(),
        "trecho_transcricao": str(trecho).strip(),
    }

    if not _vazio(atitude):
        if isinstance(atitude, str) and "," in atitude:
            atitude = atitude.split(",", 1)[0].strip()
        try:
            n = int(atitude)
            if n in (-1, 0, 1):
                payload["atitude_causador"] = n
        except (ValueError, TypeError):
            pass

    return payload


def salvar_tecnicas(
    apa_id: str,
    lista_tecnicas: list[dict[str, Any]],
) -> tuple[int, int, list[str]]:
    """
    Insere ou atualiza técnicas vinculadas à APA.

    Item com `id` ou `Airtable_Record_ID` faz update; caso contrário, insert.
    Retorna (inseridas, atualizadas, erros).
    """
    if not apa_id:
        return 0, 0, ["apa_id obrigatório."]

    client = get_supabase_client()
    inseridas = 0
    atualizadas = 0
    erros: list[str] = []

    for idx, item in enumerate(lista_tecnicas):
        try:
            payload = _preparar_payload_tecnica(item, apa_id)
            reg_id = item.get("id") or item.get("Airtable_Record_ID") or item.get("record_id")

            if reg_id and not _vazio(reg_id):
                client.table(TABELA_TECNICAS).update(
                    {k: v for k, v in payload.items() if k != "apa_id"}
                ).eq("id", str(reg_id)).execute()
                atualizadas += 1
            else:
                client.table(TABELA_TECNICAS).insert(payload).execute()
                inseridas += 1
        except Exception as exc:
            nome = item.get("TÉCNICAS") or item.get("tecnica") or f"linha {idx + 1}"
            erros.append(f"{nome}: {exc}")

    if inseridas or atualizadas:
        invalidar_cache_completo()

    return inseridas, atualizadas, erros


def criar_tecnica(
    payload: dict[str, Any],
    apa_id: str | None = None,
    vinculo_record_id: str | None = None,
    id_apa: Any = None,
) -> tuple[bool, str | None]:
    """Compatível com airtable_link.criar_tecnica()."""
    uuid = apa_id or vinculo_record_id or buscar_apa_uuid(id_apa)
    if not uuid:
        return False, f"Não foi possível localizar a APA {id_apa or 'informada'}."

    ins, upd, erros = salvar_tecnicas(uuid, [payload])
    if erros:
        return False, erros[0]
    if ins + upd == 0:
        return False, "Nenhuma técnica gravada."
    return True, None


def atualizar_apa_validacao(
    id_apa: Any,
    payload: dict[str, Any],
    record_id_interno: str | None = None,
) -> bool:
    """Compatível com airtable_link.atualizar_apa_validacao()."""
    apa_uuid = record_id_interno or buscar_apa_uuid(id_apa)
    if not apa_uuid:
        raise ValueError(f"APA {id_apa} não encontrada no Supabase.")

    resultado = salvar_apa(payload, apa_id=apa_uuid)
    if resultado.get("erro"):
        raise RuntimeError(resultado["erro"])
    return True


def criar_nova_apa(payload: dict[str, Any]) -> dict[str, Any]:
    """Compatível com airtable_link.criar_nova_apa()."""
    return salvar_apa(payload)


def deletar_apa(apa_id: str) -> tuple[bool, str | None]:
    """Remove APA e técnicas vinculadas."""
    if not apa_id:
        return False, "apa_id obrigatório."

    try:
        client = get_supabase_client()
        client.table(TABELA_TECNICAS).delete().eq("apa_id", apa_id).execute()
        client.table(TABELA_APAS).delete().eq("id", apa_id).execute()
        invalidar_cache_completo()
        return True, None
    except Exception as exc:
        return False, str(exc)
