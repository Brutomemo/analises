#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script temporário e isolado — migração Airtable → Supabase.

Uso:
    python migrar_airtable_para_supabase.py

Credenciais (ordem de prioridade):
    1. Variáveis de ambiente (inclui .env.local via python-dotenv)
    2. st.secrets do Streamlit (se disponível)
    3. Arquivo .streamlit/secrets.toml

Requisitos Supabase:
    Tabelas `apas` e `tecnicas` com colunas snake_case mapeadas abaixo.
    A tabela `apas` deve expor `id` (UUID) e aceitar `airtable_record_id` (TEXT).
    A tabela `tecnicas` deve ter FK `apa_id` → apas(id).
"""

from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pyairtable import Api
from supabase import create_client

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent
SECRETS_PATH = ROOT_DIR / ".streamlit" / "secrets.toml"
ENV_LOCAL_PATH = ROOT_DIR / ".env.local"

TABELA_APA_AIRTABLE = "PARA ANALISE QUALITATIVA DA APA"
TABELA_TECNICAS_AIRTABLE = "TABELA DE FREQUÊNCIAS DAS TÉCNICAS"

TABELA_APA_SUPABASE = "apas"
TABELA_TECNICAS_SUPABASE = "tecnicas"

# Airtable (nome legado) → Supabase (snake_case)
MAPA_CAMPOS_APA: dict[str, str] = {
    "ID": "id_numero",
    "Data da ocorrência": "data_ocorrencia",
    "Modalidade do incidente": "modalidade_incidente",
    "Tipologia": "tipologia",
    "Forma de Transição": "forma_transicao",
    "Resolução": "resolucao",
    "Motivação": "motivacao",
    "Negociador Principal": "negociador_principal",
    "Negociador Secundário": "negociador_secundario",
    "Negociador Anotador": "negociador_anotador",
    "Negociador Líder": "negociador_lider",
    "Negociador Auxiliar de Informações": "negociador_auxiliar_informacoes",
    "Negociador Auxiliar de Logística": "negociador_auxiliar_logistica",
    "Profissional de Saúde Mental": "profissional_saude_mental",
    "12 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A AGRESSIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": "percep_12_agr_principal_chegada",
    "12 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A AGRESSIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": "percep_12_agr_secundario_chegada",
    "12 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A AGRESSIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": "percep_12_agr_lider_chegada",
    "13 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A RECEPTIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": "percep_13_rec_principal_chegada",
    "13 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A RECEPTIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": "percep_13_rec_secundario_chegada",
    "13 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A RECEPTIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": "percep_13_rec_lider_chegada",
    "24 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A AGRESSIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": "percep_24_agr_principal_encerramento",
    "24 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A AGRESSIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": "percep_24_agr_secundario_encerramento",
    "24 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A AGRESSIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": "percep_24_agr_lider_encerramento",
    "25 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A RECEPTIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": "percep_25_rec_principal_encerramento",
    "25 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A RECEPTIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": "percep_25_rec_secundario_encerramento",
    "25 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A RECEPTIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": "percep_25_rec_lider_encerramento",
    "TRANSCRIÇÃO DO CAUSADOR": "transcricao_causador",
    "TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL": "transcricao_negociador_principal",
    "TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO": "transcricao_negociador_secundario",
    "FUNÇÕES: NEGOCIADOR PRINCIPAL": "funcoes_negociador_principal",
    "FUNÇÕES: NEGOCIADOR PRINCIPAL - PROBLEMA IDENTIFICADO": "funcoes_negociador_principal_problema",
    "FUNÇÕES: NEGOCIADOR PRINCIPAL - AÇÕES CORRETIVAS ADOTADAS": "funcoes_negociador_principal_acoes",
    "FUNÇÕES: NEGOCIADOR PRINCIPAL - PRÁTICAS PROMISSORAS": "funcoes_negociador_principal_praticas",
    "FUNÇÕES: NEGOCIADOR SECUNDÁRIO": "funcoes_negociador_secundario",
    "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PROBLEMA IDENTIFICADO": "funcoes_negociador_secundario_problema",
    "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - AÇÕES CORRETIVAS ADOTADAS": "funcoes_negociador_secundario_acoes",
    "FUNÇÕES: NEGOCIADOR SECUNDÁRIO - PRÁTICAS PROMISSORAS": "funcoes_negociador_secundario_praticas",
    "FUNÇÕES: NEGOCIADOR ANOTADOR": "funcoes_negociador_anotador",
    "FUNÇÕES: NEGOCIADOR ANOTADOR - PROBLEMA IDENTIFICADO": "funcoes_negociador_anotador_problema",
    "FUNÇÕES: NEGOCIADOR ANOTADOR - AÇÕES CORRETIVAS ADOTADAS": "funcoes_negociador_anotador_acoes",
    "FUNÇÕES: NEGOCIADOR ANOTADOR - PRÁTICAS PROMISSORAS": "funcoes_negociador_anotador_praticas",
    "FUNÇÕES: NEGOCIADOR LÍDER": "funcoes_negociador_lider",
    "FUNÇÕES: NEGOCIADOR LÍDER - PROBLEMA IDENTIFICADO": "funcoes_negociador_lider_problema",
    "FUNÇÕES: NEGOCIADOR LÍDER - AÇÕES CORRETIVAS ADOTADAS": "funcoes_negociador_lider_acoes",
    "FUNÇÕES: NEGOCIADOR LÍDER - PRÁTICAS PROMISSORAS": "funcoes_negociador_lider_praticas",
    "FUNÇÕES: NEGOCIADOR AUXILIAR DE LOGÍSTICA": "funcoes_negociador_auxiliar_logistica",
    "FUNÇÕES: AUXILIAR DE LOGÍSTICA - PROBLEMA IDENTIFICADO": "funcoes_auxiliar_logistica_problema",
    "FUNÇÕES: AUXILIAR DE LOGÍSTICA - AÇÕES CORRETIVAS": "funcoes_auxiliar_logistica_acoes",
    "FUNÇÕES: AUXILIAR DE LOGÍSTICA - PRÁTICAS PROMISSORAS": "funcoes_auxiliar_logistica_praticas",
    "FUNÇÕES: NEGOCIADOR AUXILIAR DE INFORMAÇÕES": "funcoes_negociador_auxiliar_informacoes",
    "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PROBLEMA IDENTIFICADO": "funcoes_auxiliar_informacoes_problema",
    "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - AÇÕES CORRETIVAS": "funcoes_auxiliar_informacoes_acoes",
    "FUNÇÕES: AUXILIAR DE INFORMAÇÕES - PRÁTICAS PROMISSORAS": "funcoes_auxiliar_informacoes_praticas",
    "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL": "funcoes_profissional_saude_mental",
    "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PROBLEMA IDENTIFICADO": "funcoes_profissional_saude_mental_problema",
    "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - AÇÕES CORRETIVAS ADOTADAS": "funcoes_profissional_saude_mental_acoes",
    "FUNÇÕES: PROFISSIONAL DE SAÚDE MENTAL - PRÁTICAS PROMISSORAS": "funcoes_profissional_saude_mental_praticas",
    "Tempo de Negociação Real": "tempo_negociacao_real_seg",
    "Tempo de Negociação Tática": "tempo_negociacao_tatica_seg",
    "Uniforme Usado": "uniforme_usado",
    "Sexo do Causador": "sexo_causador",
}

MAPA_CAMPOS_TECNICA: dict[str, str] = {
    "TÉCNICAS": "tecnica",
    "TRECHO DA TRANSCRIÇÃO": "trecho_transcricao",
    "ATITUDE DO CAUSADOR": "atitude_causador",
}

CAMPOS_DURACAO_APA = {"tempo_negociacao_real_seg", "tempo_negociacao_tatica_seg"}


# ---------------------------------------------------------------------------
# Credenciais
# ---------------------------------------------------------------------------

def _carregar_env_local() -> None:
    """Carrega variáveis de .env.local para os.environ (se existir)."""
    try:
        from dotenv import load_dotenv

        load_dotenv(ENV_LOCAL_PATH)
    except ImportError:
        if ENV_LOCAL_PATH.is_file():
            print(
                "[credenciais] Aviso: python-dotenv não instalado; "
                "instale com `pip install python-dotenv` ou defina variáveis de ambiente manualmente."
            )
    except Exception as exc:
        print(f"[credenciais] Aviso: falha ao carregar .env.local: {exc}")


def _limpar_valor_credencial(val: Any) -> str | None:
    """Remove aspas simples/duplas extras e espaços dos valores lidos."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    while len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        s = s[1:-1].strip()
    return s or None


