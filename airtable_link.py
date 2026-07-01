# ============================================================
# airtable_link.py - INTEGRAÇÃO COM AIRTABLE
# ============================================================

import os
import re
import unicodedata
import pandas as pd
import requests
from pyairtable import Api
from datetime import datetime
import utils

_TABELA_VINCULO_TECNICAS = None
_TABELA_APA = "PARA ANALISE QUALITATIVA DA APA"
_SCHEMA_SELECTS_APA_CACHE = None


def _formatar_erro_airtable(exc):
    """Extrai mensagem legível de exceções da API Airtable/pyairtable."""
    msg = None
    for arg in getattr(exc, "args", ()):
        if isinstance(arg, str) and "message" in arg:
            match = re.search(r"""['"]message['"]\s*:\s*['"]([^'"]+)['"]""", arg)
            if match:
                msg = match.group(1)
                break
    if not msg:
        msg = str(exc)
    if "create new select option" in msg.lower():
        msg += (
            " — escolha uma opção já cadastrada no Airtable (lista do formulário) "
            "ou peça a um editor da base para adicionar a opção manualmente."
        )
    return msg


def _normalizar_opcao(valor):
    if valor is None:
        return ""
    s = unicodedata.normalize("NFKD", str(valor))
    return s.encode("ascii", "ignore").decode("ascii").lower().strip()


def obter_campos_select_apa(force_refresh=False):
    """{nome_campo: [opções]} dos single select da tabela APA."""
    global _SCHEMA_SELECTS_APA_CACHE
    if _SCHEMA_SELECTS_APA_CACHE is not None and not force_refresh:
        return _SCHEMA_SELECTS_APA_CACHE

    api_key, base_id = get_credentials()
    if not api_key or not base_id:
        _SCHEMA_SELECTS_APA_CACHE = {}
        return _SCHEMA_SELECTS_APA_CACHE

    try:
        url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        if not resp.ok:
            _SCHEMA_SELECTS_APA_CACHE = {}
            return _SCHEMA_SELECTS_APA_CACHE

        selects = {}
        for table in resp.json().get("tables", []):
            if table.get("name") != _TABELA_APA:
                continue
            for field in table.get("fields", []):
                if field.get("type") == "singleSelect":
                    choices = [
                        c.get("name")
                        for c in field.get("options", {}).get("choices", [])
                        if c.get("name")
                    ]
                    selects[field["name"]] = choices

        _SCHEMA_SELECTS_APA_CACHE = selects
        return selects
    except Exception:
        _SCHEMA_SELECTS_APA_CACHE = {}
        return _SCHEMA_SELECTS_APA_CACHE


def obter_opcoes_campo_apa(nome_campo):
    """Opções oficiais do Airtable para um campo select (lista vazia se indisponível)."""
    return list(obter_campos_select_apa().get(nome_campo, []))


def _mapear_valor_para_opcao(valor, opcoes):
    if not opcoes or valor is None:
        return None
    bruto = str(valor).strip()
    if not bruto:
        return None
    if bruto in opcoes:
        return bruto
    alvo = _normalizar_opcao(bruto)
    for opcao in opcoes:
        if _normalizar_opcao(opcao) == alvo:
            return opcao
    return None


def validar_selects_payload_apa(payload):
    """
    Garante que valores de single select existem no Airtable.
    Levanta ValueError com o campo e opções válidas antes do POST.
    """
    schema = obter_campos_select_apa()
    if not schema:
        try:
            import streamlit as st

            df = st.session_state.get("df_quali")
            if df is not None and not df.empty:
                schema = {}
                for campo in payload:
                    if campo not in df.columns:
                        continue
                    vals = (
                        df[campo]
                        .dropna()
                        .astype(str)
                        .str.strip()
                        .loc[lambda s: ~s.isin(["", "N/D", "nan", "None"])]
                        .unique()
                        .tolist()
                    )
                    if vals:
                        schema[campo] = vals
        except Exception:
            pass
    if not schema:
        return payload

    erros = []
    for campo, valor in list(payload.items()):
        if campo not in schema or valor is None or str(valor).strip() in ("", "N/D"):
            continue
        mapeado = _mapear_valor_para_opcao(valor, schema[campo])
        if mapeado is None:
            amostra = ", ".join(f'"{o}"' for o in schema[campo][:8])
            sufixo = "…" if len(schema[campo]) > 8 else ""
            erros.append(
                f'Campo "{campo}": valor "{valor}" não está cadastrado no Airtable. '
                f"Opções válidas: {amostra}{sufixo}"
            )
        else:
            payload[campo] = mapeado

    if erros:
        raise ValueError(" ".join(erros))
    return payload


