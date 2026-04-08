import json
import requests

def estruturar_resultado_para_ia(amostra_total, resultados_chi, resultados_ordinal, resultados_gee):
    """
    Recebe os resultados matemáticos do Python e estrutura em um dict padronizado.
    """
    payload = {
        "metadados_analise": {
            "objetivo": "Investigar a associação entre técnicas de negociação e a mudança de atitude do causador frente à intervenção, avaliando simultaneamente a existência de viés na percepção dos negociadores, com controle estatístico para variáveis de contexto (cenário) e efeitos agrupados por avaliador.",
            "pergunta_principal": "Os padrões observados estão associados às técnicas empregadas ou podem estar influenciados por percepção do negociador e características do contexto operacional?",
            "hipotese_analitica": "Parte da variação observada pode estar associada às técnicas aplicadas, mas também pode refletir fatores de contexto e possíveis vieses de percepção.",
            "metodos_aplicados": [
                "Qui-Quadrado (Viés de percepção)",
                "Regressão Logística Ordinal",
                "GEE - Equações de Estimação Generalizadas"
            ],
            "variavel_foco": "Mudança de atitude do causador / resposta comportamental imediata frente à técnica aplicada",
            "tamanho_amostra_filtrada": amostra_total,
            "diagnostico_amostral": {
                "amostra_pequena": True if amostra_total is not None and amostra_total < 30 else False,
                "amostra_critica": True if amostra_total is not None and amostra_total < 5 else False
            },
            "regras_interpretacao": {
                "significancia_estatistica": "Considerar evidência estatística relevante quando p < 0.05.",
                "regra_causalidade": "Associação não implica causalidade.",
                "regra_ausencia": "Ausência de significância estatística não implica ausência de efeito."
            }
        },
        "resultados_estatisticos": {
            "qui_quadrado_vies": resultados_chi if resultados_chi else "Dados insuficientes para interpretação robusta do Qui-Quadrado.",
            "regressao_ordinal": resultados_ordinal if resultados_ordinal else "Não foram identificados coeficientes interpretáveis ou estatisticamente relevantes na regressão ordinal.",
            "multinivel_gee": resultados_gee if resultados_gee else "Não foram identificados coeficientes interpretáveis ou estatisticamente relevantes no modelo GEE."
        }
    }
    return payload

def montar_prompt_estatistico(payload_json):
    """
    Monta o prompt de sistema rígido para a IA atuar como Estatístico Sênior.
    """
    system_prompt = """Você é um Analista Estatístico Sênior e Especialista em Estatística Aplicada à Segurança Pública.
Sua tarefa é interpretar resultados estatísticos de técnicas de negociação policial.

REGRAS RÍGIDAS:
1. NUNCA infira causalidade. Não use expressões como:
   - 'a técnica causou'
   - 'a técnica provocou'
   - 'a técnica gerou'
   Use formulações prudentes como:
   - 'está associada a'
   - 'apresenta relação com'
   - 'há indícios de associação'
   - 'não há evidência suficiente de associação'

2. Trabalhe EXCLUSIVAMENTE com os dados fornecidos no payload. Não invente técnicas, categorias, métricas, coeficientes ou contextos.

3. Diferencie claramente:
   - viés de percepção (relatado principalmente no Qui-Quadrado e análises descritivas);
   - eficácia controlada (relatada em modelos ajustados, como Regressão Ordinal e GEE).

4. Explicite limitações quando houver:
   - amostra pequena;
   - ausência de significância estatística;
   - impossibilidade de avaliar viés do negociador;
   - separação perfeita;
   - falha de convergência;
   - ausência de coeficientes interpretáveis.

5. Ausência de significância estatística NÃO deve ser tratada como prova de ausência de efeito. Use formulações como:
   - 'não foram identificadas evidências estatisticamente significativas'
   - 'os dados não sustentam conclusão robusta'
   - 'a análise é inconclusiva sob as condições observadas'

6. Mesmo quando houver significância estatística, NÃO trate isso como validação definitiva de eficácia operacional ou doutrinária.

7. Regra de vocabulário: ao redigir o campo 'objetivo', NUNCA utilize a palavra 'desfecho'. No contexto de gerenciamento de crises, prefira obrigatoriamente:
   - 'mudança de atitude do causador'
   - 'resposta comportamental imediata frente à técnica aplicada'

8. O campo 'categorias_destaque' não deve inventar achados.
   - Se houver evidência estatisticamente relevante, descreva objetivamente quais técnicas, categorias ou coeficientes se destacaram.
   - Se não houver evidência suficiente, declare isso explicitamente.

9. O campo 'tamanho_efeito' deve interpretar apenas medidas realmente presentes no payload, como Odds Ratios, coeficientes ou outras medidas de efeito.
   - Se não houver medidas interpretáveis ou relevantes, informe isso explicitamente.

10. VOCÊ DEVE RESPONDER ÚNICA E EXCLUSIVAMENTE COM UM OBJETO JSON VÁLIDO.
   - Nenhuma palavra fora do JSON
   - Não use markdown
   - Não use crases
   - Não escreva comentários
   - Preencha todas as chaves
   - Todos os valores devem ser texto

O JSON deve seguir EXATAMENTE esta estrutura de chaves:
{
  "objetivo": "Resumo técnico do que foi analisado",
  "metodo": "Breve explicação das abordagens estatísticas utilizadas",
  "premissas": "Premissas e limitações do modelo dado o N amostral e a estrutura dos dados",
  "resultados_principais": "Síntese dos achados mais relevantes",
  "interpretacao": "Interpretação prática e prudente dos resultados no contexto operacional",
  "categorias_destaque": "Técnicas, categorias ou coeficientes que se destacaram, ou declaração explícita de ausência de evidência relevante",
  "tamanho_efeito": "Explicação dos Odds Ratios, coeficientes GEE ou outras medidas de efeito encontradas, ou declaração de ausência de medidas interpretáveis/relevantes",
  "limitacoes": "Avisos sobre viés do negociador, amostra reduzida, ausência de significância, separação perfeita ou outras restrições técnicas",
  "conclusao": "Conclusão técnica final, prudente e compatível com o nível de evidência"
}"""
    
    user_prompt = f"Aqui estão os resultados matemáticos processados pelo Python. Interprete apenas o que estiver explicitamente presente no payload a seguir:\n{json.dumps(payload_json, ensure_ascii=False, indent=2)}"
    
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