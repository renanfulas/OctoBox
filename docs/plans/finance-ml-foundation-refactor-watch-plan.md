<!--
ARQUIVO: plano de vigilancia para evitar concentracao excessiva na trilha de inteligencia financeira antes do momento certo de refactor.

TIPO DE DOCUMENTO:
- plano de vigilancia estrutural

AUTORIDADE:
- media

DOCUMENTO PAI:
- [../architecture/finance-churn-ml-foundation.md](../architecture/finance-churn-ml-foundation.md)

DOCUMENTOS IRMAOS:
- [../architecture/operational-intelligence-ml-layer.md](../architecture/operational-intelligence-ml-layer.md)
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)

QUANDO USAR:
- quando a duvida for se a trilha de inteligencia financeira ainda pode crescer sem refactor
- quando precisarmos decidir se o peso esta ficando concentrado demais em poucos arquivos
- quando formos abrir uma nova onda de fila, score historico ou recomendacao assistida

POR QUE ELE EXISTE:
- registra que a base atual esta boa e nao pede refactor imediato.
- evita esquecer os sinais que indicam concentracao excessiva de regra, presenter e snapshot.
- protege a frente de ML financeiro contra debito tecnico silencioso.

O QUE ESTE ARQUIVO FAZ:
1. define a leitura honesta do estado atual.
2. lista os pontos que devem ser vigiados nas proximas ondas.
3. estabelece gatilhos claros para saber quando refactor deixa de ser opcional.
4. organiza uma resposta futura sem pressa e sem romantizar improviso.

PONTOS CRITICOS:
- este documento nao autoriza refactor agora.
- ele existe para vigilancia e memoria operacional.
- se os gatilhos aparecerem, ignorar por muito tempo pode transformar flexibilidade em fragilidade.
-->

# Finance ML Foundation Refactor Watch Plan

## Resumo

A trilha de inteligencia financeira do OctoBox esta evoluindo bem.

Em linguagem simples:

1. a casa esta firme
2. ainda da para subir mais alguns andares
3. mas ja vale marcar quais colunas precisam ser observadas

Este plano existe para lembrar que a base atual esta saudavel, mas nao deve crescer no piloto automatico para sempre.

Regra oficial deste documento:

1. nao fazer refactor agora so por ansiedade arquitetural
2. continuar entregando valor
3. observar concentracao de peso
4. agir antes que a mochila fique pesada demais num ombro so

## Leitura honesta do estado atual

Hoje o projeto esta em um ponto bom.

Sinais positivos reais:

1. conseguimos adicionar fundacao de churn, fila operacional, persistencia de follow-up, analytics historico, ajuste de acao, ajuste de confianca e ajuste de janela sem quebrar o predio
2. a estrategia de `snapshot` e `data product` esta funcionando como plataforma de leitura
3. a separacao entre fato operacional, recomendacao e resultado ainda esta inteligivel
4. os testes estao segurando bem a evolucao

Traducao curta:

1. a estrutura nao esta travada
2. a estrutura nao esta caotica
3. a estrutura ainda aceita crescimento com disciplina

## Onde o peso ja comeca a se concentrar

Os principais pontos de vigilancia agora sao estes:

1. [churn_foundation.py](../../catalog/finance_snapshot/churn_foundation.py)
2. [follow_up_analytics.py](../../catalog/finance_snapshot/follow_up_analytics.py)
3. [finance_center_page.py](../../catalog/presentation/finance_center_page.py)
4. [follow_up_tracker.py](../../finance/follow_up_tracker.py)

Leitura por papel:

### 1. Churn foundation

Risco observado:

1. concentrar regra base
2. concentrar override historico
3. concentrar ajuste de confianca
4. concentrar ajuste de janela
5. concentrar ordenacao e contrato da fila

Metafora:

1. hoje esse arquivo e um bom maestro
2. mais adiante ele pode virar banda, palco e bilheteria ao mesmo tempo

### 2. Follow-up analytics

Risco observado:

1. virar um pequeno motor de inteligencia sozinho
2. acumular matrizes, score e heuristicas demais
3. ficar responsavel por mais decisao do que so leitura historica

### 3. Presenter do financeiro

Risco observado:

1. a traducao operacional da fila ficar inchada
2. copy, badges, ajuste, labels e playbooks crescerem sem modularizacao
3. a camada de apresentacao virar dona informal da semantica

### 4. Follow-up tracker

Risco observado:

