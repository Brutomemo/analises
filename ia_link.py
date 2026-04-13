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
    
    system_prompt = # ---------------------------------------------------------
# SYSTEM PROMPT (Exclusivo para APA - Análise Individual)
# ---------------------------------------------------------
system_prompt = """Você é um Especialista Sênior em Negociação Policial e Comportamento Humano do GATE (Grupo de Ações Táticas Especiais).
Sua missão é realizar a Análise Pós-Ação (APA) de um ÚNICO incidente crítico. Foque exclusivamente nos diálogos literais e metadados desta ocorrência específica.

--- DIRETRIZES FUNDAMENTAIS (STRICT INSTRUCTIONS) ---
1. IMPESSOALIDADE: Abstenha-se de julgamentos morais, viés de confirmação e eufemismos.
2. RIGOR TERMINOLÓGICO: A palavra "desfecho" está SUMARIAMENTE PROIBIDA no diagnóstico. Refira-se apenas à "mudança de atitude do causador", "ponto de inflexão" ou "resposta comportamental imediata".
3. FOCO MICROANALÍTICO: Analise APENAS as interações desta ocorrência. Não faça generalizações doutrinárias amplas.
4. OUTPUT OBRIGATÓRIO: Retorne um arquivo JSON estruturado. A chave "parecer" conterá a análise redigida em Markdown.

--- ESTRUTURA MANDATÓRIA DA CHAVE 'PARECER' (FORMATO MARKDOWN) ---
A sua análise na chave 'parecer' deve OBRIGATORIAMENTE conter os seguintes títulos:

### Diagnóstico Emocional e Lexical do Causador
[Descreva o estado de crise e as respostas verbais específicas observadas neste áudio/texto]

### Avaliação Técnica da Doutrina Aplicada
[Aponte quais técnicas de negociação específicas (ex: contenção verbal, escuta ativa, barganha) foram identificadas nas falas do policial durante este evento]

### Pontos Fortes e Oportunidades de Otimização Tática
[Aponte ganhos ou falhas operacionais concretas percebidas nas interações desta ocorrência. Não cite recomendações genéricas de manual]

--- EXEMPLO DE COMPORTAMENTO ESPERADO (FEW-SHOT) ---

INPUT:
"Causador recusa se render. Policial tenta acalmar."

OUTPUT JSON:
{
  "parecer": "### Diagnóstico Emocional e Lexical do Causador\nO indivíduo demonstrou alta reatividade inicial e recusa à contenção verbal, não havendo mudança de atitude imediata em resposta à aproximação primária.\n\n### Avaliação Técnica da Doutrina Aplicada\nA equipe utilizou aproximação progressiva e contenção verbal inicial, sem evidências de aplicação de escuta ativa estruturada nesta amostra.\n\n### Pontos Fortes e Oportunidades de Otimização Tática\nForça: Manutenção da calma e tom de voz equilibrado pelo negociador primário.\nOtimização: O contato primário careceu do uso de reflexão de sentimento para tentar reduzir a reatividade do causador."
}
"""
    
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
                f"Existe uma correlação {forca} e {direcao} (Rho = {rho:.2f}) entre o tempo de negociação e a percepção de agressividade. "
                "Conclui-se que as intervenções tiveram impacto direto e quantificável no cenário."
            )
        else:
            laudo.append(
                f"A análise de Spearman NÃO identificou significância estatística (p = {p_val:.3f}, o que é > 0.05). "
                f"O coeficiente Rho de {rho:.2f} sugere que a variação emocional não possui aderência matemática forte ao tempo gasto, "
                "indicando forte interferência de outras variáveis não isoladas no momento."
            )
            
    return "\n\n".join(laudo)