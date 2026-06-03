import streamlit as st
import requests
import pandas as pd
import os


# ==========================================
# CREDENCIAIS DO AIRTABLE
# ==========================================
def get_credentials():
    """Lê credenciais de variáveis de ambiente (Railway) ou secrets.toml (local)."""
    airtable_token = os.getenv("AIRTABLE_TOKEN")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    if not airtable_token or not base_id:
        try:
            airtable_token = st.secrets.get("AIRTABLE_TOKEN") or airtable_token
            base_id = st.secrets.get("BASE_ID") or st.secrets.get("AIRTABLE_BASE_ID") or base_id
        except Exception:
            pass

    if not airtable_token or not base_id:
        raise ValueError("❌ AIRTABLE_TOKEN ou BASE_ID não configurados!")

    return airtable_token, base_id


TABELA_QUALITATIVA = "PARA ANALISE QUALITATIVA DA APA"
TABELA_TECNICAS = "TABELA DE FREQUÊNCIAS DAS TÉCNICAS"


# ==========================================
# LEITURA DE DADOS
# ==========================================

@st.cache_data(ttl=600, show_spinner=False)
def buscar_tabela_airtable(nome_tabela):
    """Busca todos os registros de uma tabela Airtable com paginação."""
    try:
        AIRTABLE_TOKEN, BASE_ID = get_credentials()
    except ValueError as e:
        return pd.DataFrame(), f"Erro: {str(e)}"
    except Exception as e:
        return pd.DataFrame(), f"Erro ao obter credenciais: {str(e)}"

    url = f"https://api.airtable.com/v0/{BASE_ID}/{nome_tabela}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}

    registos = []
    offset = None

    while True:
        params = {}
        if offset:
            params["offset"] = offset

        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return pd.DataFrame(), f"Erro de rede/API: {str(e)}"

        dados = response.json()

        for r in dados.get("records", []):
            campos = r.get("fields", {})
            campos["Airtable_Record_ID"] = r.get("id")
            registos.append(campos)

        offset = dados.get("offset")
        if not offset:
            break

    return pd.DataFrame(registos), "Sucesso"


def buscar_dados_apa():
    """Busca dados da tabela qualitativa."""
    df, status = buscar_tabela_airtable(TABELA_QUALITATIVA)
    if status == "Sucesso" and not df.empty:
        st.session_state["df_quali"] = df
    return df, status


def buscar_todas_tecnicas():
    """Busca dados da tabela de técnicas."""
    df, status = buscar_tabela_airtable(TABELA_TECNICAS)
    if status == "Sucesso" and not df.empty:
        st.session_state["df_tec"] = df
    return df, status


# ==========================================
# ESCRITA DE DADOS
# ==========================================

def criar_nova_apa(payload):
    """
    Cria um novo registro de APA no Airtable.

    O campo 'ID' é autonumeração (somente leitura) — nunca deve ser enviado no payload.
    Retorna o ID formatado como 'APA 007' em caso de sucesso, ou False em caso de erro.
    """
    from pyairtable import Api

    print("\n" + "=" * 60)
    print("INICIANDO criar_nova_apa()")
    print("=" * 60)

    try:
        api_key, base_id = get_credentials()
        print(f"Credenciais OK — BASE_ID: {base_id}")

        api = Api(api_key)
        table = api.base(base_id).table(TABELA_QUALITATIVA)

        # O campo 'ID' é computed (autonumeração); removê-lo evita erro 422
        payload.pop("ID", None)

        print(f"Campos enviados: {list(payload.keys())}")

        novo_record = table.create(payload)

        id_numerico = novo_record.get("fields", {}).get("ID", "")
        id_formatado = f"APA {int(id_numerico):03d}" if id_numerico else novo_record.get("id", "criado")

        print(f"SUCESSO — Record Airtable: {novo_record.get('id')} | ID: {id_formatado}")
        print("=" * 60 + "\n")
        return id_formatado

    except Exception as e:
        import traceback
        print(f"\nERRO: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        print("=" * 60 + "\n")
        return False


def criar_tecnica(payload):
    """Cria um novo registro na tabela de técnicas do Airtable."""
    from pyairtable import Api

    try:
        api_key, base_id = get_credentials()
        api = Api(api_key)
        table = api.base(base_id).table(TABELA_TECNICAS)
        table.create(payload)
        return True
    except Exception as e:
        print(f"Erro ao criar técnica: {type(e).__name__}: {str(e)}")
        return False


def atualizar_apa_validacao(id_apa, payload):
    """
    Atualiza um registro de APA com dados de validação.

    Args:
        id_apa: ID numérico da APA no Airtable (int) ou formatado "APA 007"
        payload: Dict com campos a atualizar

    Returns:
        bool: True se sucesso, False se erro
    """
    from pyairtable import Api

    try:
        api_key, base_id = get_credentials()
        api = Api(api_key)
        table = api.base(base_id).table(TABELA_QUALITATIVA)

        # Normaliza o ID para comparação (aceita "APA 007" ou número inteiro)
        id_limpo = str(id_apa).strip().upper()
        todos_records = table.all()
        record_encontrado = None

        for record in todos_records:
            id_no_airtable = str(record["fields"].get("ID", "")).strip().upper()
            if id_no_airtable == id_limpo:
                record_encontrado = record
                break

        if not record_encontrado:
            print(f"APA {id_apa} não encontrada")
            return False

        table.update(record_encontrado["id"], payload)
        print(f"APA {id_apa} atualizada com sucesso")
        return True

    except Exception as e:
        print(f"Erro ao atualizar APA: {str(e)}")
        return False
