# Front-end Card Architecture

## Objetivo

Este arquivo e a lei da cidade para cards e superficies do OctoBox.

Ele existe para decidir com rapidez:

1. onde uma mudanca deve entrar
2. quando usar token
3. quando usar shell da pagina
4. quando criar variante oficial
5. quando separar um card proprio da pagina

Em linguagem simples:

1. o [front-end-city-map.md](C:\Users\renan\OneDrive\Documents\OctoBOX\docs\reference\front-end-city-map.md) mostra os bairros
2. este doc diz qual regra de construcao vale em cada bairro

## Regras da cascata

Ordem oficial de autoridade:

1. [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\tokens.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\tokens.css)
2. [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\cards.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\cards.css)
3. [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\card-variants.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\card-variants.css)
4. shell da pagina
5. card proprio da pagina

Regra central:

1. `tokens.css` define o DNA
2. `cards.css` define o corpo
3. `card-variants.css` define personalidades oficiais reutilizaveis
4. a pagina ajusta o clima
5. o card proprio e excecao governada

## Estado atual vs alvo

Hoje o OctoBox ja segue bem esta arquitetura, mas ainda existe uma diferenca entre:

1. contrato real dominante do presente
2. contrato-alvo que o sistema quer consolidar

### Contrato real de hoje

No codigo atual, a maior parte dos overrides locais ainda usa:

1. `--card-local-*`
2. knobs especificos de shell como `--finance-card-*`
3. tokens locais de dominio como `--class-grid-*` e `--student-form-*`

### Contrato-alvo

Os nomes abaixo continuam validos como direcao futura e linguagem de arquitetura:

1. `--page-card-surface`
2. `--page-card-border`
3. `--page-card-shadow`
4. `--page-text-primary`
5. `--page-text-secondary`
6. `--page-accent`

Regra de honestidade:

1. para ler o estado real do produto, procure primeiro `--card-local-*`
2. para evoluir o sistema, trate `--page-*` como uma camada futura e mais semantica
3. nao assuma que `--page-*` ja esta implantado no CSS inteiro

## Tabela de decisao rapida

| Mudanca desejada | Lugar certo |
|---|---|
| mudou cor, tema, texto base, surface semantica | `tokens.css` |
| mudou o clima visual de uma pagina | shell da pagina |
| mudou um padrao reutilizavel entre varias telas | variante oficial |
| mudou a anatomia do card | card proprio da pagina |

## Regra de decisao

Toda triagem deve seguir esta ordem:

1. resolve no token global?
2. se nao, resolve no shell da pagina?
3. se nao, resolve com variante oficial?
4. se nao, precisa de card proprio da pagina?

Regra curta:

1. se o mesmo ajuste vale para varias telas, desconfie de CSS local
2. se o ajuste e visual/contextual, tente shell antes de split
3. se o ajuste muda a anatomia do bloco, pare de lutar contra o host

## Regra de criacao

Novo card ou nova superficie deve seguir esta escada:

1. reutilizar `card` ou `table-card`
2. tentar override local da pagina
3. tentar variante oficial
4. so entao criar card proprio

### Naming

Padrao recomendado:

1. nome contextual por dominio
2. sem nomes genericos como `special-card`, `new-card`, `custom-box`

Exemplos bons:

1. `student-page-charge-card`
2. `finance-filter-summary-card`
3. `class-grid-focus-card`

## Regra de split

Split nao acontece porque o card ficou diferente.

Split acontece quando ele ficou perigoso para manter dentro da familia compartilhada.

### Gatilho oficial

Um card deve virar proprio da pagina quando acumular 2 ou mais sinais:

1. layout estrutural mudou
2. slots, header, footer ou actions mudaram
3. hierarquia interna mudou muito
4. responsividade quebra ao tentar adaptar
5. dark mode paralelo comeca a aparecer
6. muitos seletores contextuais passam a ser necessarios
7. o host deixou de responder de forma previsivel

Formula oficial:

1. pele = override
2. anatomia = split

Em linguagem simples:

1. apertar a roupa e uma coisa
2. cortar o corpo da roupa para caber e outra bem diferente

## Contrato de override por pagina

O shell da pagina pode ajustar variaveis locais como:

1. `--page-card-surface`
2. `--page-card-border`
3. `--page-card-shadow`
4. `--page-text-primary`
5. `--page-text-secondary`
6. `--page-accent`

Tambem sao aceitaveis overrides locais controlados com:

1. `--card-local-surface`
2. `--card-local-border`
3. `--card-local-shadow`
4. knobs locais por dominio, como `--finance-card-*`, `--class-grid-*` e `--student-form-*`

Regra:

1. a pagina pode ajustar knobs
2. a pagina nao pode reinventar o host inteiro

## O que a pagina pode e nao pode fazer

### Permitido

1. ajustar variaveis locais
2. mudar densidade e espacamento contextual
3. mudar accent e clima visual do shell
4. ajustar composicao editorial

### Proibido

1. reescrever `.card` estruturalmente como regra local
2. fazer dark mode proprio do card se o problema e do host
3. usar `!important` visual para superficie, borda ou sombra
4. espalhar a mesma personalizacao por varios arquivos sem shell central

## Card Registry

Todo card relevante deve conseguir ser classificado neste formato:

| Nome | Tipo | Shell dono | Arquivo principal | Status |
|---|---|---|---|---|
| `card` | `shared` | global | [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\cards.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\cards.css) | saudavel |
| `card--sci-fi` | `variant` | global | [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\card-variants.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\card-variants.css) | saudavel |
| `class-grid` cards com `--card-local-*` | `page-override` | class-grid | [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\class-grid\workspace.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\class-grid\workspace.css) | saudavel |
| `student-form-shell` stepper e disclosures | `page-override` | student-form-shell | [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\student_form_stepper.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\student_form_stepper.css) | saudavel |
| `finance-shell` boards e KPI strip | `page-override` | finance-shell | [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\finance\_shell.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\finance\_shell.css) | saudavel |
| `finance` signature cards | `page-override` | finance-shell | [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\finance\_signature.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\finance\_signature.css) | transitorio |
| `intake` boards e filter card | `page-override` | intake-scene | [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\onboarding\intakes.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\onboarding\intakes.css) | transitorio |
| `owner notion` panels | `page-override` | owner-notion-shell | [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\operations\owner\notion\panels.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\operations\owner\notion\panels.css) | saudavel |
| `student-page-charge-card` | `page-owned` | student-page-shell | [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-page-shell.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-page-shell.css) | saudavel |

## Reclassificacao operacional atual

Depois das ondas de alinhamento, a leitura oficial do territorio fica assim:

### Ja classificados como `page-owned`

1. `student-page-charge-card`
2. cards editoriais e estruturas premium da [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-page-shell.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-page-shell.css)

Motivo:

1. carregam anatomia propria
2. tem layout, actions, header/footer e densidade local fortes
3. ja cruzaram o limiar de "pele" e entraram em "anatomia"

### Permanecem `page-override` saudavel

1. `class-grid`
2. `student-form-shell`
3. `finance-shell` boards e KPI strip
4. `owner notion`
5. `intake-scene`

Motivo:

1. ainda respondem bem ao host e ao shell
2. a maior parte da diferenca esta em clima, contraste, superficie e densidade
3. nao pedem split estrutural agora

### Permanecem `transitorio`, mas ainda nao pedem split

1. `finance` signature cards

Motivo:

1. ainda tem identidade visual forte
2. mas hoje funcionam mais como camada de assinatura do shell do que como card independente de anatomia propria

### Nao devem virar `page-owned` por enquanto

1. `student-financial-*`
2. `intake` boards
3. `student-form-stepper`
4. `class-grid` cards semanais e mensais

Motivo:

1. a maior parte do problema anterior era cascata e ownership
2. depois da limpeza, esses blocos respondem melhor ao shell
3. split agora criaria mais manutencao do que beneficio

Tipos oficiais:

1. `shared`
2. `page-override`
3. `variant`
4. `page-owned`

Status recomendados:

1. `saudavel`
2. `transitorio`
3. `candidato a split`

## Prompt de triagem

Use este prompt curto para triagem rapida:

```text
Analise este card ou superficie do OctoBox e classifique em uma das 4 categorias: global, shell da pagina, variante oficial ou page-owned. Explique por que, cite o arquivo dono e diga se o caso pede override, variante ou split.
```

## Checklist de criacao

Antes de criar ou refatorar um card, revise:

1. ja existe card parecido?
2. resolve com `card` ou `table-card`?
3. resolve com shell da pagina?
4. resolve com variante oficial?
5. precisa mesmo split?
6. o nome esta contextual?
7. o card continua obedecendo ao tema global?
8. o ownership ficou claro em um unico arquivo principal?

## Anti-patterns

Evite estes erros:

1. split precoce
2. card proprio sem necessidade estrutural real
3. variante oficial criada para um caso unico local
4. pagina reescrevendo `.card` estruturalmente
5. override multiplo sem centralizacao no shell
6. host compartilhado perdendo autoridade para uma excecao local

## Estudos de caso

### Caso global

Se uma mudanca mexe em `--card-surface` ou `--theme-text-primary`, o lugar certo e:

1. [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\tokens.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\tokens.css)

### Caso shell

Se a grade precisa de outro clima visual sem mudar o host:

1. use [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\class-grid\workspace.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\class-grid\workspace.css)
2. ajuste `--card-local-*`

### Caso variante

Se varios cards pedem a mesma personalidade premium:

1. use ou evolua [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\card-variants.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\card-variants.css)

### Caso page-owned

Se a pagina do aluno precisa de um card editorial com anatomia propria:

1. mantenha esse ownership em [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-page-shell.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-page-shell.css)

## Referencias cruzadas

Para localizar os bairros e ownership, leia:

1. [C:\Users\renan\OneDrive\Documents\OctoBOX\docs\reference\front-end-city-map.md](C:\Users\renan\OneDrive\Documents\OctoBOX\docs\reference\front-end-city-map.md)
2. [C:\Users\renan\OneDrive\Documents\OctoBOX\docs\reference\design-system-contract.md](C:\Users\renan\OneDrive\Documents\OctoBOX\docs\reference\design-system-contract.md)
3. [C:\Users\renan\OneDrive\Documents\OctoBOX\docs\experience\css-guide.md](C:\Users\renan\OneDrive\Documents\OctoBOX\docs\experience\css-guide.md)
