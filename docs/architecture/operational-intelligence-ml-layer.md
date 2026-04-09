<!--
ARQUIVO: formalizacao da camada de inteligencia operacional e machine learning do OctoBox.

TIPO DE DOCUMENTO:
- direcao arquitetural satelite

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [architecture-growth-plan.md](architecture-growth-plan.md)

QUANDO USAR:
- quando a duvida for onde ML, scoring, previsao e atribuicao analitica devem viver na arquitetura do OctoBox

POR QUE ELE EXISTE:
- impede que IA e ML vazem para o core transacional cedo demais.
- formaliza a camada de inteligencia como estrutura acima do core, alimentada por dados confiaveis, reconciliados e auditaveis.
- define guardrails para score, previsao, atribuicao e automacao orientada por modelo.

O QUE ESTE ARQUIVO FAZ:
1. define o que e a camada de inteligencia operacional e ML no OctoBox.
2. separa essa camada do core, do Center Layer e da Signal Mesh.
3. estabelece principios, riscos e ordem correta de implantacao.

PONTOS CRITICOS:
- ML nao pode virar fonte primaria de verdade do sistema.
- previsao nao pode contaminar escrita transacional sensivel.
- sem qualidade de dado, reconciliacao e observabilidade, ML entra como brilho precoce e cria opacidade.
-->

# Operational Intelligence and ML Layer

## Tese central

O OctoBox precisa crescer para inteligencia operacional sem deixar que inteligencia vire confusao estrutural.

A camada de `Machine Learning` do OctoBox nao pertence ao nucleo transacional do produto.

Ela pertence a um andar superior de leitura, atribuicao, previsao, score e recomendacao, sempre alimentado por dados consolidados e nunca tratado como verdade primaria de escrita.

Em linguagem curta:

1. o core decide e registra
2. a camada de ML observa, aprende e recomenda
3. a verdade oficial continua no dominio transacional

## O que essa camada resolve

Sem uma camada propria, o sistema tende a cair em erros previsiveis:

1. score calculado dentro de view ou template
2. previsao misturada com regra de negocio obrigatoria
3. modelo usando dado cru e contraditorio
4. automacao disparada por inferencia sem rastreabilidade
5. interface mostrando "certeza" onde o sistema so tem probabilidade

A camada de ML existe para impedir isso.

## Regra-mestra

No OctoBox, `ML nunca escreve verdade primaria`.

ML pode:

1. classificar
2. prever
3. priorizar
4. recomendar
5. sinalizar conflito
6. sugerir proxima acao

ML nao pode, por padrao:

1. criar verdade canonica sozinho
2. sobrescrever dado operacional auditado
3. substituir reconciliacao explicita de dominio
4. disparar mutacao sensivel sem guardrail

## Lugar dessa camada no predio

O predio passa a ser lido assim:

### Nivel 1: acesso

1. web operacional
2. admin
3. API
4. integracoes externas
5. jobs de entrada

### CENTER

1. entradas publicas oficiais por capacidade
2. traducao entre borda e nucleo

### Nivel 2: nucleo interno

1. `domain`
2. `application`
3. `infrastructure`
4. persistencia e invariantes oficiais

### Signal Mesh

1. sinais externos
2. envelopes tecnicos
3. filas
4. reprocessamentos
5. integracoes e propagacao

### Operational Intelligence and ML Layer

1. consolidacao analitica
2. feature computation
3. scoring
4. previsao
5. atribuicao reconciliada
6. recomendacao operacional
7. leitura executiva assistida

Resumo:

1. o core registra o que aconteceu
2. a Signal Mesh transporta sinais
3. a camada de ML interpreta padroes acima disso

## Diferenca entre core, Signal Mesh e ML

### Core

Pergunta que o core responde:

1. o que e verdade operacional e transacional agora?

### Signal Mesh

Pergunta que a Signal Mesh responde:

1. como sinais entram, circulam e chegam ao lugar certo sem deformar o nucleo?

### ML Layer

Pergunta que a camada de ML responde:

1. dado o historico consolidado e reconciliado, o que o sistema pode inferir, priorizar ou prever com seguranca controlada?

Resumo:

1. core decide verdade
2. mesh move sinais
3. ML interpreta padroes

## Fontes de dado permitidas

A camada de ML so pode operar sobre dados que tenham passado por consolidacao suficiente.

Fontes corretas:

1. snapshots publicos
2. tabelas reconciliadas
3. eventos auditaveis
4. historicos com versao
5. atribuicao resolvida
6. metricas operacionais agregadas

Fontes perigosas quando usadas direto:

1. payload externo cru
2. campo temporario de form
3. valor contraditorio sem reconciliacao
4. evento parcial de integracao
5. suposicao inferida no frontend

Regra:

1. dado cru pode entrar na malha
2. dado reconciliado e que pode subir para ML

## Camadas internas da inteligencia operacional

A camada de ML do OctoBox deve crescer em quatro blocos.

### 1. Consolidated Data Products

Responsavel por:

1. juntar sinais dispersos
2. produzir leituras estaveis para analytics
3. separar operacional, declarado e resolvido quando houver conflito

Exemplos:

1. origem operacional do aluno
2. origem declarada do aluno
3. origem resolvida para analytics
4. tempo ate matricula
5. atraso financeiro consolidado
6. recorrencia de faltas

