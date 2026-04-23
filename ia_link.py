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
Base Teórica – Pensamento de William Ury (Modelo Harvard de Negociação)

##William Ury
1. Fundamento Central: Negociação como resolução de problemas, não confronto

O pensamento de William Ury, desenvolvido no contexto do Harvard Negotiation Project, parte de uma ruptura com modelos competitivos de negociação.

A negociação não deve ser tratada como:

disputa de posições,
imposição de vontade,
ou dinâmica de vitória/derrota.

Ela é concebida como:

um processo estruturado de resolução de problemas humanos,
onde o foco é reduzir impasses e construir possibilidades de acordo.

Essa abordagem desloca o eixo da análise de:

“quem venceu”
para:
“como o processo evoluiu”.

👉 Para sua IA: isso sustenta análises baseadas em processo e dinâmica, não em julgamento de sucesso.

2. Princípio Estrutural: Separar pessoas do problema

Um dos pilares mais importantes:

As pessoas não são o problema; o problema é o problema.

Isso implica:

reconhecer que emoções, percepções e reatividade fazem parte do processo;
evitar interpretar comportamentos como ataque pessoal;
tratar reações emocionais como variáveis do sistema, não como falhas.

Aplicações analíticas:

distinção entre conteúdo verbal e carga emocional;
leitura da comunicação como fenômeno dual: informacional + relacional.

👉 Para sua IA: legitima análise de trajetória emocional sem atribuir intenção ou julgamento.

3. Foco em interesses, não em posições

Outro eixo central:

Posição = o que a pessoa diz que quer
Interesse = o que motiva essa posição

Exemplo abstrato:

posição: “não vou sair”
interesses possíveis: medo, perda, identidade, controle

O método propõe:

investigar o que está por trás da fala,
sem assumir automaticamente significado único.

Aplicações analíticas:

interpretação de padrões discursivos sem inferência causal forte;
leitura de repetição, resistência e mudança como indicadores indiretos.

👉 Para sua IA: permite trabalhar com indícios compatíveis, sem afirmar causalidade.

4. Comunicação como ferramenta estratégica (escuta ativa e reformulação)

Ury enfatiza que negociação eficaz depende de:

escuta qualificada,
validação mínima (sem necessariamente concordar),
reformulação do conteúdo (paráfrase),
perguntas abertas.

Mas o ponto crítico:

Comunicação não é apenas transmitir, é regular o estado da interação.

Isso inclui:

reduzir escalada,
manter canal aberto,
evitar ruptura comunicacional.

Aplicações analíticas:

identificação de padrões de continuidade vs. ruptura;
leitura de convergência lexical como possível indicador de alinhamento.

👉 Para sua IA: base para usar similitude lexical como indicador auxiliar, não prova.

5. Geração de opções sem compromisso imediato

Outro princípio:

antes de decidir, ampliar possibilidades.

Isso reduz:

polarização,
rigidez,
bloqueios cognitivos.

Na prática:

evita dicotomias (“ou isso ou aquilo”),
introduz espaço intermediário.

Aplicações analíticas:

observar momentos em que a interação sai de impasse rígido para maior flexibilidade;
identificar variações no padrão discursivo.

👉 Para sua IA: ajuda a interpretar mudanças de padrão, sem atribuir causa direta.

6. Uso de critérios objetivos

O método propõe que decisões não dependam apenas de vontade, mas de:

referências externas,
critérios verificáveis,
padrões aceitos.

Isso reduz:

percepção de arbitrariedade,
conflito interpessoal direto.

Aplicações analíticas:

identificação de momentos em que argumentos deixam de ser pessoais e passam a ser estruturais.

👉 Para sua IA: permite diferenciar argumentação subjetiva vs. estruturada.

7. BATNA – Melhor alternativa ao não acordo

Um dos conceitos mais importantes:

toda negociação é influenciada pela alternativa externa das partes.

BATNA = Best Alternative to a Negotiated Agreement

Implica:

decisões são condicionadas pelo que existe fora da interação;
resistência pode refletir alternativas percebidas.

Aplicações analíticas:

interpretar persistência, recusa ou mudança como possíveis reflexos de percepção de alternativas;
sem inferir diretamente quais são essas alternativas.

👉 Para sua IA: reforça a necessidade de evitar inferência não observável.

