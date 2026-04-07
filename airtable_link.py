import streamlit as st # Adicione esta linha no topo
import requests
import pandas as pd

# ==========================================
# CREDENCIAIS DO AIRTABLE (VIA SECRETS)
# ==========================================
# O Streamlit vai buscar automaticamente no local correto
AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
BASE_ID = st.secrets["BASE_ID"]

TABELA_QUALITATIVA = "PARA ANALISE QUALITATIVA DA APA"
TABELA_TECNICAS = "TABELA DE FREQUÊNCIAS DAS TÉCNICAS"

def buscar_tabela_airtable(nome_tabela):
    """Função mestre de conexão com a API (com captura de Record ID)."""
    url = f"https://api.airtable.com/v0/{BASE_ID}/{nome_tabela}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    # ... resto do código igual ...
    
    registos = []
    offset = None
    
    while True:
        params = {}
        if offset: params['offset'] = offset
            
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            return pd.DataFrame(), f"Erro: {response.status_code} - {response.text}"
            
        dados = response.json()
        
        # O PULO DO GATO: Captura o ID interno do Airtable para os cruzamentos
        for r in dados.get('records', []):
            campos = r.get('fields', {})
            campos['Airtable_Record_ID'] = r.get('id') 
            registos.append(campos)
        
        offset = dados.get('offset')
        if not offset: break
            
    return pd.DataFrame(registos), "Sucesso"

def buscar_dados_apa():
    return buscar_tabela_airtable(TABELA_QUALITATIVA)

def buscar_todas_tecnicas():
    return buscar_tabela_airtable(TABELA_TECNICAS)