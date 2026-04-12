<!--
ARQUIVO: mapa operacional da Onda 1 do dark mode do financeiro.

POR QUE ELE EXISTE:
- consolida hosts e subcards reais da central financeira antes das correcoes em cascata.
- evita que a equipe continue corrigindo um board por vez sem classificar a familia.
- deixa ownership, risco e ordem de ataque visiveis para as proximas ondas.

O QUE ESTE ARQUIVO FAZ:
1. lista os hosts financeiros vivos no runtime.
2. lista os subcards internos que participam da leitura dark.
3. classifica o risco visual principal de cada familia.
4. define a ordem segura para Onda 2 e Onda 3.

PONTOS CRITICOS:
- runtime real vence memoria.
- `finance-board-shell` e `finance-board-trend*` nao devem receber tema base em tres camadas ao mesmo tempo.
- se o bug parecer nascer do miolo, comparar sempre o subcard com o host pai antes de mexer.
-->

# Finance Dark Mode Wave 1 Map

## Veredito rapido

A Onda 1 confirmou que o financeiro nao esta sofrendo de bugs aleatorios.

Os sintomas se concentram em duas familias grandes:

1. `hosts financeiros` com dark mode duplicado entre `_boards.css`, `_dark.css`, `_signature.css` e `_shell.css`
2. `subcards analiticos` com contraste, divisoria e superficie dependentes do host errado

Traducao simples:

1. o problema nao e "um card feio"
2. o problema e "quem manda na casca" e "quem manda no miolo"

## Ownership vivo da tela

1. template principal: [../../templates/catalog/finance.html](../../templates/catalog/finance.html)
2. presenter: [../../catalog/presentation/finance_center_page.py](../../catalog/presentation/finance_center_page.py)
3. hosts locais: [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)
4. subcards locais: [../../static/css/catalog/finance/_cards.css](../../static/css/catalog/finance/_cards.css)
5. assinatura final: [../../static/css/catalog/finance/_signature.css](../../static/css/catalog/finance/_signature.css)
6. cobertura dark: [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)
7. baseline historico: [../../static/css/catalog/finance/_shell.css](../../static/css/catalog/finance/_shell.css)

## Matriz curta de ownership

### Hosts canonicos

1. `finance-board-shell`
   - markup vivo:
     - [../../templates/includes/catalog/finance/views/priority_rail.html](../../templates/includes/catalog/finance/views/priority_rail.html)
     - [../../templates/includes/catalog/finance/boards/queue_board.html](../../templates/includes/catalog/finance/boards/queue_board.html)
     - [../../templates/includes/catalog/finance/boards/follow_up_analytics_board.html](../../templates/includes/catalog/finance/boards/follow_up_analytics_board.html)
   - anatomia base: [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)
   - assinatura final: [../../static/css/catalog/finance/_signature.css](../../static/css/catalog/finance/_signature.css)
   - cobertura dark residual permitida: [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)
   - risco operacional: `wrapper local virando segundo tema`

2. `finance-board-trend`
   - markup vivo:
     - [../../templates/includes/catalog/finance/boards/revenue_chart_board.html](../../templates/includes/catalog/finance/boards/revenue_chart_board.html)
     - [../../templates/includes/catalog/finance/boards/revenue_chart_preview.html](../../templates/includes/catalog/finance/boards/revenue_chart_preview.html)
   - scaffolding historico ainda ativo: [../../static/css/catalog/finance/_shell.css](../../static/css/catalog/finance/_shell.css)
   - assinatura compartilhada: [../../static/css/catalog/finance/_signature.css](../../static/css/catalog/finance/_signature.css)
   - contraste dark complementar: [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)
   - risco operacional: `baseline historico ainda pintando host canonico`

3. `finance-board-trend-side`
   - markup vivo:
     - [../../templates/includes/catalog/finance/boards/churn_growth_board.html](../../templates/includes/catalog/finance/boards/churn_growth_board.html)
     - [../../templates/includes/catalog/finance/boards/follow_up_analytics_board.html](../../templates/includes/catalog/finance/boards/follow_up_analytics_board.html)
   - scaffolding historico ainda ativo: [../../static/css/catalog/finance/_shell.css](../../static/css/catalog/finance/_shell.css)
   - assinatura compartilhada: [../../static/css/catalog/finance/_signature.css](../../static/css/catalog/finance/_signature.css)
   - contraste dark complementar: [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)
   - risco operacional: `baseline historico ainda pintando host canonico`

