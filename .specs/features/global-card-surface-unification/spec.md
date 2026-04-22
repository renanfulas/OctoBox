# SDD — Global Card Surface Unification

## Contexto

O OctoBox ja possui uma familia base de cards (`.card`, `.table-card`, `.metric-card`, `.quick-card`) definida no design system, mas a aparencia real dos cards foi se fragmentando por dominio.

Hoje a base convive com:

- cards canonicos no design system
- variantes locais por cena
- overrides contextuais em dark mode
- herancas via `--legacy-panel-*`
- zonas com `!important`
- componentes que parecem cards, mas nao nascem da familia canonica

Resultado:

- a aparencia muda de tela para tela
- a direcao visual premium nao escala de forma previsivel
- trocar tudo "de uma vez" direto no CSS base pode quebrar cenas inteiras
- existe debito tecnico visual escondido na cascata

Em metafora simples:

o sistema ja tem um molde oficial de pecas, mas cada bairro da cidade ainda fabrica suas portas e janelas num tamanho proprio.

## Objetivo

Fazer os cards do OctoBox nascerem com a mesma linguagem visual **Apple + Cyberpunk premium** em todo o produto, sem depender de repaint local improvisado.

O objetivo nao e apenas trocar a cor dos cards.
O objetivo e:

- unificar a fundacao visual dos cards
- reduzir overrides escondidos
- identificar onde a migracao global e segura
- identificar onde a troca direta e arriscada e exige refactor estrutural

## Nao objetivos

- redesenhar cada tela manualmente uma por uma sem contrato sistemico
- mexer em layout ou comportamento de negocio sem necessidade
- perseguir pixel-perfect por pagina antes da fundacao estar pronta
- reescrever todos os dominios em um unico PR cego

## Leitura atual do sistema

### Autoridade visual atual dos cards

Base canonica:

- `static/css/design-system/components/cards.css`
- `static/css/design-system/components/card-variants.css`
- `static/css/design-system/components/quick-cards.css`

Base auxiliar que interfere:

- `static/css/design-system/workspace.css`
- `static/css/design-system/operations/core.css`
- `static/css/design-system/neon.css`
- `static/css/design-system/spacing.css`

Dominios com forte customizacao local:

- `static/css/catalog/class-grid/*.css`
- `static/css/catalog/finance_*.css`
- `static/css/catalog/shared/student-financial.css`
- `static/css/onboarding/intakes.css`
- `static/css/design-system/operations/owner/notion/*.css`
- `static/css/design-system/operations/refinements/*.css`

### Causa raiz

Os cards nao falham porque falta um estilo bonito.
Eles falham porque a base canonica existe, mas nao e a autoridade final em runtime.

A autoridade visual esta distribuida entre:

1. familia base de cards
2. aliases `--legacy-panel-*`
3. variantes de cena
4. overrides locais em dark mode
5. arquivos com `!important`

Isso cria um sistema onde o card:

- nasce de um jeito
- cresce de outro
- recebe maquiagem local depois

## Evidencias do Master Debugger

### 1. O berco canonico existe

Arquivo:

- `static/css/design-system/components/cards.css`

Evidencia:

- `.card, .table-card` ja definem border, radius, background, glow e hover base
- `.metric-card` ja tem contrato proprio de superficie e pseudo-elementos

Diagnostico:

- a base nao esta ausente
- ela esta sendo contornada

### 2. Existem overrides locais com `!important`

Arquivos com sinais fortes:

- `static/css/catalog/class-grid/workspace.css`
- `static/css/catalog/class-grid/calendar.css`
- `static/css/catalog/finance/_cards.css`
- `static/css/catalog/finance/_metrics.css`
- `static/css/catalog/shared/student-financial.css`
- `static/css/catalog/student_form_stepper.css`

Diagnostico:

- a presenca de `!important` em superficies de card indica que a hierarquia visual atual nao consegue vencer por contrato
- isso e sinal de guerra de especificidade

### 3. O legado ainda manda pela fundacao

Arquivo:

- `static/css/design-system/tokens.css`

Evidencia:

- `--legacy-panel-surface`
- `--legacy-panel-surface-strong`
- `--legacy-panel-border`
- `--legacy-panel-shadow`

Diagnostico:

- hoje o "legado" nao e apenas compatibilidade
- ele ainda e canal de alimentacao visual de varias telas

### 4. Dark mode reaplica cartas locais por contexto

Arquivos com sinais fortes:

- `static/css/catalog/class-grid/workspace.css`
- `static/css/catalog/class-grid/scene.css`
- `static/css/catalog/finance/_dark.css`
- `static/css/design-system/components/dashboard/metrics.css`
- `static/css/onboarding/intakes.css`

Diagnostico:

- varias cenas nao confiam que os textos e superficies herdarao certo
- por isso reescrevem `.card-title`, `.card-copy`, `.table-card` e afins por contexto

### 5. Ha dominos que ainda nascem fora da familia canonica

Exemplos:

- `student-financial-*`
- varios paineis de `owner notion`
- alguns cards do `class-grid`

Diagnostico:

- trocar tudo so na base nao resolve os componentes que fingem ser card sem usar o contrato de card

## Tese arquitetural

Nao devemos simplesmente "trocar tudo de uma vez" em `cards.css` e torcer.

A estrategia correta e:

