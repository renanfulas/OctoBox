# Canonical Theme Unification C.O.R.D.A.

**Status**: Approved
**Approved On**: 2026-03-30
**Decision**: Official north star for the final theme normalization phase

## Contexto

O OctoBOX nao sofre por falta de talento visual. Ele sofre por excesso de autores validos convivendo ao mesmo tempo.

Hoje o tema real do produto nasce da sobreposicao de varias ondas:

1. base original do design system
2. passe de consistencia SaaS
3. passe Front Display Wall
4. patches locais por tela

Isso gerou valor, mas tambem gerou fragmentacao.

Na pratica, banners, cards, hero e topbar nao parecem errados de forma isolada. Eles parecem escritos por dialetos diferentes da mesma lingua.

Em linguagem simples:

- a casa tem boas paredes
- mas cada pintor trouxe um balde de tinta diferente
- agora precisamos de um pintor-chefe definitivo para uniformizar a casa inteira

## Objetivo

Criar uma unica autoridade visual canonica para o OctoBOX.

Essa autoridade final precisa:

1. definir o tema-base de todo o produto
2. unificar tokens, surfaces, cards, banners, hero e topbar
3. transformar os quatro pintores anteriores em referencia, nao em autoridade viva
4. reduzir conflito de cascata, inconsistencias de classe e dialetos visuais concorrentes
5. servir como base para tudo que vier depois

Direcao estetica consolidada:

1. dark premium
2. aberto e respiravel
3. elegante sem parecer fechado
4. editavel sem reabrir o sistema inteiro

## Riscos

### 1. Risco de continuar com varios pintores ativos

Se deixarmos tudo como esta, cada melhoria local vai continuar produzindo mais fragmentacao global.

### 2. Risco de reescrever demais

Se tentarmos redesenhar o app inteiro de uma vez, abriremos uma obra maior do que o necessario.

### 3. Risco de criar um novo tema abstrato demais

Se o novo pintor ignorar o que ja funciona no produto, ele vira uma teoria bonita e uma pratica fraca.

### 4. Risco de manter alias de legado para sempre

Alias temporario e ponte.
Alias permanente vira cidade improvisada.

### 5. Risco de quebrar telas ao atacar a raiz

Tokens, card-base, hero e topbar sao estruturas de fundacao. Migracao sem mapa pode causar regressao ampla.

## Direcao

### Regra-mestra

**Um unico pintor definitivo, varias referencias historicas, zero autoridades concorrentes.**

### Norte tecnico

1. eleger uma autoridade canonica por familia visual
2. mover utilitarios e classes antigas para papel de alias ou legado
3. impedir redefinicoes competitivas de card, hero, banner e topbar em varios lugares
4. migrar por familia e autoridade, nao por arquivo aleatorio
5. transformar a referencia visual em tokens e primitivas, nao em screenshot CSS

### Eleicao ja consolidada

1. `tokens.css` segue como casa oficial dos tokens semanticos
2. `.card` vira a superficie canonica principal
3. `.table-card` vira variante estrutural da mesma familia
4. `.hero` segue como hero canonico
5. `notice-panel family` vira o alvo oficial para notices e banners
6. `.topbar` segue viva, mas perde soberania paralela e passa a obedecer o tema-base

### Norte visual

1. fundo escuro em azul-marinho profundo, nao preto absoluto
2. surfaces premium com translucidez leve e contraste legivel
3. bordas suaves com brilho controlado
4. glow atmosferico, nao neon berrado
5. CTA com acento quente bem dosado
6. containers que respiram, sem truncar a interface

### Norte de produto

O usuario deve sentir que o app inteiro pertence ao mesmo predio visual.

Quando ele navegar entre telas, deve haver continuidade de:

1. peso visual
2. ritmo
3. elevacao
4. temperatura
5. confianca

## Acoes

## Onda 1. Inventario e Eleicao do Pintor Final

Objetivo:
mapear as familias ativas e escolher a autoridade canonica de cada uma.

Inclui:

1. inventariar as classes-base concorrentes
2. mapear conflitos de tokens, surfaces, hero e topbar
3. definir o novo contrato canonico por familia
4. criar a matriz `canonical / alias / migrate / remove`

## Onda 2. Fundacao do Tema Canonico

Objetivo:
fazer o pintor final existir nas estruturas centrais.

Inclui:

1. consolidar tokens semanticos
2. consolidar card-base e surface-base
3. consolidar hero-base
4. fazer a topbar consumir o tema, nao competir com ele

## Onda 3. Normalizacao dos Componentes de Fachada

Objetivo:
levar o tema canonico para notices, banners, quick actions e estados de superficie.

Inclui:

1. banners e notices
2. pills e micro-estados
3. cabecalhos de acao
4. blocos de destaque e contexto

## Onda 4. Migracao das Superficies Centrais

Objetivo:
aplicar o pintor final nas telas que mais definem a experiencia do produto.

Inclui:

1. `students`
2. `finance`
3. `dashboard`
4. `reports-hub`
5. topbar e shell global

## Onda 5. Aposentadoria do Legado Concorrente

Objetivo:
desligar as autoridades antigas e travar novas divergencias.

Inclui:

1. reduzir `!important`
2. aposentar classes concorrentes
3. documentar o contrato final
4. bloquear novos dialetos fora do tema-base

## Prioridade de Execucao

1. Onda 1 - Inventario e Eleicao do Pintor Final
2. Onda 2 - Fundacao do Tema Canonico
3. Onda 3 - Normalizacao dos Componentes de Fachada
4. Onda 4 - Migracao das Superficies Centrais
5. Onda 5 - Aposentadoria do Legado Concorrente
