import json
import requests
import streamlit as st


# =========================================================
# CONFIGURAÇÕES FIXAS
# =========================================================
OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"

TECNICAS_VALIDAS = [
    "Escuta Ativa",
    "Paráfrase",
    "Classificação das Emoções",
    "Perguntas Abertas",
    "Resumo",
    "Introdução de Assunto",
    "Espelhamento",
    "Encorajamento Mínimo",
    "Perguntas Fechadas",
    "Elevação de Status",
    "Sucesso Anterior",
    "Medo",
    "Escassez",
    "Afeição",
    "Compromisso e Coerência",
    "Pausas Estratégicas",
    "Silêncio",
    "Tranquilização",
    "Primazia por Terceiros",
    "Desconstrução",
    "Reciprocidade",
    "Aprovação social",
    "Rejeição Seguida Recuo",
    "Escolha Condicionada",
    "Despertar da curiosidade",
    "Inquietação",
    "Distração",
    "Bom e Mal",
    "Reforço Positivo",
    "Metáfora como Reconexão",
    "Exploração da Ambivalência",
    "Orientação Psíquica",
    "Choque de Realidade",
]


# =========================================================
# FUNÇÕES AUXILIARES INTERNAS
# =========================================================
def _obter_api_key():
    if "OPENAI_API_KEY" in st.secrets:
        return st.secrets["OPENAI_API_KEY"]
    raise RuntimeError("Chave da OpenAI não configurada nos Secrets do Streamlit.")


def _safe_json_dumps(data):
    return json.dumps(data, ensure_ascii=False, default=str)


def _extrair_nome_negociador(dados_extraidos):
    """
    Mantém robustez para DataFrame, dict ou estrutura mista.
    """
    try:
        metadados = dados_extraidos.get("metadados")

        if hasattr(metadados, "iloc"):
            if "Negociador Principal" in metadados.columns and len(metadados) > 0:
                return str(metadados["Negociador Principal"].iloc[0]).strip()

        if isinstance(metadados, dict):
            return str(metadados.get("Negociador Principal", "da equipe")).strip()

        if isinstance(metadados, list) and len(metadados) > 0 and isinstance(metadados[0], dict):
            return str(metadados[0].get("Negociador Principal", "da equipe")).strip()

    except Exception:
        pass

    return "da equipe"


def _serializar_dados_ocorrencia(dados_extraidos):
    """
    Converte DataFrames em estruturas JSON serializáveis, sem quebrar o app.
    """
    try:
        transcricao = dados_extraidos.get("transcricao")
        metadados = dados_extraidos.get("metadados")

        if hasattr(transcricao, "to_dict"):
            transcricao = transcricao.to_dict(orient="records")

        if hasattr(metadados, "to_dict"):
            metadados = metadados.to_dict(orient="records")

        return {
            "transcricao": transcricao,
            "metadados": metadados,
        }
    except Exception:
        return dados_extraidos


def _montar_estatisticas_minimas(dados_extraidos, estatisticas_ocorrencia=None):
    """
    Garante compatibilidade total:
    - se o app não mandar estatísticas, cria um bloco mínimo;
    - se mandar, preserva.
    """
    if estatisticas_ocorrencia is None:
        estatisticas_ocorrencia = {}

    estatisticas_ocorrencia.setdefault("frequencia_tecnicas_ocorrencia", {})
    estatisticas_ocorrencia.setdefault("observacao_estatistica", "Nenhuma estatística adicional foi enviada pelo sistema.")
    return estatisticas_ocorrencia


