<!--
ARQUIVO: mapa do contrato de neon e highlight da navegacao lateral.

POR QUE ELE EXISTE:
- tira o contrato de blink da sidebar do "conhecimento oral" e coloca em um mapa tecnico.
- conecta KPI, payload, shell, nav_key e CSS da navegacao em um so lugar.
- evita que uma mudanca de nome ou de camada quebre o highlight sem ninguem perceber.

O QUE ESTE ARQUIVO FAZ:
1. documenta o fluxo real do clique no KPI ate o highlight da sidebar.
2. registra o mapeamento vivo entre KPI, `data_action`, `nav_key` e cor.
3. separa neon historico de highlight real implementado hoje.
4. aponta pistas de drift, legado e riscos de manutencao.

PONTOS CRITICOS:
- o runtime principal usa `templates/` e `static/`; a arvore `OctoBox/` e espelho/legado.
- a sidebar nao usa neon animado real hoje; ela usa highlight temporario por classe.
- o caso vermelho de `financeiro` depende de uma regra explicita no JS; renomear `nav_key` sem alinhar shell quebra o contrato.
-->

# Mapa do contrato de neon da sidebar

Este documento responde a pergunta:

1. "quando eu clico em um KPI do dashboard, por que um item da sidebar pisca e como isso decide a cor certa?"

Em linguagem simples:

1. o KPI e como um botao que toca uma campainha
2. o shell escuta a campainha, procura a porta certa da casa e acende a luz daquela porta
3. dependendo da porta, a luz fica verde ou vermelha

## Regra viva hoje

No runtime principal, o contrato atual e este:

1. `Receita realizada` aciona highlight vermelho em `Financeiro`
2. `Comunidade ativa` aciona highlight verde em `Alunos`
3. `Presenca do mes` aciona highlight verde em `Alunos`

Traduzido para o contrato tecnico:

1. `Receita realizada` -> `blink-sidebar-financeiro` -> `nav_key="financeiro"` -> classe `blink-danger`
2. `Comunidade ativa` -> `blink-sidebar-alunos` -> `nav_key="alunos"` -> classe `blink`
3. `Presenca do mes` -> `blink-sidebar-alunos` -> `nav_key="alunos"` -> classe `blink`

## Fontes de verdade

Se esse contrato parecer quebrado, leia nesta ordem:

1. [../../dashboard/dashboard_snapshot_queries.py](../../dashboard/dashboard_snapshot_queries.py)
2. [../../static/js/core/shell.js](../../static/js/core/shell.js)
3. [../../access/context_processors.py](../../access/context_processors.py)
4. [../../templates/includes/ui/layout/shell_sidebar.html](../../templates/includes/ui/layout/shell_sidebar.html)
5. [../../static/css/design-system/sidebar/sidebar_nav.css](../../static/css/design-system/sidebar/sidebar_nav.css)
6. [front-end-runtime-boundary-map.md](front-end-runtime-boundary-map.md)

## Fluxo real do clique

### 1. O backend define a intencao do KPI

Os KPIs interativos saem do backend com `data_action`.

Pontos vivos importantes:

1. `Receita realizada` sai com `data_action="blink-sidebar-financeiro"`
2. `Comunidade ativa` sai com `data_action="blink-sidebar-alunos"`
3. `Presenca do mes` sai com `data_action="blink-sidebar-alunos"`

Leitura simples:

1. o backend nao pinta a sidebar diretamente
2. ele so escreve um bilhete dizendo qual porta deve piscar

### 2. O template do KPI so repassa o comando

O template interativo nao decide cor nem destino final.

Ele apenas expõe o `data-action` no HTML para o shell capturar.

### 3. O shell captura o clique e resolve o alvo

O JS do shell escuta cliques em elementos com `data-action`.

Quando encontra um valor com prefixo `blink-sidebar-`, ele:

1. extrai o `nav_key`
2. procura o link da sidebar por `data-nav-key`
3. se achar o item, injeta uma classe temporaria

Essa classe temporaria hoje segue esta regra:

1. se o `nav_key` for `financeiro`, usa `blink-danger`
2. para os demais casos mapeados pela sidebar, usa `blink`

Analogia:

1. o shell e o porteiro
2. ele le o nome do apartamento no bilhete
3. se for `financeiro`, ele acende a luz vermelha
4. se for `alunos`, ele acende a luz verde

