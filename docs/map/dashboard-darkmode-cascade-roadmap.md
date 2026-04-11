<!--
ARQUIVO: mapa e roadmap da cascata de correcoes do dark mode residual no dashboard.

POR QUE ELE EXISTE:
- transforma uma lista de sintomas visuais em familias de problema com owner claro.
- evita corrigir card por card quando varios blocos falham pelo mesmo motivo estrutural.
- deixa um trilho curto para futuras ondas de hardening de dark mode.

O QUE ESTE ARQUIVO FAZ:
1. agrupa hotspots do dashboard por familia de problema.
2. registra causa raiz, owner correto e risco de cada familia.
3. define a ordem segura para corrigir em cascata sem criar tema paralelo.

PONTOS CRITICOS:
- este documento nao autoriza patch local em massa sem validar o host canonico primeiro.
- se um bloco usa `.card`, `.table-card`, `.pill` ou `metric-card`, a base compartilhada deve vencer antes do dashboard-local.
- o foco aqui e dashboard e shells relacionados; nao use este mapa para redefinir o tema inteiro.
-->

# Dashboard Dark Mode Cascade Roadmap

Este documento responde:

1. por que varios cards diferentes parecem errados pelo mesmo motivo no dark mode
2. qual arquivo realmente manda em cada familia
3. em que ordem corrigir para uma mudanca arrumar varias salas ao mesmo tempo

Em linguagem simples:

1. nao estamos lidando com varios buracos aleatorios na parede
2. estamos vendo rachaduras diferentes vindas das mesmas vigas
3. se reforcarmos a viga certa, varias rachaduras somem juntas

## Veredito rapido

Os sintomas citados nesta rodada se concentram em cinco familias:

1. `metric-card` e seus filhos (`metric-number`, `card-signal`, `card-copy`, `dashboard-kpi-sparkline`)
2. `pill` e as familias semanticas de status e ocupacao
3. `dashboard-support-card` e `#dashboard-sessions-board`
4. tipografia de apoio do dashboard (`operation-card-copy`, `dashboard-session-occupancy-label`, `card-signal-value`)
5. composicao `dashboard-metrics-lead` quando o layout passa a carregar contraste, brilho e densidade ao mesmo tempo

O problema nao e "o dark mode do dashboard inteiro esta quebrado".

O problema real e mais preciso:

1. hosts canonicos ainda carregam receitas light-first
2. familias semanticas de estado nao fecharam seu contrato dark
3. wrappers locais do dashboard viraram um segundo motor de tema

## Ownership curto da superficie

### KPI cards do dashboard

Trilha real:

1. template: [../../templates/includes/ui/shared/metric_card.html](../../templates/includes/ui/shared/metric_card.html)
2. host canonico: [../../static/css/design-system/components/cards.css](../../static/css/design-system/components/cards.css)
3. refinamento local atual: [../../static/css/design-system/components/dashboard/metrics.css](../../static/css/design-system/components/dashboard/metrics.css)

Elementos afetados:

1. `span.metric-number.is-bad`
2. `div.card-signal.is-warning`
3. `span.card-signal-value`
4. `div.dashboard-kpi-sparkline`
5. `p.metric-note.card-copy`

### Sessions board do dashboard

Trilha real:

1. template: [../../templates/dashboard/blocks/sessions_board.html](../../templates/dashboard/blocks/sessions_board.html)
2. include da sessao destaque: [../../templates/includes/ui/dashboard/dashboard_session_featured_card.html](../../templates/includes/ui/dashboard/dashboard_session_featured_card.html)
3. host canonico base: [../../static/css/design-system/components/cards.css](../../static/css/design-system/components/cards.css)
4. host de estados: [../../static/css/design-system/components/pills.css](../../static/css/design-system/components/pills.css)
5. refinamentos locais atuais: [../../static/css/design-system/components/dashboard/sessions_board.css](../../static/css/design-system/components/dashboard/sessions_board.css) e [../../static/css/design-system/components/dashboard/side.css](../../static/css/design-system/components/dashboard/side.css)

Elementos afetados:

1. `h2.operation-card-title.card-title`
2. `strong` de nomes como `Cross 09h`
3. `span.pill.class-status-scheduled`
4. `span.pill.class-occupancy-critical`
5. `span.dashboard-session-occupancy-label`

### Grid principal do pulso curto

Trilha real:

1. template: [../../templates/dashboard/blocks/metrics_cluster.html](../../templates/dashboard/blocks/metrics_cluster.html)
2. grid local: [../../static/css/design-system/components/dashboard/metrics.css](../../static/css/design-system/components/dashboard/metrics.css)
3. host de card usado dentro do grid: [../../static/css/design-system/components/cards.css](../../static/css/design-system/components/cards.css)

