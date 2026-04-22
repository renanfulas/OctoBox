# Financial Residual Dead-Code Retirement C.O.R.D.A.

**Status**: Approved
**Created On**: 2026-03-30
**Approved On**: 2026-03-30
**Decision**: Official north star for the detached financial residual retirement pass

## Contexto

O OctoBOX ja resolveu a parte viva do residual financeiro:

1. a topbar contextual saiu de `elite-*`
2. o CSS vivo saiu de `--elite-*`
3. o trilho operacional agora fala a lingua canonica

Mas ainda existe um bloco legado em [financial.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/financial.css) com naming `elite-*` que, pela vistoria atual, parece desacoplado do runtime principal.

Em linguagem simples:

- a central de comando nova ja esta ligada
- agora estamos olhando as caixas antigas no deposito para decidir o que vai para descarte e o que ainda pode estar ligado a alguma sala esquecida

## Objetivo

Confirmar e aposentar com seguranca o bloco residual desacoplado do design-system financeiro.

Objetivo operacional:

1. provar se o bloco residual esta morto ou apenas oculto
2. remover com seguranca o que nao alimenta mais o runtime real
3. registrar o que foi retirado e o que, por cautela, precisa ficar para outra passada

## Riscos

### 1. Risco de apagar algo que ainda alimenta uma tela rara

Classe residual nao significa automaticamente codigo morto.
Pode ser:

1. template pouco usado
2. caminho raro de role
3. include esquecido

### 2. Risco de manter lixo por medo

Se a evidencia for suficiente e mesmo assim deixarmos tudo, a base continua carregando ruido desnecessario.

### 3. Risco de misturar limpeza com redesign

Esta fase e aposentadoria de bloco.
Nao e reforma estetica.

## Direcao

### Regra-mestra

**So remover depois de provar que o bloco esta desacoplado do runtime real.**

Se a evidencia mostrar que ele ainda respira:

1. nao deletar
2. reclassificar
3. abrir uma nova montanha de migracao controlada

Se a evidencia mostrar que ele morreu:

1. retirar
2. validar
3. registrar a aposentadoria

## Acoes

## Onda 1. Prova de vida do bloco residual

Objetivo:
mapear referencias reais ou provar ausencia de uso.

## Onda 2. Classificacao de risco

Objetivo:
separar o que pode sair agora do que precisa de adiamento seguro.

## Onda 3. Aposentadoria controlada

Objetivo:
remover o bloco morto e manter o runtime estavel.

## Onda 4. Laudo final

Objetivo:
documentar o que foi enterrado e o que ainda merece radar.
