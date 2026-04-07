import json
import requests

def estruturar_resultado_para_ia(amostra_total, resultados_chi, resultados_ordinal, resultados_gee):
    """
    Recebe os resultados matemáticos do Python e estrutura em um dict padronizado.
    """
    payload = {
        "metadados_analise": {
            "objetivo": "Investigar a associação entre técnicas de negociação e desfecho da interação, avaliando simultaneamente a existência de viés na percepção dos negociadores, com controle estatístico para variáveis de contexto (cenário) e efeitos agrupados por avaliador.",
            "metodos_aplicados": ["Qui-Quadrado (Viés)", "Regressão Logística Ordinal", "GEE - Equações de Estimação Generalizadas"],
            "tamanho_amostra_filtrada": amostra_total
        },
        "resultados_estatisticos": {
            "qui_quadrado_vies": resultados_chi if resultados_chi else "Dados insuficientes",
            "regressao_ordinal": resultados_ordinal if resultados_ordinal else "Nenhum coeficiente significativo",
            "multinivel_gee": resultados_gee if resultados_gee else "Nenhum coeficiente significativo"
        }
    }
    return payload

def montar_prompt_estatistico(payload_json):
    """
    Monta o prompt de sistema rígido para a IA atuar como Estatístico Sênior.
    """
    system_prompt = """Você é um Cientista de Dados Sênior e Especialista em Estatística Aplicada à Segurança Pública.
Sua tarefa é interpretar resultados estatísticos de técnicas de negociação policial.
REGRAS RÍGIDAS:
1. NUNCA infira causalidade (ex: 'A técnica causou a rendição'). Use termos como 'está associada a', 'apresenta maior chance de'.
2. Trabalhe EXCLUSIVAMENTE com os dados numéricos fornecidos no payload. Não invente técnicas ou métricas.
3. Diferencie claramente viés de percepção (relatado no Qui-Quadrado) da eficácia controlada (GEE/Ordinal).
4. Explicite limitações se as amostras forem baixas.
5. VOCÊ DEVE RESPONDER ÚNICA E EXCLUSIVAMENTE COM UM OBJETO JSON VÁLIDO. Nenhuma palavra fora do JSON.

O JSON deve seguir EXATAMENTE esta estrutura de chaves:
{
  "objetivo": "Resumo do que foi analisado",
  "metodo": "Breve explicação das abordagens matemáticas utilizadas",
  "premissas": "Premissas e limitações do modelo dado o N amostral",
  "resultados_principais": "Síntese dos achados mais relevantes",
  "interpretacao": "Tradução tática dos coeficientes (O que significa na prática para o GATE?)",
  "categorias_destaque": "Técnicas que tiveram P-valor < 0.05",
  "tamanho_efeito": "Explicação dos Odds Ratios ou coeficientes GEE encontrados",
  "limitacoes": "Avisos sobre viés do negociador ou separação perfeita",
  "conclusao": "Veredito estratégico final e prudente"
}"""
    
    user_prompt = f"Aqui estão os resultados matemáticos processados pelo Python:\n{json.dumps(payload_json, ensure_ascii=False)}"
    
    return system_prompt, user_prompt

import streamlit as st # Garanta que este import esteja no topo do arquivo

def gerar_relatorio_com_ia(payload):
    """
    Chama a API da OpenAI de forma autônoma e segura.
    """
    system, user = montar_prompt_estatistico(payload)
    
    # === ACESSO SEGURO AO COFRE ===
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        return {"erro": "Configuração de chave ausente no Streamlit Cloud."}
    
    endpoint = "https://api.openai.com/v1/chat/completions"
        
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": "gpt-4o-mini", # Você pode mudar para "gpt-4o" ou "gpt-3.5-turbo" se preferir
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "temperature": 0.2, 
        "response_format": { "type": "json_object" } # Trava a IA para responder apenas em JSON
    }
    
    try:
        import requests
        
        # Dispara a requisição direta para a OpenAI
        response = requests.post(endpoint, headers=headers, json=data, timeout=60)
        
        # Se a chave estiver errada ou sem saldo, ele captura o erro aqui
        response.raise_for_status() 
        
        raw_json = response.json()['choices'][0]['message']['content']
        return json.loads(raw_json)
        
    except json.JSONDecodeError:
        return {"erro": "A IA não retornou um formato JSON válido."}
    except requests.exceptions.HTTPError as err:
        return {"erro": f"Erro de comunicação com a OpenAI (Verifique sua chave): {err.response.text}"}
    except Exception as e:
        return {"erro": f"Falha na execução da IA: {str(e)}"}