1. criar o novo **Card Surface 2050 Premium** como autoridade oficial do design system
2. mapear quais superficies ja obedecem a esse host
3. separar os dominios em:
   - migracao direta
   - migracao com adaptador
   - refactor estrutural
4. reduzir o peso de `--legacy-panel-*` ate ele virar apenas ponte de compatibilidade

## Arquitetura alvo

### 1. Card host unico

Nova autoridade principal:

- `static/css/design-system/components/cards.css`

O host deve definir:

- surface
- border
- glow
- hover
- focus
- pseudo-elementos
- dark mode nativo

### 2. Variantes como knobs, nao repaints

Arquivo-alvo:

- `static/css/design-system/components/card-variants.css`

As variantes devem apenas ajustar:

- intensidade
- acento
- profundidade
- prioridade
- rail/support/focus/critical

Sem redefinir o conceito inteiro de card.

### 3. Adaptadores temporarios por dominio

Dominios como:

- `class-grid`
- `student-financial`
- `finance boards`
- `owner notion`

podem receber classes ponte como:

- `.card-surface--premium`
- `.card-surface--premium-rail`
- `.card-surface--premium-focus`
- `.card-surface--premium-sci-fi`

para reduzir repaint local durante a transicao.

### 4. Reestruturacao onde o card nao nasce como card

Para componentes que sao "cards falsos", a frente deve trocar:

- container legado customizado

por:

- host canonico + variante oficial + elementos internos locais

## Classificacao de migracao

### Grupo A — migracao direta

Pode migrar quase so pela base:

- cards gerais do dashboard
- metric cards compartilhados
- quick cards
- info cards simples
- cards de onboarding que ja usam `.card` ou `.table-card`

### Grupo B — migracao com adaptador

Precisa de ponte local curta:

- `class-grid`
- boards financeiros do catalogo
- cards de reception e manager
- rails de owner simple

### Grupo C — refactor estrutural antes de migrar

Nao deve receber repaint global puro:

- `student-financial-*`
- `owner notion`
- alguns paineis de `operations/refinements/display-wall.css`
- cards que dependem fortemente de `legacy-panel-*` + dark-mode local + `!important`

## Plano CORDA por ondas

### Onda 1 — Fundacao canonica

Objetivo:

- criar a nova linguagem global em `cards.css` e `card-variants.css`

Entra:

- surface premium oficial
- pseudo-elementos oficiais
- hover/focus oficiais
- dark mode oficial
- tokens novos se necessario

Nao entra:

- repaint manual em todos os dominios

Risco:

- regressao visual difusa

Fix:

- introduzir via novos custom properties e fallback seguro

### Onda 2 — Adaptadores de alta cobertura

Objetivo:

- conectar o maior numero de cards existentes ao novo host sem refactor profundo

Entra:

- dashboard
- onboarding
- finance cards que ja usam `.card`/`.table-card`
- class-grid de contexto e workspace

Risco:

- overrides locais anularem a nova base

Fix:

- mapear e remover overrides redundantes por cena

### Onda 3 — Refactor dos falsos cards

Objetivo:

- fazer componentes locais nascerem no contrato oficial

Entra:

- `student-financial-*`
- `owner notion`
- pontos de `display-wall`

Risco:

- telas premium antigas quebrarem o equilibrio

Fix:

- migrar componente por componente, nao por arquivo inteiro cego

### Onda 4 — Aposentadoria de legado visual

Objetivo:

- reduzir `--legacy-panel-*` a compatibilidade residual

Entra:

- troca progressiva de referencias para tokens premium
- remocao de overrides redundantes
- documentacao da nova autoridade

Risco:

- dependencia escondida em dark mode

Fix:

- auditoria final de `body[data-theme=\"dark\"]` e `!important`

## Riscos principais

### Risco 1 — Trocar tudo de uma vez e quebrar dominos premium locais

Por que existe:

- varias telas ja tem acabamento proprio e nao obedecem so ao host base

Mitigacao:

- trocar em ondas com classificacao A/B/C

### Risco 2 — Regressao silenciosa em dark mode

Por que existe:

- muitos contextos ainda reescrevem titulos/copys dos cards

Mitigacao:

- auditar overrides de dark mode antes da troca global

### Risco 3 — A base nova virar mais uma camada em cima do caos

Por que existe:

- se o host novo entrar sem remover adaptacoes locais, teremos duas arquiteturas de card ao mesmo tempo

Mitigacao:

- toda onda precisa remover algo antigo, nao so adicionar novo

## Limite maximo de output

- 800 palavras por update operacional

Formato de update:

- `Status`
- `Foco`
- `Decisao central`
- `Principal risco`
- `Proximo passo`

## Criterio de sucesso

A frente sera sucesso quando:

- a familia canonica de cards virar a autoridade real do produto
- dark mode nao depender de repaints espalhados para manter contraste
- dominios novos puderem nascer premium sem CSS local excessivo
- o numero de overrides com `!important` em superficies de card cair de forma mensuravel
- `--legacy-panel-*` deixar de ser muleta estrutural e virar so compatibilidade residual

## Success Verdict

Se tentarmos trocar tudo agora sem esse mapa, o risco de regressao e alto.
Se seguirmos este plano, conseguimos trocar a cidade inteira de uniforme sem arrancar a pele junto.

Decisao recomendada:

- **sim**, perseguir a troca global
- **nao**, fazer isso como repaint cego
- **sim**, preparar a base para que os proximos cards ja nascam no padrao novo
