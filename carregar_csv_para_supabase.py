#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Carga local apas.csv + tecnicas.csv → Supabase.
Mapeia apenas colunas existentes no schema real das tabelas.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv
from supabase import Client, create_client

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
APAS_CSV = os.path.join(ROOT_DIR, "apas.csv")
TECNICAS_CSV = os.path.join(ROOT_DIR, "tecnicas.csv")

# CSV (Airtable) → colunas reais da tabela `apas` no Supabase
MAPA_APA: dict[str, str] = {
    "ID": "id_numero",
    "Data da ocorrência": "data_ocorrencia",
    "Modalidade do incidente": "modalidade_incidente",
    "Tipologia": "tipologia",
    "Motivação": "motivacao",
    "Forma de Transição": "forma_transicao",
    "Resolução": "resolucao",
    "Negociador Principal": "negociador_principal",
    "Negociador Secundário": "negociador_secundario",
    "Negociador Anotador": "negociador_anotador",
    "Negociador Líder": "negociador_lider",
    "Negociador Auxiliar de Informações": "negociador_aux_info",
    "Negociador Auxiliar de Logística": "negociador_aux_log",
    "Profissional de Saúde Mental": "prof_saude_mental",
    "12 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A AGRESSIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": "percep_agr_principal_chegada",
    "12 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A AGRESSIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": "percep_agr_secundario_chegada",
    "12 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A AGRESSIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": "percep_agr_terceiro_chegada",
    "13 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A RECEPTIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": "percep_rec_principal_chegada",
    "13 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A RECEPTIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": "percep_rec_secundario_chegada",
    "13 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A RECEPTIVIDADE DO  CAUSADOR NA CHEGADA À OCORRÊNCIA": "percep_rec_terceiro_chegada",
    "24 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A AGRESSIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": "percep_agr_principal_encerramento",
    "24 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A AGRESSIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": "percep_agr_secundario_encerramento",
    "24 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A AGRESSIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": "percep_agr_terceiro_encerramento",
    "25 - PERCEPÇÕES DO NEGOCIADOR PRINCIPAL SOBRE A RECEPTIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": "percep_rec_principal_encerramento",
    "25 - PERCEPÇÕES DO NEGOCIADOR SECUNDÁRIO SOBRE A RECEPTIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": "percep_rec_secundario_encerramento",
    "25 - PERCEPÇÕES DO NEGOCIADOR LÍDER SOBRE A RECEPTIVIDADE DO  CAUSADOR NO ENCERRAMENTO DA OCORRÊNCIA": "percep_rec_terceiro_encerramento",
    "TRANSCRIÇÃO DO CAUSADOR": "transcricao_causador",
    "TRANSCRIÇÃO DO NEGOCIADOR PRINCIPAL": "transcricao_principal",
    "TRANSCRIÇÃO DO NEGOCIADOR SECUNDÁRIO": "transcricao_secundario",
    "Tempo de Negociação Real": "tempo_negociacao_real_seg",
    "Tempo de Negociação Tática": "tempo_negociacao_tatica_seg",
    "Uniforme Usado": "uniforme_usado",
    "Sexo do Causador": "sexo_causador",
}

CAMPOS_INTEIROS_APA = {"id_numero", "tempo_negociacao_real_seg", "tempo_negociacao_tatica_seg"}
PREFIXO_FUNCOES = "FUNÇÕES:"


def carregar_credenciais() -> tuple[str, str]:
    env_path = os.path.join(ROOT_DIR, ".env.local")
    if os.path.exists(env_path):
        load_dotenv(env_path)

    url = (
        os.getenv("SUPABASE_URL")
        or os.getenv("SUPABASE_PROJECT_URL")
        or os.getenv("URL_SUPABASE")
        or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    )
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    )

    if not url or not key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_KEY/SERVICE_ROLE_KEY não encontradas em .env.local")
    return url, key


def obter_colunas_supabase(url: str, key: str, tabela: str) -> set[str]:
    """Consulta o schema OpenAPI do PostgREST para listar colunas da tabela."""
    endpoint = url.rstrip("/") + "/rest/v1/"
    resp = requests.get(
        endpoint,
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        timeout=30,
    )
    resp.raise_for_status()
    props = resp.json().get("definitions", {}).get(tabela, {}).get("properties", {})
    if not props:
        raise RuntimeError(f"Tabela '{tabela}' não encontrada no schema Supabase.")
    return set(props.keys())


def _vazio(val: Any) -> bool:
    if val is None:
        return True
    try:
        if pd.isna(val):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(val, str) and not val.strip()


def _texto(val: Any) -> str | None:
    if _vazio(val):
        return None
    return str(val).strip()


def _inteiro(val: Any) -> int | None:
    if _vazio(val):
        return None
    s = str(val).strip().replace(",", ".")
    if s.endswith(".0"):
        s = s[:-2]
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _data_iso(val: Any) -> str | None:
    if _vazio(val):
        return None
    s = str(val).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s[:10] if len(s) > 10 else s, fmt).date().isoformat()
        except ValueError:
            continue
    try:
        parsed = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.notna(parsed):
            return parsed.date().isoformat()
    except Exception:
        pass
    return None


def _tempo_hhmm_para_segundos(val: Any) -> int | None:
    """H:MM — horas e minutos (formato do app/Airtable)."""
    if _vazio(val):
        return None
    s = str(val).strip()
    if s in ("0:00", "00:00"):
        return 0
    if ":" in s:
        partes = [p.strip() for p in s.split(":")]
        try:
            h = int(partes[0])
            m = int(partes[1]) if len(partes) > 1 else 0
            return h * 3600 + m * 60
        except (ValueError, TypeError):
            return None
    return _inteiro(s)