Elemento afetado:

1. `section.dashboard-metrics-lead`

## Padroes raiz encontrados nesta rodada

## Padrao A: host compartilhado ainda light-first

Cheiro:

1. o componente compartilhado funciona no light, mas no dark pede remendo local
2. aparecem varias regras `body[data-theme="dark"]` tentando salvar texto, surface e sombra
3. o mesmo card ganha uma receita base e outra receita especial so para sobreviver no dark

Evidencia atual:

1. [cards.css](../../static/css/design-system/components/cards.css) define `metric-card` com superficies e acentos ainda acoplados a receitas visuais
2. [metrics.css](../../static/css/design-system/components/dashboard/metrics.css) recompra o visual do KPI card com backgrounds, borders, shadows e copy dark
3. [sessions_board.css](../../static/css/design-system/components/dashboard/sessions_board.css) e [side.css](../../static/css/design-system/components/dashboard/side.css) reconstroem superficies e tipografia do board no dark

Leitura:

1. o host canonico ainda nao fecha a promessa sozinho
2. por isso o dashboard-local tenta virar salva-vidas

Classificacao:

1. `canonical primitive drift`

Correcao segura:

1. endurecer primeiro o host canonico
2. so depois podar o repaint local

## Padrao B: familia semantica sem branch dark proprio

Cheiro:

1. a classe semantica existe no shared
2. o dark mode trata a base generica, mas nao fecha todas as subclasses reais
3. algumas pills e estados ficam com contraste torto, tom errado ou personalidade de light mode

Evidencia atual:

1. [pills.css](../../static/css/design-system/components/pills.css) cobre `.pill`, `.pill.info`, `.pill.success`, `.pill.warning` e `.pill.accent` no dark
2. as familias reais do dashboard incluem `class-status-scheduled`, `class-status-in-progress`, `class-status-completed`, `class-occupancy-medium`, `class-occupancy-high`, `class-occupancy-critical`
3. essas familias continuam com receitas raw de fundo e texto fora de um contrato dark mais completo

Leitura:

1. o dicionario do estado existe
2. mas o sotaque do dark mode ainda nao foi ensinado para todas as palavras

Classificacao:

1. `override-hotspot`
2. `duplicate-rule` potencial quando o dashboard tenta compensar localmente

Correcao segura:

1. fechar a semantica em [pills.css](../../static/css/design-system/components/pills.css)
2. evitar resolver status com repaint no board local

## Padrao C: wrapper local virando segundo tema

Cheiro:

1. o template ja declara `.card`, `.table-card` ou `.pill`
2. classes locais como `dashboard-support-card`, `dashboard-table-card`, `dashboard-side-card` e `layout-panel` ainda repintam surface, border, shadow e copy
3. a tela passa a ter uma segunda autoridade visual em cima do host canonico

Evidencia atual:

1. [sessions_board.html](../../templates/dashboard/blocks/sessions_board.html) usa `table-card layout-panel layout-panel--stack dashboard-table-card dashboard-side-card dashboard-support-card`
2. [sessions_board.css](../../static/css/design-system/components/dashboard/sessions_board.css) redefine background, border, shadow, copy e estados internos do board
3. [side.css](../../static/css/design-system/components/dashboard/side.css) redefine novamente `dashboard-support-card`, `dashboard-session-card`, `dashboard-session-time` e `dashboard-session-occupancy-label`

Leitura:

1. o dashboard esta vestindo um casaco proprio por cima do uniforme compartilhado
2. por isso ele nao conversa bem com o resto do produto no dark

Classificacao:

1. `override-hotspot`
2. `duplicate-rule`

Correcao segura:

1. manter wrapper local para layout, sticky e semantica
2. tirar dele o papel de decidir tema base

## Padrao D: tipografia de apoio sem token semantico forte

Cheiro:

1. textos de apoio parecem lavados, escuros ou inconsistentes
2. labels de suporte e microcopy usam `var(--muted)` ou `rgba(...)` local
3. cada modulo escolhe sua propria transparencia de leitura

Evidencia atual:

1. [metrics.css](../../static/css/design-system/components/dashboard/metrics.css) usa varias combinacoes locais para `card-copy`, `card-label` e `card-kicker`
2. [sessions_board.css](../../static/css/design-system/components/dashboard/sessions_board.css) usa `rgba(226, 232, 240, 0.72)` para multiplos textos de apoio
3. [side.css](../../static/css/design-system/components/dashboard/side.css) reaplica `rgba(226, 232, 240, 0.68)` para occupancy labels e meta text

