<!--
ARQUIVO: relatorio operacional das ondas de dark mode do financeiro.

POR QUE ELE EXISTE:
- registra o que foi corrigido por onda sem depender de memoria da thread.
- deixa explicito o que sobrou, o que tem risco residual e o que pede smoke visual.
- ajuda a equipe a decidir se vale uma segunda camada de refinamento.
-->

# Finance Dark Mode Wave Report

## Resumo executivo

As ondas aplicadas nesta rodada atacaram primeiro a casca e depois o miolo do financeiro.

Traducao simples:

1. primeiro arrumamos as paredes
2. depois tiramos divisorias que estavam sobrando por dentro
3. por fim anotamos o que ainda precisa de lanterna

## Onda 2 - Hosts canonicos

Arquivos mexidos:

1. [../../static/css/catalog/finance/_shell.css](../../static/css/catalog/finance/_shell.css)
2. [../../static/css/catalog/finance/_signature.css](../../static/css/catalog/finance/_signature.css)
3. [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)

O que foi feito:

1. `finance-board-trend` e `finance-board-trend-side` deixaram de receber superficie base em `_shell.css`
2. a casca desses hosts subiu para `_signature.css`
3. o dark complementar ficou focado em contraste e legibilidade, nao em repintar a casca inteira
4. `finance-revenue-trend` e `finance-churn-trend` agora falam a mesma lingua no dark

Risco reduzido:

1. `baseline historico ainda pintando host canonico`

## Onda 3 - Containers-ponte e segunda moldura

Arquivo mexido:

1. [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)

O que foi feito:

1. `finance-board-queue-stage` voltou a ser so palco estrutural
2. foram removidos `background`, `border` e `box-shadow` do stage interno
3. `finance-analytics-disclosure` ficou menos pesado
4. `finance-followup-line` ficou com divisoria mais discreta

Risco reduzido:

1. `shell duplicado em container interno`
2. `segunda moldura interna`

## Onda 4 - Contraste complementar

Arquivo mexido:

1. [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)

O que foi feito:

1. `finance-churn-trend-title`
2. `finance-churn-trend-subtitle`
3. `finance-churn-trend-legend`
4. `finance-churn-trend-legend-item`

Todos esses pontos agora entram no mesmo contrato de contraste do dark.

## Onda 5 - KPIs e cards de modo

Arquivos mexidos:

1. [../../static/css/catalog/finance/_metrics.css](../../static/css/catalog/finance/_metrics.css)
2. [../../static/css/catalog/finance/_modes.css](../../static/css/catalog/finance/_modes.css)

O que foi feito:

1. os KPIs interativos ganharam dark mode mais coerente com a familia `metric-card`
2. o estado `is-selected-tab` ficou mais legivel e mais claramente ativo
3. o `icon-box` dos KPIs passou a conversar com a cor semantica de cada card
4. os cards `Tradicional`, `Hibrido` e `IA` ganharam branch dark proprio
5. o hover e o estado ativo dos cards de modo ficaram mais consistentes

## Onda 6 - Subcards de handoff, carteira e filtros

Arquivos mexidos:

1. [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)
2. [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)

O que foi feito:

1. `finance-queue-guide-card` e seus textos internos passaram a seguir hierarquia dark mais consistente
2. `finance-risk-summary` deixou de parecer badge clara herdada do light mode
3. `finance-overdue-row` ganhou trilha dark mais coerente em hover e separadores
4. `finance-portfolio-panel-row` virou subcard real no dark, em vez de linha crua dentro da carteira
5. `finance-command-card` e `finance-filter-summary-card` ganharam reforco de titulo e profundidade nos subcards internos

## Onda 7 - Casca final dos blocos operacionais

Arquivos mexidos:

1. [../../static/css/catalog/finance/_cards.css](../../static/css/catalog/finance/_cards.css)
2. [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)
3. [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)

O que foi feito:

1. `finance-action-message.finance-action-message-compact` ganhou superficie dark mais coerente e raio final alinhado com a familia do financeiro
2. `finance-queue-guide-grid` passou a esticar os cards internos para evitar degraus visuais
3. `finance-risk-queue` ganhou respiro mais regular entre os subcards
4. `finance-portfolio-panel-card` deixou de depender so das linhas internas e passou a ter casca dark propria
5. `finance-board-plan.finance-command-card` e `finance-filter-summary-card` foram promovidos para a mesma familia de shell dos blocos operacionais

## Onda 8 - Autoridade canonica dos subcomponentes

Arquivos mexidos:

1. [../../static/css/catalog/finance/_cards.css](../../static/css/catalog/finance/_cards.css)
2. [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)
3. [../../static/css/catalog/finance/_signature.css](../../static/css/catalog/finance/_signature.css)

O que foi feito:

