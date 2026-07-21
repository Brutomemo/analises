# ============================================================
# airtable_link.py - INTEGRAÇÃO COM AIRTABLE (COM CACHE OTIMIZADO)
# ============================================================

import os
import re
import pandas as pd
import requests
import streamlit as st
from pyairtable import Api
from datetime import datetime
import utils

_TABELA_VINCULO_TECNICAS = None


def _formatar_erro_airtable(exc):
    """Extrai mensagem legível de exceções da API Airtable/pyairtable."""
    for arg in getattr(exc, "args", ()):
        if isinstance(arg, str) and "message" in arg:
            match = re.search(r"""['"]message['"]\s*:\s*['"]([^'"]+)['"]""", arg)
            if match:
                return match.group(1)
    return str(exc)


def _get_setting(key, default=None):
    try:
        val = st.secrets.get(key)
        if val:
            return val
    except Exception:
        pass
    return os.getenv(key, default)


def get_credentials():
    # Aceita tanto AIRTABLE_TOKEN quanto AIRTABLE_API_KEY do Secrets
    api_key = _get_setting("AIRTABLE_TOKEN") or _get_setting("AIRTABLE_API_KEY")
    base_id = _get_setting("AIRTABLE_BASE_ID") or _get_setting("BASE_ID")
    return api_key, base_id


def limpar_cache_airtable():
    """Invalida o cache do Streamlit quando dados forem salvos/alterados."""
    buscar_todas_apas.clear()
    buscar_todas_tecnicas.clear()


def _normalizar_ref_id_apa(id_apa):
    if id_apa is None or (isinstance(id_apa, float) and pd.isna(id_apa)):
        return None, None

    bruto = str(id_apa).strip()
    if bruto.endswith(".0"):
        bruto = bruto[:-2]

    try:
        num = int(float(bruto.replace("APA", "").strip()))
    except (ValueError, TypeError):
        num = None

    if bruto.upper().startswith("APA"):
        fmt = bruto.upper()
    elif num is not None:
        fmt = f"APA {num:03d}"
    else:
        fmt = bruto.upper()

    return num, fmt


def _campo_id_coincide(campo_id, id_num, id_fmt):
    if campo_id is None or (isinstance(campo_id, float) and pd.isna(campo_id)):
        return False

    campo_bruto = str(campo_id).strip()
    if campo_bruto.endswith(".0"):
        campo_bruto = campo_bruto[:-2]

    if id_num is not None:
        try:
            if int(float(campo_bruto.replace("APA", "").strip())) == id_num:
                return True
        except (ValueError, TypeError):
            pass

    campo_fmt = campo_bruto.upper()
    if campo_fmt.startswith("APA"):
        return campo_fmt == id_fmt
    if id_num is not None:
        return campo_fmt == str(id_num) or campo_fmt == id_fmt
    return campo_fmt == id_fmt


