<!--
ARQUIVO: inventario curto de regras-ponte visuais do financeiro.

TIPO DE DOCUMENTO:
- inventario operacional de risco visual

AUTORIDADE:
- media para manutencao de CSS local do financeiro

DOCUMENTO PAI:
- [front-legacy-rule-retirement-sdd.md](front-legacy-rule-retirement-sdd.md)

QUANDO USAR:
- quando um board do financeiro parecer fora do padrao mesmo com shell correto
- quando houver suspeita de override escondido, dupla moldura ou divisoria interna
- quando o time precisar decidir se uma regra pode morrer, ser rebaixada ou deve continuar como ponte

POR QUE ELE EXISTE:
- registra as regras pequenas que ainda podem recriar fantasma visual
- reduz debug cego em casos onde o shell parece certo, mas o miolo sabota a composicao
- ajuda a distinguir entre regra intencional e legado perigoso
-->

# Inventario curto de risco visual do financeiro

## Resumo

Este inventario guarda as regras do financeiro que hoje funcionam como **ponte controlada**.

Traducao simples:

1. nao sao bug por si so
2. nao devem ser copiadas para qualquer card
3. podem recriar o efeito de `segunda moldura interna` se forem usadas no lugar errado

## Regras em observacao

### 1. Disclosure da fila

Arquivo:

1. [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)

Regra:

1. `.finance-risk-details`

Motivo do risco:

1. usa `border-top` + `padding-top` para separar o bloco `Ver sinais de apoio`
2. isso e legitimo enquanto continuar sendo disclosure secundario
3. se esse conteudo passar a ficar sempre aberto, pode voltar a parecer uma segunda moldura dentro do card da fila

Status:

1. ponte controlada

### 2. Linha de follow-up em cards de apoio

Arquivo:

1. [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)

Regra:

1. `.finance-followup-line`

Motivo do risco:

1. usa `border-top` + `padding`
2. hoje funciona como separador interno de leitura curta
3. se for reutilizada dentro de hosts que ja tenham divisao propria, pode duplicar moldura visual

Status:

1. ponte controlada

### 3. Meta interna do card de acao

Arquivo:

1. [../../static/css/catalog/finance/_cards.css](../../static/css/catalog/finance/_cards.css)

Regra:

1. `.finance-action-meta-list`

Motivo do risco:

1. usa `padding-top` + `border-top`
2. hoje pertence ao subcard da regua, nao ao shell externo
3. se for promovida para outros cards sem contexto, pode recriar o mesmo erro que existia na fila

Status:

1. ponte controlada

### 4. Acoes do card compacto de plano

Arquivo:

1. [../../static/css/catalog/finance/_cards.css](../../static/css/catalog/finance/_cards.css)

Regra:

1. `.finance-plan-card-compact .actions`

Motivo do risco:

1. usa `margin-top: auto` + `padding-top` + `border-top`
2. e correta dentro do card compacto de plano
3. vira risco quando a mesma solucao e copiada como “atalho” para separar secoes internas de outros cards

Status:

1. ponte controlada

### 5. Camadas largas que podem achatar diferencas

Arquivos:

1. [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)
2. [../../static/css/catalog/finance/_shell.css](../../static/css/catalog/finance/_shell.css)
3. [../../static/css/catalog/finance/_signature.css](../../static/css/catalog/finance/_signature.css)

Motivo do risco:

1. sao camadas de cobertura larga
2. quando muito genericas, podem nivelar diferencas entre `is-rail`, `is-queue` e `is-support`
3. foi exatamente esse tipo de achatamento que mascarou o problema do `queue`

Status:

1. vigiar sempre

## Regra operacional

Antes de criar ou copiar qualquer bloco interno no financeiro, revisar:

1. existe `border-top` + `padding-top` aqui?
2. o host externo ja faz separacao suficiente?
3. a divisao e semantica de disclosure ou e so um remendo visual?
4. isso esta sendo colocado dentro de `finance-board-shell` ou `finance-board-shell-body`?

Se a resposta for “sim” para as duas primeiras perguntas ao mesmo tempo, ha risco de segunda moldura.

## Onde procurar primeiro quando o fantasma voltar

1. [../../templates/includes/catalog/finance/boards/queue_board.html](../../templates/includes/catalog/finance/boards/queue_board.html)
2. [../../templates/includes/catalog/finance/views/priority_rail.html](../../templates/includes/catalog/finance/views/priority_rail.html)
3. [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)
4. [../../static/css/catalog/finance/_cards.css](../../static/css/catalog/finance/_cards.css)
5. [../../static/css/catalog/finance/_signature.css](../../static/css/catalog/finance/_signature.css)
6. [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)
7. [../../static/css/catalog/finance/_shell.css](../../static/css/catalog/finance/_shell.css)
