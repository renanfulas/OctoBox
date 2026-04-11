<!--
ARQUIVO: guia operacional de CSS do projeto.

TIPO DE DOCUMENTO:
- guia operacional de front-end

AUTORIDADE:
- media

DOCUMENTO PAI:
- [front-display-wall.md](front-display-wall.md)

QUANDO USAR:
- quando a duvida for onde um estilo deve morar, como manter consistencia visual e como depurar CSS sem remendo

POR QUE ELE EXISTE:
- transforma o CSS da base em um sistema legivel, previsivel e seguro de evoluir.

O QUE ESTE ARQUIVO FAZ:
1. explica a arquitetura real dos CSS do projeto.
2. define como decidir onde cada estilo deve morar.
3. registra regras para naming, layout, responsividade e debug.
4. evita que novos estilos nascam por coincidencia ou heranca fragil.

PONTOS CRITICOS:
- este guia precisa acompanhar a organizacao real dos arquivos em static/css.
- se ele ficar generico demais, perde valor e vira decoracao documental.
-->

# Guide inteligente de CSS

## Objetivo

Este guide existe para que o CSS do projeto continue simples de ler, facil de localizar e seguro de expandir.

Para decidir o tema visual oficial antes de decidir onde a classe mora, use [../architecture/themeOctoBox.md](../architecture/themeOctoBox.md).

Regra central:

1. CSS aqui nao pode nascer como remendo solto.
2. cada classe relevante precisa ter casa certa, responsabilidade clara e efeito previsivel.
3. nenhum bloco importante deve depender de coincidencia de heranca para funcionar bem.

## Canon do ultimo pintor

Depois da unificacao do tema, este projeto passou a operar com uma regra simples:

1. existe um pintor definitivo
2. os pintores antigos viraram referencia historica
3. nenhum arquivo novo pode voltar a criar uma autoridade visual paralela
4. a assinatura premium forte so pode nascer por escopo aprovado

Traducao pratica:

1. cor, sombra, borda e glow nascem dos tokens
2. cards, hero, notice e topbar nascem dos hosts canonicos
3. CSS local monta a pagina, mas nao reinventa a familia visual
4. a familia visual oficial atual e governada pelo tema Luxo Futurista 2050 definido em [../architecture/themeOctoBox.md](../architecture/themeOctoBox.md)
5. o brilho mais forte fica reservado para escopos premium aprovados no criterio arquitetural

### Autoridades canonicas

Estas sao as familias que mandam no tema:

1. tokens semanticos: [static/css/design-system/tokens.css](../../static/css/design-system/tokens.css)
2. card e table-card: [static/css/design-system/components/cards.css](../../static/css/design-system/components/cards.css)
3. hero: [static/css/design-system/components/hero.css](../../static/css/design-system/components/hero.css)
4. notice-panel e state-notice: [static/css/design-system/components/states.css](../../static/css/design-system/components/states.css)
5. topbar: [static/css/design-system/topbar.css](../../static/css/design-system/topbar.css)

### Variantes oficiais

Entre o host canonico e o CSS local agora existe uma camada oficial de variantes.

Ela mora aqui:

1. hero variants: [static/css/design-system/components/hero-variants.css](../../static/css/design-system/components/hero-variants.css)
2. card variants: [static/css/design-system/components/card-variants.css](../../static/css/design-system/components/card-variants.css)

Responsabilidade dessa camada:

1. ajustar knobs do host por semantica
2. definir familias oficiais como `hero--command`, `hero--feature`, `card--support` e `card--priority`
3. absorver repeticoes visuais que aparecem em mais de uma tela

Regra pratica:

1. se duas telas pedem a mesma pele para `hero`, `card` ou `table-card`, isso deve virar variante oficial
2. se uma classe local precisa redefinir fundo, borda ou sombra estrutural de um host canonico, pare e reavalie
3. o caminho preferido agora e `token -> host -> variante -> composicao local`

### Legado permitido apenas como ponte

Estas familias nao sao mais soberanas:

1. `glass-panel`
2. `finance-glass-panel`
3. `note-panel*`
4. `elite-glass-card`
5. `glass-panel-elite`
6. `ui-card`

Elas podem aparecer durante migracoes controladas, mas nao podem mais:

1. definir o container principal de uma superficie
2. escolher a identidade visual de uma pagina
3. competir com `card`, `hero`, `notice-panel` ou `topbar`

Em linguagem simples:

1. o balde oficial de tinta agora e um so
2. os potes antigos podem ajudar em pequenos retoques
3. mas nao podem mais escolher a cor da parede

