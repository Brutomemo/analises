import requests
import json
import re

# =========================================================
# 1. COMUNICAÇÃO COM O N8N E LIMPEZA DE JSON
# =========================================================

def enviar_para_n8n(dados_extraidos, url_n8n):
    """
    Envia os dados crus da APA para o webhook do n8n.
    Adiciona timeout para evitar que o Streamlit trave infinitamente.
    """
    try:
        # Envia apenas o texto necessário para a IA não se perder
        payload = {
            "transcricao_completa": dados_extraidos["transcricao"].to_dict(orient="records"),
            "metadados": dados_extraidos["metadados"].to_dict(orient="records")[0]
        }
        
        response = requests.post(url_n8n, json=payload, timeout=90) # 90s de limite
        
        if response.status_code == 200:
            return limpar_e_carregar_json(response.text)
        else:
            return {"erro": f"Servidor retornou erro: {response.status_code}", "bruto": response.text}
            
    except requests.exceptions.Timeout:
        return {"erro": "O n8n demorou muito para responder (Timeout)."}
    except requests.exceptions.RequestException as e:
        return {"erro": f"Falha de conexão com o n8n: {e}"}

def limpar_e_carregar_json(texto_sujo):
    """
    O 'Triturador de Alucinações'. Remove crases, markdown e 
    garante que o Python receba um dicionário limpo.
    """
    if not texto_sujo or not texto_sujo.strip():
        return {"erro": "O n8n retornou uma resposta vazia."}
        
    texto = texto_sujo.strip()
    
    # 1. Limpa blocos de código Markdown
    texto = re.sub(r'^```json\s*', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'^```\s*', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'```$', '', texto, flags=re.MULTILINE)
    
    try:
        # 2. Tenta o parse direto
        dados = json.loads(texto.strip())
        
        # 3. Desempacotamento de segurança (Se a IA mandar string dentro de array ou objeto)
        if isinstance(dados, list) and len(dados) > 0:
            dados = dados[0]
        if isinstance(dados, str):
            dados = json.loads(dados)
            
        return dados
    except json.JSONDecodeError as e:
        return {"erro": "A IA gerou um JSON inválido que não pôde ser reparado.", "bruto": texto}


# =========================================================
# 2. MOTOR DE INFERÊNCIA ESTATÍSTICA (SEM VIÉS DA IA)
# =========================================================

def gerar_laudo_frio(likert_inicio, likert_fim, stats_spearman):
    """
    Escreve o parecer tático puramente baseado nos números.
    Se a agressividade não caiu, ele vai dizer de forma direta.
    """
    laudo = []
    
    # Cálculos dos Deltas (Variação entre o final e o início)
    delta_r = likert_fim.get('receptividade_media', 0) - likert_inicio.get('receptividade_media', 0)
    delta_a = likert_fim.get('agressividade_media', 0) - likert_inicio.get('agressividade_media', 0)
    
    # 1. Análise de Receptividade (Fato Frio)
    if delta_r > 0:
        laudo.append(f"A receptividade média do causador apresentou aumento durante a ocorrência ($\Delta = +{delta_r:.1f}$).")
    elif delta_r < 0:
        laudo.append(f"A receptividade média do causador sofreu redução durante a ocorrência ($\Delta = {delta_r:.1f}$).")
    else:
        laudo.append("A receptividade média do causador permaneceu inalterada/estagnada ao longo da ocorrência.")

    # 2. Análise de Agressividade (Fato Frio)
    if delta_a < 0:
        laudo.append(f"Observou-se mitigação na agressividade média ($\Delta = {delta_a:.1f}$).")
    elif delta_a > 0:
        laudo.append(f"Houve escalada na agressividade média ($\Delta = +{delta_a:.1f}$).")
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
                f"A análise de Spearman confirma validade estatística ($p < 0.05$). "
                f"Existe uma correlação {forca} e {direcao} ($Rho = {rho:.2f}$) entre o emprego das técnicas e o progresso da ocorrência. "
                "Conclui-se que as intervenções tiveram impacto direto e quantificável no desfecho."
            )
        else:
            laudo.append(
                f"A análise de Spearman NÃO identificou significância estatística ($p = {p_val:.3f}$, o que é $> 0.05$). "
                f"O coeficiente de $Rho$ de {rho:.2f} sugere que qualquer variação observada pode ter ocorrido ao acaso (fator sorte) "
                "ou que o desfecho dependeu de fatores táticos além da negociação verbal isolada."
            )
            
    return "\n\n".join(laudo)