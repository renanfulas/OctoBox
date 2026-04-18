<!--
ARQUIVO: C.O.R.D.A. da evolucao de aprendizado local do box para inteligencia cross-box e playbooks operacionais.

TIPO DE DOCUMENTO:
- plano arquitetural e estrategico
- trilho de evolucao de produto e dados

AUTORIDADE:
- alta para a camada de aprendizado operacional entre boxes

DOCUMENTOS PAIS:
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)
- [wod-post-publication-operational-loop.md](wod-post-publication-operational-loop.md)
- [coach-wod-approval-corda.md](coach-wod-approval-corda.md)

QUANDO USAR:
- quando a duvida for como sair do aprendizado local de um box para inteligencia entre varios boxes
- quando precisarmos evitar debito tecnico em analytics operacional e metodologia
- quando quisermos transformar sinais operacionais em playbooks sem misturar isso com o core transacional

POR QUE ELE EXISTE:
- evita comparar boxes diferentes com dados baguncados
- protege o produto contra overengineering analitico cedo demais
- organiza a subida de maturidade: box local -> cluster -> cross-box -> playbook

O QUE ESTE ARQUIVO FAZ:
1. define a tese da inteligencia operacional cross-box
2. formaliza pre-requisitos de dados e taxonomia
3. registra riscos de produto e arquitetura
4. organiza a evolucao em ondas pragmaticas

PONTOS CRITICOS:
- isso nao deve contaminar o core transacional
- media bruta entre boxes pode mentir
- linguagem inconsistente de eventos destrói a comparacao
-->

# C.O.R.D.A. - Box local -> inteligencia cross-box -> playbooks operacionais

## C - Contexto

O OctoBox ja comecou a construir uma camada muito valiosa dentro de um box:

1. sinais operacionais apos o WOD
2. acoes sugeridas
3. retorno registrado
4. releitura before/after
5. resumo semanal
6. checkpoint de gestao
7. ritmo, maturidade e compromisso semanal

Isso significa que o sistema ja esta aprendendo, de forma leve, como um box opera.

Em linguagem simples:

1. antes o sistema so mostrava o treino
2. agora ele comeca a mostrar como a casa reage aos sinais do treino
3. o proximo salto e aprender o que costuma funcionar entre varias casas

### Tese de produto

O valor de longo prazo nao esta apenas em executar o WOD.

O valor grande esta em aprender:

1. quais metodologias operacionais funcionam melhor
2. em que tipo de box elas funcionam
3. quais delas merecem virar playbook oficial

### Tese de arquitetura

A inteligencia cross-box deve nascer acima da operacao local.

Ela nao deve:

1. redefinir verdade transacional
2. morar dentro da logica de request do box
3. misturar analytics global com decisao local cedo demais

Metafora curta:

1. cada box e uma cozinha
2. o core cuida para o fogao funcionar
3. a inteligencia cross-box observa varias cozinhas para descobrir quais receitas de operacao se repetem com sucesso

## O - Objetivo

Construir um trilho seguro para evoluir de:

1. aprendizado local de um box
2. para inteligencia por cluster de boxes
3. para playbooks operacionais sugeridos

Sem criar:

1. dashboard falso com medias enganosas
2. debito tecnico de taxonomia quebrada
3. acoplamento entre core local e camada agregada

### Sucesso significa

1. o box continua operando mesmo sem a camada cross-box
2. os eventos locais ficam padronizados e auditaveis
3. a leitura entre boxes acontece por segmento, nao por media cega
4. o sistema consegue sugerir playbooks com honestidade, nao com magia

## R - Riscos

### 1. Risco de linguagem quebrada

Se cada box registrar a mesma ideia com nomes diferentes:

1. `coach_aligned`
2. `briefing_professor`
3. `fala_inicial`

O sistema perde comparabilidade.

### 2. Risco de comparar boxes errados

Se um box premium com recepcao for comparado diretamente com um box enxuto sem recepcao:

1. a media mente
2. a recomendacao engana
3. o playbook vira ruido

### 3. Risco de confundir correlacao com verdade

Se uma acao aparece muito em boxes com bom resultado:

1. isso e um sinal forte
2. mas nao prova causa absoluta

O sistema precisa falar como painel operacional, nao como paper cientifico.

### 4. Risco de contaminar o core transacional

Se o box local depender da inteligencia cross-box para funcionar:

1. o request fica pesado
2. a confiabilidade cai
3. a manutencao fica cara

### 5. Risco de subir analytics cedo demais

Se voces pularem cedo para score, benchmark e ranking:

1. o produto parece inteligente
2. mas aprende em cima de dado prematuro
3. e o debito tecnico vira cimento molhado

