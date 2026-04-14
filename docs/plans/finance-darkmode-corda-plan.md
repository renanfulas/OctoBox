<!--
ARQUIVO: plano C.O.R.D.A. para auditoria e correcao em cascata do dark mode do financeiro.

POR QUE ELE EXISTE:
- evita atacar boards e subcards financeiros um por um.
- transforma sintomas visuais repetidos em familias de problema com ownership claro.
- cria um prompt operacional reutilizavel para futuras ondas de auditoria do financeiro.

O QUE ESTE ARQUIVO FAZ:
1. registra o contexto atual da frente de dark mode do financeiro.
2. define objetivo, riscos, direcao e ondas de execucao.
3. entrega um prompt pronto para auditar e corrigir toda a familia de cards do financeiro.

PONTOS CRITICOS:
- runtime real vence memoria e screenshot antiga.
- a autoridade de host deve seguir a ordem: _boards.css -> _cards.css -> _signature.css -> _dark.css -> _shell.css.
- nao corrigir card por card antes de classificar a familia do problema.
-->

# Finance Dark Mode C.O.R.D.A.

## C - Contexto

Estamos vendo no financeiro o mesmo cheiro estrutural que ja apareceu em dashboard e owner:

1. `finance-board-shell`, `finance-board-trend` e `finance-board-trend-side` receberam dark mode em camadas demais.
2. subcards como `finance-guide-card`, `finance-followup-window-card` e grids analiticos acabam herdando contraste inconsistente.
3. a equipe comeca a corrigir board por board, o que aumenta custo e risco de debito tecnico.

Ownership curto desta frente:

1. template principal: [../../templates/catalog/finance.html](../../templates/catalog/finance.html)
2. presenter: [../../catalog/presentation/finance_center_page.py](../../catalog/presentation/finance_center_page.py)
3. hosts locais: [../../static/css/catalog/finance/_boards.css](../../static/css/catalog/finance/_boards.css)
4. subcards locais: [../../static/css/catalog/finance/_cards.css](../../static/css/catalog/finance/_cards.css)
5. assinatura final: [../../static/css/catalog/finance/_signature.css](../../static/css/catalog/finance/_signature.css)
6. cobertura dark: [../../static/css/catalog/finance/_dark.css](../../static/css/catalog/finance/_dark.css)
7. baseline historico: [../../static/css/catalog/finance/_shell.css](../../static/css/catalog/finance/_shell.css)

## O - Objetivo

Corrigir o dark mode do financeiro por familias visuais, nao por sintomas soltos.

Sucesso significa:

1. todos os hosts financeiros relevantes usam uma autoridade dark clara.
2. rail, queue, support, trend e analytics mantem diferenca de personalidade sem parecer cinco temas diferentes.
3. subcards e textos internos ficam legiveis e coerentes no dark.
4. cada novo bug visual do financeiro cai num mapa conhecido, com owner e acao segura.

## R - Riscos

1. `shell duplicado`: `_boards.css`, `_signature.css` e `_dark.css` podem repintar o mesmo host.
2. `segunda moldura interna`: `border-top + padding-top + margin-top` em subcards podem recriar divisorias falsas.
3. `token gap`: copy, subtitle e labels de apoio podem usar tons diferentes em cada subcard.
4. `bulk dark flattening`: regras largas em `_dark.css` podem achatar a diferenca entre `is-rail`, `is-queue`, `is-support` e `is-analytics`.
5. `static drift`: codigo certo com asset espelhado velho no runtime pode dar falso negativo visual.

Traducao simples:

1. se cinco pintores mexem no mesmo muro, o resultado pode ficar bonito por acidente hoje e caro de manter amanha.

## D - Direcao

Trabalhar em cascata, nesta ordem:

1. classificar primeiro os hosts financeiros por familia.
2. escolher um unico dono da casca dark de cada familia.
3. corrigir depois o miolo: subcards, copy, labels, disclosures e trilhas internas.
4. documentar o novo padrao antes de partir para a proxima onda.

Heuristica de decisao:

1. se o problema e da casca, revisar primeiro `_boards.css`, `_signature.css`, `_dark.css` e `_shell.css`.
2. se o problema e do miolo, revisar `_cards.css` e subblocos de `_boards.css`.
3. se o visual parece “lavado”, suspeitar de contraste e token gap.
4. se parece “caixa dupla”, suspeitar de shell duplicado ou divisoria interna herdada.