## Mapa real do CSS

Hoje a base esta organizada em uma entrada global e complementos por pagina:

1. [static/css/design-system.css](../../static/css/design-system.css) para o shell autenticado e o design system base
2. [static/css/catalog/shared.css](../../static/css/catalog/shared.css) como base reutilizavel do catalogo
3. [static/css/catalog/students.css](../../static/css/catalog/students.css), [static/css/catalog/finance/](../../static/css/catalog/finance/) e [static/css/catalog/class-grid.css](../../static/css/catalog/class-grid.css) carregados apenas nas telas que precisam deles

Dentro disso, a divisao atual e:

1. [static/css/design-system.css](../../static/css/design-system.css)
define o manifesto base do shell autenticado, importando tokens, shell, sidebar, topbar, compass e componentes compartilhados

2. [static/css/design-system/operations.css](../../static/css/design-system/operations.css)
define variacoes e estruturas das areas operacionais, access e a base operacional reutilizada pelo catalogo

3. [static/css/design-system/dashboard.css](../../static/css/design-system/dashboard.css)
define ajustes especificos do dashboard sem contaminar operations ou catalogo

4. [static/css/design-system/components.css](../../static/css/design-system/components.css)
agora funciona como manifesto estavel dos componentes compartilhados e delega a implementacao para modulos menores

5. [static/css/design-system/components/hero.css](../../static/css/design-system/components/hero.css)
define o hero compartilhado e seus stats laterais

6. [static/css/design-system/components/hero-variants.css](../../static/css/design-system/components/hero-variants.css)
define personalidades oficiais do hero sem recriar um segundo host

7. [static/css/design-system/components/cards.css](../../static/css/design-system/components/cards.css)
define cards, table-cards, panel-grid, layout-grid e metricas

8. [static/css/design-system/components/card-variants.css](../../static/css/design-system/components/card-variants.css)
define personalidades oficiais de `card` e `table-card`

9. [static/css/design-system/components/tables.css](../../static/css/design-system/components/tables.css)
define a apresentacao tabular compartilhada

10. [static/css/design-system/components/pills.css](../../static/css/design-system/components/pills.css)
define badges, pills e variacoes de status/ocupacao

11. [static/css/design-system/components/actions.css](../../static/css/design-system/components/actions.css)
define botoes, barras de acao e listas de capacidade

12. [static/css/design-system/components/states.css](../../static/css/design-system/components/states.css)
define empty states, notices, `notice-panel` e mensagens

13. [static/css/design-system/components/quick-cards.css](../../static/css/design-system/components/quick-cards.css)
define quick cards e accent bars

14. [static/css/catalog/shared.css](../../static/css/catalog/shared.css)
define utilitarios, grids de formulario e bases compartilhadas do catalogo sem autoridade de tema

13. [static/css/catalog/students.css](../../static/css/catalog/students.css)
define apenas o diretorio de alunos e sua vitrine operacional

14. [static/css/catalog/student_form_stepper.css](../../static/css/catalog/student_form_stepper.css)
define a hierarquia propria da ficha do aluno, mapa de leitura, progressao e acabamento local do workspace

15. [static/css/catalog/finance/](../../static/css/catalog/finance/)
define layout, cards, rail, carteira, tendencia e comportamento responsivo do financeiro

16. [static/css/catalog/class-grid.css](../../static/css/catalog/class-grid.css)
define a grade visual de aulas

## Regra de localizacao

Antes de criar ou editar uma classe, decida em qual camada ela pertence.

Use esta regra:

1. se a classe mexe com token global, input base, shell, topbar, sidebar ou componente universal, ela pertence ao design system
2. se a classe e utilitaria, neutra ou compartilhada entre alunos, financeiro e grade, ela pertence ao shared do catalogo
3. se a classe existe para uma tela ou modulo especifico, ela pertence ao arquivo da propria area
4. se a classe e importante para leitura daquela tela, ela deve existir no CSS local da area, mesmo quando tambem herda algo compartilhado
5. se a mudanca pede assinatura premium forte, ela so entra depois de passar no criterio de escopo do tema em [../architecture/themeOctoBox.md](../architecture/themeOctoBox.md)

Regra nova para evitar regressao:
se a tela for a ficha do aluno, a hierarquia do mapa, a progressao e o workspace financeiro nao podem nascer em `students.css`.
essa tela usa `catalog/shared.css` como base estrutural e `catalog/student_form_stepper.css` como autoridade de hierarquia local.

Traducao pratica:

