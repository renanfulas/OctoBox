<!--
ARQUIVO: guia de arquitetura CSS viva do OctoBox.

TIPO DE DOCUMENTO:
- guia de CSS

AUTORIDADE:
- media para organizacao pratica de CSS

DOCUMENTO PAI:
- [README.md](./README.md)

DOCUMENTOS IRMAOS:
- [../reference/front-end-octobox-organization-standard.md](../reference/front-end-octobox-organization-standard.md)
- [../reference/front-end-city-map.md](../reference/front-end-city-map.md)
- [../experience/css-guide.md](../experience/css-guide.md)
-->

# Guia de arquitetura CSS

## Tese CSS atual

O CSS do OctoBox ficou mais eficiente quando deixou de ser apenas "estilo por tela" e passou a ser lido em camadas.

Hoje a ordem correta e:

1. tokens e DNA global
2. componentes compartilhados
3. manifestos de superficie
4. sub-superficies por persona ou dominio
5. modulo local da feature

## O que melhorou em relacao ao inicio

No comeco, a prioridade era acertar a operacao e a aparencia util.

Agora o CSS esta mais maduro porque:

1. existe design system em `static/css/design-system/*`
2. existem manifestos como `operations.css`, `dashboard.css` e `financial.css`
3. existem camadas por persona, como `operations/dev-coach/*`, `operations/manager/*`, `operations/reception/*`
4. ainda existe CSS historico de `catalog/*`, mas ele ja pode ser lido com ownership e estrategia melhores

## Regra de ouro

`global antes de local, shell antes de excecao, split apenas quando a anatomia realmente mudou`

Em linguagem de crianca:

1. se a tinta mudou na casa toda, mexa na lata de tinta
2. se mudou so um quarto, nao pinte o bairro inteiro

## Onde CSS novo deve nascer

### Caso global

Lugar certo:

1. `static/css/design-system/tokens.css`
2. `static/css/design-system/components/*`

Use quando:

1. a mudanca vale para muitas telas
2. o comportamento visual sera reutilizado

### Caso de superficie

Lugar certo:

1. `static/css/design-system/operations.css`
2. `static/css/design-system/dashboard.css`
3. `static/css/design-system/financial.css`

Use quando:

1. a familia de telas compartilha a mesma atmosfera e cascade

### Caso por persona ou dominio

Lugar certo:

1. `static/css/design-system/operations/dev-coach.css`
2. `static/css/design-system/operations/manager.css`
3. `static/css/design-system/operations/reception.css`

Use quando:

1. a feature pertence claramente a um corredor do produto

### Caso local

Lugar certo:

1. modulo local da feature
2. CSS do shell da pagina
3. card ou bloco proprio daquela experiencia

Use quando:

1. a anatomia e realmente local
2. subir para o global seria arquitetura demais cedo demais

## O que hoje e um sinal de maturidade

1. tokens, spacing, responsiveness e shell separados
2. componentes de card, hero, actions, pills e tables em hosts compartilhados
3. manifests e pastas por superficie
4. city map e organization standard documentando a cascade

## O que ainda exige cautela

1. coexistencia entre o design system novo e CSS historico de `catalog/*`
2. risco de override duplicado entre shell de pagina e componente compartilhado
3. risco de um ajuste urgente entrar fora da camada certa

## Anti-padroes que mais custam caro

1. `!important` para ganhar na forca
2. redefinir `.card` estruturalmente em pagina local
3. criar segundo manifesto paralelo para a mesma superficie
4. resolver problema local mexendo no token global por reflexo
5. deixar dark mode local reescrever o mesmo componente inteiro sem necessidade

## Regra para evitar debito tecnico

Antes de escrever CSS novo, pergunte:

1. isso e tinta da casa toda ou so deste comodo?
2. isso sera reutilizado ou e local?
3. estou corrigindo anatomia, clima ou excecao?
4. este estilo tem um dono tecnico claro?

Se essas quatro respostas estiverem claras, a chance de nascer remendo cai muito.
