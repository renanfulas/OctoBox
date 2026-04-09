<!--
ARQUIVO: mapa dos contratos de data_action interativos do dashboard.

POR QUE ELE EXISTE:
- documenta os comandos que os KPIs do dashboard emitem hoje.
- liga backend, template, shell e alvo visual em uma tabela unica.
- evita que `data_action` vire magia escondida entre Python, HTML e JS.

O QUE ESTE ARQUIVO FAZ:
1. lista as familias de acao interativa do dashboard.
2. registra qual KPI dispara qual comando e qual alvo recebe o efeito.
3. explica a diferenca entre topbar, board e sidebar.
4. aponta riscos de manutencao e a ordem certa de debug.

PONTOS CRITICOS:
- este mapa descreve o runtime principal em `templates/` e `static/`.
- o template do KPI apenas repassa `data-action`; a inteligencia mora no payload e no shell.
- renomear `data_action`, `nav_key`, `data-ui` ou `id` de board sem alinhar as camadas quebra o comportamento silenciosamente.
-->

# Mapa dos contratos de `data_action` do dashboard

Este documento responde a pergunta:

1. "quando eu clico em um KPI do dashboard, que tipo de reacao a interface dispara e onde isso esta definido?"

Em linguagem simples:

1. cada KPI e um botao com um bilhete preso nele
2. o bilhete diz para qual comodo da casa o porteiro deve olhar
3. o shell le esse bilhete e acende a luz certa no topo, na parede ou na sidebar

## Fontes de verdade

Leia nesta ordem:

1. [../../dashboard/dashboard_snapshot_queries.py](../../dashboard/dashboard_snapshot_queries.py)
2. [../../templates/includes/ui/shared/interactive_kpi_card.html](../../templates/includes/ui/shared/interactive_kpi_card.html)
3. [../../static/js/core/shell.js](../../static/js/core/shell.js)
4. [../../templates/includes/ui/layout/shell_sidebar.html](../../templates/includes/ui/layout/shell_sidebar.html)
5. [../../access/context_processors.py](../../access/context_processors.py)
6. [front-end-neon-contract-map.md](front-end-neon-contract-map.md)
7. [front-end-runtime-boundary-map.md](front-end-runtime-boundary-map.md)

## Como o contrato funciona

### 1. O backend escreve o comando

O payload do dashboard envia `data_action` em cada KPI interativo.

Exemplo simples:

1. o Python escreve `blink-sidebar-financeiro`
2. o template poe isso no HTML como `data-action`
3. o shell escuta o clique e resolve o alvo

### 2. O template nao toma decisao

O template [interactive_kpi_card.html](../../templates/includes/ui/shared/interactive_kpi_card.html) apenas:

1. renderiza o card
2. expõe `data-action` quando ele existe

Ele nao decide cor, destino nem animacao.

### 3. O shell interpreta o prefixo da acao

Hoje o shell conhece tres familias principais de acao do dashboard:

1. `blink-topbar-*`
2. `blink-board-*`
3. `blink-sidebar-*`

Cada familia aponta para um alvo diferente.

## Tabela viva dos KPIs principais

### 1. Cobrancas em atraso

Contrato:

1. KPI: `Cobrancas em atraso`
2. `data_action`: `blink-topbar-finance`
3. familia: `topbar`
4. alvo: `[data-ui="topbar-finance-alert"]`
5. efeito: classe temporaria `blink`

Leitura simples:

1. esse KPI nao manda para a sidebar
2. ele acende o alerta financeiro do topo

### 2. Receita realizada

Contrato:

1. KPI: `Receita realizada`
2. `data_action`: `blink-sidebar-financeiro`
3. familia: `sidebar`
4. alvo: link com `data-nav-key="financeiro"`
5. efeito: classe temporaria `blink-danger`

Observacao:

1. este e o caso vermelho especial da sidebar

### 3. Entradas pendentes

Contrato:

1. KPI: `Entradas pendentes`
2. `data_action`: `blink-topbar-intake`
3. familia: `topbar`
4. alvo: `[data-ui="topbar-intake-alert"]`
5. efeito: classe temporaria `blink`

Leitura simples:

1. ele toca o sino da intake no topo
2. nao usa board nem sidebar