### 4. A sidebar conhece os alvos por `data-nav-key`

O HTML da sidebar liga cada link a um `nav_key`.

No contrato relevante desta trilha:

1. `Alunos` usa `data-nav-key="alunos"`
2. `Financeiro` usa `data-nav-key="financeiro"`

Se esse nome mudar no template ou no context processor sem alinhar o backend e o shell, o blink para de funcionar.

### 5. O CSS pinta o highlight temporario

Hoje a sidebar nao usa animacao neon real com `@keyframes`.

Ela usa classes temporarias:

1. `.nav-link.blink` para o destaque verde
2. `.nav-link.blink-danger` para o destaque vermelho

O shell aplica a classe e remove depois de um intervalo curto.

Leitura pratica:

1. historicamente chamamos isso de "neon"
2. tecnicamente, no estado atual, isso e highlight temporario

## Diferenca entre nome historico e implementacao real

Aqui mora uma pegadinha comum.

Quando alguem fala:

1. "o card pisca em neon"

Isso pode significar tres coisas diferentes na base:

1. blink real com animacao em alguns contextos visuais
2. glow forte de card em boards ou topbar
3. highlight temporario da sidebar por troca de classe

Para a sidebar, o contrato atual e o item 3.

Nao trate a sidebar como se ela tivesse uma engine de neon dedicada, porque isso pode levar a correcoes erradas.

## Tabela curta de diagnostico

Se um KPI deixa de acender o item certo, investigue assim:

1. o KPI tem `data_action` certo no payload?
2. o template interativo esta expondo `data-action` no HTML?
3. o shell esta capturando `blink-sidebar-*`?
4. o link da sidebar existe com `data-nav-key` igual ao alvo?
5. o CSS ainda conhece `blink` e `blink-danger`?
6. o `nav_key` foi renomeado em backend ou template sem atualizar o shell?

## Pistas de drift e legado

Essas pistas ja apareceram nesta trilha:

1. comentarios antigos em `shell.js` diziam que o highlight da sidebar tinha sido removido, mas o fluxo vivo continuava ativo
2. havia regra antiga de `[data-no-pointer="true"]` em `sidebar_nav.css` sem consumidor no runtime principal
3. a arvore `OctoBox/` ainda guarda espelhos e rastros antigos que nao devem ser usados como fonte canonica do runtime

Regra de ouro:

1. se o arquivo esta em `OctoBox/`, suspeite de espelho antes de assumir runtime vivo

## Riscos de manutencao

Os riscos principais deste contrato sao:

1. `financeiro` vermelho depende de uma decisao explicita em `shell.js`, nao de token automatico
2. renomear `nav_key` em `context_processors.py` ou no template da sidebar quebra o blink silenciosamente
3. trocar o nome da `data_action` no backend sem alinhar o shell quebra a ponte KPI -> sidebar
4. tentar transformar esse highlight em "neon real" sem separar sidebar de topbar pode misturar contratos diferentes

## Correcao segura quando algo quebrar

Se o comportamento falhar, a ordem de corte mais segura e esta:

1. corrigir primeiro o `data_action` no backend
2. corrigir depois o casamento entre `data_action` e `data-nav-key`
3. corrigir por ultimo o tom visual em `sidebar_nav.css`

Evite:

1. enfiar `!important` novo na sidebar sem entender a cascata
2. renomear `financeiro` ou `alunos` em uma camada so
3. debugar com base na arvore `OctoBox/` achando que ela e o runtime principal

## Relacao com os outros mapas

Use este mapa junto com:

1. [front-end-forensics-map.md](front-end-forensics-map.md) para trilho curto de investigacao visual
2. [front-end-contract-forensics-map.md](front-end-contract-forensics-map.md) para bugs que parecem visuais, mas nascem em payload ou presenter
3. [front-end-runtime-boundary-map.md](front-end-runtime-boundary-map.md) para nao confundir runtime com arvore espelho
4. [front-end-error-patterns-map.md](front-end-error-patterns-map.md) para reconhecer cheiro de drift, ownership e cascata errada
5. [front-end-dashboard-action-contract-map.md](front-end-dashboard-action-contract-map.md) para o catalogo mais amplo dos `data_action` do dashboard