# =========================================================
# FUNÇÃO PRINCIPAL CHAMADA PELO APP
# NOME MANTIDO: analisar_ocorrencia_gate
# =========================================================
def analisar_ocorrencia_gate(dados_extraidos, estatisticas_ocorrencia=None):
    """
    Analisa uma ocorrência específica com foco em:
    - reduzir alucinação de técnicas;
    - exigir aderência à lista fechada;
    - produzir saída compatível com o app existente.
    """

    try:
        api_key = _obter_api_key()
    except Exception as e:
        return {"parecer": f"Erro: {str(e)}"}

    try:
        nome_negociador = _extrair_nome_negociador(dados_extraidos)
        dados_serializados = _serializar_dados_ocorrencia(dados_extraidos)
        estatisticas_ocorrencia = _montar_estatisticas_minimas(dados_extraidos, estatisticas_ocorrencia)

        developer_prompt = f"""
Você é um Especialista Sênior em Negociação Policial e Comportamento Humano do GATE (Grupo de Ações Táticas Especiais).

Sua missão é realizar a Análise Pós-Ação (APA) de UM ÚNICO incidente crítico.

REGRAS ABSOLUTAS:
1. Analise EXCLUSIVAMENTE os dados fornecidos nesta ocorrência.
2. NÃO invente técnicas.
3. Ao identificar técnicas, você DEVE escolher EXCLUSIVAMENTE entre estas opções:
{_safe_json_dumps(TECNICAS_VALIDAS)}

4. É PROIBIDO usar sinônimos fora da lista.
5. Só identifique uma técnica se houver evidência textual suficiente nas transcrições.
6. Se não houver evidência suficiente, declare insuficiência de evidência.
7. Não trate o Negociador Principal como comandante/líder da equipe.
8. Não use a palavra "desfecho". Prefira:
   - "mudança de atitude do causador"
   - "ponto de inflexão"
   - "resposta comportamental imediata"
9. Não afirme eficácia de técnica sem base textual ou numérica mínima.
10. Quando a frequência das técnicas estiver ausente, incompleta ou precoce, diga isso explicitamente.

FORMATO OBRIGATÓRIO:
Retorne APENAS JSON VÁLIDO com a chave:
- "parecer"

A chave "parecer" deve conter markdown com EXATAMENTE estas seções:

### Diagnóstico Emocional e Lexical do Causador
### Avaliação Técnica da Doutrina Aplicada
### Pontos Fortes e Oportunidades de Otimização Tática

A seção "Avaliação Técnica da Doutrina Aplicada" DEVE começar EXATAMENTE com:
"A verbalização com o causador, conduzida pelo Negociador Principal {nome_negociador}, caracterizou-se por..."

ORIENTAÇÃO CRÍTICA:
- Não preencha lacunas com suposição.
- Se a amostra textual for pobre, curta, incompleta ou unilateral, diga isso claramente.
- Se nenhuma técnica puder ser confirmada com segurança, diga isso claramente.
"""

        user_payload = {
            "ocorrencia": dados_serializados,
            "estatisticas_ocorrencia": estatisticas_ocorrencia,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        data = {
            "model": "gpt-4o-mini",
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "developer", "content": developer_prompt},
                {"role": "user", "content": _safe_json_dumps(user_payload)},
            ],
        }

        response = requests.post(OPENAI_ENDPOINT, headers=headers, json=data, timeout=90)
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        resultado = json.loads(content)

        if not isinstance(resultado, dict):
            return {"parecer": "Erro: a IA retornou um formato inválido."}

        if "parecer" not in resultado:
            return {"parecer": "Erro: a IA não retornou a chave obrigatória 'parecer'."}

        if not isinstance(resultado["parecer"], str):
            resultado["parecer"] = str(resultado["parecer"])

        return resultado

    except requests.exceptions.HTTPError as err:
        detalhe = ""
        try:
            detalhe = err.response.text
        except Exception:
            detalhe = str(err)
        return {"parecer": f"Erro de comunicação com a OpenAI. Detalhe: {detalhe}"}

    except json.JSONDecodeError:
        return {"parecer": "Erro: a Inteligência Artificial falhou em estruturar o laudo analítico em JSON válido."}

    except Exception as e:
        return {"parecer": f"Falha na execução da IA: {str(e)}"}


# =========================================================
# MOTOR DE INFERÊNCIA ESTATÍSTICA
# NOME MANTIDO: gerar_laudo_frio
# =========================================================
def gerar_laudo_frio(likert_inicio, likert_fim, stats_spearman):
    """
    Escreve o parecer tático puramente baseado nos números matemáticos.
    Mantido com o mesmo nome para compatibilidade com o app.
    """
    laudo = []

    likert_inicio = likert_inicio or {}
    likert_fim = likert_fim or {}
    stats_spearman = stats_spearman or {}

    delta_r = likert_fim.get("receptividade_media", 0) - likert_inicio.get("receptividade_media", 0)
    delta_a = likert_fim.get("agressividade_media", 0) - likert_inicio.get("agressividade_media", 0)

    # 1. Análise de Receptividade
    if delta_r > 0:
        laudo.append(f"A receptividade média do causador apresentou aumento durante a ocorrência (Delta = +{delta_r:.1f}).")
    elif delta_r < 0:
        laudo.append(f"A receptividade média do causador sofreu redução durante a ocorrência (Delta = {delta_r:.1f}).")
    else:
        laudo.append("A receptividade média do causador permaneceu inalterada/estagnada ao longo da ocorrência.")

    # 2. Análise de Agressividade
    if delta_a < 0:
        laudo.append(f"Observou-se mitigação na agressividade média (Delta = {delta_a:.1f}).")
    elif delta_a > 0:
        laudo.append(f"Houve escalada na agressividade média (Delta = +{delta_a:.1f}).")
    else:
        laudo.append("A agressividade média não apresentou variação direcional.")

    # 3. Análise inferencial
    if not stats_spearman.get("valido"):
        laudo.append("Não foi possível estabelecer correlação estatística devido à insuficiência de pontos de dados nos quartis (N < 3).")
    else:
        p_val = stats_spearman.get("p_value")
        rho = stats_spearman.get("rho")

        if p_val is None or rho is None:
            laudo.append("Os parâmetros estatísticos de Spearman vieram incompletos para interpretação.")
        else:
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

    nota_metodologica = """
---
**📖 Nota Metodológica: O que é o Laudo Frio e o Delta (Δ)?**
A *Estatística Fria* avalia exclusivamente a trajetória numérica dos dados coletados, sem interpretações subjetivas.
O valor de **Delta (Δ)** representa a variação entre o estado final e o inicial:
* **Δ Positivo (+):** Indica que o comportamento (Agressividade ou Receptividade) **aumentou**.
* **Δ Negativo (-):** Indica que o comportamento **diminuiu**.
* **Δ Zero (0):** Indica estagnação ou ausência de mudança mensurável.
"""
    laudo.append(nota_metodologica)

    return "\n\n".join(laudo)