def _load_streamlit_secrets() -> dict[str, str]:
    """Lê st.secrets quando o Streamlit estiver disponível."""
    secrets: dict[str, str] = {}
    try:
        import streamlit as st

        if not hasattr(st, "secrets"):
            return secrets

        for key in st.secrets:
            try:
                val = st.secrets[key]
            except Exception:
                continue
            if isinstance(val, (str, int, float, bool)):
                limpo = _limpar_valor_credencial(val)
                if limpo:
                    secrets[str(key)] = limpo
    except Exception:
        pass
    return secrets


def _parse_secrets_toml_simple(path: Path) -> dict[str, str]:
    """Parser mínimo para secrets.toml (chaves planas KEY = \"valor\")."""
    secrets: dict[str, str] = {}
    if not path.is_file():
        return secrets

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("[") and line.endswith("]"):
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = _limpar_valor_credencial(value.strip().strip('"').strip("'"))
        if key and value:
            secrets[key] = value
    return secrets


def _load_secrets() -> dict[str, str]:
    secrets: dict[str, str] = {}

    # secrets.toml (fallback)
    secrets.update(_parse_secrets_toml_simple(SECRETS_PATH))
    try:
        import tomllib  # Python 3.11+

        if SECRETS_PATH.is_file():
            with SECRETS_PATH.open("rb") as fh:
                parsed = tomllib.load(fh)
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    if isinstance(value, (str, int, float, bool)):
                        limpo = _limpar_valor_credencial(value)
                        if limpo:
                            secrets[str(key)] = limpo
    except ImportError:
        pass

    # st.secrets sobrescreve secrets.toml
    secrets.update(_load_streamlit_secrets())
    return secrets


