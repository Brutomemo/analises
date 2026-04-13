import streamlit as st
import requests
import json
from typing import Any, Dict, List

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
    "Choque de Realidade"
]

def _get_api_key() -> str:
    if "OPENAI_API_KEY" in st.secrets:
        return st.secrets["OPENAI_API_KEY"]
    raise RuntimeError("Chave da OpenAI não configurada nos Secrets.")

def _safe_json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)

def _extrair_nome_negociador(dados_extraidos: Dict[str, Any]) -> str:
    try:
        metadados = dados_extraidos["metadados"]
        if hasattr(metadados, "iloc"):
            valor = metadados.get("Negociador Principal", None)
            if valor is not None:
                return str(valor.iloc[0]).strip()
        elif isinstance(metadados, dict):
            return str(metadados.get("Negociador Principal", "da equipe")).strip()
    except Exception:
        pass
    return "da equipe"

def _serializar_dados_ocorrencia(dados_extraidos: Dict[str, Any]) -> Dict[str, Any]:
    try:
        transcricao = dados_extraidos.get("transcricao")
        metadados = dados_extraidos.get("metadados")

        if hasattr(transcricao, "to_dict"):
            transcricao = transcricao.to_dict(orient="records")
        if hasattr(metadados, "to_dict"):
            metadados = metadados.to_dict(orient="records")

        return {
            "metadados": metadados,
            "transcricao": transcricao
        }
    except Exception:
        return dados_extraidos

def analisar_ocorrencia_gate_refinado(
    dados_extraidos: Dict[str, Any],
    estatisticas_ocorrencia: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """
    Extração estruturada + parecer final com bloqueio de alucinação.
    """

    try:
        api_key = _get_api_key()
    except Exception as e:
        return {"erro": str(e), "parecer": "Erro de configuração da chave de API."}

    nome_negociador = _extrair_nome_negociador(dados_extraidos)
    dados_serializados = _serializar_dados_ocorrencia(dados_extraidos)

    if estatisticas_ocorrencia is None:
        estatisticas_ocorrencia = {}

    developer_prompt = f"""
Você é um auditor técnico de negociação policial.

Sua tarefa é analisar UMA única ocorrência com base EXCLUSIVA em:
1. metadados fornecidos;
2. transcrição fornecida;
3. estatísticas fornecidas pelo sistema.

Regras obrigatórias:
- Não invente técnicas.
- Não use sinônimos fora da lista oficial.
- Só identifique uma técnica se houver evidência textual suficiente na transcrição.
- É proibido inferir técnica com base em intenção presumida, contexto genérico, tom presumido, experiência esperada do policial ou doutrina abstrata.
- Se a evidência for insuficiente, não classifique a técnica.
- Cada técnica identificada deve ter pelo menos 1 trecho literal da transcrição.
- Se não houver base suficiente para concluir, declare insuficiência de evidência.
- Não confunda “Negociador Principal” com comandante/líder da equipe.
- Não use a palavra “desfecho”. Use “mudança de atitude do causador”, “ponto de inflexão” ou “resposta comportamental imediata”.

Lista oficial e exclusiva de técnicas:
{_safe_json_dumps(TECNICAS_VALIDAS)}

Regras para o parecer:
- O parecer deve refletir apenas o que está nos dados.
- Quando houver estatística da ocorrência, você DEVE citá-la de forma objetiva.
- Não atribua causalidade forte se os próprios números não sustentarem isso.
- Não diga que uma técnica “funcionou” sem evidência textual e/ou numérica mínima.
- Se a frequência das técnicas não estiver disponível ou for precoce/incompleta, diga isso explicitamente.

A seção “Avaliação Técnica da Doutrina Aplicada” deve começar EXATAMENTE com:
"A verbalização com o causador, conduzida pelo Negociador Principal {nome_negociador}, caracterizou-se por..."

Retorne APENAS JSON válido.
"""

    user_payload = {
        "ocorrencia": dados_serializados,
        "estatisticas_ocorrencia": estatisticas_ocorrencia,
        "instrucao_final": (
            "Extraia apenas técnicas com evidência literal. "
            "Depois redija o parecer em markdown usando exclusivamente os dados fornecidos."
        )
    }

    json_schema = {
        "name": "analise_ocorrencia_gate",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "diagnostico_baseado_em_texto": {
                    "type": "string"
                },
                "tecnicas_identificadas": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "tecnica": {
                                "type": "string",
                                "enum": TECNICAS_VALIDAS
                            },
                            "justificativa": {
                                "type": "string"
                            },
                            "confianca": {
                                "type": "number"
                            },
                            "evidencias": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "trecho": {"type": "string"},
                                        "falante": {"type": "string"}
                                    },
                                    "required": ["trecho", "falante"]
                                }
                            }
                        },
                        "required": ["tecnica", "justificativa", "confianca", "evidencias"]
                    }
                },
                "tecnicas_nao_confirmadas_por_falta_de_evidencia": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": TECNICAS_VALIDAS
                    }
                },
                "alertas_metodologicos": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "uso_dos_resultados_estatisticos": {
                    "type": "string"
                },
                "parecer": {
                    "type": "string"
                }
            },
            "required": [
                "diagnostico_baseado_em_texto",
                "tecnicas_identificadas",
                "tecnicas_nao_confirmadas_por_falta_de_evidencia",
                "alertas_metodologicos",
                "uso_dos_resultados_estatisticos",
                "parecer"
            ]
        },
        "strict": True
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "messages": [
            {"role": "developer", "content": developer_prompt},
            {"role": "user", "content": _safe_json_dumps(user_payload)}
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": json_schema
        }
    }

    try:
        response = requests.post(OPENAI_ENDPOINT, headers=headers, json=data, timeout=90)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        resultado = json.loads(content)

        # Validação defensiva adicional no Python
        tecnicas_filtradas = []
        for item in resultado.get("tecnicas_identificadas", []):
            tecnica = item.get("tecnica")
            evidencias = item.get("evidencias", [])
            if tecnica in TECNICAS_VALIDAS and evidencias:
                tecnicas_filtradas.append(item)

        resultado["tecnicas_identificadas"] = tecnicas_filtradas

        return resultado

    except requests.exceptions.HTTPError as err:
        detalhe = ""
        try:
            detalhe = err.response.text
        except Exception:
            detalhe = str(err)
        return {
            "erro": "http_error",
            "parecer": f"Erro de comunicação com a OpenAI: {detalhe}"
        }
    except json.JSONDecodeError:
        return {
            "erro": "json_decode_error",
            "parecer": "A IA retornou conteúdo fora do JSON esperado."
        }
    except Exception as e:
        return {
            "erro": "runtime_error",
            "parecer": f"Falha na execução da IA: {str(e)}"
        }