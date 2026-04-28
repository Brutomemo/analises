import json
import requests
import streamlit as st


OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"

CHAVES_OBRIGATORIAS = [
    "objetivo",
    "metodo",
    "premissas",
    "resultados_principais",
    "interpretacao",
    "categorias_destaque",
    "tamanho_efeito",
    "limitacoes",
    "conclusao",
]


def estruturar_resultado_para_ia(amostra_total, resultados_chi, resultados_ordinal, resultados_gee):
    """
    Recebe os resultados matemáticos do Python e estrutura em um dict padronizado.
    """
    payload = {
        "metadados_analise": {
            "objetivo": (
                "Investigar a associação entre técnicas de negociação e a mudança de atitude do causador "
                "frente à intervenção, avaliando simultaneamente a existência de viés na percepção dos "
                "negociadores, com controle estatístico para variáveis de contexto (cenário) e efeitos "
                "agrupados por avaliador."
            ),
            "pergunta_principal": (
                "Os padrões observados estão associados às técnicas empregadas ou podem estar influenciados "
                "por percepção do negociador e características do contexto operacional?"
            ),
            "hipotese_analitica": (
                "Parte da variação observada pode estar associada às técnicas aplicadas, mas também pode "
                "refletir fatores de contexto e possíveis vieses de percepção."
            ),
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


def _preencher_chaves_faltantes(resposta_ia):
    """
    Garante padronização da resposta final da IA sem alterar a funcionalidade central.
    Todos os campos obrigatórios devem existir e conter texto.
    """
    fallback = {
        "objetivo": "Resumo técnico não pôde ser estruturado integralmente a partir da resposta da IA.",
        "metodo": "Descrição metodológica não informada de forma adequada pela IA.",
        "premissas": "Premissas e limitações não foram informadas adequadamente pela IA.",
        "resultados_principais": "Os resultados principais não puderam ser consolidados de forma padronizada.",
        "interpretacao": "Não foi possível consolidar interpretação técnica padronizada a partir da resposta da IA.",
        "categorias_destaque": "Não há evidência estatística suficiente para destacar categorias de forma robusta.",
        "tamanho_efeito": "Não foram informadas medidas de efeito interpretáveis ou relevantes.",
        "limitacoes": "As limitações analíticas não foram descritas de forma adequada pela IA.",
        "conclusao": "Conclusão técnica não pôde ser consolidada adequadamente a partir da resposta da IA."
    }

    if not isinstance(resposta_ia, dict):
        return {k: fallback[k] for k in CHAVES_OBRIGATORIAS}

    resposta_padronizada = {}
    for chave in CHAVES_OBRIGATORIAS:
        valor = resposta_ia.get(chave, fallback[chave])
        if valor is None:
            valor = fallback[chave]
        if not isinstance(valor, str):
            valor = str(valor)
        resposta_padronizada[chave] = valor.strip() if valor.strip() else fallback[chave]

    return resposta_padronizada


def montar_prompt_estatistico(payload_json):
    """
    Monta o prompt de sistema rígido para a IA atuar como Estatístico Sênior.
    """
    system_prompt = """
Você é um Analista Estatístico Sênior e Especialista em Estatística Aplicada à Segurança Pública.
Sua tarefa é interpretar resultados estatísticos de técnicas de negociação policial.

PRINCÍPIO MÁXIMO:
Esta tarefa opera em CONTEXTO FECHADO. Trabalhe EXCLUSIVAMENTE com os dados presentes no payload.
Não utilize conhecimento externo, doutrina operacional externa, exemplos genéricos, intuição estatística não sustentada pelo payload, nem complete lacunas com inferências livres.

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

2. Trabalhe EXCLUSIVAMENTE com os dados fornecidos no payload. Não invente técnicas, categorias, métricas, coeficientes, cenários, magnitudes ou contextos.

3. Diferencie claramente:
   - viés de percepção (relatado principalmente no Qui-Quadrado e análises descritivas);
   - associação ajustada / eficácia controlada (relatada apenas em modelos ajustados, como Regressão Ordinal e GEE).

4. Explicite limitações quando houver:
   - amostra pequena;
   - amostra crítica;
   - ausência de significância estatística;
   - impossibilidade de avaliar viés do negociador;
   - separação perfeita;
   - falha de convergência;
   - ausência de coeficientes interpretáveis;
   - ausência de medidas de efeito interpretáveis.

5. Ausência de significância estatística NÃO deve ser tratada como prova de ausência de efeito. Use formulações como:
   - 'não foram identificadas evidências estatisticamente significativas'
   - 'os dados não sustentam conclusão robusta'
   - 'a análise é inconclusiva sob as condições observadas'

6. Mesmo quando houver significância estatística, NÃO trate isso como validação definitiva de eficácia operacional, doutrinária ou institucional.

7. Regra de vocabulário: ao redigir o campo 'objetivo', NUNCA utilize a palavra 'desfecho'. No contexto de gerenciamento de crises, prefira obrigatoriamente:
   - 'mudança de atitude do causador'
   - 'resposta comportamental imediata frente à técnica aplicada'

8. O campo 'categorias_destaque' não deve inventar achados.
   - Se houver evidência estatisticamente relevante, descreva objetivamente quais técnicas, categorias ou coeficientes se destacaram.
   - Se não houver evidência suficiente, declare isso explicitamente.

9. O campo 'tamanho_efeito' deve interpretar apenas medidas realmente presentes no payload, como Odds Ratios, coeficientes GEE ou outras medidas de efeito.
   - Se não houver medidas interpretáveis ou relevantes, informe isso explicitamente.

10. SIGNIFICÂNCIA ESTATÍSTICA NÃO É SINÔNIMO DE RELEVÂNCIA OPERACIONAL.
    - Não transforme p < 0.05 em recomendação prática automática.
    - Não transforme coeficiente interpretável em superioridade operacional automática.

11. Se o payload indicar dados insuficientes, amostra crítica, falha de convergência, separação perfeita ou ausência de coeficientes interpretáveis, a conclusão deve ser explicitamente prudente e pode ser classificada como inconclusiva sob as condições observadas.

12. Não repita o mesmo conteúdo em campos diferentes. Cada campo deve cumprir sua função:
   - 'metodo' = quais métodos foram aplicados e para quê;
   - 'premissas' = condições e fragilidades analíticas;
   - 'resultados_principais' = achados diretamente sustentados;
   - 'interpretacao' = leitura prática prudente;
   - 'limitacoes' = restrições técnicas;
   - 'conclusao' = síntese final compatível com o nível de evidência.

13. Todos os valores do JSON devem ser TEXTO, mas tecnicamente objetivos, sem floreio e sem generalizações.

PADRONIZAÇÃO OBRIGATÓRIA DE ESTRUTURA:
- Responda SEMPRE com as mesmas chaves.
- Não omita chaves.
- Não renomeie chaves.
- Não crie chaves extras.
- Não use markdown.
- Não use crases.
- Não escreva comentários.
- Nenhuma palavra fora do JSON.

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
}

VALIDAÇÃO INTERNA ANTES DE RESPONDER:
- Verifique se todas as chaves estão presentes.
- Verifique se todos os valores são texto.
- Verifique se nenhuma afirmação excede o que está explicitamente presente no payload.
- Se houver dúvida entre interpretar um achado como robusto ou tratá-lo como inconclusivo, prefira a formulação mais prudente.
""".strip()

    user_prompt = (
        "Aqui estão os resultados matemáticos processados pelo Python. "
        "Interprete apenas o que estiver explicitamente presente no payload a seguir:\n"
        f"{json.dumps(payload_json, ensure_ascii=False, indent=2)}"
    )

    return system_prompt, user_prompt


def gerar_relatorio_com_ia(payload):
    """
    Chama a API da OpenAI de forma autônoma e segura.
    """
    system, user = montar_prompt_estatistico(payload)

    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        return {"erro": "Configuração de chave ausente no Streamlit Cloud."}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(OPENAI_ENDPOINT, headers=headers, json=data, timeout=60)
        response.raise_for_status()

        raw_json = response.json()["choices"][0]["message"]["content"]
        resposta_ia = json.loads(raw_json)

        return _preencher_chaves_faltantes(resposta_ia)

    except json.JSONDecodeError:
        return {"erro": "A IA não retornou um formato JSON válido."}
    except requests.exceptions.HTTPError as err:
        return {"erro": f"Erro de comunicação com a OpenAI (Verifique sua chave): {err.response.text}"}
    except Exception as e:
        return {"erro": f"Falha na execução da IA: {str(e)}"}
    
    ##INCLUSAO DE MOTOR ESTATISTICO PARA ANALISE VIA CHAT

def _normalizar_nome_coluna(texto):
    texto = str(texto)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.lower().strip()

def _achar_coluna(df, candidatos):
    if df is None or df.empty:
        return None

    mapa = {_normalizar_nome_coluna(col): col for col in df.columns}

    for candidato in candidatos:
        chave = _normalizar_nome_coluna(candidato)
        if chave in mapa:
            return mapa[chave]

    for col_norm, col_real in mapa.items():
        for candidato in candidatos:
            if _normalizar_nome_coluna(candidato) in col_norm:
                return col_real

    return None

def _tempo_para_minutos(valor):
    try:
        if isinstance(valor, list):
            valor = valor[0] if valor else None
        if pd.isna(valor) or valor in ["", "N/D", None]:
            return np.nan
        return float(valor) / 60.0
    except Exception:
        return np.nan

def sumarizar_banco_para_ia(df_quali, df_tec=None):
    """
    Resume a base filtrada para uso no chat com IA.
    Retorna apenas fatos agregados, evitando enviar a base bruta.
    """

    if df_quali is None or df_quali.empty:
        return {
            "n_total_ocorrencias": 0,
            "resolucoes": {},
            "tipologias": {},
            "modalidades": {},
            "negociadores": {},
            "tempo_medio_min": None,
            "top_tecnicas": {},
            "observacao": "Base vazia para os filtros atuais."
        }

    resumo = {
        "n_total_ocorrencias": int(len(df_quali)),
        "resolucoes": {},
        "tipologias": {},
        "modalidades": {},
        "negociadores": {},
        "tempo_medio_min": None,
        "top_tecnicas": {},
        "observacao": "Resumo gerado com sucesso."
    }

    col_resolucao = _achar_coluna(df_quali, ["Resolução", "RESOLUCAO"])
    col_tipologia = _achar_coluna(df_quali, ["Tipologia"])
    col_modalidade = _achar_coluna(df_quali, ["Modalidade do incidente", "Modalidade"])
    col_negociador = _achar_coluna(df_quali, ["Negociador Principal", "Negociador principal"])
    col_tempo = _achar_coluna(df_quali, ["Tempo de Negociação Real", "Tempo Total"])

    if col_resolucao:
        resumo["resolucoes"] = df_quali[col_resolucao].fillna("N/D").astype(str).value_counts().head(10).to_dict()

    if col_tipologia:
        resumo["tipologias"] = df_quali[col_tipologia].fillna("N/D").astype(str).value_counts().head(10).to_dict()

    if col_modalidade:
        resumo["modalidades"] = df_quali[col_modalidade].fillna("N/D").astype(str).value_counts().head(10).to_dict()

    if col_negociador:
        resumo["negociadores"] = df_quali[col_negociador].fillna("N/D").astype(str).value_counts().head(10).to_dict()

    if col_tempo:
        tempos = df_quali[col_tempo].apply(_tempo_para_minutos).dropna()
        if not tempos.empty:
            resumo["tempo_medio_min"] = round(float(tempos.mean()), 2)

# ==========================================
# ALTERAÇÃO PARA CRIAR MEMORIA NA BUSCA DE DADOS 
# ==========================================

    if df_tec is not None and not df_tec.empty:
        col_tecnica = _achar_coluna(df_tec, ["TÉCNICAS", "TECNICAS", "TÉCNICA", "TECNICA"])
        if col_tecnica:
            resumo["top_tecnicas"] = (
                df_tec[col_tecnica]
                .dropna()
                .astype(str)
                .str.strip()
                .replace("", np.nan)
                .dropna()
                .value_counts()
                .head(10)
                .to_dict()
            )

    # ÂNCORA 3: Salva as estatísticas globais para o Agente DELTA consumir na Aba 3
    st.session_state["stats_calculados"] = resumo

    return resumo