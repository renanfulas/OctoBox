# Reception Action Surface Hardening C.O.R.D.A.

**Status**: Approved
**Created On**: 2026-03-30
**Approved On**: 2026-03-30
**Decision**: Official north star for the reception payment action hardening pass

## Contexto

Depois da grande limpeza visual, a recepcao ainda guarda uma superficie viva que mistura responsabilidades demais em um unico template:

1. [reception_payment_card.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/includes/reception/reception_payment_card.html)

Hoje essa peca mistura:

1. layout
2. inline styles
3. comportamento em `onclick`
4. `fetch(...)`
5. abertura de WhatsApp
6. copy transacional embutida no HTML

Em linguagem simples:

- a fachada da loja ja esta bonita
- mas no caixa ainda tem fita, bilhete colado e uma tomada improvisada atras do monitor

## Objetivo

Fortalecer a superficie de acao de pagamento da recepcao sem quebrar o fluxo operacional real.

Objetivo operacional:

1. retirar inline debt dominante
2. separar markup, estilo e comportamento
3. preservar o fluxo de confirmacao, bloqueio e mensagem de WhatsApp
4. deixar a peca mais clara, segura e evolutiva

## Riscos

### 1. Risco de quebrar uma superficie operacional viva

Essa peca toca:

1. pagamento
2. bloqueio por papel
3. comunicacao
4. follow-up de cobranca

### 2. Risco de piorar UX de balcao

Se endurecermos demais, a recepcao pode perder velocidade.

### 3. Risco de mover JS para o lugar errado

O comportamento precisa ir para uma casa melhor, mas sem virar labirinto tecnico.

## Direcao

### Regra-mestra

**Separar apresentacao, comportamento e copy operacional sem perder agilidade de uso.**

### Norte visual

1. leitura de balcao clara
2. acoes previsiveis
3. bloqueios explicitos sem parecer gambiarra

### Norte tecnico

1. sair de `onclick` inline
2. reduzir `style=` dominantes
3. manter o fluxo de WhatsApp e auditoria operacional intactos

## Acoes

## Onda 1. Mapear comportamento e acoplamento

Objetivo:
entender tudo que o card faz hoje e do que ele depende.

## Onda 2. Extrair comportamento vivo

Objetivo:
tirar JS inline do HTML e mover para camada apropriada.

## Onda 3. Limpar superficie visual

Objetivo:
retirar inline style dominante e deixar o card com ownership claro.

## Onda 4. Validar o fluxo de balcao

Objetivo:
confirmar que confirmacao, bloqueio e WhatsApp continuam confiaveis.
