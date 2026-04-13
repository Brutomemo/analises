import json
import requests
import streamlit as st


OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"


def _obter_api_key():
    if "OPENAI_API_KEY" in st.secrets:
        return st.secrets["OPENAI_API_KEY"]
    raise RuntimeError("Chave da OpenAI não configurada nos Secrets do Streamlit.")


def _safe_json_dumps(data):
    return json.dumps(data, ensure_ascii=False, default=str)


def _extrair_nome_negociador(dados_extraidos):
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


def analisar_ocorrencia_gate(
    dados_extraidos,
    estatisticas_ocorrencia=None,
    tecnicas_ocorrencia=None
):
    """
    Analisa a ocorrência limitando-se EXCLUSIVAMENTE às técnicas já registradas
    na tabela de frequências da APA atual.
    """

    try:
        api_key = _obter_api_key()
    except Exception as e:
        return {"parecer": f"Erro: {str(e)}"}

    try:
        nome_negociador = _extrair_nome_negociador(dados_extraidos)
        dados_serializados = _serializar_dados_ocorrencia(dados_extraidos)

        if estatisticas_ocorrencia is None:
            estatisticas_ocorrencia = {}

        if tecnicas_ocorrencia is None:
            tecnicas_ocorrencia = []

        # normaliza e remove duplicatas preservando ordem
        tecnicas_ocorrencia = [
            str(t).strip() for t in tecnicas_ocorrencia
            if str(t).strip()
        ]
        tecnicas_ocorrencia = list(dict.fromkeys(tecnicas_ocorrencia))

        if not tecnicas_ocorrencia:
            return {
                "parecer": (
                    "### Diagnóstico Emocional e Lexical do Causador\n"
                    "Não foi possível elaborar análise técnica confiável, pois a ocorrência não apresentou técnicas registradas na tabela de frequências.\n\n"
                    "### Avaliação Técnica da Doutrina Aplicada\n"
                    f"A verbalização com o causador, conduzida pelo Negociador Principal {nome_negociador}, caracterizou-se por material insuficiente para correlação técnica, "
                    "uma vez que a lista de técnicas efetivamente registradas nesta ocorrência não foi fornecida ao motor analítico.\n\n"
                    "### Pontos Fortes e Oportunidades de Otimização Tática\n"
                    "Sem a lista de técnicas efetivamente registradas nesta APA, a análise ficaria sujeita a inferência indevida. Por rigor metodológico, o parecer foi interrompido nesse ponto."
                )
            }

        developer_prompt = f"""
Você é um Especialista Sênior em Negociação Policial e Comportamento Humano do GATE.

Sua missão é realizar a Análise Pós-Ação (APA) de UMA única ocorrência crítica.

REGRA MAIS IMPORTANTE DESTA TAREFA:
Você está TERMINANTEMENTE PROIBIDO de mencionar, discutir, negar, comparar, supor ou citar qualquer técnica que não esteja presente na lista de técnicas efetivamente registradas nesta ocorrência.

LISTA EXCLUSIVA DE TÉCNICAS REGISTRADAS NESTA OCORRÊNCIA:
{_safe_json_dumps(tecnicas_ocorrencia)}

REGRAS OBRIGATÓRIAS:
1. Analise EXCLUSIVAMENTE os dados desta ocorrência.
2. Mencione SOMENTE técnicas contidas na lista acima.
3. Não cite técnicas ausentes, nem mesmo para dizer que não apareceram.
4. Não use sinônimos técnicos fora dos nomes já registrados.
5. Não invente técnica, não complete lacunas e não faça preenchimento doutrinário.
6. Seu trabalho é:
   - ler a transcrição literal;
   - interpretar as técnicas já registradas na ocorrência;
   - buscar relação provável entre essas técnicas e a progressão observada;
   - relacionar isso, quando possível, com:
     a) percepção dos negociadores,
     b) análise de similitude lexical,
     c) variação observada na agressividade/receptividade.
7. Se a transcrição não permitir vincular claramente uma técnica registrada a uma fala específica, você pode dizer que a vinculação textual ficou limitada, MAS sem mencionar nenhuma técnica fora da lista registrada.
8. Não use a palavra "desfecho".
9. Não trate o Negociador Principal como comandante/líder da equipe.
10. Não faça generalizações amplas de manual.
11. Quando falar das técnicas, fale apenas das técnicas realmente registradas nesta APA.

FORMATO OBRIGATÓRIO:
Retorne APENAS JSON VÁLIDO, com uma única chave:
- "parecer"

A chave "parecer" deve conter markdown com EXATAMENTE estes títulos:

### Diagnóstico Emocional e Lexical do Causador
### Avaliação Técnica da Doutrina Aplicada
### Pontos Fortes e Oportunidades de Otimização Tática

A seção "Avaliação Técnica da Doutrina Aplicada" DEVE começar EXATAMENTE com:
"A verbalização com o causador, conduzida pelo Negociador Principal {nome_negociador}, caracterizou-se por..."

REGRAS DE ESTILO ANALÍTICO:
- Não seja genérico.
- Não seja pobre.
- Não invente.
- Não mencione técnicas ausentes.
- Use as técnicas registradas como âncora central da análise.
- Relacione as técnicas apenas com os dados realmente disponíveis.
"""

        user_payload = {
            "ocorrencia": dados_serializados,
            "estatisticas_ocorrencia": estatisticas_ocorrencia,
            "tecnicas_registradas_na_ocorrencia": tecnicas_ocorrencia
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