def _get_setting(key: str, secrets: dict[str, str], default: str | None = None) -> str | None:
    env_val = _limpar_valor_credencial(os.getenv(key))
    if env_val:
        return env_val
    secret_val = _limpar_valor_credencial(secrets.get(key))
    if secret_val:
        return secret_val
    return default


def _buscar_credencial(
    nomes: list[str],
    secrets: dict[str, str],
    rotulo: str,
) -> str | None:
    """Busca credencial por lista de aliases (env/.env.local → secrets)."""
    print(f"[credenciais] Buscando {rotulo}: {', '.join(nomes)}")
    for nome in nomes:
        bruto_env = os.getenv(nome)
        bruto_secret = secrets.get(nome)
        valor = _limpar_valor_credencial(bruto_env) or _limpar_valor_credencial(bruto_secret)
        if valor:
            origem = "ambiente/.env.local" if _limpar_valor_credencial(bruto_env) else "secrets"
            print(f"[credenciais]   ✓ {nome} encontrada ({origem})")
            return valor
        print(f"[credenciais]   · {nome} não definida")
    print(f"[credenciais]   ✗ Nenhuma variável de {rotulo} encontrada")
    return None


def carregar_credenciais() -> tuple[str, str, str, str]:
    print("[credenciais] Carregando credenciais...")
    print(f"[credenciais] Arquivo .env.local: {ENV_LOCAL_PATH}")
    _carregar_env_local()
    secrets = _load_secrets()

    airtable_token = _buscar_credencial(
        ["AIRTABLE_TOKEN", "AIRTABLE_API_KEY", "PAT", "AIRTABLE_PAT"],
        secrets,
        "token do Airtable",
    )
    airtable_base_id = _buscar_credencial(
        ["AIRTABLE_BASE_ID", "BASE_ID"],
        secrets,
        "base_id do Airtable",
    )
    supabase_url = _buscar_credencial(
        ["SUPABASE_URL", "SUPABASE_PROJECT_URL", "URL_SUPABASE"],
        secrets,
        "URL do Supabase",
    )
    supabase_key = _buscar_credencial(
        ["SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ANON_KEY"],
        secrets,
        "key do Supabase",
    )

    faltando = []
    if not airtable_token:
        faltando.append("AIRTABLE_TOKEN, AIRTABLE_API_KEY, PAT ou AIRTABLE_PAT")
    if not airtable_base_id:
        faltando.append("AIRTABLE_BASE_ID ou BASE_ID")
    if not supabase_url:
        faltando.append("SUPABASE_URL, SUPABASE_PROJECT_URL ou URL_SUPABASE")
    if not supabase_key:
        faltando.append("SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY ou SUPABASE_ANON_KEY")

    if faltando:
        raise RuntimeError(
            "Credenciais ausentes: "
            + "; ".join(faltando)
            + ". Configure em .env.local, variáveis de ambiente ou .streamlit/secrets.toml."
        )

    return airtable_token, airtable_base_id, supabase_url, supabase_key


# ---------------------------------------------------------------------------
# Normalização de valores
# ---------------------------------------------------------------------------

