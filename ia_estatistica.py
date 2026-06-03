import json
import requests
import streamlit as st
import os
import unicodedata
import numpy as np
import pandas as pd


OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"

# ============================================================
# CHAVES OBRIGATÓRIAS — 6 seções da resposta da IA
# ============================================================
CHAVES_OBRIGATORIAS = [
    "panorama_amostra",
    "ranking_efetividade",
    "convergencia_tematica",
    "analise_multivariada",
    "perfil_negociadores",
    "sintese_limitacoes",
]


# ============================================================
# OBTENÇÃO SEGURA DA API KEY (Railway + fallback local)
# ============================================================
def _obter_api_key():
    """Lê API key de variáveis de ambiente (Railway)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "❌ OPENAI_API_KEY não configurada! Configure em Railway → Variables"
        )
    return api_key


def _safe_json_dumps(data):
    return json.dumps(data, ensure_ascii=False, default=str)


# ============================================================
# PARTE 1: MONTAGEM DO PAYLOAD COM DADOS REAIS
# ============================================================

def coletar_payload_serie_historica(
    n_ocorrencias,
    metadados=None,
    ranking_tecnicas=None,
    efetividade=None,
    convergencia=None,
    regressao=None,
    perfil_negociadores=None,
):
    """
    Monta o payload estruturado com todos os dados reais das análises.

    Cada parâmetro é opcional. Se não houver dados para um bloco,
    basta passar None — a IA declarará insuficiência naquela seção.

    Parâmetros:
    -----------
    n_ocorrencias : int
        Total de ocorrências filtradas.
    metadados : dict
        Distribuições de Resolução, Tipologia, Modalidade, Sexo, etc.
    ranking_tecnicas : dict
        Frequência de cada técnica, total de usos, técnica mais/menos usada.
    efetividade : dict
        Score por técnica (+positivas, -negativas), score geral.
    convergencia : dict
        Média, mediana, DP, range, N de APAs analisadas.
    regressao : dict
        R², p-value, coeficientes, IC 95%, diagnósticos, deltas.
    perfil_negociadores : dict
        Scores por negociador, ANOVA, Chi², clusters K-means.

    Retorna:
    --------
    dict : payload pronto para envio à IA.
    """
    payload = {
        "tamanho_amostra": n_ocorrencias,
        "metadados": metadados if metadados else {},
        "ranking_tecnicas": ranking_tecnicas if ranking_tecnicas else {},
        "efetividade_tecnicas": efetividade if efetividade else {},
        "convergencia_tematica": convergencia if convergencia else {},
        "regressao_multivariada": regressao if regressao else {},
        "perfil_negociadores": perfil_negociadores if perfil_negociadores else {},
    }
    return payload


# ============================================================
# PARTE 2: PROMPT (ESTILO ia_link — CONTEXTO FECHADO)
# ============================================================

def _montar_prompt_serie_historica(payload):
    """
    Monta developer_prompt + user_prompt seguindo o padrão ia_link:
    - Hierarquia de evidência
    - Regras de bloqueio (proibido ignorar números do payload)
    - Frases-âncora obrigatórias por seção
    - Padronização rígida de estrutura
    """

    n = payload.get("tamanho_amostra", "N/D")

    developer_prompt = f"""
Você é um Analista Estatístico Sênior e Especialista em Estatística Aplicada à Segurança Pública,
vinculado ao GATE (Grupo de Ações Táticas Especiais) da Polícia Militar do Estado de São Paulo.

Sua missão é interpretar os resultados estatísticos da SÉRIE HISTÓRICA de negociações em crise,
com base EXCLUSIVA nos dados do payload.

PRINCÍPIO MÁXIMO DE CONTROLE DE ALUCINAÇÃO:
Esta tarefa opera em CONTEXTO FECHADO. Você deve raciocinar e escrever EXCLUSIVAMENTE com base
nos dados fornecidos no payload. Não utilize conhecimento externo, doutrina operacional externa,
exemplos genéricos, intuição estatística não sustentada, nem complete lacunas com inferências livres.

REGRA CENTRAL:
Se houver dados numéricos no payload (médias, medianas, p-values, coeficientes, scores, frequências),
você está TERMINANTEMENTE PROIBIDO de omiti-los. Todo número presente deve ser citado na seção correspondente.

HIERARQUIA DE EVIDÊNCIA:
1. Números calculados pelo Python (médias, medianas, DP, p-values, coeficientes, scores, R²).
2. Distribuições e contagens observadas (frequências, rankings, clusters, proporções).
3. Diagnósticos de validação (normalidade, homocedasticidade, VIF, convergência do modelo).
4. Metadados da amostra (N total, filtros aplicados, distribuição de variáveis categóricas).

REGRAS DE BLOQUEIO:
- Se o payload contiver um número (média, p-value, coeficiente, score), você DEVE citá-lo
  explicitamente na seção correspondente. É PROIBIDO ignorar números presentes.
