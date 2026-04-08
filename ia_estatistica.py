import json
from typing import Any, Dict, Optional

import requests
import streamlit as st


RELATORIO_SCHEMA = {
    "objetivo": "",
    "metodo": "",
    "premissas": "",
    "resultados_principais": "",
    "interpretacao": "",
    "categorias_destaque": "",
    "tamanho_efeito": "",
    "limitacoes": "",
    "conclusao": ""
}


def _tem_conteudo(valor: Any) -> bool:
    """
    Verifica se um objeto possui conteúdo útil.
    """
    if valor is None:
        return False
    if isinstance(valor, str):
        return valor.strip() != ""
    if isinstance(valor, (list, tuple, set, dict)):
        return len(valor) > 0
    return True


def _status_bloco(resultado: Any) -> str:
    """
    Classifica o status de um bloco de resultado estatístico.
    """
    if not _tem_conteudo(resultado):
        return "sem_resultado"
    return "ok"


def _detectar_sinais_limitacao(
    amostra_total: int,
    resultados_chi: Any,
    resultados_ordinal: Any,
    resultados_gee: Any
) -> Dict[str, Any]:
    """
    Cria metadados auxiliares para orientar a IA de forma mais controlada.
    """
    return {
        "amostra_pequena": amostra_total < 30,
        "amostra_critica": amostra_total < 5,
        "possui_resultado_chi": _tem_conteudo(resultados_chi),
        "possui_resultado_ordinal": _tem_conteudo(resultados_ordinal),
        "possui_resultado_gee": _tem_conteudo(resultados_gee),
        "regra_significancia": "Considerar evidência estatística relevante quando p < 0.05.",
        "regra_causalidade": "Associação não implica causalidade.",
        "regra_ausencia": "Ausência de significância estatística não implica ausência de efeito.",
        "regra_amostra": "Amostras pequenas reduzem o poder estatístico e a estabilidade das estimativas."
    }


