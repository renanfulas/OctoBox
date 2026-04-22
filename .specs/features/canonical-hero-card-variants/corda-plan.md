# Canonical Hero Card Variants C.O.R.D.A.

**Status**: Approved
**Created On**: 2026-04-03
**Decision**: Official north star for the canonical hero and card variants architecture

## Contexto

O endurecimento recente de dark mode provou uma coisa importante:

1. trocar tokens ajuda
2. endurecer os hosts ajuda
3. mas, sem variantes oficiais, os arquivos locais continuam tentando repintar `hero`, `card` e `table-card`

As superficies mais sensiveis ja mostraram esse padrao:

1. dashboard
2. financeiro
3. owner
4. whatsapp placeholder

Em linguagem simples:

- hoje a tinta principal melhorou
- mas cada comodo ainda guarda um pincel escondido
- precisamos tirar esses pinceis soltos e entregar caixas oficiais de acabamento

## Objetivo

Definir e implementar uma arquitetura onde:

1. `hero` e a autoridade estrutural dos heroes
2. `card` e `table-card` sao as autoridades estruturais dos cards
3. variacoes visuais acontecem por variantes oficiais e custom properties
4. CSS local cuida de layout e composicao, nao de identidade base

## Restricoes

1. nao transformar isso em redesign completo
2. nao reescrever o produto inteiro de uma vez
3. nao permitir que cada pagina invente sua propria familia visual de novo
4. preservar contratos atuais de markup sempre que possivel
5. migrar em ondas, começando pelas superficies com maior retorno

## Definition of Done

O trabalho estara pronto quando:

1. existir contrato claro para variantes de `hero`, `card` e `table-card`
2. os hosts canonicos aceitarem tuning por variaveis sem exigir repaint local
3. `dashboard`, `financeiro` e `owner` tiverem pelo menos uma migracao inicial para variantes oficiais
4. o guia de CSS registrar que arquivos locais nao podem redefinir container visual base
5. ficar mais barato ajustar uma familia visual do que perseguir overrides isolados

## Auditoria

1. citar arquivos que hoje repintam os hosts
2. separar ownership de tokens, host canonico, variantes e CSS local
3. registrar riscos de regressao e risco de exagerar no escopo
4. validar com smoke basico nas superficies migradas

## Direcao

### Regra-mestra

**Toda familia visual compartilhada deve nascer do host canonico e variar por knobs oficiais, nunca por repaint local repetido.**

### Norte tecnico

1. `tokens.css` continua definindo a tinta
2. `hero.css` e `cards.css` definem a engenharia base
3. novos arquivos de variantes definem personalidades oficiais
4. CSS local passa a usar classes e variaveis oficiais

### Norte operacional

1. ajustar um hero deve repercutir em outros heroes da mesma familia
2. ajustar um card de support, priority ou command deve repercutir nas telas que usam essa variante
3. novas telas devem nascer com composicao, nao com mini design system proprio

## Ondas

### Onda 1. Definir o contrato

Objetivo:
mapear o que e host, o que e variante e o que e override indevido.

### Onda 2. Criar a arquitetura de variantes

Objetivo:
introduzir variantes oficiais para `hero`, `card` e `table-card`.

### Onda 3. Migrar as primeiras superficies

Objetivo:
validar a arquitetura em `dashboard`, `financeiro` e `owner`.

### Onda 4. Endurecer a governanca

Objetivo:
registrar no guide de CSS que repaint local de host canonico nao e mais aceito.