def _get_setting(key, default=None):
    import streamlit as st

    try:
        val = st.secrets.get(key)
        if val:
            return val
    except Exception:
        pass
    return os.getenv(key, default)


def get_credentials():
    api_key = _get_setting("AIRTABLE_TOKEN")
    base_id = _get_setting("AIRTABLE_BASE_ID") or _get_setting("BASE_ID")
    return api_key, base_id


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
            timeout=30,
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


def buscar_todas_apas():
    """
    Busca todas as APAs da tabela "PARA ANALISE QUALITATIVA DA APA".
    Retorna: DataFrame com os dados
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
            # Garante que 'id' não fique com o número da APA (campo ID) por colisão de nome
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
    Retorna: (DataFrame, status_string)
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


def buscar_todas_tecnicas():
    """
    Busca todas as técnicas da tabela "TABELA DE FREQUÊNCIAS DAS TÉCNICAS".

    Usada por: app.py
        df_tec, status_t = airtable_link.buscar_todas_tecnicas()

    Retorna:
        - DataFrame com todas as técnicas (pode ser vazio se não há registros)
        - String de status
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
    """Confirma que o record_id existe e pertence ao ID numérico da APA (campo ID)."""
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
    """
    Busca o record_id (rec...) de uma APA pelo número/código do campo ID.
    Ex.: 31, 31.0, 'APA 031' → 'recXXXXXXXX'
    """
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

        for registro in table.all():
            campo_id = registro["fields"].get("ID")
            if _campo_id_coincide(campo_id, id_num, id_fmt):
                return registro["id"]
        return None
    except Exception as exc:
        print(f"[airtable_link] Erro ao buscar APA {id_apa} em {table_name}: {exc}")
        return None


def buscar_record_id_vinculo_tecnica(id_apa, record_id_hint=None):
    """
    Record ID na tabela PARA ANALISE ligada ao Vinculo_APA, localizado pelo ID da APA.
    Nunca reutiliza record_id do cache sem confirmar que é a APA correta.
    """
    tabela_apa = _tabela_vinculo_tecnicas()

    if record_id_hint and str(record_id_hint).strip().startswith("rec"):
        hint = str(record_id_hint).strip()
        if record_id_pertence_apa(hint, id_apa, table_name=tabela_apa):
            return hint
        print(
            f"[airtable_link] record_id em cache ({hint}) não corresponde à APA {id_apa}; "
            "buscando novamente na API."
        )

    return buscar_record_id_por_id_apa(id_apa, table_name=tabela_apa)


def atualizar_apa_validacao(id_apa, payload, record_id_interno=None):
    """
    Atualiza um registro de APA existente.

    Args:
        id_apa: ID formatado "APA 001" — usado como fallback de busca.
        payload: Dict com os campos a atualizar.
        record_id_interno: Airtable internal record ID (ex: 'recXXXXXXXXXXXXXX').
            Quando fornecido, atualiza diretamente sem varrer registros.

    Returns:
        True se atualizado com sucesso.
        False se APA não encontrada (sem record_id e busca vazia).

    Raises:
        RuntimeError: com mensagem da API do Airtable em caso de erro de escrita.
        ValueError: se credenciais não configuradas.
    """
    api_key, base_id = get_credentials()

    if not api_key or not base_id:
        raise ValueError("Credenciais do Airtable não configuradas (AIRTABLE_TOKEN / AIRTABLE_BASE_ID).")

    api = Api(api_key)
    base = api.base(base_id)
    table = base.table("PARA ANALISE QUALITATIVA DA APA")

    utils.validar_tempos_payload_airtable(payload)
    validar_selects_payload_apa(payload)

    # Caminho direto: record_id_interno fornecido (recXXXXXX)
    if record_id_interno and str(record_id_interno).startswith("rec"):
        try:
            table.update(record_id_interno, payload)
            print(f"✅ APA {id_apa} atualizada com sucesso (via record_id_interno={record_id_interno})")
            return True
        except Exception as e:
            raise RuntimeError(
                f"Airtable rejeitou a atualização (record={record_id_interno}): {str(e)}"
            ) from e

    # Fallback: busca pelo campo ID
    try:
        id_num = int(str(id_apa).replace("APA", "").strip())
    except (ValueError, TypeError):
        id_num = None

    id_apa_str = str(id_apa).strip().upper()

    record_encontrado = None
    try:
        for r in table.all():
            campo_id = r['fields'].get('ID')
            if campo_id is None:
                continue
            match_num = (id_num is not None and campo_id == id_num)
            try:
                campo_id_fmt = f"APA {int(campo_id):03d}"
                match_fmt = (campo_id_fmt == id_apa_str)
            except (ValueError, TypeError):
                match_fmt = (str(campo_id).strip().upper() == id_apa_str)
            if match_num or match_fmt:
                record_encontrado = r
                break
    except Exception as e:
        raise RuntimeError(f"Erro ao buscar registros no Airtable: {str(e)}") from e

    if not record_encontrado:
        print(f"❌ APA {id_apa} não encontrada via busca de campo")
        return False

    try:
        table.update(record_encontrado['id'], payload)
        print(f"✅ APA {id_apa} atualizada com sucesso (via busca de campo)")
        return True
    except Exception as e:
        raise RuntimeError(
            f"Airtable rejeitou a atualização (record={record_encontrado['id']}): {str(e)}"
        ) from e


