# ============================================================
# airtable_link.py - INTEGRAÇÃO COM AIRTABLE
# ============================================================

import os
import pandas as pd
from pyairtable import Api
from datetime import datetime


def get_credentials():
    """
    Obtém credenciais do Airtable de variáveis de ambiente.
    Retorna: (api_key, base_id)
    """
    api_key = os.getenv("AIRTABLE_TOKEN")
    base_id = os.getenv("AIRTABLE_BASE_ID") or os.getenv("BASE_ID")
    return api_key, base_id


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
            fields['id'] = record['id']
            # Alias para compatibilidade com código que usa 'Airtable_Record_ID'
            fields['Airtable_Record_ID'] = record['id']
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
            fields['id'] = record['id']
            data.append(fields)

        df = pd.DataFrame(data)

        if df.empty:
            return df, "⚠️ Nenhuma técnica encontrada"
        else:
            return df, f"✅ {len(df)} técnicas carregadas"

    except Exception as e:
        print(f"❌ Erro ao buscar técnicas: {str(e)}")
        return pd.DataFrame(), f"❌ Erro: {str(e)}"


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
    Retorna: str ID formatado ("APA 007") se sucesso, None se erro.
    """
    print("\n" + "="*60)
    print("🔍 INICIANDO criar_nova_apa()")
    print("="*60)

    try:
        api_key, base_id = get_credentials()

        print(f"1️⃣ API_KEY carregada? {bool(api_key)}")
        print(f"2️⃣ BASE_ID carregada? {bool(base_id)}")

        if not api_key or not base_id:
            print("❌ ERRO: Credenciais não configuradas!")
            return None

        print("✅ Credenciais OK")

        print("\n3️⃣ Conectando à API Airtable...")
        api = Api(api_key)
        base = api.base(base_id)
        table = base.table("PARA ANALISE QUALITATIVA DA APA")
        print("✅ Tabela acessada")

        if "ID" in payload:
            del payload["ID"]

        print("\n4️⃣ Criando registro no Airtable...")
        print(f"   Campos: {list(payload.keys())}")

        novo_record = table.create(payload)

        print("✅ Registro criado no Airtable")

        id_numero = novo_record.get('fields', {}).get('ID')

        if id_numero:
            id_formatado = f"APA {int(id_numero):03d}"
            print(f"✅ ID gerado: {id_formatado}")
        else:
            id_formatado = None
            todos = table.all()
            max_id = 0

            for r in todos:
                try:
                    num = int(r['fields'].get('ID', 0))
                    if num > max_id:
                        max_id = num
                except Exception:
                    pass

            if max_id > 0:
                id_formatado = f"APA {max_id:03d}"
                print(f"✅ ID gerado (buscado): {id_formatado}")

        print("="*60 + "\n")
        return id_formatado

    except Exception as e:
        print(f"\n❌ ERRO: {type(e).__name__}")
        print(f"   Mensagem: {str(e)}")
        print("="*60 + "\n")
        import traceback
        traceback.print_exc()
        return None


def criar_tecnica(payload, vinculo_record_id=None):
    """
    Cria um novo registro de técnica no Airtable.

    Args:
        payload: Dict com:
            - TÉCNICAS: Nome da técnica (obrigatório)
            - TRECHO DA TRANSCRIÇÃO: Texto (obrigatório)
            - Vinculo_APA: ID formatado "APA 001" — usado apenas como fallback
            - ATITUDE DO CAUSADOR: -1, 0 ou 1 (opcional — vazio = Inaudível/Não Observado)
        vinculo_record_id: Airtable internal record ID da APA (ex: 'recXXXXXXXXXXXXXX').
            Quando fornecido, `Vinculo_APA` é enviado como lista ['recXXX'] (linked record),
            que é o formato correto para campos do tipo "Link to another record".

    Returns:
        bool: True se sucesso, False se erro
    """
    try:
        api_key, base_id = get_credentials()

        if not api_key or not base_id:
            print("❌ Credenciais não configuradas")
            return False

        api = Api(api_key)
        base = api.base(base_id)
        table = base.table("TABELA DE FREQUÊNCIAS DAS TÉCNICAS")

        if not payload.get('TÉCNICAS'):
            print("❌ Campo TÉCNICAS obrigatório")
            return False

        if not payload.get('TRECHO DA TRANSCRIÇÃO'):
            print("❌ Campo TRECHO DA TRANSCRIÇÃO obrigatório")
            return False

        # Montar Vinculo_APA no formato correto para linked record
        if vinculo_record_id and str(vinculo_record_id).startswith("rec"):
            payload['Vinculo_APA'] = [vinculo_record_id]
            print(f"🔗 Vinculo_APA como linked record: [{vinculo_record_id}]")
        elif not payload.get('Vinculo_APA'):
            print("❌ Campo Vinculo_APA obrigatório (nem texto nem record_id fornecido)")
            return False
        else:
            print(f"⚠️ Vinculo_APA como texto simples: {payload['Vinculo_APA']} (linked record não disponível)")

        # Validar ATITUDE — vazio é válido (Inaudível/Não Observado)
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
                    print(f"❌ ATITUDE inválida: {atitude} (esperado -1, 0 ou 1)")
                    return False
                payload['ATITUDE DO CAUSADOR'] = atitude
            except (ValueError, TypeError):
                print("❌ ATITUDE deve ser número inteiro (-1, 0 ou 1)")
                return False

        novo_record = table.create(payload)
        print(f"✅ Técnica criada: {payload.get('TÉCNICAS')} → {payload.get('Vinculo_APA')}")
        return True

    except Exception as e:
        print(f"❌ Erro ao criar técnica: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
