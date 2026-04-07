import streamlit as st # Adicione este import no topo
import requests
import json
import re

def analisar_ocorrencia_gate(dados_extraidos):
    """
    Versão segura para GitHub/Streamlit Cloud.
    """
    # Em vez de colar a chave aqui, chamamos o "cofre" do Streamlit
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        # Caso você rode localmente e esqueça de configurar
        return {"parecer": "Erro: Chave da OpenAI não configurada nos Secrets."}

    endpoint = "https://api.openai.com/v1/chat/completions"
    
    # ... o restante do seu código continua IGUAL ...
    
    system_prompt = """Você é um Especialista Sênior em Negociação Policial (GATE).
Sua missão é analisar as transcrições de áudio e os metadados de uma ocorrência crítica.
Você DEVE retornar a sua análise obrigatoriamente no formato JSON, contendo uma única chave chamada "parecer".

O conteúdo dentro da chave "parecer" deve ser um texto analítico e direto (usando formatação Markdown), dividido em:
1. **Diagnóstico Emocional do Causador**
2. **Avaliação Tática da Equipe de Negociação** (uso de rapport, escuta ativa, etc)
3. **Pontos Fortes e Oportunidades de Melhoria**"""
    
    # Prepara os dados para enviar à IA
    try:
        if isinstance(dados_extraidos["transcricao"], dict):
            transcricao_str = json.dumps(dados_extraidos["transcricao"], ensure_ascii=False)
        else:
            transcricao_str = dados_extraidos["transcricao"].to_json(orient="records", force_ascii=False)
            
        metadados_str = dados_extraidos["metadados"].to_json(orient="records", force_ascii=False)
        user_prompt = f"Metadados da ocorrência:\n{metadados_str}\n\nTranscrições do Áudio:\n{transcricao_str}"
    except Exception:
        user_prompt = f"Dados do incidente crítico:\n{dados_extraidos}"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3, # Baixa temperatura para foco analítico
        "response_format": { "type": "json_object" } # Força o retorno estrito em JSON
    }
    
    try:
        response = requests.post(endpoint, headers=headers, json=data, timeout=60)
        response.raise_for_status() 
        raw_json = response.json()['choices'][0]['message']['content']
        return json.loads(raw_json)
        
    except requests.exceptions.HTTPError as err:
        return {"parecer": f"Erro de comunicação com a OpenAI (Verifique a sua Chave de API). Detalhe: {err.response.text}"}
    except json.JSONDecodeError:
        return {"parecer": "Erro: A Inteligência Artificial falhou em estruturar o laudo analítico."}
    except Exception as e:
        return {"parecer": f"Falha na execução da IA: {str(e)}"}

# =========================================================
# 2. MOTOR DE INFERÊNCIA ESTATÍSTICA (SEM VIÉS DA IA)
# =========================================================

def gerar_laudo_frio(likert_inicio, likert_fim, stats_spearman):
    """
    Escreve o parecer tático puramente baseado nos números matemáticos.
    Se a agressividade não caiu, ele vai dizer de forma direta, sem eufemismos.
    """
    laudo = []
    
    # Cálculos dos Deltas (Variação entre o final e o início)
    delta_r = likert_fim.get('receptividade_media', 0) - likert_inicio.get('receptividade_media', 0)
    delta_a = likert_fim.get('agressividade_media', 0) - likert_inicio.get('agressividade_media', 0)
    
    # 1. Análise de Receptividade (Fato Frio)
    if delta_r > 0:
        laudo.append(f"A receptividade média do causador apresentou aumento durante a ocorrência (Delta = +{delta_r:.1f}).")
    elif delta_r < 0:
        laudo.append(f"A receptividade média do causador sofreu redução durante a ocorrência (Delta = {delta_r:.1f}).")
    else:
        laudo.append("A receptividade média do causador permaneceu inalterada/estagnada ao longo da ocorrência.")

    # 2. Análise de Agressividade (Fato Frio)
    if delta_a < 0:
        laudo.append(f"Observou-se mitigação na agressividade média (Delta = {delta_a:.1f}).")
    elif delta_a > 0:
        laudo.append(f"Houve escalada na agressividade média (Delta = +{delta_a:.1f}).")
    else:
        laudo.append("A agressividade média não apresentou variação direcional.")

    # 3. Análise Inferencial (O teste de realidade)
    if not stats_spearman.get('valido'):
        laudo.append("Não foi possível estabelecer correlação estatística devido à insuficiência de pontos de dados nos quartis (N < 3).")
    else:
        p_val = stats_spearman['p_value']
        rho = stats_spearman['rho']
        
        # Rigor estatístico: p-value tem que ser menor que 0.05 para não ser sorte
        if p_val < 0.05:
            forca = "forte" if abs(rho) > 0.6 else "moderada"
            direcao = "positiva" if rho > 0 else "negativa"
            laudo.append(
                f"A análise de Spearman confirma validade estatística (p < 0.05). "
                f"Existe uma correlação {forca} e {direcao} (Rho = {rho:.2f}) entre o tempo de negociação e o desfecho da agressividade. "
                "Conclui-se que as intervenções tiveram impacto direto e quantificável no cenário."
            )
        else:
            laudo.append(
                f"A análise de Spearman NÃO identificou significância estatística (p = {p_val:.3f}, o que é > 0.05). "
                f"O coeficiente Rho de {rho:.2f} sugere que a variação emocional não possui aderência matemática forte ao tempo gasto, "
                "indicando forte interferência de outras variáveis não isoladas no momento."
            )
            
    return "\n\n".join(laudo)