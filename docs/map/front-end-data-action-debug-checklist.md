<!--
ARQUIVO: checklist curto de debug para contratos de data_action.

POR QUE ELE EXISTE:
- transforma clique "morto" em investigacao curta e repetivel.
- evita que a equipe pule direto para CSS, `!important` ou remendo visual.
- ajuda a descobrir em qual elo o sinal se perdeu: payload, HTML, shell, alvo ou CSS.

O QUE ESTE ARQUIVO FAZ:
1. organiza uma trilha curta de verificacao para `data_action`.
2. separa sintomas de topbar, board e sidebar.
3. registra os erros mais provaveis e a menor correcao segura.

PONTOS CRITICOS:
- o template do KPI nao decide o destino; ele apenas expõe `data-action`.
- o runtime principal e `templates/` + `static/`; `OctoBox/` e arvore espelho.
- se o contrato estiver quebrado, corrigir o fio certo e melhor do que gritar mais alto no CSS.
-->

# Checklist curto de debug para `data_action`

Use esta checklist quando o usuario clicar em um KPI e "nada acontecer".

Em linguagem simples:

1. o clique e um recado
2. esse recado passa por cinco portas
3. se a luz nao acendeu, a gente precisa descobrir em qual porta o recado ficou preso

## Ordem curta de investigacao

### 1. O payload escreveu o comando?

- [ ] Confirmei no backend se o card ainda sai com `data_action`.
- [ ] Confirmei se o valor emitido e o esperado, por exemplo `blink-sidebar-financeiro`.
- [ ] Se o KPI mudou de nome, confirmei que o nome mudou, mas o contrato de `data_action` continua coerente.

Onde olhar:

1. [../../dashboard/dashboard_snapshot_queries.py](../../dashboard/dashboard_snapshot_queries.py)

Cheiro de bug:

1. o KPI renderiza normal, mas o clique nao tem instrução nenhuma para seguir

### 2. O HTML expôs `data-action`?

- [ ] Confirmei no template que `data-action="{{ card.data_action }}"` ainda esta sendo renderizado.
- [ ] Confirmei se o card clicavel realmente recebeu o atributo no DOM.
- [ ] Confirmei se o card nao perdeu a classe/estrutura que o torna interativo.

Onde olhar:

1. [../../templates/includes/ui/shared/interactive_kpi_card.html](../../templates/includes/ui/shared/interactive_kpi_card.html)

Cheiro de bug:

1. o Python manda o bilhete, mas o template esquece de colocar o bilhete na mochila da crianca

### 3. O shell conhece esse prefixo?

- [ ] Confirmei se o `shell.js` ainda escuta o prefixo certo.
- [ ] Confirmei se o clique esta entrando na familia correta: `topbar`, `board` ou `sidebar`.
- [ ] Confirmei se o handler nao foi removido, renomeado ou desviado.

Onde olhar:

1. [../../static/js/core/shell.js](../../static/js/core/shell.js)

Tabela rapida:

1. `blink-topbar-foo` -> procura `[data-ui="topbar-foo-alert"]`
2. `blink-board-foo` -> procura `#dashboard-foo-board`
3. `blink-sidebar-foo` -> procura `a[data-nav-key="foo"]`

### 4. O alvo existe com o seletor esperado?

- [ ] Confirmei se o elemento de destino ainda existe.
- [ ] Confirmei se o `data-ui`, `id` ou `data-nav-key` nao mudou de nome.
- [ ] Confirmei se o alvo existe no runtime principal, nao so na arvore espelho `OctoBox/`.

Onde olhar:

1. topbar: markup da shell/topbar
2. board: template ou include do board
3. sidebar: [../../templates/includes/ui/layout/shell_sidebar.html](../../templates/includes/ui/layout/shell_sidebar.html)
4. mapeamento de `nav_key`: [../../access/context_processors.py](../../access/context_processors.py)
5. fronteira de runtime: [front-end-runtime-boundary-map.md](front-end-runtime-boundary-map.md)

Cheiro de bug:

1. o porteiro recebeu o recado certo, mas a porta mudou de numero

### 5. O CSS ainda conhece a classe temporaria?

- [ ] Confirmei se a classe aplicada pelo shell ainda existe no CSS.
- [ ] Confirmei se o estilo foi removido, renomeado ou soterrado por cascata errada.
- [ ] Confirmei se alguem nao "consertou" o efeito com `!important` em outra camada.

Onde olhar:

1. sidebar: [../../static/css/design-system/sidebar/sidebar_nav.css](../../static/css/design-system/sidebar/sidebar_nav.css)
2. contratos visuais especificos: [front-end-neon-contract-map.md](front-end-neon-contract-map.md)

Cheiro de bug:

1. o shell colocou a fantasia certa, mas o guarda-roupa nao reconhece mais a roupa

## Diagnostico por familia

### Se o problema for `blink-topbar-*`

- [ ] Verifiquei `data-ui="topbar-<kind>-alert"`
- [ ] Confirmei se o alvo existe na shell ativa
- [ ] Confirmei se a classe `blink` ainda pinta esse alerta

### Se o problema for `blink-board-*`

- [ ] Verifiquei o `id` do board alvo
- [ ] Confirmei se o include novo nao removeu o `id`
- [ ] Se for `sessions`, confirmei o tratamento especial com overlay no `shell.js`

### Se o problema for `blink-sidebar-*`

- [ ] Verifiquei o `data-nav-key` correspondente
- [ ] Confirmei se `financeiro` continua sendo o caso vermelho especial
- [ ] Confirmei se o link ainda existe para o papel do usuario logado

## Erros provaveis e correcao segura

### O KPI clica, mas nada acontece

Causa provavel:

1. `data_action` ausente no payload ou no HTML

Correcao segura:

1. corrigir backend ou template antes de tocar no CSS

### O shell reage, mas o item errado acende

Causa provavel:

1. `nav_key`, `data-ui` ou `id` divergente

Correcao segura:

1. alinhar nomes entre payload, shell e alvo

### O alvo certo e encontrado, mas nao pisca

Causa provavel:

1. classe temporaria removida, renomeada ou soterrada

Correcao segura:

1. corrigir o contrato CSS
2. evitar novo `!important` como primeira resposta

## Regra de ouro

Antes de mexer no visual, responda:

- [ ] o comando foi emitido?
- [ ] o comando foi entregue?
- [ ] o alvo foi encontrado?
- [ ] o alvo reconheceu a classe?

Se a resposta for "nao" em qualquer etapa, o problema nao nasceu no ultimo elo.

## Mapas irmaos

1. [front-end-dashboard-action-contract-map.md](front-end-dashboard-action-contract-map.md)
2. [front-end-neon-contract-map.md](front-end-neon-contract-map.md)
3. [front-end-contract-forensics-map.md](front-end-contract-forensics-map.md)
4. [front-end-forensics-checklist.md](front-end-forensics-checklist.md)