1. `card` e `table-card` sao base compartilhada canonicamente
2. `finance-radar-card` e semantica local do financeiro
3. `student-focus-card` e semantica local de alunos
4. `glass-panel` pode decorar atmosfera, mas nao pode ser a estrutura-base
5. `student-workspace-map-card` e semantica local da ficha do aluno, nao do diretorio

## Mapa rapido de ownership

Se a alteracao for visual e recorrente, o primeiro passo e cair no modulo certo.

1. hero compartilhado e stats laterais: [static/css/design-system/components/hero.css](../../static/css/design-system/components/hero.css)
2. cards, metric cards, panel-grid e layout-grid: [static/css/design-system/components/cards.css](../../static/css/design-system/components/cards.css)
3. tabela, thead, tbody e empty cell: [static/css/design-system/components/tables.css](../../static/css/design-system/components/tables.css)
4. pills de status, badges e ocupacao: [static/css/design-system/components/pills.css](../../static/css/design-system/components/pills.css)
5. botoes, barras de acao e capability-list: [static/css/design-system/components/actions.css](../../static/css/design-system/components/actions.css)
6. empty state, `notice-panel`, `state-notice` e mensagens: [static/css/design-system/components/states.css](../../static/css/design-system/components/states.css)
7. quick cards e accent bar: [static/css/design-system/components/quick-cards.css](../../static/css/design-system/components/quick-cards.css)
8. estrutura operacional da pagina: [static/css/design-system/operations.css](../../static/css/design-system/operations.css)
9. visual exclusivo do dashboard: [static/css/design-system/dashboard.css](../../static/css/design-system/dashboard.css)
10. semantica local de catalogo: arquivos de [static/css/catalog](../../static/css/catalog)

## Regra de soberania visual

Esta e a regra mais importante do guide a partir de agora.

### O que pode mandar

So pode mandar na identidade visual:

1. `tokens.css` para semantica de tema
2. `cards.css` para surfaces e containers principais
3. `hero.css` para faixas de comando
4. `states.css` para notices, mensagens e estados vazios
5. `topbar.css` para a shell rail

### O que nao pode mandar

Nao pode voltar a mandar:

1. arquivo local de pagina redefinindo a familia de `card`
2. `utilities.css` criando tema paralelo
3. modulo local inventando outra `topbar`
4. helper atmosferico decidindo estrutura base
5. patch de emergencia com `!important` para ganhar no grito

### Regra operacional

Quando houver duvida, use esta escada:

1. token semantico
2. primitivo canonico
3. variante oficial
4. classe semantica local
5. helper neutro

Nunca ao contrario.

## Regra de escopo premium

Escopo premium nao e um atalho para deixar qualquer tela mais bonita.

Ele existe para concentrar a assinatura forte do produto nas superfices certas.

### Quando usar

1. dashboard, fachada principal ou area de alta percepcao de valor
2. telas que concentram hero, CTA dominante ou leitura executiva
3. superfices cuja frequencia e importancia justificam assinatura mais forte

### Quando nao usar

1. formularios utilitarios
2. fluxos intermediarios
3. telas com hierarquia ainda imatura
4. areas onde silencio visual vale mais do que impacto

### Regra pratica de implementacao

1. primeiro estabilizar com token global
2. depois aplicar classe local semantica
3. so entao promover para `data-shell-scope` ou cena premium
4. se a tela precisar de muitas excecoes, retirar do escopo premium

Em linguagem simples:

1. primeiro a casa precisa estar arrumada
2. depois a gente escolhe qual comodo merece luz de vitrine

## Regra de naming

O projeto ja usa um padrÃ£o bom: namespace por area e nomes orientados a papel.

Mantenha assim:

1. `finance-*` para financeiro
2. `student-*` para alunos e intake
3. `operation-*` para estruturas operacionais
4. `dashboard-*` para dashboard
5. `stack-*`, `field-grid-*`, `section-*`, `text-*` para utilitarios compartilhados

Regra de ouro:

1. nome de classe deve dizer o papel do bloco, nao so sua aparencia
2. prefira `finance-board-support-rail` a `right-column`
3. prefira `finance-radar-card` a `green-card`
4. prefira `finance-focus-item` a `card-row-2`

## Regra de contrato explicito

Este e o ponto mais importante do guide.

Se uma classe aparece no template como parte importante da leitura da pagina, ela precisa ter contrato explicito no CSS correspondente.

Nao confie apenas em:

1. heranca indireta
2. utilitario aplicado por sorte
3. comportamento vindo de outra classe que so esta presente por acaso

Exemplo do que e fragil:

