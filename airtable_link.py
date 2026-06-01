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
    import os
    from pyairtable import Api
    
    try:
        api_key = os.getenv("AIRTABLE_TOKEN")
        base_id = os.getenv("AIRTABLE_BASE_ID")
        
        if not api_key or not base_id:
            print("❌ Credenciais não configuradas")
            return False
        
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