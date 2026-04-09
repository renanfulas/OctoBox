<!--
ARQUIVO: formalizacao da fundacao de ML financeiro para churn e cancelamento no OctoBox.

TIPO DE DOCUMENTO:
- direcao arquitetural satelite

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [operational-intelligence-ml-layer.md](operational-intelligence-ml-layer.md)

DOCUMENTOS IRMAOS:
- [../plans/finance-ml-foundation-refactor-watch-plan.md](../plans/finance-ml-foundation-refactor-watch-plan.md)

QUANDO USAR:
- quando a duvida for como preparar o financeiro para score de churn, risco de cancelamento e fila operacional assistida sem contaminar o core transacional

POR QUE ELE EXISTE:
- impede que churn financeiro seja tratado como simples inadimplencia ou como score solto sem verdade de negocio.
- formaliza a fundacao de dados, sinais e reconciliacao antes de qualquer modelo estatistico.
- prepara a primeira trilha de ML financeiro com saida operacional e auditavel.

O QUE ESTE ARQUIVO FAZ:
1. define a verdade de negocio inicial para churn financeiro.
2. separa sinal financeiro, estado operacional e inferencia futura.
3. estabelece a fundacao de dados e contratos para fila operacional assistida.

PONTOS CRITICOS:
- churn financeiro nao pode ser reduzido a pagamento atrasado.
- score futuro nao pode substituir o estado real do aluno.
- sem linha do tempo reconciliada entre financeiro, matricula e status do aluno, o modelo aprende em cima de ruído.
-->

# Financial Churn ML Foundation

## Tese central

No OctoBox, a primeira trilha de ML aplicada ao financeiro deve responder uma pergunta maior do que "quem esta atrasado?".

Ela deve responder:

1. quem esta dando sinais financeiros de saida
2. quem realmente saiu
3. quem ainda pode ser recuperado antes de virar perda real

Por isso, a fundacao de `ML financeiro` nao deve nascer como motor de cobranca.

Ela deve nascer como camada de leitura reconciliada para `churn/cancelamento`, com saida futura em `fila operacional`.

Em linguagem curta:

1. atraso e sinal
2. inatividade e verdade final inicial
3. score vem depois para priorizar acao

## Verdade de negocio inicial

Para a trilha inicial desta capacidade, o `churn verdadeiro` passa a ser definido assim:

1. `Student.status = inactive`

Essa escolha importa porque:

1. pagamento atrasado sozinho nao prova saida
2. matricula expirada sozinha nao prova abandono
3. o estado do aluno entrega a leitura final de perda operacional nesta fase

Regra:

1. inadimplencia entra como sinal forte
2. cancelamento ou deterioracao financeira entram como sinal forte
3. churn real inicial continua sendo a inatividade do aluno

## As tres camadas obrigatorias

O OctoBox deve separar essa leitura em tres planos.

### 1. Financial Signal

Aqui vivem:

1. atraso
2. estorno
3. falha de renovacao
4. recorrencia de atraso
5. ausencia de pagamento recente
6. interacao financeira sem conversao

Pergunta:

1. o que no financeiro sugere risco?

### 2. Operational State

Aqui vivem:

1. status da matricula
2. expiração
3. cancelamento
4. reativacao
5. status do aluno

Pergunta:

1. o que o sistema reconhece como estado real do aluno agora?

### 3. ML Inference

Aqui vivem:

1. `financial_risk_score`
2. `churn_risk_score`
3. `confidence`
4. `reason_codes`
5. `recommended_action`

Pergunta:

1. dado o historico reconciliado, quem merece prioridade antes de virar churn real?

Resumo:

1. sinal nao e verdade
2. estado nao e score
3. score nao pode virar verdade sozinho

## Linha do tempo reconciliada

A fundacao correta para ML financeiro nao e um campo novo isolado.

Ela e uma `linha do tempo reconciliada por aluno`.

Essa linha do tempo deve conseguir consolidar:

1. vencimentos
2. pagamentos
3. dias em atraso
4. cancelamento ou expiracao de matricula
5. transicao para `inactive`
6. comunicacoes financeiras
7. retorno ou reativacao

Ela precisa responder com seguranca:

1. quando os sinais financeiros começaram
2. quando o comportamento piorou
3. quando o aluno virou inativo
4. se houve recuperacao depois

Regra:

1. essa leitura deve nascer como data product, snapshot ou agregacao reconciliada
2. ela nao deve ficar espalhada entre template, queryset solto e regra local de tela

## Fundacao de dados que ja existe no predio

Hoje o predio ja tem partes importantes dessa base:

1. `Payment` com `due_date`, `paid_at`, `amount`, `status`, `method`, `billing_group`, parcelas e referencia
2. `Enrollment` com status e janela temporal
3. `Student.status` como leitura final inicial do churn real
4. `catalog/finance_snapshot/` como superficie de leitura consolidada
5. `finance/overdue_metrics.py` como regra compartilhada de atraso real
6. `finance_communication_actions` como trilho de toque financeiro

Isso significa:

1. a fundacao nao precisa inventar um novo predio
2. ela precisa costurar e versionar melhor a leitura temporal entre essas pecas