def criar_nova_apa(payload):
    """
    Cria um novo registro de APA no Airtable.

    O campo ID é autonumeração — não deve ser enviado no payload.
    Retorna: dict com chaves "id" (str|None) e "erro" (str|None).
    """
    print("[criar_nova_apa] Iniciando criacao de registro")

    try:
        api_key, base_id = get_credentials()

        print(f"[criar_nova_apa] API_KEY configurada: {bool(api_key)}")
        print(f"[criar_nova_apa] BASE_ID configurada: {bool(base_id)}")

        if not api_key or not base_id:
            erro = "Credenciais do Airtable nao configuradas (AIRTABLE_TOKEN / AIRTABLE_BASE_ID)."
            print(f"[criar_nova_apa] ERRO: {erro}")
            return {"id": None, "erro": erro}

        api = Api(api_key)
        base = api.base(base_id)
        table = base.table("PARA ANALISE QUALITATIVA DA APA")

        if "ID" in payload:
            del payload["ID"]

        utils.validar_tempos_payload_airtable(payload)
        validar_selects_payload_apa(payload)

        print(f"[criar_nova_apa] Enviando {len(payload)} campos para o Airtable")

        novo_record = table.create(payload)
        record_id = novo_record.get("id")
        fields = novo_record.get("fields", {})
        id_numero = fields.get("ID")

        if id_numero is None and record_id:
            try:
                refetch = table.get(record_id)
                id_numero = refetch.get("fields", {}).get("ID")
            except Exception as exc:
                print(f"[criar_nova_apa] Releitura do registro falhou: {exc}")

        if id_numero is None:
            erro = (
                "Registro criado no Airtable, mas o campo ID (autonumeração) não foi retornado. "
                f"Confira manualmente o registro {record_id}."
            )
            print(f"[criar_nova_apa] AVISO: {erro}")
            return {"id": None, "record_id": record_id, "erro": erro}

        id_formatado = f"APA {int(id_numero):03d}"
        print(f"[criar_nova_apa] Registro criado: {id_formatado} ({record_id})")
        return {"id": id_formatado, "record_id": record_id, "erro": None}

    except ValueError as e:
        return {"id": None, "erro": str(e)}
    except Exception as e:
        erro = _formatar_erro_airtable(e)
        print(f"[criar_nova_apa] ERRO {type(e).__name__}: {erro}")
        import traceback
        traceback.print_exc()
        return {"id": None, "erro": erro}


def criar_tecnica(payload, vinculo_record_id=None, id_apa=None):
    """
    Cria um novo registro de técnica no Airtable.

    Vinculo_APA é linked record: envia [rec...] da APA encontrada pelo ID (31, APA 031).

    Returns:
        tuple: (sucesso: bool, erro: str | None)
    """
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
            return False, (
                f"Não foi possível localizar o registro Airtable da APA {ref_msg} "
                f"na tabela de vínculo ({_tabela_vinculo_tecnicas()})."
            )

        if id_apa and not record_id_pertence_apa(rec, id_apa):
            return False, (
                f"O vínculo interno ({rec}) não corresponde à APA {id_apa}. "
                "Recarregue os dados e selecione a APA novamente."
            )

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
                    return False, f"ATITUDE inválida: {atitude} (esperado -1, 0 ou 1)."
                payload['ATITUDE DO CAUSADOR'] = atitude
            except (ValueError, TypeError):
                return False, "ATITUDE deve ser número inteiro (-1, 0 ou 1)."

        table.create(payload)
        return True, None

    except Exception as e:
        return False, _formatar_erro_airtable(e)