## D - Direcao

### Principio mestre

`padronizar antes de comparar, segmentar antes de concluir, playbook antes de score`

Essa frase deveria decidir a ordem dessa trilha.

### Camadas recomendadas

#### 1. Camada local do box

Responsavel por:

1. registrar eventos
2. registrar compromissos
3. mostrar leitura operacional local

Regra:

1. essa camada continua sendo a fonte de verdade operacional local

#### 2. Camada agregada por leitura

Responsavel por:

1. consolidar eventos padronizados
2. comparar por cluster
3. gerar sinais de metodologia recorrente

Regra:

1. leitura somente
2. sem influenciar diretamente o core local no inicio

#### 3. Camada de playbooks

Responsavel por:

1. sugerir praticas recorrentes
2. transformar padroes em recomendacoes estruturadas
3. alimentar onboarding e metodologia

Regra:

1. playbook nasce depois que o padrao se repete com contexto suficiente

## A - Acoes / Ondas

### Onda 1 - Taxonomia oficial

Objetivo:

1. padronizar nomes de acoes
2. padronizar resultados
3. padronizar status semanais

Entrega minima:

1. dicionario unico de eventos operacionais
2. dicionario unico de fechamento
3. dicionario unico de compromisso semanal

Sem isso, nada acima presta.

### Onda 2 - Perfil operacional do box

Objetivo:

registrar contexto minimo do box para comparacao justa.

Campos minimos recomendados:

1. tamanho do box
2. numero de coaches
3. presenca ou nao de recepcao
4. volume medio de aulas
5. estagio de maturidade operacional

Metafora curta:

1. antes de comparar 20 panelas, precisamos saber se sao panela de pressao ou frigideira

### Onda 3 - Camada agregadora de leitura

Objetivo:

consolidar eventos padronizados fora do fluxo local.

Regra:

1. leitura agregada deve ser separada do request do box
2. pode ser tabela consolidada, snapshot ou job periodico

Ainda nao:

1. ranking
2. score magico
3. benchmark comercial bonito

### Onda 4 - Clusterizacao pragmatica

Objetivo:

comparar boxes parecidos.

Exemplos de cluster:

1. box pequeno sem recepcao
2. box medio com recepcao
3. box com coach muito presente
4. box com operacao mais distribuida

Regra:

1. comparar dentro do grupo antes de comparar o universo inteiro

### Onda 5 - Leitura de padroes recorrentes

Objetivo:

responder perguntas pequenas e valiosas como:

1. em boxes parecidos com este, quais acoes mais terminam em `Funcionou`?
2. quais acoes mais empacam em `Parcial`?
3. quais rituais estao maduros o suficiente para recomendacao?

### Onda 6 - Playbooks operacionais

Objetivo:

transformar padroes recorrentes em metodologia sugerida.

Exemplos:

1. `Coach alinhado na abertura` como boa pratica de boxes com forte presenca de coach
2. `Recepcao + coach` como combinacao mais forte do que recepcao isolada em boxes com check-in presencial alto
3. `WhatsApp isolado` como acao fraca em determinados clusters

Regra:

1. playbook e sugestao
2. nao dogma

### Onda 7 - Inteligencia assistida, nao autoritaria

Objetivo:

apresentar recomendacoes do tipo:

1. `Em boxes parecidos com o seu, coach alinhado costuma fechar melhor que WhatsApp isolado.`

Mas nunca:

1. `Essa e a unica verdade operacional.`

## Contratos tecnicos minimos

### Contrato 1 - Evento auditavel

Todo evento que sobe para comparacao cross-box precisa ter:

1. `event_type`
2. `box_id`
3. `week_start`
4. `actor_role`
5. `result_status`
6. `context_snapshot`

### Contrato 2 - Segmentacao

Nenhuma recomendacao cross-box deve nascer sem:

1. cluster
2. janela de observacao
3. base minima

### Contrato 3 - Honestidade de leitura

Toda leitura cross-box precisa admitir:

1. base curta
2. sinal moderado
3. padrao recorrente

Em vez de parecer absoluta.

## Fora de escopo por enquanto

1. ranking de boxes
2. score proprietario bonito sem base estatistica suficiente
3. IA generativa inventando playbook sem dado padronizado
4. dashboard gigante com mil filtros
5. benchmark publico entre boxes

## Resumo executivo

O trilho saudavel e este:

1. padronizar a lingua
2. registrar contexto
3. consolidar leitura fora do core
4. comparar por segmento
5. descobrir padroes
6. sugerir playbooks

Em linguagem simples:

1. primeiro aprendemos a escrever o diario direito
2. depois comparamos diarios parecidos
3. so entao viramos isso em manual oficial da casa
