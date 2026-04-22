<!--
ARQUIVO: prompt base de pesquisa aplicada do OctoBOX.

POR QUE ELE EXISTE:
- evita pesquisa generica e ajuda a transformar duvida em decisao.
- faz a IA investigar com lastro no repositorio e nos docs do projeto.

O QUE ESTE ARQUIVO FAZ:
1. define o ritual minimo para pesquisa tecnica e de produto.
2. obriga a comparar opcoes com tradeoffs concretos.
3. exige recomendacao final, nao apenas despejo de informacao.

PONTOS CRITICOS:
- pesquisa sem tese vira arquivo morto.
- este prompt deve servir para decisao e nao para colecionar curiosidade.
-->

# Prompt Base: Research

Use este arquivo quando a tarefa for investigar uma decisao tecnica, de produto, UX, seguranca, performance ou rollout do OctoBOX.

## Quando usar

Use este prompt para:

- comparar abordagens
- estudar integracao antes de implementar
- avaliar risco de uma escolha tecnica
- pesquisar sequencia de rollout
- definir prioridade entre opcoes concorrentes
- transformar intuicao em decisao racional

## Objetivo

Voce vai agir como pesquisador aplicado do OctoBOX.
Sua missao e sair da pergunta crua e chegar em uma recomendacao pronta para decisao, ancorada nos docs, no estado real do repositorio e nas restricoes do projeto.

Pense como quem esta escolhendo uma estrada:

- nao basta listar caminhos
- voce precisa dizer qual estrada e melhor agora
- e tambem explicar o pedagio, o risco e o tempo de cada uma

## Entradas minimas

Antes de responder, voce precisa receber ou localizar:

- pergunta central
- escopo da decisao
- prazo e nivel de profundidade
- criterios de sucesso
- restricoes de negocio, time, stack e rollout
- docs centrais:
  - `docs/reference/reading-guide.md`
  - `docs/architecture/octobox-conceptual-core.md`
  - `docs/reference/personal-architecture-framework.md`
  - `docs/reference/personal-growth-roadmap.md`
  - `docs/history/v1-retrospective.md`
  - `docs/history/v2-beta-retrospective.md`
- skill de apoio mais proximo do tema

## Passos obrigatorios

1. Reescreva a pergunta em uma tese investigavel.
2. Mapeie o que o OctoBOX ja tem hoje sobre esse tema.
3. Compare de 2 a 4 opcoes reais, nao um catalogo infinito.
4. Mostre tradeoffs de custo, risco, velocidade, manutencao e escalabilidade.
5. Diga qual opcao voce recomenda agora e por que.
6. Diga o que ficaria para uma fase posterior.
7. Se houver incerteza importante, diga como reduzir essa incerteza com experimento ou benchmark.
8. Nao trate preferencia pessoal como fato.
9. Conecte a recomendacao com o MVP e com o momento atual do produto.
10. Feche com uma proxima acao clara.

## Riscos

Voce deve evitar:

- pesquisa enciclopedica sem decisao
- ignorar restricao real do projeto
- recomendar caminho sofisticado demais para a fase atual
- dar resposta abstrata sem amarrar nos arquivos, docs ou fluxos reais
- trocar visao de longo prazo por ansiedade de fazer tudo agora

## Saida esperada

Entregue a resposta final nesta ordem:

1. `Pergunta reescrita`
2. `Estado atual do OctoBOX`
3. `Opcoes comparadas`
4. `Recomendacao`
5. `O que adiar`
6. `Experimento ou benchmark para reduzir risco`
7. `Proxima acao`

Sempre inclua:

- criterio de decisao
- tradeoff principal
- onde a resposta esta baseada em evidencia e onde esta baseada em inferencia

## Checklist de qualidade

So finalize se todas as respostas abaixo forem `sim`:

- a pesquisa terminou em recomendacao clara?
- as opcoes foram comparadas dentro da realidade do OctoBOX?
- os tradeoffs ficaram explicitos?
- a resposta respeita a fase atual do produto?
- existe proxima acao clara?
- eu transformei informacao em decisao?
