<!--
ARQUIVO: guia de entrada da biblioteca de prompts do OctoBOX.

POR QUE ELE EXISTE:
- evita que a biblioteca de prompts vire um labirinto.
- mostra em poucos passos qual arquivo usar em cada tipo de tarefa.

O QUE ESTE ARQUIVO FAZ:
1. explica a arquitetura da pasta prompts.
2. mostra o fluxo recomendado de uso no dia a dia.
3. aponta qual prompt, workflow e checklist usar em cada situacao.

PONTOS CRITICOS:
- este README deve continuar simples, operacional e orientado a decisao.
- se ele ficar prolixo, perde a funcao de porta de entrada.
-->

# Biblioteca de Prompts do OctoBOX

Esta pasta existe para transformar intuicao em engenharia.

Em linguagem simples:

- sua ideia crua entra de um lado
- a biblioteca organiza, estrutura e audita
- o prompt final sai do outro lado pronto para execucao

## Mapa rapido

### Base

- [`corda.md`](./corda.md): framework mestre para montar prompts fortes
- [`corda-fast.md`](./corda-fast.md): versao curta para preencher rapido
- [`corda-diagnostico.md`](./corda-diagnostico.md): pre-diagnostico quando a ideia ainda esta nebulosa
- [`mer.md`](./mer.md): medicao, evals e roteamento de modelo e modo
- [`prompt-journal.md`](./prompt-journal.md): diario operacional para registrar uso, custo, acerto, erro e melhoria

### Prompts-base

- [`architecture.md`](./architecture.md): fronteiras, camadas, ownership, escalabilidade
- [`debug.md`](./debug.md): causa raiz, evidencia e correcao minima
- [`refactor.md`](./refactor.md): reorganizacao estrutural sem quebrar comportamento
- [`frontend.md`](./frontend.md): UI, UX, template, CSS, JS, assets
- [`review.md`](./review.md): findings, risco, regressao, seguranca, manutencao
- [`research.md`](./research.md): comparar caminhos e tomar decisoes

### Checklists

- [`checklists/debug-checklist.md`](./checklists/debug-checklist.md)
- [`checklists/refactor-checklist.md`](./checklists/refactor-checklist.md)
- [`checklists/frontend-checklist.md`](./checklists/frontend-checklist.md)
- [`checklists/review-checklist.md`](./checklists/review-checklist.md)
- [`checklists/technical-debt-good-vs-bad.md`](./checklists/technical-debt-good-vs-bad.md)

### Workflows

- [`workflows/genio-sistemas.md`](./workflows/genio-sistemas.md): eficiencia, banco, cache, fila, Celery, snapshot, gargalo
- [`workflows/orquestrador-total.md`](./workflows/orquestrador-total.md): workflow mestre que junta tudo

## Qual arquivo usar primeiro

Use esta regra:

- se sua ideia esta confusa: abra [`workflows/orquestrador-total.md`](./workflows/orquestrador-total.md)
- se sua ideia esta semi-clara: abra [`corda-diagnostico.md`](./corda-diagnostico.md)
- se voce ja sabe o tipo da tarefa: use [`corda-fast.md`](./corda-fast.md)
- se voce quer montar manualmente com precisao: use [`corda.md`](./corda.md)

## Fluxo recomendado no dia a dia

### Fluxo 1: ideia nebulosa

Use quando estiver pensando algo como:

- "acho que preciso mexer em Celery"
- "essa tela esta pesada"
- "nao sei se isso e refator ou arquitetura"

Ordem:

1. [`workflows/orquestrador-total.md`](./workflows/orquestrador-total.md)
2. prompt-base sugerido pela resposta
3. checklist correspondente
4. registro em [`prompt-journal.md`](./prompt-journal.md) se a tarefa for relevante

### Fluxo 2: ideia semi-estruturada

Use quando voce ja souber mais ou menos:

- o fluxo afetado
- os arquivos provaveis
- o que nao pode quebrar

Ordem:

1. [`corda-diagnostico.md`](./corda-diagnostico.md)
2. [`corda-fast.md`](./corda-fast.md)
3. [`corda.md`](./corda.md)
4. prompt-base escolhido
5. checklist correspondente
6. registro em [`prompt-journal.md`](./prompt-journal.md)

### Fluxo 3: tarefa clara e objetiva

Use quando voce ja sabe exatamente o tipo:

