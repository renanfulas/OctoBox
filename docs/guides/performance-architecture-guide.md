<!--
ARQUIVO: guia de performance viva do OctoBox.

TIPO DE DOCUMENTO:
- guia de performance

AUTORIDADE:
- media para orientacao de performance

DOCUMENTO PAI:
- [README.md](./README.md)

DOCUMENTOS IRMAOS:
- [../plans/front-end-performance-master-plan.md](../plans/front-end-performance-master-plan.md)
- [../reference/reading-guide.md](../reference/reading-guide.md)
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
-->

# Guia de performance

## Tese atual

A performance do OctoBox hoje esta mais madura porque deixou de ser tratada como "depois a gente deixa rapido".

Ela passou a ser tratada como parte da arquitetura.

Em linguagem simples:

1. nao basta o carro ser bonito
2. ele precisa responder na hora que voce pisa

## O que ficou mais eficiente desde o inicio

### 1. Telemetria real

Hoje o projeto ja possui instrumentos que melhoram a conversa sobre performance:

1. `RequestTimingMiddleware` publica `Server-Timing`
2. middleware Prometheus expoe contadores e latencia
3. probes de pagina publicada ajudam a medir experiencia real
4. commits recentes otimizaram batch de snapshot e parsing de timing

### 2. Performance de shell e request

O runtime ficou mais eficiente porque:

1. custo de auth e shell pode ser observado
2. sessao esta orientada a cache
3. cache Redis e tratada como parte importante da operacao
4. leituras pesadas ganharam mais visibilidade e throttling por escopo

### 3. Performance de tela

No frontend, a maturidade subiu porque:

1. assets criticos e diferidos passaram a ser declarados
2. o projeto passou a medir excesso de CSS e custo de shell
3. existe plano explicito para LCP, INP, busca global e visuals dinamicos

### 4. Performance de query e snapshot

O backend ficou mais eficiente em frentes recentes porque:

1. listagens de alunos foram otimizadas
2. snapshot financeiro recebeu batching melhor
3. timing de snapshot e probes foi refinado

## Regra correta de performance hoje

1. medir antes de cortar
2. cortar primeiro o que esta no caminho critico
3. preservar a identidade visual premium sem pagar tudo no primeiro paint
4. preferir contratos pequenos, leitura pronta e menos travessias

## Lugares que concentram a maturidade atual

1. `shared_support/request_timing_middleware.py`
2. `monitoring/prometheus_middleware.py`
3. `shared_support/page_payloads.py`
4. `catalog/presentation/*`
5. `catalog/finance_snapshot/*`
6. `docs/plans/front-end-performance-master-plan.md`

## O que nao devemos fazer

1. otimizar com base em intuicao apenas
2. reduzir bytes e piorar ownership
3. quebrar assinatura premium para ganhar numero bonito artificial
4. inflar backend com duplicacao de UI
5. deixar query pesada escondida dentro de montagem de tela

## Budgets mentais simples

Antes de aprovar uma mudanca, pergunte:

1. isso reduziu travessia, bytes, query ou custo de pintura?
2. isso ficou medivel?
3. isso manteve ownership claro?
4. isso preservou experiencia percebida?

Se a resposta for nao para um desses pontos, a "otimizacao" pode estar comprando debito tecnico.

## O que ainda pede cuidado

1. carga ampla de CSS em algumas telas centrais
2. convivencia entre CSS historico e design system novo
3. risco de enhancement virar dependencia inicial sem necessidade
4. risco de presenter crescer demais e carregar leitura que deveria estar em query dedicada

## Resumo do ganho de maturidade

O ganho principal de performance nao foi so "ficou mais rapido".

Foi isto:

1. o projeto mede melhor
2. localiza melhor
3. otimiza com mais contexto
4. e consegue discutir latencia como arquitetura, nao como supersticao
