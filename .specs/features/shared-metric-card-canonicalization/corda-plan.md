# Shared Metric Card Canonicalization C.O.R.D.A.

**Status**: Approved
**Created On**: 2026-03-30
**Approved On**: 2026-03-30
**Decision**: Official north star for the shared metric card canonicalization pass

## Contexto

O tema canonico ja foi consolidado e as grandes ilhas residuais ja foram limpas.

Mas a vistoria curta mostrou que o componente compartilhado de metrica ainda fala um dialeto antigo:

1. [metric_card.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/ui/shared/metric_card.html) ainda usa `glass-panel-elite`

Como esse componente e compartilhado, ele tem efeito cascata em varias superficies.

Em linguagem simples:

- nao estamos mexendo num quarto
- estamos mexendo no molde usado para fabricar varias portas

## Objetivo

Absorver o shared metric card no sistema canonico sem perder:

1. legibilidade de metrica
2. hierarquia de valor e variacao
3. sensacao premium controlada
4. previsibilidade de manutencao

## Riscos

### 1. Risco de respingar em varias telas

Por ser compartilhado, um ajuste errado pode piorar:

1. dashboard
2. alunos
3. financeiro
4. qualquer area que reuse esse card

### 2. Risco de achatar o componente

Se removermos o legado errado, o card pode perder presenca e ficar generico demais.

### 3. Risco de mover ownership para o lugar errado

O card precisa obedecer o sistema canonico. Nao pode virar mini sistema local de novo.

## Direcao

### Regra-mestra

**O shared metric card deve nascer do host canonico e usar o legado premium apenas como acabamento permitido, nunca como base estrutural.**

### Norte visual

1. dark premium aberto
2. leitura forte de numero
3. contraste e sparkline legiveis
4. sem cara de componente de outra epoca

### Norte tecnico

1. retirar `glass-panel-elite` do host
2. manter semantica de `metric-card` clara
3. localizar o CSS no ownership certo
4. preservar contratos de link, action, footer e sparkline

## Acoes

## Onda 1. Mapear uso e ownership real

Objetivo:
entender onde o componente e usado e quem estiliza suas partes mais importantes.

## Onda 2. Canonizar o host do componente

Objetivo:
trocar o envelope estrutural legado pelo host correto.

## Onda 3. Ajustar acabamento e verificar continuidade

Objetivo:
manter o premium como acento controlado e validar o componente em contexto.