def _is_empty(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and val != val:  # NaN
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    if isinstance(val, (list, tuple, dict)) and len(val) == 0:
        return True
    return False


def _scalar(val: Any) -> Any:
    """Desempacota listas simples do Airtable (linked/lookup)."""
    if isinstance(val, list):
        if not val:
            return None
        if len(val) == 1:
            return val[0]
        return val
    return val


def _normalizar_data(val: Any) -> str | None:
    val = _scalar(val)
    if _is_empty(val):
        return None
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, date):
        return val.isoformat()
    s = str(val).strip()
    if not s:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    if "/" in s:
        try:
            return datetime.strptime(s, "%m/%d/%Y").date().isoformat()
        except ValueError:
            pass
        try:
            return datetime.strptime(s, "%d/%m/%Y").date().isoformat()
        except ValueError:
            pass
    return s


def _normalizar_inteiro(val: Any) -> int | None:
    val = _scalar(val)
    if _is_empty(val):
        return None
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return None


def _normalizar_duracao_segundos(val: Any) -> int | None:
    """Mantém duração como segundos inteiros (formato nativo do Airtable)."""
    val = _scalar(val)
    if _is_empty(val):
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        seg = int(val)
        return seg if seg >= 0 else None
    s = str(val).strip()
    if not s:
        return None
    if ":" in s:
        partes = [p.strip() for p in s.split(":")]
        try:
            h = int(partes[0])
            m = int(partes[1]) if len(partes) > 1 else 0
            return h * 3600 + m * 60
        except (ValueError, TypeError):
            return None
    try:
        return int(float(s.replace(",", ".")))
    except (ValueError, TypeError):
        return None


def _normalizar_texto(val: Any) -> str | None:
    val = _scalar(val)
    if _is_empty(val):
        return None
    return str(val)


def _extrair_vinculo_apa_record_id(val: Any) -> str | None:
    """Extrai rec... do campo Vinculo_APA (lista ou string)."""
    if _is_empty(val):
        return None
    if isinstance(val, list):
        for item in val:
            item_str = str(item).strip()
            if item_str.startswith("rec"):
                return item_str
        return None
    s = str(val).strip()
    if s.startswith("rec"):
        return s
    match = re.search(r"rec[a-zA-Z0-9]+", s)
    return match.group(0) if match else None


def mapear_registro_apa(fields: dict[str, Any], record_id: str) -> dict[str, Any]:
    row: dict[str, Any] = {"airtable_record_id": record_id}

    for campo_airtable, coluna_supabase in MAPA_CAMPOS_APA.items():
        if campo_airtable not in fields:
            continue
        bruto = fields[campo_airtable]

        if coluna_supabase == "id_numero":
            valor = _normalizar_inteiro(bruto)
        elif coluna_supabase == "data_ocorrencia":
            valor = _normalizar_data(bruto)
        elif coluna_supabase in CAMPOS_DURACAO_APA:
            valor = _normalizar_duracao_segundos(bruto)
        else:
            valor = _normalizar_texto(bruto)

        if not _is_empty(valor):
            row[coluna_supabase] = valor

    return row


def mapear_registro_tecnica(
    fields: dict[str, Any],
    record_id: str,
    apa_uuid: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "apa_id": apa_uuid,
        "airtable_record_id": record_id,
    }

    for campo_airtable, coluna_supabase in MAPA_CAMPOS_TECNICA.items():
        if campo_airtable not in fields:
            continue
        bruto = fields[campo_airtable]

        if coluna_supabase == "atitude_causador":
            valor = _normalizar_inteiro(bruto)
            if valor is not None and valor not in (-1, 0, 1):
                valor = None
        else:
            valor = _normalizar_texto(bruto)

        if not _is_empty(valor):
            row[coluna_supabase] = valor

    return row


# ---------------------------------------------------------------------------
# Migração
# ---------------------------------------------------------------------------

def ler_registros_airtable(api: Api, base_id: str, table_name: str) -> list[dict[str, Any]]:
    table = api.base(base_id).table(table_name)
    return table.all()