def _atitude(val: Any) -> int | None:
    if _vazio(val):
        return None
    s = str(val).strip()
    if "," in s:
        s = s.split(",", 1)[0].strip()
    match = re.search(r"-?\d+", s)
    if not match:
        return None
    n = int(match.group(0))
    return n if n in (-1, 0, 1) else None


def _filtrar_colunas(payload: dict[str, Any], colunas_validas: set[str]) -> dict[str, Any]:
    ignoradas = [k for k in payload if k not in colunas_validas]
    if ignoradas:
        print(f"      (ignoradas — não existem no schema: {', '.join(sorted(ignoradas))})")
    return {k: v for k, v in payload.items() if k in colunas_validas}


def montar_apa(row: pd.Series, colunas_apas: set[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for col_csv, col_db in MAPA_APA.items():
        if col_csv not in row.index:
            continue
        bruto = row[col_csv]

        if col_db == "id_numero":
            valor = _inteiro(bruto)
        elif col_db == "data_ocorrencia":
            valor = _data_iso(bruto)
        elif col_db in CAMPOS_INTEIROS_APA:
            valor = _tempo_hhmm_para_segundos(bruto) if "tempo" in col_db else _inteiro(bruto)
        else:
            valor = _texto(bruto)

        if not _vazio(valor):
            payload[col_db] = valor

    funcoes: dict[str, str] = {}
    for col in row.index:
        if not str(col).startswith(PREFIXO_FUNCOES):
            continue
        txt = _texto(row[col])
        if txt:
            funcoes[str(col)] = txt

    if funcoes and "funcoes_dados" in colunas_apas:
        payload["funcoes_dados"] = funcoes

    return _filtrar_colunas(payload, colunas_apas)


def montar_tecnica(row: pd.Series, apa_uuid: str, colunas_tecnicas: set[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {"apa_id": apa_uuid}

    tecnica = _texto(row.get("TÉCNICAS"))
    trecho = _texto(row.get("TRECHO DA TRANSCRIÇÃO"))
    atitude = _atitude(row.get("ATITUDE DO CAUSADOR"))

    if tecnica:
        payload["tecnica"] = tecnica
    # trecho_transcricao é NOT NULL no banco — placeholder se vazio no CSV
    payload["trecho_transcricao"] = trecho or "(trecho nao informado no export CSV)"
    if atitude is not None:
        payload["atitude_causador"] = atitude

    return _filtrar_colunas(payload, colunas_tecnicas)


def main() -> int:
    print("=" * 60)
    print("Carga CSV -> Supabase")
    print("=" * 60)

    if not os.path.exists(APAS_CSV) or not os.path.exists(TECNICAS_CSV):
        print("[ERRO] apas.csv ou tecnicas.csv nao encontrados na raiz do projeto.")
        return 1

    try:
        supabase_url, supabase_key = carregar_credenciais()
        supabase: Client = create_client(supabase_url, supabase_key)

        colunas_apas = obter_colunas_supabase(supabase_url, supabase_key, "apas")
        colunas_tecnicas = obter_colunas_supabase(supabase_url, supabase_key, "tecnicas")

        print("\n[schema] Colunas em `apas`:")
        for c in sorted(colunas_apas):
            print(f"  - {c}")
        print("\n[schema] Colunas em `tecnicas`:")
        for c in sorted(colunas_tecnicas):
            print(f"  - {c}")

        df_apas = pd.read_csv(APAS_CSV, encoding="utf-8-sig")
        df_tecnicas = pd.read_csv(TECNICAS_CSV, encoding="utf-8-sig")
        print(f"\n[csv] {len(df_apas)} APAs | {len(df_tecnicas)} técnicas")

        mapa_uuid: dict[int, str] = {}
        count_apas = 0
        erros_apas = 0

        print("\n[apas] Inserindo...")
        for idx, row in df_apas.iterrows():
            payload = montar_apa(row, colunas_apas)
            id_num = payload.get("id_numero")
            if id_num is None:
                erros_apas += 1
                print(f"  [X] Linha {idx}: sem id_numero")
                continue
            try:
                res = supabase.table("apas").insert(payload).execute()
                uuid = res.data[0]["id"]
                mapa_uuid[int(id_num)] = uuid
                count_apas += 1
                print(f"  [OK] APA {id_num} -> {uuid}")
            except Exception as exc:
                erros_apas += 1
                print(f"  [X] APA {id_num}: {exc}")

        count_tecnicas = 0
        erros_tecnicas = 0
        sem_vinculo = 0

        print("\n[tecnicas] Inserindo...")
        for idx, row in df_tecnicas.iterrows():
            vinculo = row.get("Vinculo_APA")
            apa_num = _inteiro(vinculo)
            if apa_num is None:
                sem_vinculo += 1
                continue

            apa_uuid = mapa_uuid.get(int(apa_num))
            if not apa_uuid:
                erros_tecnicas += 1
                print(f"  [X] Linha {idx}: APA {apa_num} nao encontrada no mapa")
                continue

            payload = montar_tecnica(row, apa_uuid, colunas_tecnicas)
            if not payload.get("tecnica"):
                erros_tecnicas += 1
                continue

            try:
                supabase.table("tecnicas").insert(payload).execute()
                count_tecnicas += 1
            except Exception as exc:
                erros_tecnicas += 1
                if erros_tecnicas <= 5:
                    print(f"  [X] Linha {idx}: {exc}")

        print("\n" + "=" * 60)
        print(f"APAs inseridas:     {count_apas} ({erros_apas} erros)")
        print(f"Técnicas inseridas: {count_tecnicas} ({erros_tecnicas} erros, {sem_vinculo} sem vínculo)")
        print("=" * 60)
        return 0 if erros_apas == 0 else 1

    except Exception as exc:
        print(f"\n[ERRO FATAL] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
