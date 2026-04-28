import streamlit as st
import requests
import pandas as pd

# ==========================================
# CREDENCIAIS DO AIRTABLE (VIA SECRETS)
# ==========================================
def get_credentials():
    return st.secrets["AIRTABLE_TOKEN"], st.secrets["BASE_ID"]

TABELA_QUALITATIVA = "PARA ANALISE QUALITATIVA DA APA"
TABELA_TECNICAS = "TABELA DE FREQUÊNCIAS DAS TÉCNICAS"

@st.cache_data(ttl=600, show_spinner=False)
def buscar_tabela_airtable(nome_tabela):
    """Função mestre de conexão com a API (com captura de Record ID e Caching)."""
    try:
        AIRTABLE_TOKEN, BASE_ID = get_credentials()
    except KeyError:
        return pd.DataFrame(), "Erro: Credenciais do Airtable não encontradas nos secrets."

    url = f"https://api.airtable.com/v0/{BASE_ID}/{nome_tabela}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    
    registos = []
    offset = None
    
    while True:
        params = {}
        if offset: params['offset'] = offset
            
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
        if not offset: break
            
    return pd.DataFrame(registos), "Sucesso"

# ==========================================
# BUSCAR DADOS
# ==========================================

def buscar_dados_apa():
    df, status = buscar_tabela_airtable(TABELA_QUALITATIVA)
    # ÂNCORA 1: Salva a base de ocorrências no momento do download
    if status == "Sucesso" and not df.empty:
        st.session_state["df_quali"] = df
    return df, status

def buscar_todas_tecnicas():
    df, status = buscar_tabela_airtable(TABELA_TECNICAS)
    # ÂNCORA 2: Salva a base de técnicas no momento do download
    if status == "Sucesso" and not df.empty:
        st.session_state["df_tec"] = df
    return df, status