- bug -> [`debug.md`](./debug.md)
- refator -> [`refactor.md`](./refactor.md)
- UI/UX -> [`frontend.md`](./frontend.md)
- fronteira/escala -> [`architecture.md`](./architecture.md)
- revisao -> [`review.md`](./review.md)
- decisao/pesquisa -> [`research.md`](./research.md)

Ordem:

1. [`corda-fast.md`](./corda-fast.md)
2. [`corda.md`](./corda.md)
3. prompt-base
4. checklist
5. [`prompt-journal.md`](./prompt-journal.md) se a tarefa ensinar algo reutilizavel

## Como decidir o tipo da tarefa

Use esta heuristica:

- `debug`: algo quebrou, falhou, regrediu ou esta inconsistente
- `refactor`: a estrutura esta ruim, confusa ou acoplada demais
- `frontend`: a experiencia, o layout, o CSS, o JS ou os assets pedem evolucao
- `architecture`: o problema envolve fronteira, ownership, camada ou escalabilidade
- `review`: voce quer avaliar risco, diff, seguranca ou manutencao
- `research`: voce quer comparar caminhos antes de decidir

Se aparecerem palavras como:

- banco
- cache
- Celery
- fila
- snapshot
- latencia
- gargalo

considere tambem o workflow [`genio-sistemas.md`](./workflows/genio-sistemas.md).

## Como escolher modo e modelo

Regra rapida baseada em [`mer.md`](./mer.md):

- tarefa simples e local -> `modelo rapido + Fast`
- bug real, refator grande ou arquitetura -> `modelo forte + Planning`

Se a tarefa tocar em varios arquivos, contrato publico, banco, cache, fila ou seguranca, prefira `Planning`.

## Como fechar o loop de aprendizado

Depois de uma tarefa relevante, use [`prompt-journal.md`](./prompt-journal.md).

Ele serve para:

- registrar qual workflow e prompt-base voce usou
- anotar se acertou de primeira ou nao
- medir custo, tempo e numero de rodadas
- transformar erro em guardrail
- transformar acerto em padrao reutilizavel

Regra pratica:

- tarefa pequena demais: nao precisa registrar
- tarefa importante, cara, dificil ou repetivel: registre

## Exemplo pratico

Quero refatorar a pagina de financas.

Fluxo recomendado:

1. abrir [`corda-fast.md`](./corda-fast.md)
2. preencher tarefa, fluxo, arquivos, restricoes
3. gerar o `C.O.R.D.A`
4. combinar com [`refactor.md`](./refactor.md)
5. validar com [`checklists/refactor-checklist.md`](./checklists/refactor-checklist.md)
6. se tocar em UX e assets, cruzar tambem com [`frontend.md`](./frontend.md)

Quero mexer em Celery, cache e banco, mas nao sei o problema real.

Fluxo recomendado:

1. abrir [`workflows/orquestrador-total.md`](./workflows/orquestrador-total.md)
2. deixar o workflow classificar o problema
3. se houver eficiencia, aplicar [`workflows/genio-sistemas.md`](./workflows/genio-sistemas.md)
4. so depois montar o prompt final

## Regra de ouro

Nao comece pela resposta.
Comece pelo trilho.

Prompt forte no OctoBOX funciona assim:

- contexto primeiro
- objetivo claro depois
- restricao explicita
- definition of done concreta
- auditoria forte

Isso e o que impede a IA de soar inteligente e ainda assim trabalhar no lugar errado.

## Sequencia minima para quase tudo

Se voce quiser decorar uma unica receita, decore esta:

1. ideia crua -> [`workflows/orquestrador-total.md`](./workflows/orquestrador-total.md)
2. estrutura -> [`corda.md`](./corda.md)
3. especializacao -> prompt-base certo
4. validacao -> checklist certo
5. aprendizado -> registrar em [`prompt-journal.md`](./prompt-journal.md) e atualizar uso com base em [`mer.md`](./mer.md)

## O que nao fazer

- nao pular direto para um prompt-base sem contexto
- nao usar Celery, cache ou arquitetura como palavras magicas
- nao confiar em resposta bonita sem auditoria
- nao tratar tarefa grande como se fosse tarefa local
- nao ampliar escopo cedo demais

## Objetivo final desta biblioteca

Fazer voce sair do modo:

- "vou pedir ajuda para a IA"

e entrar no modo:

- "vou orquestrar a IA dentro de um sistema"
