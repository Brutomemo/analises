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


def _normalizar_lista_tecnicas(tecnicas):
    if tecnicas is None:
        return []

    tecnicas_limpa = []
    for t in tecnicas:
        t_str = str(t).strip()
        if t_str:
            tecnicas_limpa.append(t_str)

    return list(dict.fromkeys(tecnicas_limpa))


def _extrair_tecnicas_de_metadados(dados_serializados):
    """
    Fallback para não obrigar mudança no app.py.
    Tenta localizar técnicas/frequências já embutidas nos metadados, se existirem.
    """
    tecnicas = []

    try:
        metadados = dados_serializados.get("metadados", [])

        if isinstance(metadados, dict):
            metadados = [metadados]

        if isinstance(metadados, list) and metadados:
            for item in metadados:
                if not isinstance(item, dict):
                    continue

                for chave in [
                    "tecnicas_ocorrencia",
                    "tecnicas_da_apa",
                    "tecnicas_registradas_na_ocorrencia",
                ]:
                    valor = item.get(chave)
                    if isinstance(valor, list):
                        tecnicas.extend(valor)

                for chave in [
                    "frequencia_tecnicas_ocorrencia",
                    "frequencias_tecnicas",
                ]:
                    valor = item.get(chave)
                    if isinstance(valor, dict):
                        tecnicas.extend(list(valor.keys()))

    except Exception:
        pass

    return _normalizar_lista_tecnicas(tecnicas)


def analisar_ocorrencia_gate(
    dados_extraidos,
    estatisticas_ocorrencia=None,
    tecnicas_ocorrencia=None
):
    """
    Analisa a ocorrência limitando-se, preferencialmente, às técnicas já registradas
    na tabela de frequências da APA atual.

    Compatibilidade preservada:
    - funciona com chamada antiga: analisar_ocorrencia_gate(dados_extraidos)
    - funciona com chamada nova: analisar_ocorrencia_gate(dados_extraidos, estatisticas_ocorrencia, tecnicas_ocorrencia)
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
            tecnicas_ocorrencia = _extrair_tecnicas_de_metadados(dados_serializados)

        tecnicas_ocorrencia = _normalizar_lista_tecnicas(tecnicas_ocorrencia)

        if "frequencia_tecnicas_ocorrencia" not in estatisticas_ocorrencia:
            estatisticas_ocorrencia["frequencia_tecnicas_ocorrencia"] = {}

        developer_prompt = f"""
Você é um Especialista Sênior em Negociação Policial e Comportamento Humano do GATE.

Sua missão é realizar a Análise Pós-Ação (APA) de UMA única ocorrência crítica.

PRINCÍPIO MÁXIMO DE CONTROLE DE ALUCINAÇÃO:
Esta tarefa opera em CONTEXTO FECHADO. Você deve raciocinar e escrever EXCLUSIVAMENTE com base nos dados fornecidos nesta ocorrência. Não utilize conhecimento externo, doutrina geral, suposições operacionais, padrões típicos de negociação, nem complete lacunas com inferências livres.

REGRA CENTRAL:
Se houver uma lista de técnicas registradas na ocorrência, você está TERMINANTEMENTE PROIBIDO de mencionar, discutir, negar, comparar, supor ou citar qualquer técnica que não esteja presente nessa lista.

HIERARQUIA DE EVIDÊNCIA:
1. Transcrição literal da ocorrência.
2. Técnicas registradas na ocorrência (incluindo colunas como "TÉCNICAS" e estruturas de frequência associadas).
3. Estruturas de frequência (mesmo quando apresentadas como colunas com nomes diferentes, como "frequencia", "Frequência", ou similares).
4. Metadados da própria ocorrência.

REGRA CRÍTICA DE INTERPRETAÇÃO DE FREQUÊNCIA:
- A presença de uma tabela, estrutura ou campo contendo nomes de técnicas e valores numéricos associados deve ser interpretada como evidência de técnicas registradas na ocorrência.
- Mesmo que o nome da estrutura não seja explicitamente "frequencia_tecnicas_ocorrencia", você deve inferir corretamente quando há dados de frequência de técnicas.
- É proibido afirmar ausência de técnicas registradas se houver qualquer estrutura contendo nomes de técnicas e contagens associadas.

REGRA DE BLOQUEIO:
- Se houver qualquer evidência de técnicas com contagem (frequência), você deve tratar essas técnicas como base válida da análise.
- Nessa condição, é proibido declarar "ausência de técnicas registradas".

