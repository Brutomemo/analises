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

    def atualizar_apa_com_validacoes(id_apa, agressividade, 
                                  receptividade, tecnicas, 
                                  observacoes, duplicata, validado_por):
    """Atualiza APA com dados de validação"""
    
    import airtable
    
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    table_name = "APAs"
    
    at = airtable.Airtable(base_id, table_name, api_key)
    
    # Converter escala para número
    escala_map = {
        "Não agressivo": 1,
        "Neutro": 2,
        "Parc. agressivo": 3,
        "Agressivo": 4,
        "Muito agressivo": 5
    }
    
    payload = {
        "Agressividade Chegada": escala_map.get(agressividade, 0),
        "Receptividade Chegada": escala_map.get(receptividade, 0),
        "Técnicas Aplicadas": tecnicas,
        "Observações Validador": observacoes,
        "É Duplicata": duplicata,
        "Validado Por": validado_por,
        "Data Validação": datetime.now().isoformat()
    }
    
    # Buscar e atualizar record
    records = at.get_all(
        formula=f"{{ID}} = '{id_apa}'"
    )
    
    if records:
        record_id = records[0]['id']
        at.update(record_id, payload)
        return True
    
    return False