1. um card importante usar so `finance-support-card` sem classe propria da funcao dele
2. um bloco de grid existir no template sem seletor local definindo sua coluna, largura ou papel
3. um namespace `finance-*` aparecer no HTML sem seletor em [static/css/catalog/finance/](../../static/css/catalog/finance/) nem em [static/css/catalog/shared.css](../../static/css/catalog/shared.css)

Exemplo do que e robusto:

1. o bloco tem base compartilhada
2. o bloco tem classe semantica propria
3. o CSS local define o que faz aquele bloco existir como entidade visual

Formula recomendada:

1. base compartilhada para comportamento neutro
2. classe local para papel do bloco
3. modificador curto apenas quando houver variacao real

Exemplo forte:

1. `card student-directory-surface`
2. `table-card manager-finance-board`
3. `notice-panel notice-panel--warning`

Exemplo fraco:

1. `glass-panel rounded-xl border-soft`
2. `ui-card reports-hub-card`
3. `card glass-panel-elite`

## Como estruturar um arquivo CSS da area

Quando um CSS de area crescer, mantenha a ordem abaixo:

1. cabecalho do arquivo
2. cena geral da pagina e hero
3. grid macro da tela
4. cards e paineis principais
5. componentes internos da area
6. estados compactos e variacoes locais
7. responsividade no final

Ordem ideal dentro do arquivo:

1. shell da area
2. board principal
3. trilhos laterais e subgrids
4. cards de leitura
5. listas, chips, blocos de apoio
6. formularios e acoes
7. media queries

Se um trecho do arquivo passar a falar de outra tela, ele esta no lugar errado.

## Regra de layout macro

Toda tela com grid principal precisa deixar claro:

1. quem ocupa a largura inteira
2. quem ocupa 4, 5, 7 ou 8 colunas
3. quem e trilho lateral
4. quem muda de linha no mobile

Para telas em grid complexo como financeiro:

1. cada bloco principal deve ter `grid-column` explicito quando a largura dele importa
2. cards laterais devem ter `min-width: 0` quando estiverem dentro de colunas apertadas
3. listas em grid nao devem depender apenas de `stack-*` para existir se forem semanticas da tela
4. blocos ancora devem usar `scroll-margin-top` se a topbar for sticky

## Regra de cards

Card bom aqui nao e so bonito. Ele precisa deixar claro:

1. o que ele e
2. por que existe
3. qual bloco manda e qual bloco apoia
4. onde a acao mora

Padrao recomendado:

1. `operation-card-head` para cabeca compartilhada
2. copy curta e funcional
3. CTA no mesmo lugar mental dentro de cards da mesma familia
4. altura consistente apenas quando isso melhora comparacao visual

Quando usar `height: 100%`:

1. em grids onde os cards precisam alinhar entre si
2. quando o card tem rail de botoes ou footer que deve descer para a base

Quando nao usar:

1. em blocos que dependem de conteudo livre e nao competem entre si
2. quando o alongamento artificial piora a leitura

## Regra de responsividade

Nao trate mobile como remendo no fim.

Cada bloco novo precisa responder estas perguntas:

1. no desktop ele e largura principal, secundaria ou apoio?
2. no tablet ele empilha ou ainda compara lado a lado?
3. no mobile ele continua legivel sem CTA esmagado?

Padrao atual da base:

1. telas principais quebram em `max-width: 960px`
2. ajustes mais agressivos entram perto de `720px` ou `640px`

Regras praticas:

1. reduza para uma coluna cedo quando o card comeca a competir demais
2. botoes em cards laterais podem ir para largura total no mobile
3. grids de metricas e chips devem quebrar antes de virar mosaico apertado

## Regra de utilitarios compartilhados

Utilitario e para acelerar, nao para esconder intencao.

Use utilitario quando ele for realmente neutro:

1. `stack-8`, `stack-14`, `stack-16`
2. `field-grid-200`, `field-grid-220`, `field-grid-240`
3. `section-gap-*`, `text-muted`, `no-margin`

Nao use utilitario como substituto de classe semantica quando:

1. o bloco e importante para o entendimento da tela
2. a largura, hierarquia ou papel dele precisam ser declarados no modulo local
3. uma futura pessoa precisara encontrar aquele comportamento por nome de dominio

Regra nova:

1. utilitario pode ajudar espacamento e layout
2. utilitario nao pode fundar a familia visual do bloco
3. helper atmosferico nao pode substituir `card`, `hero` ou `notice-panel`

## Anti-padroes que este projeto deve evitar