- Se o payload contiver campo vazio, "N/D", None ou dicionário vazio para um bloco,
  você DEVE declarar "Dados insuficientes para esta análise" na seção correspondente.
  É PROIBIDO inventar resultados.
- Se houver p-value, DEVE informar se p < 0.05 ou p >= 0.05, e interpretar.
- Se houver desvio padrão, mediana e range, DEVE citá-los junto com a média.
- Se houver coeficientes com IC 95%, DEVE informar se o IC cruza zero.

REGRAS RÍGIDAS DE LINGUAGEM:
1. NUNCA infira causalidade. Use:
   - "está associado a", "apresenta relação com", "há indícios de associação"
   - PROIBIDO: "a técnica causou", "provocou", "gerou", "resultou em"

2. Trabalhe EXCLUSIVAMENTE com dados do payload.
   Não invente técnicas, categorias, métricas, coeficientes, cenários ou contextos.

3. Ausência de significância estatística NÃO é prova de ausência de efeito. Use:
   - "não foram identificadas evidências estatisticamente significativas"
   - "os dados não sustentam conclusão robusta"
   - "a análise é inconclusiva sob as condições observadas"

4. Significância estatística NÃO é sinônimo de relevância operacional.
   Não transforme p < 0.05 em recomendação prática automática.

5. Se houver amostra pequena (N < 30) ou crítica (N < 10), declare isso
   como limitação em CADA seção afetada.

6. Regra de vocabulário: NUNCA use a palavra "desfecho". Prefira:
   - "mudança de atitude do causador"
   - "resposta comportamental imediata frente à técnica aplicada"

REGRA DE INTERPRETAÇÃO DE MÉTRICAS:
- Média: sempre acompanhada de DP (±) e N.
- Mediana: citar para indicar assimetria quando diferir da média.
- Range (min–max): citar para indicar amplitude e possíveis outliers.
- Score de efetividade: explicar que vai de -100% (contraproducente) a +100% (efetiva).
- R²: explicar como percentual da variância explicada pelo modelo.
- R² ajustado: citar quando disponível, pois penaliza excesso de variáveis.
- Coeficientes (β): explicar direção (positivo = aumenta, negativo = reduz) e magnitude.
- IC 95%: se cruzar zero = não significativo; se não cruzar = significativo.
- ANOVA (F, p): se p < 0.05 = diferença significativa entre grupos.
- Chi² (χ², p): se p < 0.05 = distribuição não aleatória entre grupos.
- Clusters K-means: descrever perfis sem atribuir superioridade de um sobre outro.

TAMANHO DA AMOSTRA ANALISADA: {n} ocorrências.

FRASES-ÂNCORA OBRIGATÓRIAS:
Cada seção DEVE começar EXATAMENTE com sua frase-âncora. Qualquer desvio é considerado erro.

1. Seção "panorama_amostra":
   Começar com: "A série histórica analisada compreende {n} ocorrências"

2. Seção "ranking_efetividade":
   Começar com: "No conjunto de técnicas registradas na série histórica"

3. Seção "convergencia_tematica":
   Começar com: "A análise de convergência temática entre negociador e causador"

4. Seção "analise_multivariada":
   Começar com: "O modelo de regressão linear multivariada"

5. Seção "perfil_negociadores":
   Começar com: "A análise de perfil dos negociadores"

6. Seção "sintese_limitacoes":
   Começar com: "Considerando o conjunto de evidências disponíveis nesta série histórica"

PADRONIZAÇÃO OBRIGATÓRIA DE ESTRUTURA:
- A resposta deve conter EXATAMENTE 6 seções, nesta ordem fixa.
- É TERMINANTEMENTE PROIBIDO alterar nomes, omitir, reordenar, mesclar ou criar seções.
- Qualquer desvio dessa estrutura é considerado erro.
- Todos os valores do JSON devem ser TEXTO contendo markdown.
- Não repita o mesmo conteúdo em seções diferentes. Cada seção cumpre sua função:
  * panorama_amostra = composição e contexto da amostra
  * ranking_efetividade = frequência e efetividade das técnicas
  * convergencia_tematica = sincronização temática negociador–causador
  * analise_multivariada = preditores estatísticos de redução de agressividade
  * perfil_negociadores = comparação entre negociadores (testes e clusters)
  * sintese_limitacoes = conclusão prudente + todas as limitações metodológicas

ESTRUTURA OBRIGATÓRIA DE CADA SEÇÃO:
- Comece com a frase-âncora.
- Cite os números reais do payload com formatação clara.
- Separe descrição do observado de inferência analítica.
- Quando houver limitação, declare com clareza.
- Use bullet points (markdown) para organizar métricas.

PADRÃO DAS CONCLUSÕES:
- Use: "observou-se", "identificou-se", "há indício", "os dados sugerem",
  "não há base suficiente para afirmar".