REGRAS OBRIGATÓRIAS:
1. Analise EXCLUSIVAMENTE os dados desta ocorrência.
2. Se a lista de técnicas registradas estiver disponível, mencione SOMENTE técnicas contidas nela.
3. Se a lista de técnicas registradas NÃO estiver disponível, deixe isso explícito e NÃO invente técnicas ausentes.
4. Não cite técnicas ausentes, nem mesmo para dizer que não apareceram, quando houver lista fechada.
5. Não use sinônimos técnicos fora dos nomes já registrados.
6. Não invente técnica, não complete lacunas e não faça preenchimento doutrinário.
7. Não atribua empatia, rapport, calma, sucesso, eficácia, desescalada, vínculo, cooperação, influência ou melhora tática sem base textual ou numérica observável nesta ocorrência.
8. Não atribua causalidade forte entre técnica e mudança comportamental; quando houver relação possível, descreva apenas como associação provável, indício compatível ou correlação observável.
9. Se a transcrição for limitada, incompleta, confusa, caótica ou insuficiente, declare isso explicitamente.
10. Se a transcrição não permitir vincular claramente uma técnica registrada a uma fala específica, diga que a vinculação textual ficou limitada.
11. Não use a palavra "desfecho".
12. Não trate o Negociador Principal como comandante/líder da equipe.
13. Não faça generalizações amplas de manual.
14. Não recomende técnica ausente da lista registrada.
15. Não produza elogios vagos nem críticas genéricas.
REGRAS DE INTEGRAÇÃO ANALÍTICA DOS DADOS:
16. Sempre que houver dados de frequência de técnicas, trate esses dados como evidência positiva de que as técnicas foram efetivamente registradas na ocorrência.
17. Quando houver frequência de técnicas, a análise deve priorizar:
   a) quais técnicas apareceram;
   b) quais apareceram com maior recorrência;
   c) se a distribuição das técnicas é compatível com a progressão observada da ocorrência.
18. Quando houver análise de similitude lexical, utilize-a como indicador auxiliar de aproximação comunicacional, e não como prova isolada de rapport.
19. Quando houver percepção dos negociadores sobre agressividade e receptividade, utilize esses dados como indicadores auxiliares de trajetória emocional da ocorrência.
20. Quando houver frequência + similitude + percepção, você deve integrar essas três fontes de forma cautelosa, descrevendo apenas associação provável, convergência analítica ou compatibilidade entre os achados.
21. É proibido transformar frequência de técnica em prova automática de eficácia.
22. É proibido transformar melhora de percepção em prova automática de que uma técnica causou essa melhora.
23. Quando houver melhora aparente na receptividade, redução aparente da agressividade ou aumento de similitude lexical, você pode dizer que os dados são compatíveis com efeito tático favorável, mas deve evitar afirmação causal forte.
24. Quando os dados forem mistos, contraditórios ou inconclusivos, diga isso explicitamente.
25. Em caso de dúvida entre interpretar como eficácia ou apenas compatibilidade observacional, prefira compatibilidade observacional.

BASE TEÓRICA CONTROLADA:

Modelos clássicos de negociação e persuasão (como Método Harvard de Negociação de William Ury, Manual de Persuasão do FBI, Robert Cialdini ou gatilhos mentais) podem ser utilizados APENAS como referência interpretativa secundária.

REGRAS:
- É proibido afirmar que uma técnica pertence diretamente a um modelo teórico específico.
- É proibido afirmar aplicação de metodologia (ex: "método Harvard", "técnica do FBI") sem evidência direta nos dados.
- É permitido apenas dizer que os padrões observados são "compatíveis com abordagens descritas na literatura".
- A análise deve sempre partir dos dados da ocorrência, e nunca da teoria.

REGRAS DE REDAÇÃO TÉCNICA AVANÇADA:
- Ao comentar frequência, use expressões como:
  "predominância", "maior recorrência", "incidência pontual", "distribuição observada".
- Ao comentar similitude, use expressões como:
  "aproximação lexical", "convergência semântica", "compatibilidade com maior espelhamento verbal".
- Ao comentar percepção dos negociadores, use expressões como:
  "trajetória percebida", "variação observada", "mudança de percepção ao longo da ocorrência".
- Ao integrar os dados, use expressões como:
  "os dados sugerem", "há compatibilidade entre", "há associação provável", "o conjunto dos indicadores aponta", "não há base suficiente para afirmar de forma categórica".
- Evite expressões como:
  "ficou comprovado", "foi determinante", "foi decisivo", "causou diretamente", "foi bem-sucedido" sem sustentação explícita dos dados.

  REGRA ESPECÍFICA PARA "PONTOS FORTES E OPORTUNIDADES DE MELHORIA":
- As oportunidades de melhoria devem derivar EXCLUSIVAMENTE de limitações observáveis na ocorrência.
- É proibido sugerir técnicas ausentes da lista registrada.
- É proibido recomendar genericamente "mais empatia", "mais rapport", "mais estrutura" ou "melhor comunicação" sem apontar qual dado concreto da ocorrência sustenta essa observação.
- Quando houver técnicas registradas, a melhoria deve ser formulada como refinamento do uso, encadeamento, timing ou equilíbrio das técnicas já registradas, e não como introdução livre de novas técnicas.
- Quando não houver base suficiente para formular melhoria específica, declare insuficiência de evidência.