def migrar_apas(
    api: Api,
    base_id: str,
    supabase,
) -> dict[str, str]:
    """
    Migra APAs e retorna mapa {airtable_record_id: supabase_uuid}.
    """
    print(f"\n[1/2] Lendo APAs do Airtable ({TABELA_APA_AIRTABLE})...")
    registros = ler_registros_airtable(api, base_id, TABELA_APA_AIRTABLE)
    total_lidas = len(registros)
    print(f"      → {total_lidas} APA(s) lidas.")

    mapa_ids: dict[str, str] = {}
    migradas = 0
    erros = 0

    for record in registros:
        record_id = record.get("id", "")
        fields = record.get("fields", {})

        if not record_id:
            erros += 1
            print("      ⚠ Registro APA sem id — ignorado.")
            continue

        try:
            row = mapear_registro_apa(fields, record_id)
            response = supabase.table(TABELA_APA_SUPABASE).insert(row).execute()
            data = response.data or []
            if not data:
                raise RuntimeError("Insert não retornou dados.")

            supabase_uuid = data[0].get("id")
            if not supabase_uuid:
                raise RuntimeError("UUID ausente na resposta do Supabase.")

            mapa_ids[record_id] = str(supabase_uuid)
            migradas += 1
            id_num = row.get("id_numero", "?")
            print(f"      ✓ APA {id_num} | Airtable {record_id} → Supabase {supabase_uuid}")

        except Exception as exc:
            erros += 1
            id_apa = fields.get("ID", "?")
            print(f"      ✗ Falha APA ID={id_apa} ({record_id}): {exc}")

    print(f"\n      Resumo APAs: {total_lidas} lidas | {migradas} migradas | {erros} erros")
    return mapa_ids


def migrar_tecnicas(
    api: Api,
    base_id: str,
    supabase,
    mapa_apa_ids: dict[str, str],
) -> None:
    print(f"\n[2/2] Lendo Técnicas do Airtable ({TABELA_TECNICAS_AIRTABLE})...")
    registros = ler_registros_airtable(api, base_id, TABELA_TECNICAS_AIRTABLE)
    total_lidas = len(registros)
    print(f"      → {total_lidas} técnica(s) lidas.")

    migradas = 0
    erros = 0
    sem_vinculo = 0

    for record in registros:
        record_id = record.get("id", "")
        fields = record.get("fields", {})

        if not record_id:
            erros += 1
            print("      ⚠ Registro de técnica sem id — ignorado.")
            continue

        airtable_apa_id = _extrair_vinculo_apa_record_id(fields.get("Vinculo_APA"))
        if not airtable_apa_id:
            sem_vinculo += 1
            erros += 1
            tecnica_nome = fields.get("TÉCNICAS", "?")
            print(f"      ✗ Técnica '{tecnica_nome}' ({record_id}): Vinculo_APA ausente.")
            continue

        apa_uuid = mapa_apa_ids.get(airtable_apa_id)
        if not apa_uuid:
            erros += 1
            tecnica_nome = fields.get("TÉCNICAS", "?")
            print(
                f"      ✗ Técnica '{tecnica_nome}' ({record_id}): "
                f"APA {airtable_apa_id} não encontrada no mapa de migração."
            )
            continue

        try:
            row = mapear_registro_tecnica(fields, record_id, apa_uuid)

            if _is_empty(row.get("tecnica")):
                raise ValueError("Campo 'tecnica' obrigatório ausente.")
            if _is_empty(row.get("trecho_transcricao")):
                raise ValueError("Campo 'trecho_transcricao' obrigatório ausente.")

            supabase.table(TABELA_TECNICAS_SUPABASE).insert(row).execute()
            migradas += 1
            print(
                f"      ✓ Técnica '{row.get('tecnica')}' | "
                f"Airtable {record_id} → apa_id {apa_uuid}"
            )

        except Exception as exc:
            erros += 1
            tecnica_nome = fields.get("TÉCNICAS", "?")
            print(f"      ✗ Falha técnica '{tecnica_nome}' ({record_id}): {exc}")

    print(
        f"\n      Resumo Técnicas: {total_lidas} lidas | {migradas} migradas | "
        f"{sem_vinculo} sem vínculo | {erros} erros"
    )


def main() -> int:
    print("=" * 60)
    print("Migração Airtable → Supabase")
    print("=" * 60)

    try:
        airtable_token, airtable_base_id, supabase_url, supabase_key = carregar_credenciais()
    except RuntimeError as exc:
        print(f"\n❌ {exc}")
        return 1

    try:
        api = Api(airtable_token)
        supabase = create_client(supabase_url, supabase_key)

        mapa_apa_ids = migrar_apas(api, airtable_base_id, supabase)
        migrar_tecnicas(api, airtable_base_id, supabase, mapa_apa_ids)

        print("\n" + "=" * 60)
        print("Migração concluída.")
        print(f"Mapa APA (Airtable → Supabase): {len(mapa_apa_ids)} vínculo(s) criado(s).")
        print("=" * 60)
        return 0

    except Exception as exc:
        print(f"\n❌ Erro fatal durante a migração: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