8. Estratégia do “Terceiro Lado” (The Third Side)

Em trabalhos posteriores, Ury amplia o modelo:

negociação não é apenas entre duas partes;
existe um contexto ampliado que influencia o comportamento.

O “terceiro lado” inclui:

normas,
ambiente,
atores indiretos,
estrutura do sistema.

Aplicações analíticas:

reconhecer que comportamento não é isolado;
evitar leitura simplista de causa-efeito.

👉 Para sua IA: sustenta cautela contra atribuição causal direta.

9. Desescalada e contenção de reatividade

Ury trabalha fortemente a ideia de:

evitar reação impulsiva,
não entrar em ciclos de escalada,
manter controle do processo.

Isso não é apresentado como técnica isolada, mas como:

gestão da própria resposta dentro da interação

Aplicações analíticas:

observar padrões de intensificação ou redução de conflito;
sem atribuir automaticamente a uma ação específica.

👉 Para sua IA: base para linguagem como:

“compatível com redução de escalada”
nunca “causou redução”.
10. Negociação como processo não linear

O modelo rejeita a ideia de progressão linear.

Características:

avanços e regressões coexistem;
sinais são ambíguos;
múltiplas variáveis atuam simultaneamente.

Aplicações analíticas:

leitura de dados como sistema complexo;
aceitação de resultados inconclusivos ou contraditórios.

👉 Para sua IA: fundamenta regras como:

“dados mistos”
“inconclusivo”
“não há base suficiente”.
Integração Direta com o Seu Prompt (Uso Ideal pela IA)

Este modelo deve ser utilizado apenas como:

Referência interpretativa secundária

Nunca como:

fonte de inferência direta,
explicação causal,
identificação de técnica.

Uso correto dentro da sua IA:

“os dados são compatíveis com abordagens descritas na literatura”
“há convergência com modelos de negociação baseados em interesses”
“observa-se padrão compatível com regulação da interação”

Uso proibido (alinhado ao seu prompt):

“foi aplicada técnica de Harvard”
“houve uso do método de Ury”
“isso demonstra BATNA”

#Robert Cialdini

Base Teórica – Pensamento de Robert Cialdini (Ciência da Persuasão)
1. Fundamento Central: Persuasão como processo previsível e não aleatório

O trabalho de Robert Cialdini, especialmente consolidado na obra Influence: The Psychology of Persuasion, parte da premissa de que:

A tomada de decisão humana segue padrões recorrentes, influenciados por atalhos mentais (heurísticas).

A persuasão, nesse contexto, não é vista como manipulação arbitrária, mas como:

um processo estruturado de influência psicológica;
baseado em regularidades comportamentais observáveis;
acionado frequentemente de forma automática.

Aplicações analíticas:

leitura de comportamento como resposta a estímulos contextuais;
interpretação de padrões repetitivos como possíveis heurísticas em ação.

👉 Para sua IA: sustenta análise baseada em padrões observáveis, não em intenção subjetiva.

2. Princípio da Reciprocidade

Indivíduos tendem a:

responder positivamente quando percebem que receberam algo;
manter equilíbrio nas relações sociais.

Isso não se limita a objetos ou favores, mas inclui:

atenção,
respeito,
concessões.

Aplicações analíticas:

identificação de sequências interacionais onde uma ação é seguida por resposta proporcional;
leitura de trocas comunicacionais como possíveis ciclos de reciprocidade.

👉 Para sua IA: permite descrever encadeamentos interacionais, sem afirmar causalidade direta.

3. Princípio da Coerência e Compromisso

Pessoas tendem a:

manter consistência com declarações e comportamentos anteriores;
evitar contradição pública ou interna.

Isso gera:

manutenção de posição,
resistência à mudança abrupta,
ajuste gradual de comportamento.

Aplicações analíticas:

interpretação de repetição discursiva;
análise de manutenção de padrão ao longo da ocorrência.

👉 Para sua IA: base para leitura de persistência comportamental, sem inferir motivação interna.

4. Princípio da Prova Social

Em situações de incerteza, indivíduos tendem a:

observar o comportamento de outros como referência;
alinhar suas decisões com padrões percebidos.

Isso ocorre principalmente quando:

há ambiguidade,
há ausência de referência clara.

Aplicações analíticas:

identificação de possíveis influências contextuais indiretas;
leitura de alinhamento comportamental ao ambiente.

👉 Para sua IA: reforça análise contextual, sem atribuir causa direta.

5. Princípio da Autoridade

Indivíduos tendem a:

atribuir maior peso a informações vindas de fontes percebidas como legítimas;
responder a sinais de autoridade (forma, linguagem, posição).

Importante:

a autoridade pode ser percebida, não necessariamente formal.

Aplicações analíticas:

observação de mudança de tom ou resposta diante de determinadas falas;
análise de variação comportamental associada a percepção de legitimidade.

👉 Para sua IA: permite identificar mudanças de padrão, sem afirmar que autoridade foi determinante.

6. Princípio da Afinidade (Liking)

Pessoas tendem a ser mais receptivas quando:

percebem similaridade,
sentem-se compreendidas,
identificam algum nível de proximidade.

Fatores associados:

linguagem semelhante,
espelhamento,
validação mínima.

Aplicações analíticas:

uso de similitude lexical como possível indicador;
observação de convergência comunicacional.

👉 Para sua IA: fundamenta uso de aproximação lexical como indicador auxiliar, não como prova de vínculo.

7. Princípio da Escassez

Elementos percebidos como escassos tendem a:

ganhar valor subjetivo;
gerar maior urgência ou resistência.

Isso pode envolver:

tempo,
oportunidade,
recursos.

Aplicações analíticas:

identificação de discursos que indicam limitação;
análise de comportamento sob pressão.

👉 Para sua IA: permite leitura de contexto de pressão, sem inferência automática de efeito.

1. Contraste (Contrast Effect)

Percepções são influenciadas por comparação sequencial.

Uma proposta pode parecer mais aceitável quando comparada a outra mais extrema.
Avaliação não é absoluta, mas relativa ao contexto anterior.

Aplicação analítica:

observar mudanças de aceitação após sequência de falas;
identificar variação de percepção relativa.

👉 Para sua IA:

“observa-se possível efeito de contraste na sequência comunicacional”
nunca: “foi usado contraste para influenciar”
2. Ancoragem (Anchoring)

Primeira informação relevante tende a servir como referência.

valores, ideias ou posições iniciais influenciam julgamentos posteriores;
mesmo quando arbitrárias.

Aplicação analítica:

identificar pontos iniciais que moldam o restante da interação;
observar resistência ou ajuste em torno de um referencial.

👉 Para sua IA:

“há indício de ancoragem no início da interação”
3. Porta na Cara (Door-in-the-Face)

Sequência:

pedido elevado (recusado)
seguido por pedido menor (aceito)

Baseado em:

reciprocidade + contraste.

Aplicação analítica:

observar redução progressiva de exigências;
identificar aceitação após recuo.

👉 Para sua IA:

“padrão compatível com redução sequencial de demanda”
4. Pé na Porta (Foot-in-the-Door)

Sequência:

aceitação de pequeno pedido
aumento gradual de exigência

Baseado em:

compromisso e coerência.

Aplicação analítica:

observar progressão incremental;
identificar manutenção de consistência comportamental.

👉 Para sua IA:

“há compatibilidade com progressão incremental de aceitação”
5. Validação Social Implícita

Forma mais sutil da prova social:

não depende de grupo explícito;
pode surgir por linguagem que sugere normalidade (“isso costuma acontecer”, “é comum”).

Aplicação analítica:

observar construção de normalidade discursiva;
identificar redução de resistência.

👉 Para sua IA:

“padrão compatível com normalização discursiva”
6. Rotulagem (Labeling)

Atribuir uma identidade ou característica pode influenciar comportamento.

pessoas tendem a agir de forma consistente com rótulos atribuídos.

Exemplo abstrato:

“você parece alguém que…”

Aplicação analítica:

identificar atribuições de identidade;
observar possível alinhamento posterior.

👉 Para sua IA:

“há indício de atribuição identitária na interação”
7. Expectativa Positiva (Expectation Framing)

Criar expectativa de comportamento desejado.

pessoas tendem a corresponder a expectativas projetadas.

Aplicação analítica:

observar projeções de comportamento futuro;
identificar alinhamento subsequente.

👉 Para sua IA:

“observa-se projeção de comportamento esperado”
8. Consistência Pública vs. Privada