def estruturar_resultado_para_ia(
    amostra_total: int,
    resultados_chi: Optional[Dict[str, Any]],
    resultados_ordinal: Optional[Dict[str, Any]],
    resultados_gee: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Estrutura os resultados matemáticos em um payload padronizado e mais informativo,
    para reduzir inferências indevidas do modelo.
    """
    sinais = _detectar_sinais_limitacao(
        amostra_total=amostra_total,
        resultados_chi=resultados_chi,
        resultados_ordinal=resultados_ordinal,
        resultados_gee=resultados_gee
    )

    payload = {
        "metadados_analise": {
            "objetivo": (
                "Investigar a associação entre técnicas de negociação e a mudança de atitude "
                "do causador frente à intervenção, avaliando simultaneamente a existência de "
                "viés na percepção dos negociadores, com controle estatístico para variáveis "
                "de contexto (cenário) e efeitos agrupados por avaliador."
            ),
            "pergunta_principal": (
                "Os resultados observados refletem associação com a técnica aplicada, "
                "ou podem estar influenciados pela percepção do negociador e pelo contexto da ocorrência?"
            ),
            "hipotese_analitica": (
                "Parte da variação observada pode estar associada tanto às técnicas empregadas "
                "quanto a fatores de contexto e possíveis vieses de percepção."
            ),
            "metodos_aplicados": [
                "Qui-Quadrado (avaliação de associação e possível viés de percepção)",
                "Regressão Logística Ordinal",
                "GEE - Equações de Estimação Generalizadas"
            ],
            "variavel_foco": "Mudança de atitude do causador / resposta comportamental imediata frente à técnica aplicada",
            "tamanho_amostra_filtrada": amostra_total,
            "diagnostico_dados": sinais
        },
        "resultados_estatisticos": {
            "qui_quadrado_vies": {
                "status": _status_bloco(resultados_chi),
                "dados": resultados_chi if _tem_conteudo(resultados_chi) else None,
                "mensagem": (
                    "Bloco disponível para interpretação."
                    if _tem_conteudo(resultados_chi)
                    else "Não há dados suficientes para interpretar o Qui-Quadrado."
                )
            },
            "regressao_ordinal": {
                "status": _status_bloco(resultados_ordinal),
                "dados": resultados_ordinal if _tem_conteudo(resultados_ordinal) else None,
                "mensagem": (
                    "Bloco disponível para interpretação."
                    if _tem_conteudo(resultados_ordinal)
                    else "Não há coeficientes disponíveis ou interpretáveis para a regressão ordinal."
                )
            },
            "multinivel_gee": {
                "status": _status_bloco(resultados_gee),
                "dados": resultados_gee if _tem_conteudo(resultados_gee) else None,
                "mensagem": (
                    "Bloco disponível para interpretação."
                    if _tem_conteudo(resultados_gee)
                    else "Não há coeficientes disponíveis ou interpretáveis para o modelo GEE."
                )
            }
        }
    }
    return payload


def montar_prompt_estatistico(payload_json: Dict[str, Any]) -> tuple[str, str]:
    """
    Monta um prompt rígido para interpretação estatística prudente.
    """
    system_prompt = """
Você é um Analista Estatístico Sênior, com atuação técnica, conservadora e rigorosa em estatística aplicada à segurança pública.

Sua tarefa é interpretar resultados estatísticos relacionados a técnicas de negociação policial, com base EXCLUSIVA nos dados numéricos fornecidos pelo Python.

REGRAS RÍGIDAS:

1. Nunca infira causalidade.
Não use expressões como:
- "a técnica causou"
- "a técnica provocou"
- "a técnica gerou"
Use apenas formulações prudentes, como:
- "está associada a"
- "apresenta relação com"
- "há indícios de associação"
- "não há evidência suficiente de associação"

2. Trabalhe exclusivamente com os dados fornecidos no payload.
- Não invente técnicas, categorias, métricas ou contextos.
- Não extrapole para além do que os números permitem.

3. Diferencie claramente:
- viés de percepção, normalmente relacionado a análises descritivas, qui-quadrado, resíduos ou avaliações subjetivas;
- eficácia controlada, relacionada a modelos ajustados, como GEE, regressão ordinal ou outras modelagens inferenciais.

4. Sempre explicite limitações quando houver:
- amostra pequena
- ausência de significância estatística
- separação perfeita
- falha de convergência
- impossibilidade de estimar coeficientes com robustez
- impossibilidade de avaliar viés do negociador

5. Ausência de significância estatística NÃO deve ser tratada como prova de ausência de efeito.
Use formulações como:
- "não foram identificadas evidências estatisticamente significativas"
- "os dados não sustentam conclusão robusta"
- "a análise é inconclusiva sob as condições observadas"

6. Mesmo quando houver significância estatística, não trate isso como validação definitiva de eficácia operacional ou doutrinária.
A interpretação deve ser prudente e técnica.

7. Regra de vocabulário para o campo "objetivo":
- Nunca use a palavra "desfecho".
- Prefira obrigatoriamente expressões como:
  "mudança de atitude do causador"
  "resposta comportamental imediata frente à técnica aplicada"

8. O campo "categorias_destaque" não deve inventar destaques.
- Se houver evidência estatisticamente relevante, descreva objetivamente quais categorias, técnicas ou coeficientes se destacaram.
- Se não houver evidência suficiente, declare isso explicitamente.

9. O campo "tamanho_efeito" deve interpretar apenas medidas realmente presentes no payload, como:
- Odds Ratios
- coeficientes
- medidas de efeito
Se não houver medidas interpretáveis ou significativas, informe isso explicitamente.

10. Sua resposta deve ser única e exclusivamente um objeto JSON válido.
- Não use markdown
- Não use crases
- Não escreva explicações antes ou depois
- Não inclua comentários
- Preencha todas as chaves obrigatoriamente
- Todos os valores devem ser texto em formato string

11. Se algum bloco de análise vier com status diferente de "ok", trate isso como limitação explícita.

12. Quando a amostra for muito pequena, destaque a fragilidade inferencial de forma clara, sem afirmar que os dados "não refletem a realidade".

O JSON deve seguir EXATAMENTE esta estrutura:
{
  "objetivo": "Resumo técnico do que foi analisado",
  "metodo": "Breve descrição das abordagens estatísticas utilizadas",
  "premissas": "Premissas, restrições e adequação da análise ao tamanho e estrutura da amostra",
  "resultados_principais": "Síntese objetiva dos principais achados numéricos",
  "interpretacao": "Interpretação prática e prudente dos resultados no contexto operacional",
  "categorias_destaque": "Categorias, técnicas ou efeitos que se destacaram, ou declaração explícita de ausência de evidência relevante",
  "tamanho_efeito": "Interpretação das medidas de efeito presentes, ou declaração de ausência de medidas interpretáveis/relevantes",
  "limitacoes": "Limitações técnicas e analíticas identificadas",
  "conclusao": "Conclusão técnica final, prudente e compatível com o nível de evidência"
}
"""

    user_prompt = f"""
Aqui estão os resultados matemáticos processados pelo Python.
Interprete apenas o que estiver explicitamente presente no payload abaixo.

PAYLOAD:
{json.dumps(payload_json, ensure_ascii=False, indent=2)}
"""
    return system_prompt, user_prompt


def _normalizar_relatorio_json(resposta: Dict[str, Any]) -> Dict[str, str]:
    """
    Garante que todas as chaves do schema existam e sejam strings.
    """
    relatorio = {}
    for chave in RELATORIO_SCHEMA:
        valor = resposta.get(chave, "")
        if valor is None:
            valor = ""
        relatorio[chave] = str(valor).strip()
    return relatorio


def _fallback_relatorio(payload: Dict[str, Any], motivo: str) -> Dict[str, str]:
    """
    Retorna um relatório mínimo e seguro caso a IA falhe.
    """
    amostra = payload.get("metadados_analise", {}).get("tamanho_amostra_filtrada", "não informado")
    return {
        "objetivo": (
            "Analisar a associação entre técnicas de negociação, mudança de atitude do causador "
            "e possível viés de percepção dos negociadores."
        ),
        "metodo": (
            "Foram considerados os resultados disponíveis de Qui-Quadrado, regressão ordinal "
            "e GEE, conforme processados previamente pelo Python."
        ),
        "premissas": (
            f"A interpretação automática não pôde ser concluída integralmente. "
            f"Tamanho amostral informado: N={amostra}."
        ),
        "resultados_principais": "Não foi possível consolidar automaticamente os resultados em formato interpretável.",
        "interpretacao": "A leitura automatizada falhou e requer revisão manual dos resultados estatísticos.",
        "categorias_destaque": "Não disponível devido à falha na etapa automatizada.",
        "tamanho_efeito": "Não disponível devido à falha na etapa automatizada.",
        "limitacoes": f"Falha na interpretação automatizada: {motivo}",
        "conclusao": "Recomenda-se revisão manual dos resultados e nova tentativa de geração do relatório."
    }


def gerar_relatorio_com_ia(payload: Dict[str, Any], model: str = "gpt-4o-mini") -> Dict[str, str]:
    """
    Chama a API da OpenAI de forma segura e devolve um relatório JSON padronizado.
    """
    system_prompt, user_prompt = montar_prompt_estatistico(payload)

    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        return _fallback_relatorio(payload, "Configuração de chave ausente no Streamlit Cloud.")

    endpoint = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(endpoint, headers=headers, json=body, timeout=90)
        response.raise_for_status()

        response_json = response.json()
        raw_content = response_json["choices"][0]["message"]["content"]
        parsed = json.loads(raw_content)

        if not isinstance(parsed, dict):
            return _fallback_relatorio(payload, "A resposta da IA não retornou um objeto JSON.")

        relatorio_normalizado = _normalizar_relatorio_json(parsed)
        return relatorio_normalizado

    except json.JSONDecodeError:
        return _fallback_relatorio(payload, "A IA não retornou JSON válido.")
    except requests.exceptions.HTTPError as err:
        detalhe = err.response.text if err.response is not None else str(err)
        return _fallback_relatorio(payload, f"Erro HTTP na OpenAI: {detalhe}")
    except requests.exceptions.Timeout:
        return _fallback_relatorio(payload, "Tempo limite excedido na requisição à OpenAI.")
    except requests.exceptions.RequestException as err:
        return _fallback_relatorio(payload, f"Erro de comunicação com a OpenAI: {str(err)}")
    except Exception as err:
        return _fallback_relatorio(payload, f"Falha inesperada: {str(err)}")


def formatar_relatorio_markdown(relatorio: Dict[str, str]) -> str:
    """
    Converte o JSON do relatório em markdown para exibição no Streamlit.
    """
    return f"""
### Objetivo
{relatorio.get("objetivo", "")}

### Método
{relatorio.get("metodo", "")}

### Premissas
{relatorio.get("premissas", "")}

### Resultados Principais
{relatorio.get("resultados_principais", "")}

### Interpretação
{relatorio.get("interpretacao", "")}

### Categorias de Destaque
{relatorio.get("categorias_destaque", "")}

### Tamanho de Efeito
{relatorio.get("tamanho_efeito", "")}

### Limitações
{relatorio.get("limitacoes", "")}

### Conclusão
{relatorio.get("conclusao", "")}
""".strip()


def exibir_relatorio_ia_streamlit(
    amostra_total: int,
    resultados_chi: Optional[Dict[str, Any]],
    resultados_ordinal: Optional[Dict[str, Any]],
    resultados_gee: Optional[Dict[str, Any]]
) -> None:
    """
    Fluxo completo para gerar e exibir o relatório no Streamlit.
    """
    st.subheader("Interpretação estatística assistida por IA")

    if st.button("Gerar relatório interpretativo", use_container_width=True):
        payload = estruturar_resultado_para_ia(
            amostra_total=amostra_total,
            resultados_chi=resultados_chi,
            resultados_ordinal=resultados_ordinal,
            resultados_gee=resultados_gee
        )

        with st.spinner("Gerando relatório técnico..."):
            relatorio = gerar_relatorio_com_ia(payload)

        if relatorio.get("limitacoes", "").lower().startswith("falha na interpretação automatizada"):
            st.warning("A interpretação automática apresentou limitação. O relatório abaixo foi preenchido com fallback seguro.")

        st.markdown(formatar_relatorio_markdown(relatorio))

        with st.expander("Ver JSON bruto do relatório"):
            st.json(relatorio)

        with st.expander("Ver payload enviado para a IA"):
            st.json(payload)