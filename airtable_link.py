import streamlit as st
import requests
import pandas as pd
import os

# ==========================================
# CREDENCIAIS DO AIRTABLE (VIA VARIÁVEIS DE AMBIENTE)
# ==========================================
def get_credentials():
    """Lê credenciais de variáveis de ambiente (Railway) ou secrets.toml (local)"""
    
    # Tentar ler de variáveis de ambiente (Railway)
    airtable_token = os.getenv("AIRTABLE_TOKEN")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    
    # Se não encontrar, tentar de secrets.toml (local)
    if not airtable_token or not base_id:
        try:
            airtable_token = st.secrets.get("AIRTABLE_TOKEN") or airtable_token
            base_id = st.secrets.get("BASE_ID") or st.secrets.get("AIRTABLE_BASE_ID") or base_id
        except:
            pass
    
    # Validação
    if not airtable_token or not base_id:
        raise ValueError("❌ AIRTABLE_TOKEN ou AIRTABLE_BASE_ID não configurados!")
    
    return airtable_token, base_id

TABELA_QUALITATIVA = "PARA ANALISE QUALITATIVA DA APA"
TABELA_TECNICAS = "TABELA DE FREQUÊNCIAS DAS TÉCNICAS"

@st.cache_data(ttl=600, show_spinner=False)
def buscar_tabela_airtable(nome_tabela):
    """Função mestre de conexão com a API (com captura de Record ID e Caching)."""
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
            params['offset'] = offset
            
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return pd.DataFrame(), f"Erro de rede/API: {str(e)}"
            
        dados = response.json()
        
        # Captura o ID interno do Airtable para os cruzamentos
        for r in dados.get('records', []):
            campos = r.get('fields', {})
            campos['Airtable_Record_ID'] = r.get('id') 
            registos.append(campos)
        
        offset = dados.get('offset')
        if not offset: 
            break
            
    return pd.DataFrame(registos), "Sucesso"

# ==========================================
# BUSCAR DADOS
# ==========================================

def buscar_dados_apa():
    """Busca dados da tabela qualitativa"""
    df, status = buscar_tabela_airtable(TABELA_QUALITATIVA)
    # ÂNCORA 1: Salva a base de ocorrências no momento do download
    if status == "Sucesso" and not df.empty:
        st.session_state["df_quali"] = df
    return df, status

def buscar_todas_tecnicas():
    """Busca dados da tabela de técnicas"""
    df, status = buscar_tabela_airtable(TABELA_TECNICAS)
    # ÂNCORA 2: Salva a base de técnicas no momento do download
    if status == "Sucesso" and not df.empty:
        st.session_state["df_tec"] = df
    return df, status


def atualizar_apa_validacao(id_apa, payload):
    """
    Atualiza um registro de APA com dados de validação
    
    Args:
        id_apa: ID da APA (ex: "APA 001")
        payload: Dict com campos a atualizar
    
    Returns:
        bool: True se sucesso, False se erro
    """
    from pyairtable import Api
    
    try:
        api_key, base_id = get_credentials()
        
        # Conectar ao Airtable
        api = Api(api_key)
        base = api.base(base_id)
        table = base.table("PARA ANALISE QUALITATIVA DA APA")
        
        # Buscar registro pela ID
        id_limpo = str(id_apa).strip().upper()
        todos_records = table.all()
        record_encontrado = None
        
        for record in todos_records:
            id_no_airtable = str(record['fields'].get('ID', '')).strip().upper()
            if id_no_airtable == id_limpo:
                record_encontrado = record
                break
        
        # Validar se encontrou
        if not record_encontrado:
            print(f"❌ APA {id_apa} não encontrada")
            return False
        
        # Atualizar o registro
        record_id = record_encontrado['id']
        table.update(record_id, payload)
        
        print(f"✅ APA {id_apa} atualizada com sucesso")
        return True
    
    except Exception as e:
        print(f"❌ Erro ao atualizar APA: {str(e)}")
        return False


# ============================================================
# ADICIONAR ESTA FUNÇÃO AO FINAL DO SEU airtable_link.py
# ============================================================

def criar_nova_apa(payload):
    """Cria um novo registro de APA no Airtable com DEBUG detalhado"""
    from pyairtable import Api
    
    print("\n" + "="*60)
    print("🔍 INICIANDO criar_nova_apa()")
    print("="*60)
    
    try:
        # 1. Verificar credenciais (usa get_credentials() para suportar secrets.toml local)
        api_key, base_id = get_credentials()
        
        print(f"1️⃣ API_KEY carregada? {bool(api_key)}")
        if api_key:
            print(f"   Primeiros 5 chars: {api_key[:5]}***")
        
        print(f"2️⃣ BASE_ID carregada? {bool(base_id)}")
        if base_id:
            print(f"   Value: {base_id}")
        
        print("✅ Credenciais OK")
        
        # 2. Conectar à API
        print("\n3️⃣ Conectando à API Airtable...")
        api = Api(api_key)
        print("✅ API conectada")
        
        # 3. Conectar à base
        print(f"\n4️⃣ Acessando base: {base_id}")
        base = api.base(base_id)
        print("✅ Base acessada")
        
        # 4. Acessar tabela
        table_name = "PARA ANALISE QUALITATIVA DA APA"
        print(f"\n5️⃣ Acessando tabela: {table_name}")
        table = base.table(table_name)
        print("✅ Tabela acessada")
        
        # 5. Gerar ID
        print("\n6️⃣ Gerando ID automático...")
        todos_records = table.all()
        print(f"   Total de registros: {len(todos_records)}")
        
        ids_existentes = []
        for r in todos_records:
            id_str = str(r['fields'].get('ID', ''))
            if id_str.startswith('APA'):
                try:
                    num = int(id_str.replace('APA', '').strip())
                    ids_existentes.append(num)
                except:
                    pass
        
        print(f"   IDs encontrados: {ids_existentes}")
        proximo_numero = max(ids_existentes) + 1 if ids_existentes else 1
        payload["ID"] = f"APA {proximo_numero:03d}"
        print(f"✅ Novo ID: {payload['ID']}")
        
        # 6. Criar registro
        print("\n7️⃣ Criando registro no Airtable...")
        print(f"   Campos: {list(payload.keys())}")
        print(f"   Total de campos: {len(payload)}")
        
        novo_record = table.create(payload)
        
        print(f"\n✅ SUCESSO! Registro criado")
        print(f"   ID no Airtable: {novo_record.get('id')}")
        print(f"   APA ID: {payload.get('ID')}")
        print("="*60 + "\n")
        # Retorna o ID gerado para que o chamador possa usá-lo
        return payload.get("ID", True)
    
    except Exception as e:
        print(f"\n❌ ERRO: {type(e).__name__}")
        print(f"   Mensagem: {str(e)}")
        print("="*60)
        import traceback
        traceback.print_exc()
        print("="*60 + "\n")
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
        print(f"❌ Erro ao criar técnica: {type(e).__name__}: {str(e)}")
        return False