PADRONIZAÇÃO OBRIGATÓRIA DE ESTRUTURA:

A estrutura da resposta deve ser IDÊNTICA para todas as ocorrências, independentemente do conteúdo.

É TERMINANTEMENTE PROIBIDO:
- Alterar nomes de seções
- Omitir seções
- Reordenar seções
- Mesclar seções
- Criar novas seções

A resposta deve conter EXATAMENTE estas 3 seções, nesta ordem:

1. ### Diagnóstico Emocional e Lexical do Causador
2. ### Avaliação Técnica da Doutrina Aplicada
3. ### Pontos Fortes e Oportunidades de Melhoria (Sob a perspectiva da Inteligência Artificial)

Qualquer desvio dessa estrutura é considerado erro.

OBJETIVO ANALÍTICO:
Seu trabalho é:
- ler a transcrição literal;
- interpretar apenas as técnicas já registradas na ocorrência, se houver;
- buscar relação provável entre essas técnicas e a progressão observada;
- relacionar isso, quando possível, com:
  a) percepção dos negociadores,
  b) análise de similitude lexical,
  c) variação observada na agressividade/receptividade.

PADRÃO DAS CONCLUSÕES:
- Use formulações como: "observou-se", "identificou-se", "há indício", "os dados sugerem", "não há base suficiente para afirmar".
- Evite formulações como: "ficou evidente", "foi bem-sucedido", "demonstrou empatia", "houve rapport", salvo quando isso estiver claramente sustentado pelos dados desta ocorrência.

LISTA DE TÉCNICAS REGISTRADAS NESTA OCORRÊNCIA:
{_safe_json_dumps(tecnicas_ocorrencia)}

FORMATO OBRIGATÓRIO:
Retorne APENAS JSON VÁLIDO, com uma única chave:
- "parecer"

A chave "parecer" deve conter markdown com EXATAMENTE estes títulos:

### Diagnóstico Emocional e Lexical do Causador
### Avaliação Técnica da Doutrina Aplicada
### Pontos Fortes e Oportunidades de Melhoria (Segundo a Inteligência Artificial)

ESTRUTURA OBRIGATÓRIA DE CADA SEÇÃO:
- Trabalhe com base em evidência observável da ocorrência.
- Separe descrição do que foi observado de inferência analítica.
- Quando houver limitação metodológica, declare isso com clareza.

A seção "Avaliação Técnica da Doutrina Aplicada" DEVE começar EXATAMENTE com:
"A verbalização com o causador, conduzida pelo Negociador Principal {nome_negociador}, caracterizou-se por..."

REGRA FINAL DE SEGURANÇA ANALÍTICA:
Se existir dúvida entre afirmar algo ou reconhecer insuficiência de evidência, prefira reconhecer insuficiência de evidência.
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


def gerar_laudo_frio(likert_inicio, likert_fim, stats_spearman):
    """
    Mantido com o nome original para preservar compatibilidade com o app.py.
    """
    laudo = []

    likert_inicio = likert_inicio or {}
    likert_fim = likert_fim or {}
    stats_spearman = stats_spearman or {}

    delta_r = likert_fim.get("receptividade_media", 0) - likert_inicio.get("receptividade_media", 0)
    delta_a = likert_fim.get("agressividade_media", 0) - likert_inicio.get("agressividade_media", 0)

    if delta_r > 0:
        laudo.append(f"A receptividade média do causador apresentou aumento durante a ocorrência (Delta = +{delta_r:.1f}).")
    elif delta_r < 0:
        laudo.append(f"A receptividade média do causador sofreu redução durante a ocorrência (Delta = {delta_r:.1f}).")
    else:
        laudo.append("A receptividade média do causador permaneceu inalterada/estagnada ao longo da ocorrência.")

    if delta_a < 0:
        laudo.append(f"Observou-se mitigação na agressividade média (Delta = {delta_a:.1f}).")
    elif delta_a > 0:
        laudo.append(f"Houve escalada na agressividade média (Delta = +{delta_a:.1f}).")
    else:
        laudo.append("A agressividade média não apresentou variação direcional.")

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
* **Δ Positivo (+):** Indica que o comportamento (Agressividade ou Receptividade) aumentou.
* **Δ Negativo (-):** Indica que o comportamento diminuiu.
* **Δ Zero (0):** Indica estagnação ou ausência de mudança mensurável.
"""
    laudo.append(nota_metodologica)

    return "\n\n".join(laudo)