Leitura:

1. o time todo esta usando "cinza claro"
2. mas cada pessoa misturou um balde diferente

Classificacao:

1. `token gap`
2. `canonical primitive drift`

Correcao segura:

1. criar ou promover uma hierarquia semantica clara para support copy em dark
2. reduzir `rgba(...)` manual espalhado pelos modulos

## Padrao E: layout acoplado ao tom visual

Cheiro:

1. o grid parece "errado" principalmente quando o dark acende
2. a estrutura em si nao esta quebrada, mas o peso visual desequilibra a leitura
3. o layout foi calibrado com uma atmosfera e agora herda outra

Evidencia atual:

1. [metrics_cluster.html](../../templates/dashboard/blocks/metrics_cluster.html) monta `dashboard-metrics-lead`
2. [metrics.css](../../static/css/design-system/components/dashboard/metrics.css) fixa `13fr / 8fr`, alturas minimas, gradientes locais e copy de alto contraste dentro do mesmo host

Leitura:

1. o tabuleiro pode estar certo
2. mas as pecas ficaram pesadas demais para a mesma disposicao

Classificacao:

1. `local residual debt`

Correcao segura:

1. primeiro estabilizar host, tokens e hierarquia tipografica
2. so depois recalibrar o grid se o desequilibrio continuar

## Padrao F: shell visual duplicado entre pai e filho

Cheiro:

1. o bloco para de vazar o fundo, mas passa a mostrar uma moldura interna feia
2. a leitura piora porque o olho enxerga mais a caixa do grid do que os cards
3. o dark mode parece "pesado" mesmo com contraste tecnicamente correto

Evidencia atual:

1. `dashboard-metrics-cluster` ganhou uma casca dark para fechar o fundo do grupo
2. `dashboard-metrics-lead` tambem ganhou casca dark e criou o efeito de moldura dupla
3. a foto do runtime mostrou que o problema nao era mais transparencia, e sim ownership visual duplicado

Leitura:

1. pai e filho estavam tentando assinar a mesma arquitetura visual
2. o certo e o pai carregar a casca e o filho voltar a ser apenas grid estrutural

Classificacao:

1. `duplicate-shell-ownership`

Correcao segura:

1. escolher um dono da superficie agrupadora
2. neutralizar o shell interno
3. validar por captura real, porque a cascata sozinha nao conta a historia inteira

## Padrao G: trilha de progresso com largura herdada de fase antiga

Cheiro:

1. a barra de ocupacao parece desalinhada mesmo com `data-visual-width` correto
2. o fill respeita a porcentagem, mas o trilho nao acompanha a largura util do card
3. o bug parece visual, mas a causa raiz e geometrica

Evidencia atual:

1. `.dashboard-session-progress` usava `width: min(233px, 100%)` em `side.css`
2. `#dashboard-sessions-board .dashboard-session-progress` usava `width: min(214px, 100%)` em `sessions_board.css`
3. a largura do card no runtime era maior, entao a barra sempre nascia amputada

Leitura:

1. o card cresceu com o refinamento
2. a barra ficou presa a um numero magico legado

Classificacao:

1. `magic-width residue`

Correcao segura:

1. devolver a trilha para `width: 100%`
2. remover `max-width` artificial
3. medir no runtime se a diferenca restante e apenas padding interno

## Matriz curta dos hotspots citados

| Sintoma citado | Owner real | Familia do erro | Melhor primeiro corte |
| --- | --- | --- | --- |
| `div.card-signal.is-warning` com texto ruim | `metric_card.html` + `dashboard/metrics.css` | host light-first + tipografia de apoio local | fechar `metric-card` e `card-signal` antes de mexer em card isolado |
| `span.metric-number.is-bad` | `metric_card.html` + `dashboard/metrics.css` | host light-first | revisar semantica do KPI card e seus tons |
| `dashboard-kpi-sparkline` | `metric_card.html` + `dashboard/metrics.css` | host light-first | alinhar cor e contraste via host do KPI |
| `p.metric-note.card-copy` | `cards.css` + `dashboard/metrics.css` | support copy sem token forte | promover token/semantica de apoio no dark |
| `h2.operation-card-title.card-title` | `cards.css` + `sessions_board.css` + `side.css` | wrapper local como tema | deixar board local cuidar de contexto, nao de tema base |
| `pill.class-status-scheduled` | `pills.css` | semantica sem branch dark completo | corrigir contrato dark em `pills.css` |
| `pill.class-occupancy-critical` | `pills.css` | semantica sem branch dark completo | corrigir contrato dark em `pills.css` |
| `dashboard-session-occupancy-label` | `side.css` + `sessions_board.css` | support copy sem token forte | puxar para semantica compartilhada de apoio |
| `strong` como `Cross 09h` | `side.css` + `sessions_board.css` | wrapper local como tema | revisar hierarquia do board no host local apos base compartilhada |
| `section.dashboard-metrics-lead` | `metrics_cluster.html` + `dashboard/metrics.css` | layout acoplado ao tom | recalibrar so depois do host |
| `span.card-signal-value` como `Responder hoje` | `metric_card.html` + `dashboard/metrics.css` | support copy sem token forte | alinhar `card-signal` no host compartilhado |

