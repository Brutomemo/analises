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


def atualizar_apa_validacao(id_apa, payload):
    """
    Atualiza um registro de APA existente.

    id_apa aceita tanto o formato "APA 001" (string) quanto o inteiro 1.
    A comparação normaliza ambos os formatos para garantir o match.
    """
    try:
        api_key, base_id = get_credentials()

        if not api_key or not base_id:
            print("❌ Credenciais não configuradas")
            return False

        api = Api(api_key)
        base = api.base(base_id)
        table = base.table("PARA ANALISE QUALITATIVA DA APA")

        # Normaliza o id_apa recebido para número inteiro (ex: "APA 001" → 1)
        try:
            id_num = int(str(id_apa).replace("APA", "").strip())
        except (ValueError, TypeError):
            id_num = None

        id_apa_str = str(id_apa).strip().upper()

        record_encontrado = None
        todos_records = table.all()

        for r in todos_records:
            campo_id = r['fields'].get('ID')
            if campo_id is None:
                continue

            # Compara por número inteiro
            match_num = (id_num is not None and campo_id == id_num)

            # Compara por string formatada "APA 001"
            try:
                campo_id_fmt = f"APA {int(campo_id):03d}"
                match_fmt = (campo_id_fmt == id_apa_str)
            except (ValueError, TypeError):
                match_fmt = (str(campo_id).strip().upper() == id_apa_str)

            if match_num or match_fmt:
                record_encontrado = r
                break

        if not record_encontrado:
            print(f"❌ APA {id_apa} não encontrada")
            return False

        record_id = record_encontrado['id']
        table.update(record_id, payload)

        print(f"✅ APA {id_apa} atualizada com sucesso")
        return True

    except Exception as e:
        print(f"❌ Erro ao atualizar APA: {str(e)}")
        return False


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


def criar_tecnica(payload):
    """
    Cria um novo registro de técnica no Airtable.

    Args:
        payload: Dict com:
            - TÉCNICAS: Nome da técnica (obrigatório)
            - TRECHO DA TRANSCRIÇÃO: Texto (obrigatório)
            - Vinculo_APA: ID formatado, ex: "APA 001" (obrigatório)
            - ATITUDE DO CAUSADOR: -1, 0 ou 1 (opcional — vazio = Inaudível/Não Observado)

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

        if not payload.get('Vinculo_APA'):
            print("❌ Campo Vinculo_APA obrigatório")
            return False

        # Validar ATITUDE — vazio é válido (Inaudível/Não Observado)
        atitude_raw = payload.get('ATITUDE DO CAUSADOR', None)
        vazio = (
            atitude_raw is None
            or atitude_raw == ""
            or (isinstance(atitude_raw, float) and pd.isna(atitude_raw))
        )

        if vazio:
            # Remove o campo para não enviar string vazia ao Airtable
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