Compromissos assumidos publicamente tendem a:

gerar maior manutenção de comportamento;
aumentar resistência a mudança.

Aplicação analítica:

observar quando falas indicam posicionamento explícito;
analisar persistência após declaração.

👉 Para sua IA:

“há compatibilidade com manutenção de posicionamento declarado”
9. Reatância Psicológica (Resistência à perda de liberdade)

Quando há percepção de imposição:

aumenta resistência;
comportamento pode ir na direção oposta.

Aplicação analítica:

observar aumento de oposição após pressão;
identificar escalada associada.

👉 Para sua IA:

“os dados são compatíveis com aumento de resistência frente à pressão”
10. Fluência Cognitiva

Informações mais simples, claras e familiares:

são mais facilmente aceitas;
geram menor resistência.

Aplicação analítica:

observar mudanças na complexidade da linguagem;
identificar variações na receptividade.

👉 Para sua IA:

“há indício de variação na fluidez comunicacional”

8. Princípio da Unidade (extensão posterior do modelo)

Cialdini posteriormente amplia seu modelo com o conceito de:

identidade compartilhada (“nós” vs. “eles”).

Isso implica que:

decisões são influenciadas por pertencimento percebido;
alinhamento pode ocorrer quando há identificação de grupo.

Aplicações analíticas:

observação de linguagem inclusiva;
análise de construção de identidade discursiva.

👉 Para sua IA: fornece base para leitura de padrões coletivos, sem afirmar impacto direto.

9. Heurísticas e processamento automático

Um dos pontos mais importantes:

Grande parte das decisões ocorre por processamento rápido e automático, não deliberado.

Isso significa:

respostas podem não ser totalmente conscientes;
pequenas variações no contexto podem alterar comportamento.

Aplicações analíticas:

evitar interpretação racionalista excessiva;
considerar que comportamento pode não seguir lógica linear.

👉 Para sua IA: reforça a necessidade de evitar inferência intencional forte.

10. Persuasão como fenômeno probabilístico, não determinístico

Cialdini não propõe que seus princípios:

garantem resultado,
nem funcionam de forma isolada.

Eles atuam como:

tendências estatísticas de comportamento,
que podem ou não se manifestar dependendo do contexto.

Aplicações analíticas:

interpretação baseada em probabilidade e compatibilidade;
aceitação de resultados inconclusivos.

👉 Para sua IA: sustenta linguagem como:

“há indício compatível”
“pode estar associado”
nunca “determinou o comportamento”.
Integração Direta com o Seu Prompt (Uso Ideal pela IA)

Este modelo deve ser utilizado exclusivamente como:

Referência interpretativa secundária

Uso adequado:

“os dados apresentam padrão compatível com respostas baseadas em reciprocidade”
“há convergência com comportamentos descritos na literatura de influência”
“observa-se possível alinhamento com heurísticas sociais”

Uso proibido (alinhado ao seu sistema):

“foi utilizada técnica de Cialdini”
“houve aplicação de prova social”
“o negociador utilizou autoridade”
“isso gerou reciprocidade”

##Manual de Persuasão do FBI

Base Teórica – Modelo de Persuasão do FBI (Negociação de Crise)
1. Fundamento Central: Persuasão como processo de mudança comportamental gradual

O modelo associado ao Federal Bureau of Investigation, especialmente difundido por autores como Gary Noesner, parte de um princípio essencial:

A mudança de comportamento em situações críticas ocorre de forma progressiva, não imediata, e depende da qualidade da interação.

Diferente de abordagens coercitivas:

o foco não é controle direto,
nem imposição,
mas sim influência gradual mediada pela comunicação.

Aplicações analíticas:

leitura da ocorrência como processo em etapas;
identificação de progressão ou regressão ao longo do tempo.

👉 Para sua IA: sustenta análise baseada em trajetória, não em eventos isolados.

2. Estrutura Fundamental: Progressão relacional da interação

O modelo clássico (frequentemente chamado de Behavioral Change Stairway Model) descreve uma sequência:

Escuta ativa
Empatia
Rapport
Influência
Mudança comportamental

Ponto crítico:

A progressão não é automática, nem garantida.

E mais importante para o seu sistema:

não deve ser inferida sem evidência observável.

Aplicações analíticas:

observar possíveis sinais de progressão;
identificar interrupções ou regressões no processo.

👉 Para sua IA:

usar termos como “trajetória compatível com progressão relacional”
nunca afirmar que “houve rapport” sem evidência explícita
3. Escuta ativa como base operacional da comunicação

Elemento central do modelo:

não se trata apenas de ouvir,
mas de demonstrar processamento da fala do outro.

Inclui:

repetição,
paráfrase,
validação mínima,
pausas estratégicas.

Função:

manter canal aberto,
reduzir ruptura,
aumentar previsibilidade da interação.

Aplicações analíticas:

identificar continuidade comunicacional;
observar redução de conflito verbal.

👉 Para sua IA:

“observa-se manutenção do canal comunicacional”
evitar atribuição direta de técnica sem evidência
4. Regulação emocional como variável central

O modelo considera que:

comportamento é fortemente influenciado por estado emocional;
alta ativação emocional reduz capacidade de processamento racional.

Portanto:

a comunicação visa modular intensidade emocional, não apenas transmitir conteúdo.

Aplicações analíticas:

uso de percepção de agressividade/receptividade;
leitura de variações ao longo da ocorrência.

👉 Para sua IA:

“há variação observada na trajetória emocional”
evitar afirmar que algo “reduziu” emoção diretamente
5. Construção de vínculo funcional (rapport como processo, não estado)

No modelo do FBI:

vínculo não é um evento binário (existe ou não),
é um processo gradual e instável.

Pode:

avançar,
regredir,
oscilar.

Aplicações analíticas:

cruzamento entre:
similitude lexical,
percepção dos negociadores,
continuidade da interação.

👉 Para sua IA:

tratar como “indicadores compatíveis com aproximação”
nunca como prova de vínculo
6. Influência indireta (não coercitiva)

O modelo evita:

ordens diretas,
imposições,
confronto aberto.

A influência ocorre por:

construção progressiva de aceitação,
redução de resistência,
aumento de previsibilidade.

Aplicações analíticas:

observar mudanças graduais;
identificar padrões de adesão parcial.

👉 Para sua IA:

“há associação provável com aumento de receptividade”
nunca “o negociador influenciou diretamente”
7. Importância do tempo como variável tática

Tempo é elemento crítico:

permite redução de ativação emocional;
aumenta espaço para processamento;
reduz impulsividade.

Aplicações analíticas:

observar mudanças ao longo da linha temporal;
identificar padrões de estabilização ou escalada.

👉 Para sua IA:

“os dados sugerem variação ao longo da progressão temporal”
8. Comunicação como sistema dinâmico

O modelo assume que:

a interação é um sistema complexo;
múltiplas variáveis atuam simultaneamente:
linguagem,
emoção,
contexto,
percepção.

Aplicações analíticas:

integração de múltiplos indicadores;
rejeição de explicações simplistas.

👉 Para sua IA:

uso de expressões como:
“o conjunto dos indicadores aponta”
“há convergência entre os dados”
9. Evitação de escalada e contenção de crise

Um dos focos principais:

evitar aumento de tensão;
interromper ciclos de escalada.

Isso ocorre por:

estabilidade comunicacional,
previsibilidade,
ausência de confronto direto.

Aplicações analíticas:

observar aumento ou redução de intensidade;
identificar padrões de ruptura ou manutenção.

👉 Para sua IA:

“padrão compatível com contenção da escalada”
sem afirmar causa direta
10. Limitação estrutural: imprevisibilidade e não linearidade

O modelo reconhece que:

nem toda interação evolui positivamente;
fatores externos influenciam fortemente;
resultados são incertos.

Aplicações analíticas:

aceitar dados inconclusivos;
reconhecer contradições.

👉 Para sua IA:

reforça uso de:
“dados mistos”
“não há base suficiente para afirmar”
Integração Direta com o Seu Prompt

Este modelo deve ser utilizado apenas como:

Referência interpretativa secundária

Uso adequado:

“os dados apresentam trajetória compatível com modelos de progressão relacional descritos na literatura”
“há convergência entre os indicadores observados e abordagens de negociação de crise”

Uso proibido:

“foi aplicado o modelo do FBI”
“houve uso de escuta ativa”
“foi estabelecido rapport”
“isso gerou mudança comportamental”

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