def _tabela_vinculo_tecnicas():
    """Tabela ligada ao campo Vinculo_APA (sempre a base de APAs, salvo override em secrets)."""
    global _TABELA_VINCULO_TECNICAS
    if _TABELA_VINCULO_TECNICAS:
        return _TABELA_VINCULO_TECNICAS

    override = _get_setting("TABLE_NAME_VINCULO_APA")
    if override:
        _TABELA_VINCULO_TECNICAS = override
        return _TABELA_VINCULO_TECNICAS

    tabela_apa = _get_setting("TABLE_NAME_APA", "PARA ANALISE QUALITATIVA DA APA")
    api_key, base_id = get_credentials()
    if not api_key or not base_id:
        _TABELA_VINCULO_TECNICAS = tabela_apa
        return _TABELA_VINCULO_TECNICAS

    try:
        resp = requests.get(
            f"https://api.airtable.com/v0/meta/bases/{base_id}/tables",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        resp.raise_for_status()
        tabelas = resp.json().get("tables", [])
        nomes = {t["id"]: t["name"] for t in tabelas}
        nome_tecnicas = _get_setting(
            "TABLE_NAME_HISTORICO", "TABELA DE FREQUÊNCIAS DAS TÉCNICAS"
        )

        for tabela in tabelas:
            if tabela.get("name") != nome_tecnicas and "FREQU" not in tabela.get("name", "").upper():
                continue
            for campo in tabela.get("fields", []):
                if campo.get("name") != "Vinculo_APA":
                    continue
                if campo.get("type") != "multipleRecordLinks":
                    continue
                linked_id = campo.get("options", {}).get("linkedTableId")
                if linked_id in nomes:
                    _TABELA_VINCULO_TECNICAS = nomes[linked_id]
                    return _TABELA_VINCULO_TECNICAS
    except Exception as exc:
        print(f"[airtable_link] Falha ao resolver tabela de vínculo: {exc}")

    _TABELA_VINCULO_TECNICAS = tabela_apa
    return _TABELA_VINCULO_TECNICAS


# ============================================================
# CONSULTAS COM CACHE (PREVINE ESTOURO DE API / RATE LIMIT)
# ============================================================

@st.cache_data(ttl=300)
def buscar_todas_apas():
    """
    Busca todas as APAs da tabela "PARA ANALISE QUALITATIVA DA APA".
    Mantém os dados em cache no Streamlit por 5 minutos (300 seg).
    """
    try:
        api_key, base_id = get_credentials()

        if not api_key or not base_id:
            print("❌ Credenciais não configuradas")
            return pd.DataFrame()

        api = Api(api_key)
        base = api.base(base_id)
        table = base.table("PARA ANALISE QUALITATIVA DA APA")

        records = table.all()

        data = []
        for record in records:
            fields = record['fields']
            record_id = record['id']
            fields['Airtable_Record_ID'] = record_id
            fields['record_id_airtable'] = record_id
            if str(fields.get('id', '')).strip().startswith('rec'):
                fields['id'] = record_id
            else:
                fields.pop('id', None)
            data.append(fields)

        df = pd.DataFrame(data)
        return df

    except Exception as e:
        print(f"❌ Erro ao buscar APAs: {str(e)}")
        return pd.DataFrame()


def buscar_dados_apa():
    """
    Alias para buscar_todas_apas() — mantém compatibilidade.
    """
    try:
        df = buscar_todas_apas()

        if df.empty:
            return df, "⚠️ Nenhuma APA encontrada"
        else:
            return df, f"✅ {len(df)} APAs carregadas"

    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return pd.DataFrame(), f"❌ Erro ao carregar APAs: {str(e)}"


@st.cache_data(ttl=300)
def buscar_todas_tecnicas():
    """
    Busca todas as técnicas da tabela com cache de 5 minutos.
    """
    try:
        api_key, base_id = get_credentials()

        if not api_key or not base_id:
            print("❌ Credenciais não configuradas")
            return pd.DataFrame(), "❌ Credenciais não configuradas"

        api = Api(api_key)
        base = api.base(base_id)
        table = base.table("TABELA DE FREQUÊNCIAS DAS TÉCNICAS")

        records = table.all()

        data = []
        for record in records:
            fields = record['fields']
            record_id = record['id']
            fields['Airtable_Record_ID'] = record_id
            fields.pop('id', None)
            data.append(fields)

        df = pd.DataFrame(data)

        if df.empty:
            return df, "⚠️ Nenhuma técnica encontrada"
        else:
            return df, f"✅ {len(df)} técnicas carregadas"

    except Exception as e:
        print(f"❌ Erro ao buscar técnicas: {str(e)}")
        return pd.DataFrame(), f"❌ Erro: {str(e)}"


def _valor_coincide_id_apa(valor, id_num, id_fmt):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return False
    if isinstance(valor, list):
        return any(_valor_coincide_id_apa(item, id_num, id_fmt) for item in valor)
    return _campo_id_coincide(valor, id_num, id_fmt)


def record_id_pertence_apa(record_id, id_apa, table_name=None):
    if not record_id or not str(record_id).strip().startswith("rec"):
        return False

    id_num, id_fmt = _normalizar_ref_id_apa(id_apa)
    if id_num is None and not id_fmt:
        return False

    if table_name is None:
        table_name = _tabela_vinculo_tecnicas()

    try:
        api_key, base_id = get_credentials()
        if not api_key or not base_id:
            return False

        api = Api(api_key)
        registro = api.base(base_id).table(table_name).get(str(record_id).strip())
        campo_id = registro.get("fields", {}).get("ID")
        return _campo_id_coincide(campo_id, id_num, id_fmt)
    except Exception as exc:
        print(f"[airtable_link] record_id_pertence_apa falhou ({record_id}): {exc}")
        return False


def buscar_record_id_por_id_apa(id_apa, table_name=None):
    id_num, id_fmt = _normalizar_ref_id_apa(id_apa)
    if id_num is None and not id_fmt:
        return None

    if table_name is None:
        table_name = _get_setting("TABLE_NAME_APA", "PARA ANALISE QUALITATIVA DA APA")

    try:
        api_key, base_id = get_credentials()
        if not api_key or not base_id:
            return None

        api = Api(api_key)
        table = api.base(base_id).table(table_name)

        if id_num is not None:
            formulas = [
                f"{{ID}}={id_num}",
                f"{{ID}}='{id_num}'",
                f"{{ID}}='{id_fmt}'",
            ]
            formula = "OR(" + ",".join(formulas) + ")"
            try:
                registros = table.all(formula=formula)
                if registros:
                    return registros[0]["id"]
            except Exception as exc:
                print(f"[airtable_link] Filtro por ID falhou em {table_name}: {exc}")

        return None
    except Exception as exc:
        print(f"[airtable_link] Erro ao buscar APA {id_apa} em {table_name}: {exc}")
        return None


def buscar_record_id_vinculo_tecnica(id_apa, record_id_hint=None):
    tabela_apa = _tabela_vinculo_tecnicas()

    if record_id_hint and str(record_id_hint).strip().startswith("rec"):
        hint = str(record_id_hint).strip()
        if record_id_pertence_apa(hint, id_apa, table_name=tabela_apa):
            return hint

    return buscar_record_id_por_id_apa(id_apa, table_name=tabela_apa)


# ============================================================
# ESCRITA E ATUALIZAÇÃO (LIMPA O CACHE APÓS EXECUTAR)
# ============================================================

def atualizar_apa_validacao(id_apa, payload, record_id_interno=None):
    api_key, base_id = get_credentials()

    if not api_key or not base_id:
        raise ValueError("Credenciais do Airtable não configuradas (AIRTABLE_TOKEN / AIRTABLE_BASE_ID).")

    api = Api(api_key)
    base = api.base(base_id)
    table = base.table("PARA ANALISE QUALITATIVA DA APA")

    utils.validar_tempos_payload_airtable(payload)

    if record_id_interno and str(record_id_interno).startswith("rec"):
        try:
            table.update(record_id_interno, payload)
            limpar_cache_airtable()  # Limpa o cache após atualizar
            print(f"✅ APA {id_apa} atualizada com sucesso")
            return True
        except Exception as e:
            raise RuntimeError(f"Airtable rejeitou a atualização: {str(e)}") from e

    # Se não veio o record_id, busca via ID por fórmula rápida
    record_id = buscar_record_id_por_id_apa(id_apa)
    if record_id:
        try:
            table.update(record_id, payload)
            limpar_cache_airtable()  # Limpa o cache após atualizar
            return True
        except Exception as e:
            raise RuntimeError(f"Airtable rejeitou a atualização: {str(e)}") from e

    return False


def criar_nova_apa(payload):
    try:
        api_key, base_id = get_credentials()

        if not api_key or not base_id:
            erro = "Credenciais do Airtable não configuradas."
            return {"id": None, "erro": erro}

        api = Api(api_key)
        base = api.base(base_id)
        table = base.table("PARA ANALISE QUALITATIVA DA APA")

        if "ID" in payload:
            del payload["ID"]

        utils.validar_tempos_payload_airtable(payload)

        novo_record = table.create(payload)
        record_id = novo_record.get("id")
        fields = novo_record.get("fields", {})
        id_numero = fields.get("ID")

        limpar_cache_airtable()  # Limpa o cache após criar registro novo

        if id_numero is None:
            return {"id": None, "record_id": record_id, "erro": None}

        id_formatado = f"APA {int(id_numero):03d}"
        return {"id": id_formatado, "record_id": record_id, "erro": None}

    except Exception as e:
        erro = _formatar_erro_airtable(e)
        return {"id": None, "erro": erro}


def criar_tecnica(payload, vinculo_record_id=None, id_apa=None):
    try:
        api_key, base_id = get_credentials()

        if not api_key or not base_id:
            return False, "Credenciais do Airtable não configuradas."

        api = Api(api_key)
        base = api.base(base_id)
        table = base.table("TABELA DE FREQUÊNCIAS DAS TÉCNICAS")

        if not payload.get('TÉCNICAS'):
            return False, "Campo TÉCNICAS obrigatório."

        if not payload.get('TRECHO DA TRANSCRIÇÃO'):
            return False, "Campo TRECHO DA TRANSCRIÇÃO obrigatório."

        rec = vinculo_record_id
        if not rec or not str(rec).startswith("rec"):
            ref_id = id_apa or payload.pop("Vinculo_APA_ID", None)
            if ref_id is None:
                ref_id = payload.pop("Vinculo_APA", None)
            if ref_id and str(ref_id).startswith("rec"):
                rec = str(ref_id).strip()
            elif ref_id:
                rec = buscar_record_id_vinculo_tecnica(ref_id)

        if not rec or not str(rec).startswith("rec"):
            ref_msg = id_apa or "informado"
            return False, f"Não foi possível localizar o registro Airtable da APA {ref_msg}."

        payload.pop("Vinculo_APA", None)
        payload.pop("Vinculo_APA_ID", None)
        payload["Vinculo_APA"] = [str(rec)]

        atitude_raw = payload.get('ATITUDE DO CAUSADOR', None)
        vazio = (
            atitude_raw is None
            or atitude_raw == ""
            or (isinstance(atitude_raw, float) and pd.isna(atitude_raw))
        )

        if vazio:
            payload.pop('ATITUDE DO CAUSADOR', None)
        else:
            try:
                atitude = int(atitude_raw)
                if atitude not in [-1, 0, 1]:
                    return False, f"ATITUDE inválida: {atitude}."
                payload['ATITUDE DO CAUSADOR'] = atitude
            except (ValueError, TypeError):
                return False, "ATITUDE deve ser número inteiro (-1, 0 ou 1)."

        table.create(payload)
        limpar_cache_airtable()  # Limpa o cache para recarregar a lista de técnicas
        return True, None

    except Exception as e:
        return False, _formatar_erro_airtable(e)