## Features que devem nascer como agregacoes reproduziveis

Antes de qualquer modelo, o sistema deve conseguir calcular de forma estavel:

1. dias desde o ultimo pagamento
2. numero de pagamentos atrasados em 30 dias
3. numero de pagamentos atrasados em 60 dias
4. numero de pagamentos atrasados em 90 dias
5. valor total em aberto
6. atraso medio
7. tempo entre matricula e primeiro atraso
8. tempo desde a ultima interacao financeira
9. quantidade de comunicacoes financeiras enviadas
10. quantidade de mudancas de status da matricula
11. relacao entre atraso e inatividade posterior

Regra:

1. feature boa e reproduzivel
2. feature ruim depende de leitura improvisada em tempo de request

## Contrato futuro de inferencia

Quando o score existir, a saida minima precisa carregar:

1. `student_id`
2. `actual_student_status`
3. `financial_risk_score`
4. `churn_risk_score`
5. `confidence`
6. `reason_codes`
7. `recommended_action`
8. `computed_at`
9. `rule_version` ou `model_version`
10. `prediction_window`

Regra:

1. o contrato precisa distinguir explicitamente estado real de inferencia
2. a fila operacional futura mostra recomendacao, nao um veredito escondido

## Fila operacional como primeira superficie

A primeira superficie de produto dessa trilha nao deve ser dashboard.

Ela deve ser uma `fila operacional`.

Motivo:

1. churn so melhora quando alguem age antes
2. fila operacional transforma score em prioridade utilizavel
3. dashboard sozinho informa, mas nao organiza a resposta do time

Essa fila futura deve suportar:

1. ordenacao por risco
2. filtros por janela temporal
3. reason codes curtos
4. badge de risco
5. distincao entre sinal financeiro e churn ja consumado
6. ultima acao financeira ou comercial relevante

Objetivo da fila:

1. agir antes do churn final
2. priorizar follow-up
3. evitar uma lista cega de inadimplentes sem contexto

## Explicabilidade minima obrigatoria

Se um aluno entrar em alto risco, a equipe precisa conseguir ler algo como:

1. `3 atrasos em 60 dias`
2. `14 dias sem pagamento apos vencimento`
3. `matricula expirada sem renovacao`
4. `sem resposta apos regua financeira recente`

Regra:

1. score sem explicacao curta vira caixa-preta
2. caixa-preta em operacao diaria vira desuso ou erro de confianca

## Casos que o conjunto de treino precisa distinguir

O futuro treino ou regra precisa separar com clareza:

1. aluno com atraso recorrente que depois vira `inactive`
2. aluno inadimplente que regulariza e segue ativo
3. aluno com matricula expirada, mas ainda nao tratado como churn real
4. aluno com toque financeiro que responde e se recupera
5. aluno reativado depois de inatividade

Essa separacao importa porque:

1. o modelo nao pode aprender que todo atraso termina em perda
2. o modelo tambem nao pode ignorar padroes de degradacao real

## Guardrails obrigatorios

1. inadimplencia nao deve ser rotulada como churn automaticamente
2. `Student.status = inactive` continua sendo a verdade inicial de churn real nesta fase
3. score futuro nao escreve estado real do aluno
4. reativacao precisa continuar auditavel para nao contaminar leitura historica
5. feature temporal nao pode depender de interpretacao visual de tela
6. a fila futura deve degradar com seguranca se o score falhar

## Ordem correta de implantacao

### Fase 1: fundacao de leitura

1. consolidar linha do tempo reconciliada entre financeiro, matricula, aluno e comunicacao
2. formalizar sinais financeiros e estado real de churn
3. garantir metricas estaveis e auditaveis

### Fase 2: camada de agregacoes

1. expor features temporais reproduziveis
2. versionar leituras importantes
3. preparar data products para analytics e treino futuro

### Fase 3: score transparente

1. comecar por regra explicita ou score simples
2. carregar confidence e reason codes
3. projetar resultado na fila operacional

### Fase 4: modelos mais fortes

1. risco de churn
2. probabilidade de recuperacao
3. priorizacao de follow-up
4. recomendacao de regua operacional por contexto

## Formula oficial desta trilha

A formula oficial da fundacao de ML financeiro no OctoBox passa a ser esta:

1. pagamento e atraso produzem sinal
2. matricula e status do aluno produzem estado
3. linha do tempo reconciliada produz dado confiavel
4. features reproduziveis produzem base de score
5. score auditavel produz prioridade operacional

Em frase unica:

O ML financeiro do OctoBox deve nascer como leitura reconciliada de sinais de degradacao que antecedem a inatividade real do aluno, nunca como atalho para confundir atraso com churn consumado.

## Vigilancia estrutural desta trilha

Esta trilha arquitetural ja tem um plano de vigilancia para concentracao excessiva de regra, presenter, snapshot e payload:

1. [../plans/finance-ml-foundation-refactor-watch-plan.md](../plans/finance-ml-foundation-refactor-watch-plan.md)

Regra:

1. a fundacao atual continua valida e nao pede refactor imediato
2. o plano existe para marcar os gatilhos que indicam quando a proxima onda deve deixar de ser so entrega e passar a incluir reparticao estrutural