## Roadmap de correção em cascata

## Onda 1: fechar a lingua comum dos estados

Arquivos:

1. [../../static/css/design-system/components/pills.css](../../static/css/design-system/components/pills.css)
2. [../../static/css/design-system/components/cards.css](../../static/css/design-system/components/cards.css)

Objetivo:

1. garantir que `pill`, `metric-card`, `metric-number`, `card-signal` e `card-copy` tenham contrato dark confiavel

Por que vem primeiro:

1. varios sintomas citados reaproveitam esses mesmos hosts
2. se consertarmos primeiro a palavra-base, varias frases melhoram juntas

Pronto quando:

1. status e ocupacao nao dependem de cor light residual
2. `card-signal` e `metric-number` leem bem sem patch do dashboard
3. suporte tipografico do KPI nao precisa de `rgba(...)` local para sobreviver

## Onda 2: desarmar o segundo motor de tema do dashboard

Arquivos:

1. [../../static/css/design-system/components/dashboard/metrics.css](../../static/css/design-system/components/dashboard/metrics.css)
2. [../../static/css/design-system/components/dashboard/sessions_board.css](../../static/css/design-system/components/dashboard/sessions_board.css)
3. [../../static/css/design-system/components/dashboard/side.css](../../static/css/design-system/components/dashboard/side.css)

Objetivo:

1. deixar dashboard-local cuidar de composicao, slot, sticky, densidade e semantica
2. retirar dele a responsabilidade de repintar base, copy e surface inteira

Pronto quando:

1. `dashboard-support-card`, `dashboard-side-card` e `dashboard-table-card` param de competir com `.card` e `.table-card`
2. `#dashboard-sessions-board` usa o host compartilhado como base e o CSS local so afina o contexto
3. o dark mode do board nao precisa reescrever metade da tipografia do card

## Onda 3: recalibrar o tabuleiro depois das pecas

Arquivos:

1. [../../templates/dashboard/blocks/metrics_cluster.html](../../templates/dashboard/blocks/metrics_cluster.html)
2. [../../static/css/design-system/components/dashboard/metrics.css](../../static/css/design-system/components/dashboard/metrics.css)

Objetivo:

1. revisar `dashboard-metrics-lead` so depois de estabilizar as superficies
2. confirmar se o desconforto era estrutural ou se era apenas contraste + densidade

Pronto quando:

1. o cluster principal escaneia bem no dark em ate 3 segundos
2. o card lider continua lider sem virar outdoor
3. o card secundario apoia sem sumir

## Onda 4: smoke visual orientado por familias

Superficies minimas:

1. dashboard principal no dark
2. sessions board com `class-status-scheduled` e `class-occupancy-critical`
3. KPI com `metric-number.is-bad`, `card-signal.is-warning` e `dashboard-kpi-sparkline`
4. topbar e cards compartilhados para confirmar que a linguagem continua uma so

Checklist:

1. texto principal nao cai para preto ou cinza morto
2. support copy continua legivel sem roubar a cena
3. pills mantem semantica sem ficar gritadas
4. wrappers locais nao reabrem um tema paralelo

## Anti-correcoes proibidas

Nao fazer:

1. corrigir cada card isolado com `body[data-theme="dark"]` local novo
2. trocar so a cor do texto sem revisar o host da superficie
3. resolver `pill.class-status-*` dentro de `sessions_board.css`
4. mudar o grid antes de estabilizar signal, copy e surface
5. usar `!important` para "ganhar" do dashboard-local

## Regra final

Se um bug do dashboard em dark mode aparece em:

1. `card-signal`
2. `metric-number`
3. `card-copy`
4. `pill`
5. `dashboard-support-card`

a primeira pergunta nao deve ser:

1. "qual cor eu coloco aqui?"

A primeira pergunta deve ser:

1. "isso e problema do host canonico, da semantica de estado ou do wrapper local?"

Esse filtro e o que vai deixar a correcao em cascata e nao em labirinto.