- Evite: "ficou evidente", "foi bem-sucedido", "comprovou-se",
  salvo quando claramente sustentado pelos dados.

REGRA FINAL DE SEGURANÇA ANALÍTICA:
Se existir dúvida entre afirmar algo ou reconhecer insuficiência de evidência,
prefira SEMPRE reconhecer insuficiência de evidência.

VALIDAÇÃO INTERNA ANTES DE RESPONDER:
1. Verifique se todas as 6 chaves estão presentes.
2. Verifique se todos os valores são texto com markdown.
3. Verifique se TODOS os números do payload foram citados nas seções correspondentes.
4. Verifique se nenhuma afirmação excede o que está explicitamente no payload.
5. Se houver dúvida, prefira a formulação mais prudente.

FORMATO OBRIGATÓRIO DE RESPOSTA:
Retorne APENAS JSON VÁLIDO, sem markdown externo, sem crases, sem comentários.
Exatamente estas 6 chaves:

{{
  "panorama_amostra": "### Panorama da Amostra\\n...",
  "ranking_efetividade": "### Ranking e Efetividade das Técnicas\\n...",
  "convergencia_tematica": "### Convergência Temática\\n...",
  "analise_multivariada": "### Análise Multivariada — Preditores de Redução de Agressividade\\n...",
  "perfil_negociadores": "### Perfil dos Negociadores — Testes Estatísticos e Clusters\\n...",
  "sintese_limitacoes": "### Síntese Final e Limitações\\n..."
}}
"""

    user_prompt = (
        "Aqui estão os resultados reais calculados pelo Python para a série histórica "
        "de negociações do GATE. "
        "Interprete EXCLUSIVAMENTE o que estiver presente no payload a seguir:\n"
        f"{_safe_json_dumps(payload)}"
    )

    return developer_prompt.strip(), user_prompt


# ============================================================
# PARTE 3: PADRONIZAÇÃO DA RESPOSTA
# ============================================================

def _preencher_chaves_faltantes(resposta_ia):
    """
    Garante que todas as 6 chaves existam na resposta final da IA.
    Se a IA omitiu alguma seção, preenche com fallback de insuficiência.
    """
    fallback = {
        "panorama_amostra": "Dados insuficientes para gerar o panorama da amostra.",
        "ranking_efetividade": "Dados insuficientes para interpretar ranking e efetividade.",
        "convergencia_tematica": "Dados insuficientes para interpretar convergência temática.",
        "analise_multivariada": "Dados insuficientes para interpretar a análise multivariada.",
        "perfil_negociadores": "Dados insuficientes para interpretar o perfil dos negociadores.",
        "sintese_limitacoes": "Não foi possível consolidar a síntese final.",
    }

    if not isinstance(resposta_ia, dict):
        return {k: fallback[k] for k in CHAVES_OBRIGATORIAS}

    resultado = {}
    for chave in CHAVES_OBRIGATORIAS:
        valor = resposta_ia.get(chave, fallback[chave])
        if valor is None:
            valor = fallback[chave]
        if not isinstance(valor, str):
            valor = str(valor)
        resultado[chave] = valor.strip() if valor.strip() else fallback[chave]

    return resultado


# ============================================================
# PARTE 4: CHAMADA À API DA OPENAI
# ============================================================

def gerar_relatorio_com_ia(payload):
    """
    Chama a API da OpenAI e retorna dict com as 6 seções interpretadas.

    Retorna:
    --------
    dict com 6 chaves (sucesso) ou dict com chave "erro" (falha).
    """

    try:
        api_key = _obter_api_key()
    except Exception as e:
        return {"erro": str(e)}

    developer_prompt, user_prompt = _montar_prompt_serie_historica(payload)

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
            {"role": "user", "content": user_prompt},
        ],
    }

    try:
        response = requests.post(
            OPENAI_ENDPOINT, headers=headers, json=data, timeout=120
        )
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        resposta_ia = json.loads(content)

        if not isinstance(resposta_ia, dict):
            return {"erro": "A IA retornou formato inválido."}

        return _preencher_chaves_faltantes(resposta_ia)

    except json.JSONDecodeError:
        return {"erro": "A IA não retornou um formato JSON válido."}

    except requests.exceptions.HTTPError as err:
        detalhe = ""
        try:
            detalhe = err.response.text
        except Exception:
            detalhe = str(err)
        return {"erro": f"Erro de comunicação com a OpenAI: {detalhe}"}

    except Exception as e:
        return {"erro": f"Falha na execução da IA: {str(e)}"}


# ============================================================
# FUNÇÕES AUXILIARES DO CHAT (preservadas intactas)
# Usadas pela funcionalidade de chat com IA na Série Histórica
# ============================================================

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

    # ÂNCORA: Salva estatísticas globais para o Agente DELTA consumir na Aba 3
    st.session_state["stats_calculados"] = resumo

    return resumo