1. payload crescer demais
2. memoria historica importante ficar escondida so em JSON
3. campos centrais para analytics futuro permanecerem informais tempo demais

## O que nao fazer agora

Para esta fase, estas atitudes seriam prematuras:

1. refatorar toda a trilha so porque ela ficou mais sofisticada
2. abrir uma frente grande de modularizacao sem dor real
3. mover tudo para uma `decision_engine` so por elegancia teorica
4. promover cedo demais payloads auxiliares a contrato definitivo sem prova de uso

Regra:

1. refactor por ansiedade cria o mesmo tipo de debito que falta de refactor

## Gatilhos que indicam hora de agir

O refactor deixa de ser opcional quando um ou mais sinais abaixo aparecerem de forma repetida.

### Gatilho 1: crescimento de regra em cascata

Sinal:

1. toda nova heuristica exige tocar no mesmo arquivo central
2. a cada onda, `churn_foundation.py` recebe mais um bloco de decisao
3. comecamos a precisar lembrar ordem de execucao na memoria

Leitura:

1. o cerebro central esta ficando denso demais

### Gatilho 2: presenter inchado

Sinal:

1. cada novo ajuste historico pede mais badge, nota, label e copy dentro do mesmo presenter
2. a leitura da fila fica dificil de manter
3. pequenas mudancas visuais passam a exigir contexto demais

Leitura:

1. a tradutora da tela esta carregando dicionario demais numa unica mao

### Gatilho 3: payload persistido com valor semantico demais

Sinal:

1. comecamos a consultar `payload[...]` para decidir comportamento relevante
2. dashboards ou snapshots passam a depender de chaves internas de payload como se fossem contrato
3. campos importantes para score futuro nao tem superficie explicita

Leitura:

1. o caderno de anotacao virou banco de verdade sem assumir isso

### Gatilho 4: teste novo fica caro demais

Sinal:

1. para testar uma heuristica simples precisamos montar muito contexto
2. os cenarios ficam verbosos demais
3. a leitura do teste deixa de apontar uma regra e passa a montar meio sistema

Leitura:

1. a maquina ainda funciona, mas ja pede desmontagem por modulos

### Gatilho 5: snapshots com responsabilidade demais

Sinal:

1. analytics, ranking, ajuste e contratos ficam concentrados num mesmo circuito
2. o snapshot deixa de parecer fotografia e comeca a parecer central de comando inteira

Leitura:

1. a camada de leitura esta virando camada de decisao sem declarar isso

## Resposta futura recomendada

Quando os gatilhos realmente apertarem, a resposta preferida deve ser gradual.

### Etapa 1: separar regras por familias

Possivel destino:

1. `catalog/finance_snapshot/rules/base_recommendation.py`
2. `catalog/finance_snapshot/rules/recommendation_override.py`
3. `catalog/finance_snapshot/rules/confidence_adjustment.py`
4. `catalog/finance_snapshot/rules/prediction_window_adjustment.py`

### Etapa 2: separar leitura historica de decisao

Possivel destino:

1. analytics continua medindo
2. um modulo de decisao historica passa a consumir essas medidas

### Etapa 3: reduzir dependencia de payload opaco

Possivel direcao:

1. promover para contrato explicito so o que provou valor recorrente
2. manter no payload apenas contexto auxiliar ou trilha de apoio

### Etapa 4: modularizar apresentacao da fila

Possivel destino:

1. builders pequenos para:
2. copy da recomendacao
3. badges de ajuste
4. notas de timing
5. playbook operacional

## Checklist de revisao antes de cada nova onda

Antes de abrir a proxima onda da trilha financeira, revisar:

1. quantos arquivos centrais precisam ser tocados para a nova regra?
2. a nova regra ainda cabe na familia atual ou pede modulo proprio?
3. o presenter continua legivel?
4. o payload esta guardando contexto ou escondendo contrato?
5. os testes continuam pequenos e objetivos?

Se a maioria dessas respostas comecar a piorar, o refactor deixa de ser luxo e vira protecao estrutural.

## Decisao oficial por enquanto

Decisao atual:

1. nao fazer refactor agora
2. continuar implementando valor em cima da base atual
3. usar este documento como alarme de manutencao preventiva

Em frase unica:

O OctoBox ainda esta em terreno bom para crescer sem cirurgia, mas a trilha de inteligencia financeira ja merece vigilancia consciente para que o ganho de hoje nao vire peso escondido de amanha.