### 2. Feature Layer

Responsavel por:

1. transformar dado consolidado em features
2. manter definicoes reproduziveis
3. evitar recalculo ad hoc espalhado

Exemplos:

1. dias entre lead e matricula
2. quantidade de faltas nos ultimos 30 dias
3. atraso medio por carteira
4. score de confianca da atribuicao
5. frequencia recente de interacao

### 3. Model and Scoring Layer

Responsavel por:

1. aplicar regras probabilisticas ou modelos
2. gerar score, classe ou previsao
3. expor saida pequena, auditavel e versionada

Exemplos:

1. propensao de conversao
2. risco de churn
3. risco de inadimplencia
4. score de qualidade de lead
5. confianca da origem resolvida

### 4. Decision Support Layer

Responsavel por:

1. transformar score em leitura operacional segura
2. sugerir prioridade, fila ou proxima acao
3. manter separacao entre recomendacao e mutacao automatica

Exemplos:

1. destacar leads com alta chance de conversao
2. priorizar alunos com maior risco de evasao
3. sugerir requalificacao de origem
4. elevar para revisao casos com conflito de atribuicao

## Primeira trilha oficial de ML no OctoBox

A primeira trilha de ML mais segura para o produto nao e chatbot.

Tambem nao e automacao cega.

A primeira trilha mais madura e esta:

1. atribuicao comercial reconciliada
2. score de confianca da origem
3. leitura de conversao por origem
4. previsao de conversao e retencao
5. recomendacao de follow-up e priorizacao

Motivo:

1. essa trilha nasce em cima de dados operacionais reais
2. ela melhora leitura e decisao sem invadir o core cedo demais
3. ela prepara terreno para modelos mais fortes depois

Para a trilha especifica de churn financeiro com saida em fila operacional, leia tambem [finance-churn-ml-foundation.md](finance-churn-ml-foundation.md).

## A arquitetura de atribuicao como caso exemplar

No caso da origem do aluno, a camada de ML deve partir de tres niveis:

1. `operational source`
2. `declared source`
3. `resolved source`

A camada de ML pode:

1. medir conflito entre operacional e declarada
2. calcular confianca
3. detectar padroes de erro por equipe, unidade ou canal
4. sugerir follow-up para requalificacao
5. alimentar relatorios de conversao mais confiaveis

Ela nao pode:

1. apagar historico anterior
2. escolher silenciosamente uma verdade nova sem regra
3. sobrescrever auditoria operacional

## Contratos obrigatorios dessa camada

Toda saida de inteligencia deve carregar pelo menos:

1. `model_version` ou `rule_version`
2. `computed_at`
3. `input_window` quando fizer sentido
4. `confidence`
5. `reason_code` ou explicacao curta
6. `is_recommendation` explicito quando nao for decisao oficial

Regra:

1. score sem versao vira supersticao tecnica
2. previsao sem timestamp vira fumaca historica

## Guardrails obrigatorios

1. nenhum modelo pode escrever direto em verdade primaria sem camada de decisao explicita
2. recomendacoes sensiveis precisam de reason code legivel
3. features devem ser reproduziveis
4. eventos de inferencia relevante precisam ser auditaveis
5. o produto deve degradar com seguranca se o scoring falhar
6. front-end nunca deve depender de inferencia para renderizar o caminho minimo de operacao

## Anti-padroes proibidos

1. chamar modelo dentro de request critico de escrita sem fallback seguro
2. deixar payload externo cru virar feature canonica sem reconciliacao
3. usar frontend como lugar de consolidacao analitica
4. misturar enum de funil com enum de origem
5. tratar output probabilistico como se fosse fato oficial

## Ordem correta de implantacao

### Fase 1: fundacao de dado

1. separar dado operacional, declarado e resolvido
2. criar historico e reconciliacao
3. expor metricas confiaveis
4. registrar auditoria e observabilidade

### Fase 2: feature layer estavel

1. definir features pequenas e reproduziveis
2. consolidar jobs de calculo
3. versionar agregacoes importantes

### Fase 3: scoring inicial

1. score de confianca
2. score de conversao
3. score de risco simples
4. regras transparentes antes de modelos mais sofisticados

### Fase 4: modelos mais fortes

1. previsao de churn
2. previsao de inadimplencia
3. segmentacao operacional
4. recomendacao assistida por contexto

## Regra de humildade arquitetural

O OctoBox nao deve usar ML para parecer mais avancado.

Ele deve usar ML quando:

1. o dado estiver pronto
2. a leitura humana ja estiver doendo
3. a previsao realmente reduzir atrito operacional
4. a arquitetura continuar clara depois da adicao

Em frase curta:

1. primeiro verdade
2. depois leitura
3. depois score
4. por ultimo automacao assistida

## Formula oficial

A formula arquitetural oficial da inteligencia no OctoBox passa a ser esta:

1. core transacional confiavel embaixo
2. sinais e integracoes na malha
3. dados consolidados acima
4. features reproduziveis
5. score versionado
6. recomendacao auditavel
7. mutacao sensivel continua protegida por regra explicita do dominio

Em frase unica:

A camada de ML do OctoBox existe para interpretar padroes acima do core, nunca para substituir a verdade operacional do core.