### Containers-ponte que parecem host, mas nao sao o dono final

1. `finance-priority-stage`
   - vive em [../../templates/includes/catalog/finance/views/priority_rail.html](../../templates/includes/catalog/finance/views/priority_rail.html)
   - papel: palco do carrossel da regua
   - risco: ganhar surface propria e parecer board dentro de board

2. `finance-board-queue-stage`
   - vive em [../../templates/includes/catalog/finance/boards/queue_board.html](../../templates/includes/catalog/finance/boards/queue_board.html)
   - papel: palco do carrossel da fila
   - risco: virar segunda casca visual do `is-queue`

## Familia A: hosts financeiros

### Hosts confirmados no runtime

1. `finance-board-shell`
   - markup vivo em:
     - [follow_up_analytics_board.html](../../templates/includes/catalog/finance/boards/follow_up_analytics_board.html)
     - [queue_board.html](../../templates/includes/catalog/finance/boards/queue_board.html)
     - [priority_rail.html](../../templates/includes/catalog/finance/views/priority_rail.html)
   - owner primario: [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)
   - assinatura dark final esperada: [../../static/css/catalog/finance/_signature.css](../../static/css/catalog/finance/_signature.css)
   - risco: `wrapper local virando segundo tema`

2. `finance-board-trend`
   - markup vivo em:
     - [revenue_chart_board.html](../../templates/includes/catalog/finance/boards/revenue_chart_board.html)
     - [revenue_chart_preview.html](../../templates/includes/catalog/finance/boards/revenue_chart_preview.html)
   - owner visual atual dividido entre:
     - [../../static/css/catalog/finance/_shell.css](../../static/css/catalog/finance/_shell.css)
     - [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)
   - risco: `canonical primitive drift`

3. `finance-board-trend-side`
   - markup vivo em:
     - [churn_growth_board.html](../../templates/includes/catalog/finance/boards/churn_growth_board.html)
     - [follow_up_analytics_board.html](../../templates/includes/catalog/finance/boards/follow_up_analytics_board.html)
   - owner visual atual dividido entre:
     - [../../static/css/catalog/finance/_shell.css](../../static/css/catalog/finance/_shell.css)
     - [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)
   - risco: `canonical primitive drift`

### Modifiers confirmados

1. `is-rail`
   - board: [priority_rail.html](../../templates/includes/catalog/finance/views/priority_rail.html)
   - status: ja tem dark proprio, mas precisa vigiar achatamento por bulk dark

2. `is-queue`
   - boards: [queue_board.html](../../templates/includes/catalog/finance/boards/queue_board.html)
   - status: ja tem dark proprio, mas disputa com camada larga ainda e risco recorrente

3. `is-support`
   - board: [queue_board.html](../../templates/includes/catalog/finance/boards/queue_board.html)
   - status: ja tem dark proprio, mas o dashed shell pode perder personalidade se o bulk dark nivelar tudo

4. `is-analytics`
   - board: [follow_up_analytics_board.html](../../templates/includes/catalog/finance/boards/follow_up_analytics_board.html)
   - status: antes usava dark generico; agora tem branch proprio em `_signature.css`, mas precisa smoke visual dos subcards

### Veredito operacional dos modifiers

1. `is-rail`
   - deve mandar no carater quente e urgente do board
   - nao deve repintar subcards que ja sao `finance-action-card`

2. `is-queue`
   - deve comandar a casca fria da fila
   - nao deve obrigar `finance-board-queue-stage` a virar um segundo board

3. `is-support`
   - deve manter o papel de apoio bruto com borda pontilhada
   - nao pode ser achatado pelo bulk dark ate ficar igual ao `queue`

4. `is-analytics`
   - deve comandar a atmosfera do placar de follow-up
   - nao pode delegar a assinatura inteira para `finance-guide-card`

## Familia B: subcards financeiros

### Subcards confirmados no runtime