1. `finance-action-message` deixou de ser repintado pelo `bulk dark` e pela `signature`
2. `finance-action-copy strong`, `finance-summary-chip` e `finance-alert-stat` voltaram para o owner canonico em `_cards.css`
3. a `signature` do financeiro ficou mais concentrada em host, shell e atmosfera, sem redesenhar primitivos pequenos do miolo
4. `finance-queue-guide-card` deixou de herdar a casca generica de `finance-guide-card` e `finance-board-subsurface` na camada tardia
5. `finance-board-queue-stage` deixou de se apresentar no template como `card finance-board-shell`, ficando alinhado com o contrato de container-ponte ja definido no CSS
6. `finance-queue-card` e seus subelementos deixaram de depender do verniz generico de `finance-action-card` e `finance-board-subsurface`, passando a ter dark local proprio da fila
7. `finance-portfolio-panel-card` e `finance-board-plan.finance-command-card` ganharam refinamento completo de subelementos, incluindo hierarquia de texto, badge, feedback, labels, fallback e trilhas visuais

Risco reduzido:

1. `assinatura tardia repintando primitivo canonico`

## Onda 9 - Hosts com assinatura final dividida

Arquivos mexidos:

1. [../../static/css/catalog/finance/_shell.css](../../static/css/catalog/finance/_shell.css)
2. [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)
3. [../../static/css/catalog/finance/_signature.css](../../static/css/catalog/finance/_signature.css)

O que foi feito:

1. `finance-board-portfolio.finance-portfolio-panel-card` deixou de herdar dark generico legado em `_shell.css`
2. `finance-command-card` passou a excluir o host `finance-board-plan`, para o card de plano nao ter dois donos de casca no dark
3. `finance-board-portfolio.finance-portfolio-panel-card` e `finance-board-plan.finance-command-card` foram promovidos para a assinatura final em `_signature.css`
4. a autoridade visual desses hosts ficou consolidada na ultima camada carregada da pagina, reduzindo risco de falso negativo por ordem de import

Risco reduzido:

1. `host promovido mas baseline legado ainda pintando por baixo`
2. `signature generica achatando host especifico ja corrigido no dark`

## O que ficou para tras ou merece segunda camada

### 1. Smoke visual real ainda necessario

Nao houve captura visual automatizada nesta rodada.

Isso significa:

1. o ownership ficou mais limpo
2. o CSS-fonte ficou mais correto
3. mas ainda falta a foto final do runtime para achar sobrancelhas, glow excessivo ou contraste subjetivo

### 2. `finance-followup-window-card`

Estado:

1. o card esta melhor protegido por contraste
2. mas ainda merece smoke visual no `finance-ai-board`

Risco:

1. copy pequena demais em viewports intermediarios
2. possivel sensacao de subcard “lavado” dependendo do payload

### 3. `finance-analytics-disclosure-body`

Estado:

1. a grade foi aliviada
2. mas continua densa

Risco:

1. em `900px-1100px` pode parecer apertada
2. se os textos reais crescerem, pode pedir recalibragem de spans ou min-heights

### 4. `finance-priority-stage`

Estado:

1. foi classificado como container-ponte
2. nao foi redesenhado nesta rodada

Risco:

1. se algum estilo local futuro entrar nele, o fantasma de “card dentro do card” pode voltar

### 5. `finance-trend-metric-pill`

Estado:

1. a familia ja tem branch dark
2. mas ainda depende de smoke semantico por estado real

Risco:

1. um estado menos frequente como `pending` ou `steady` pode ainda ficar mais apagado do que o ideal em payload real

### 6. KPIs interativos e cards de modo

Estado:

1. a casca dark foi fortalecida nesta rodada
2. mas ainda depende de smoke visual com payload real

Risco:

1. o `kpi-slate` pode parecer discreto demais em telas com brilho baixo
2. a variante `traditional` dos cards de modo pode pedir mais separacao cromatica se ficar proxima demais do fundo do shell

### 7. Handoff, carteira e filtros

Estado:

1. a familia de subcards agora esta mais coesa no dark
2. o risco de parecer “mistura de produtos” caiu bastante

Risco:

1. `finance-portfolio-panel-row` pode pedir microajuste de densidade se houver muitos planos com nomes longos
2. `finance-overdue-row` ainda merece smoke visual para confirmar conforto de leitura em telas medianas

## O que pode ter passado despercebido

1. viewports intermediarios entre `900px` e `1100px`
2. combinacoes raras de payload com muito texto nos subcards analiticos
3. estados semanticos menos comuns dos pills
4. qualquer `static drift` no runtime, se o navegador estiver servindo asset espelhado antigo

## Proxima camada recomendada

1. smoke visual do `/financeiro/` em dark mode
2. revisar especificamente:
   - `#finance-trend-board`
   - `#finance-ai-board`
   - `#finance-queue-board`
   - `#finance-priority-board`
   - `#finance-overdue-support-board`
3. se sobrar ruido, atacar por duas linhas:
   - `subcards pequenos`
   - `densidade de disclosure e grid`