## A - Acoes

### Onda 1 - Inventario de hosts

Mapear todos os hosts financeiros desta frente:

1. `finance-board-shell`
2. `finance-board-trend`
3. `finance-board-trend-side`
4. modifiers:
   - `is-rail`
   - `is-queue`
   - `is-support`
   - `is-analytics`

Entregavel:

1. tabela com `host -> arquivo dono -> dark owner -> risco atual`

### Onda 2 - Inventario de subcards

Mapear subcards e containers internos:

1. `finance-board-subsurface`
2. `finance-guide-card`
3. `finance-followup-window-card`
4. `finance-analytics-*grid`
5. `finance-analytics-disclosure`
6. `finance-followup-line`
7. `finance-trend-metric-pill`

Entregavel:

1. tabela com `subcard -> host pai -> conflito visual -> owner`

### Onda 3 - Correcao dos hosts

Aplicar poda de autoridade:

1. deixar `_signature.css` como dono da assinatura dark dos hosts.
2. deixar `_dark.css` cobrir apenas o que nao pertence a assinatura final.
3. deixar `_boards.css` mandar no layout e no miolo, nao no tema base do host.

Entregavel:

1. diff pequeno e intencional nos hosts financeiros.

### Onda 4 - Correcao dos subcards

Fechar contraste e superfícies internas:

1. headlines
2. subtitles
3. copy
4. disclosures
5. cards analiticos
6. pills e chips internos

Entregavel:

1. diff nos subcards com validacao visual por familia.

### Onda 5 - Smoke visual

Executar smoke do financeiro dark:

1. `finance-trend-board`
2. `finance-ai-board`
3. `finance-queue-board`
4. `finance-priority-board`
5. `finance-overdue-support-board`

Checklist:

1. contraste de titulos
2. contraste de copy
3. ausencia de moldura duplicada
4. diferenca clara entre familias visuais
5. legibilidade em `>=1280px` e `900-1024px`

## Prompt operacional reutilizavel

Use este prompt quando quisermos auditar ou corrigir a familia inteira de cards do financeiro sem cair em correcoes isoladas:

```text
Voce vai atuar como auditor e executor de dark mode do financeiro do OctoBOX.

Objetivo:
mapear e corrigir todos os cards e boards financeiros que compartilham o mesmo problema visual, em vez de atacar um por um.

Escopo:
- tela principal do financeiro
- hosts: finance-board-shell, finance-board-trend, finance-board-trend-side
- modifiers: is-rail, is-queue, is-support, is-analytics
- subcards: finance-board-subsurface, finance-guide-card, finance-followup-window-card, finance-analytics-*grid, finance-analytics-disclosure, finance-followup-line, finance-trend-metric-pill

Ordem obrigatoria:
1. localizar ownership real em templates e CSS
2. classificar o problema por familia
3. dizer se o bug e de host, subcard, token ou divisoria interna
4. corrigir primeiro os hosts, depois o miolo
5. atualizar docs se surgir um padrao novo

Arquivos de referencia obrigatorios:
- docs/map/front-end-ownership-map.md
- docs/plans/finance-visual-bridge-risk-inventory.md
- docs/map/front-end-error-patterns-map.md
- static/css/catalog/finance/_boards.css
- static/css/catalog/finance/_cards.css
- static/css/catalog/finance/_signature.css
- static/css/catalog/finance/_dark.css
- static/css/catalog/finance/_shell.css

Regras:
- nao corrigir card por card sem classificar a familia
- nao criar segundo tema local por cima do host
- nao usar !important
- se aparecer padrao novo, registrar no roadmap
- priorizar contraste, hierarquia e ownership

Formato da resposta:
1. familia de problema
2. owner correto
3. arquivos a mexer
4. patch proposto
5. risco de debito tecnico
6. validacao necessaria
```

## Check de sucesso

O plano esta funcionando quando:

1. a proxima correcao do financeiro comeca por familia, nao por card isolado.
2. os boards deixam de parecer “quase iguais, mas estranhos”.
3. a leitura do dark mode melhora sem aumentar a quantidade de overrides.
