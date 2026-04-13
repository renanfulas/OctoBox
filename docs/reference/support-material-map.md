<!--
ARQUIVO: mapa do material de apoio e das zonas nao canonicas do repositorio.

TIPO DE DOCUMENTO:
- referencia operacional de classificacao

AUTORIDADE:
- media para decidir o que e runtime, o que e apoio e o que e laboratorio

DOCUMENTO PAI:
- [../../README.md](../../README.md)

QUANDO USAR:
- quando houver duvida se uma pasta faz parte do produto vivo
- quando for limpar o repositorio sem apagar material util
- quando IA ou time precisarem distinguir base canonica de apoio historico

POR QUE ELE EXISTE:
- reduz a competicao visual entre documento vivo e material auxiliar
- evita tratar laboratorio, biblioteca de prompts ou snapshot como se fossem runtime
- cria um criterio simples para manter, isolar, arquivar ou apagar

PONTOS CRITICOS:
- este mapa nao transforma apoio em regra canonica
- se uma pasta mudar de papel, este arquivo precisa ser atualizado
- suporte util nao deve ser apagado por impulso so porque nao participa do runtime
-->

# Mapa de material de apoio

Este documento separa o predio principal do deposito, da biblioteca e do laboratorio.

Em linguagem simples:

- runtime e o motor do carro
- documentacao canonica e o manual oficial
- apoio e a caixa de ferramentas
- laboratorio e a bancada de testes

Misturar tudo no mesmo nivel faz o time perder tempo tentando descobrir o que manda e o que so ajuda.

## Regra curta

Use esta classificacao:

1. `canonico`: explica, governa ou opera o produto vivo
2. `apoio`: ajuda a pensar, revisar, aprender ou registrar
3. `laboratorio`: prototipo, experimento ou exemplo copiavel
4. `arquivo`: fotografia historica que pode continuar util como contexto

## Classificacao por zona

### `prompts/`

Status:

1. `apoio`

Papel:

1. biblioteca operacional de prompting
2. trilho de aprendizado e padronizacao de prompts
3. apoio humano e agentic para tarefas tecnicas

Regra:

1. manter
2. nao tratar como runtime
3. nao usar como prova de comportamento do produto

Traducao pratica:

1. `prompts/` e biblioteca, nao motor
2. apagar isso seria como jogar fora o caderno de formulas porque ele nao fica dentro do motor

### `prototypes/`

Status:

1. `laboratorio`

Papel:

1. guardar exemplos leves
2. testar ideias isoladas
3. permitir copia controlada para o produto quando fizer sentido

Regra:

1. manter isolado
2. nao promover nada daqui para verdade oficial sem integracao deliberada
3. remover apenas prototipos mortos, quebrados ou redundantes

Traducao pratica:

1. `prototypes/` e bancada de oficina
2. voce pode aprender ali e ate reaproveitar pecas
3. mas nao deve fingir que a bancada e a pista principal

### `docs/diagnostics/archive/`

Status:

1. `arquivo`

Papel:

1. guardar diagnosticos envelhecidos que ainda tem valor de contexto

Regra:

1. nao usar como autoridade primaria
2. consultar so quando a pergunta for historica ou comparativa

### `docs/experience/archive/`

Status:

1. `arquivo`

Papel:

1. guardar rodadas antigas de validacao e snapshots de UX

Regra:

1. manter fora da rota principal
2. preservar apenas o que ainda ajuda em comparacao, auditoria ou memoria operacional

### `docs/history/`

Status:

1. `arquivo`

Papel:

1. registrar retrospectiva e contexto de fases anteriores

Regra:

1. manter como memoria
2. nunca tratar como regra viva por si so

### `docs/reports/`

Status:

1. `apoio`

Papel:

1. snapshots analiticos
2. relatorios situacionais

Regra:

1. manter quando ajudarem a tomada de decisao
2. arquivar quando envelhecerem
3. nao competir com docs canonicos de arquitetura, plano ou rollout

### `docs/security/`

Status:

1. `apoio`

Papel:

1. relatorios e leituras de postura defensiva

Regra:

1. manter quando houver valor tecnico ou forense
2. tratar relatorio pontual como fotografia de momento, nao como baseline eterna

### `docs/tickets/`

Status:

1. `apoio` com potencial de promocao

Papel:

1. propostas focadas
2. recortes de problema e solucao

Regra:

1. manter quando o ticket ainda orientar implementacao futura
2. promover para `docs/plans/` ou `docs/reference/` se virar trilho oficial

## Decisao atual sobre limpeza

### Manter

1. `prompts/`
2. `prototypes/`
3. `docs/tickets/`

### Manter isolado

1. `prototypes/`
2. `docs/history/`
3. `docs/diagnostics/archive/`
4. `docs/experience/archive/`

### Arquivar quando envelhecer

1. `docs/reports/`
2. `docs/security/`

## Teste rapido para decidir o destino de uma pasta

Pergunte:

1. isso participa do runtime ou do deploy do produto
2. isso governa a execucao atual
3. isso so ajuda a pensar, aprender, comparar ou reaproveitar
4. isso ja virou fotografia de um momento antigo

Se a resposta for:

1. produto vivo -> canonico
2. ajuda sem governar -> apoio
3. experimento isolado -> laboratorio
4. foto historica -> arquivo

## Decisao oficial desta rodada

1. `prompts/` fica
2. `prototypes/` fica
3. ambos devem permanecer explicitamente fora do runtime principal
4. a proxima limpeza deve mirar duplicacoes internas ou prototipos mortos, nao a existencia dessas zonas