1. `finance-board-subsurface`
   - aparece dentro de:
     - `finance-guide-card`
     - cards de queue
     - cards de analytics
   - owner primario: [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)
   - owner dark secundario: [../../static/css/catalog/finance/_signature.css](../../static/css/catalog/finance/_signature.css)
   - risco: `shell duplicado em subcard`

2. `finance-guide-card`
   - aparece em:
     - `follow_up_analytics_board`
     - `queue_board`
   - owner primario: [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)
   - risco: `token gap` de copy, `strong`, `eyebrow` e `p`

3. `finance-followup-window-card`
   - aparece em [follow_up_analytics_board.html](../../templates/includes/catalog/finance/boards/follow_up_analytics_board.html)
   - owner primario: [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)
   - risco: `copy sem branch dark completo`

4. `finance-analytics-learning-grid`
   - owner: [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)
   - risco: `segunda moldura interna` e `shell decorado demais`

5. `finance-analytics-tension-grid`
   - owner: [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)
   - risco: `segunda moldura interna` e `shell decorado demais`

6. `finance-analytics-disclosure`
   - owner: [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)
   - risco: `border-top + padding-top` recriando divisoria excessiva

7. `finance-trend-metric-pill`
   - owner: [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)
   - dark complementado em [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)
   - risco: `familia semantica sem branch dark completo`

### Subcards-ponte que merecem lupa na Onda 2

1. `finance-analytics-summary-card`
   - vive so dentro do analytics
   - risco: copiar estilo de subcard e tentar virar host por acidente

2. `finance-queue-guide-card`
   - vive so dentro da fila
   - risco: misturar regra de subcard com regra de grupo semantico

3. `finance-followup-window-strip`
   - organiza janelas e timing
   - risco: ganhar surface ou divisoria e virar terceira moldura

## Classificacao de risco por familia

### Risco alto

1. `finance-board-shell`
2. `finance-board-trend`
3. `finance-board-trend-side`

Motivo:

1. recebem assinatura dark em camadas demais
2. qualquer ajuste local pode parecer funcionar e quebrar outro board

### Risco medio

1. `finance-board-subsurface`
2. `finance-guide-card`
3. `finance-analytics-learning-grid`
4. `finance-analytics-tension-grid`
5. `finance-analytics-disclosure`

Motivo:

1. o host pode estar certo, mas o miolo ainda sabota com moldura interna, contraste ou divisoria duplicada

### Risco baixo-medio

1. `finance-followup-window-card`
2. `finance-trend-metric-pill`

Motivo:

1. sao mais localizados
2. tendem a cair com contraste e familia semantica bem fechados

## Ordem segura para Onda 2

1. consolidar definitivamente a autoridade dark dos hosts:
   - `finance-board-shell`
   - `finance-board-trend`
   - `finance-board-trend-side`
2. revisar os modifiers:
   - `is-rail`
   - `is-queue`
   - `is-support`
   - `is-analytics`
3. recalibrar subcards analiticos:
   - `finance-board-subsurface`
   - `finance-guide-card`
   - `finance-followup-window-card`
4. revisar disclosures e separadores internos:
   - `finance-followup-line`
   - `finance-analytics-disclosure`

## Padrao novo confirmado nesta onda

### Baseline historico ainda pintando host canonico

Sinal:

1. o host atual parece ter owner claro
2. mas `_shell.css` ainda injeta `background` ou superficie base na mesma familia
3. o board parece aceitavel no light e torto no dark quando a assinatura moderna tenta subir por cima

Exemplo real:

1. `finance-board-trend` e `finance-board-trend-side` ainda recebem superficie em [../../static/css/catalog/finance/_shell.css](../../static/css/catalog/finance/_shell.css), enquanto a assinatura moderna tambem encosta em [../../static/css/catalog/finance/_signature.css](../../static/css/catalog/finance/_signature.css)

Correcao segura:

1. manter `_shell.css` como scaffolding e compatibilidade
2. promover a casca e a personalidade final para `_signature.css`
3. deixar `_dark.css` completar contraste e estados, nao repintar a casca inteira

## Heuristica para a proxima rodada

1. se o board inteiro parecer torto, comecar pelos hosts
2. se o titulo estiver certo e o miolo estranho, comecar pelos subcards
3. se parecer caixa dupla, procurar por `border-top + padding-top + margin-top`
4. se parecer apagado, procurar por `token gap` e copy sem branch dark