1. classe no template sem seletor nenhum no CSS relevante
2. seletor herdado de outro modulo sem contrato claro
3. bloco importante sem classe semantica propria
4. grid principal com filhos sem `grid-column` quando a distribuicao da tela depende disso
5. media query corrigindo estrutura que deveria nascer correta fora dela
6. regra local escondida em shared sem motivo real
7. CSS morto acumulado sem uso nem explicacao
8. usar `glass-panel`, `ui-card` ou `note-panel` como autoridade estrutural nova
9. topbar local com paleta e sombra independentes do tema
10. `!important` para impor identidade visual em vez de corrigir a origem do conflito
11. misturar duas familias base no mesmo bloco estrutural

Exemplos que agora sao proibidos:

1. `table-card glass-panel` para o mesmo papel estrutural
2. `card ui-card`
3. `topbar` com variaveis locais que contradizem `tokens.css`
4. `note-panel` novo criado fora de [states.css](../../static/css/design-system/components/states.css)

## Checklist antes de subir alteracao de CSS

1. a classe nova esta no arquivo certo?
2. o nome dela descreve papel e nao so look?
3. o template usa alguma classe `finance-*`, `student-*` ou similar sem seletor correspondente?
4. o bloco principal tem contrato explicito de largura, hierarquia e papel?
5. desktop e mobile continuam previsiveis?
6. botoes de uma mesma familia continuam alinhados no mesmo lugar mental?
7. existe algum bloco competindo porque faltou espacamento ou porque a hierarquia da largura esta errada?
8. este bloco esta nascendo de `card`, `table-card`, `hero`, `notice-panel` ou `topbar` quando deveria?
9. algum helper legado esta mandando mais do que o host canonico?
10. eu estou resolvendo o problema pela autoridade certa ou so vencendo a cascata no grito?

## Workflow de debug recomendado

Quando um CSS parecer â€œestranhoâ€, siga esta ordem:

1. confirme se nao e erro de sintaxe
2. compare classes do template com seletores do CSS local e do shared
3. identifique quais blocos importantes estao funcionando por coincidencia
4. verifique se o problema e de largura macro, densidade interna ou responsividade
5. so depois faca refinamento visual fino

Perguntas boas de debug:

1. este bloco esta apertado porque a copy e ruim ou porque a coluna esta errada?
2. este card compete com o outro por excesso de informacao ou por falta de distribuicao no grid?
3. esta classe deveria existir no shared ou ela e semantica demais para sair do modulo?
4. o template esta usando um nome que o CSS nao conhece?
5. quem esta mandando neste bloco: o host canonico ou um legado pendurado?
6. este efeito visual nasceu dos tokens ou de uma cor solta copiada no impulso?

## Comandos uteis de verificacao

Para procurar classes e padroes na base, use buscas simples e repetiveis.

Exemplos uteis:

```powershell
rg "finance-" templates/catalog/finance.html
rg "\.finance-" static/css/catalog/finance.css
rg "\.finance-" static/css/catalog/shared.css
rg "scroll-margin|grid-column|grid-template-columns" static/css/catalog/finance.css
```

Quando houver suspeita de classe faltando entre template e CSS, compare os dois lados antes de mexer no visual.

## Regra editorial do CSS deste projeto

O CSS do OctoBox precisa transmitir tres coisas ao mesmo tempo:

1. produto vivo
2. leitura clara
3. operacao robusta

Isso significa:

1. atmosfera visual pode existir
2. brilho e gradiente podem existir
3. identidade forte pode existir
4. mas nada disso pode esconder prioridade, CTA ou recorte operacional

Se um efeito visual deixa a leitura mais lenta, ele perdeu a funcao.

## Contrato final do tema

Se precisar da versao mais curta possivel, guarde isto:

1. `tokens.css` manda nas decisoes semanticas
2. `cards.css` manda nas surfaces
3. `hero.css` manda no topo de pagina
4. `states.css` manda em notice e mensagem
5. `topbar.css` manda na shell rail
6. CSS local compoe, nao reinventa
7. legado so vive como ponte documentada
8. novo pintor paralelo nao entra no predio
9. tema oficial e decidido por [../architecture/themeOctoBox.md](../architecture/themeOctoBox.md), nao por calibracao local solta

## Resumo operacional

Se precisar decidir rapido, siga esta regra curta:

1. shared para base neutra
2. arquivo da area para semantica local
3. classe importante sempre com contrato explicito
4. grid principal sempre com largura clara
5. debug primeiro em estrutura, depois em polimento

Se quiser a versao curta para rotina de PR, use [front-pr-checklist.md](front-pr-checklist.md).