### 4. Aproveitamento da agenda hoje

Contrato:

1. KPI: `Aproveitamento da agenda hoje`
2. `data_action`: `blink-board-sessions`
3. familia: `board`
4. alvo: `#dashboard-sessions-board`
5. efeito: overlay neon especial do board de sessoes

Ponto importante:

1. esse caso nao reutiliza o highlight simples da sidebar
2. ele usa um tratamento proprio no shell para evitar glitches de layout

### 5. Presenca no mes

Contrato:

1. KPI: `Presenca no mes`
2. `data_action`: `blink-sidebar-alunos`
3. familia: `sidebar`
4. alvo: link com `data-nav-key="alunos"`
5. efeito: classe temporaria `blink`

### 6. Comunidade ativa

Contrato:

1. KPI: `Comunidade ativa`
2. `data_action`: `blink-sidebar-alunos`
3. familia: `sidebar`
4. alvo: link com `data-nav-key="alunos"`
5. efeito: classe temporaria `blink`

## Familias de acao e donos

### `blink-topbar-*`

Dono do comando:

1. payload do dashboard

Dono da resolucao:

1. `shell.js`

Dono visual:

1. CSS e markup do topbar

Cheiro de bug quando quebra:

1. `data-ui` mudou
2. o alvo do topo nao existe mais
3. o payload ainda emite o comando antigo

### `blink-board-*`

Dono do comando:

1. payload do dashboard

Dono da resolucao:

1. `shell.js`

Dono visual:

1. board alvo e CSS de neon/overlay

Cheiro de bug quando quebra:

1. `id` do board mudou
2. o board virou include novo e perdeu o `id`
3. o shell trata um board especial que o CSS comum nao cobre

### `blink-sidebar-*`

Dono do comando:

1. payload do dashboard

Dono da resolucao:

1. `shell.js`

Dono visual:

1. `sidebar_nav.css` e os `data-nav-key` da navegacao

Cheiro de bug quando quebra:

1. `nav_key` mudou
2. o item saiu da sidebar para outro shell
3. alguem mexeu no nome do comando sem alinhar backend e JS

## Tabela curta de traduzir o prefixo

Se voce vir este prefixo, leia assim:

1. `blink-topbar-foo` = procure `[data-ui="topbar-foo-alert"]`
2. `blink-board-foo` = procure `#dashboard-foo-board`
3. `blink-sidebar-foo` = procure `a[data-nav-key="foo"]`

Analogia:

1. o prefixo e o tipo de mapa
2. o sufixo e o nome do comodo
3. juntos, eles dizem para o porteiro onde acender a luz

## Riscos de manutencao

Os riscos mais provaveis sao estes:

1. mudar nome de KPI nao quebra o contrato por si so, mas mudar `data_action` quebra
2. renomear `financeiro`, `alunos` ou `intake` em uma camada so causa falha silenciosa
3. trocar `id` de board sem alinhar `blink-board-*` faz o clique parecer morto
4. misturar "neon historico" com highlight simples da sidebar leva a correcoes erradas

## Ordem segura de debug

Se um KPI parar de reagir, siga esta ordem:

1. o payload ainda esta emitindo `data_action`?
2. o template colocou `data-action` no HTML?
3. o shell reconhece o prefixo dessa familia?
4. o alvo existe com o seletor esperado?
5. o CSS dessa superficie ainda conhece a classe temporaria aplicada?

Evite:

1. compensar contrato quebrado com `!important`
2. mudar seletor do alvo sem revisar o shell
3. usar a arvore `OctoBox/` como se fosse runtime ativo

## Relacao com os outros mapas

Use este mapa junto com:

1. [front-end-neon-contract-map.md](front-end-neon-contract-map.md) para o caso especifico da sidebar
2. [front-end-contract-forensics-map.md](front-end-contract-forensics-map.md) para bugs que parecem visuais, mas nascem no payload
3. [front-end-forensics-map.md](front-end-forensics-map.md) para o trilho curto de investigacao
4. [front-end-runtime-boundary-map.md](front-end-runtime-boundary-map.md) para evitar confundir runtime e espelho
5. [front-end-data-action-debug-checklist.md](front-end-data-action-debug-checklist.md) para debug curto quando o clique nao reage
