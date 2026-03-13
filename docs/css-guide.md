<!--
ARQUIVO: guia operacional de CSS do projeto.

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

Regra central:

1. CSS aqui nao pode nascer como remendo solto.
2. cada classe relevante precisa ter casa certa, responsabilidade clara e efeito previsivel.
3. nenhum bloco importante deve depender de coincidencia de heranca para funcionar bem.

## Mapa real do CSS

Hoje a base esta organizada em duas entradas principais:

1. [static/css/design-system.css](../static/css/design-system.css) para o shell autenticado e o design system base
2. [static/css/catalog-system.css](../static/css/catalog-system.css) para as telas visuais do catalogo

Dentro disso, a divisao atual e:

1. [static/css/design-system/core.css](../static/css/design-system/core.css)
define tokens, layout estrutural, topbar, sidebar, hero e componentes base

2. [static/css/design-system/workspaces.css](../static/css/design-system/workspaces.css)
define variacoes e estruturas das areas operacionais e dashboards fora do catalogo

3. [static/css/catalog/shared.css](../static/css/catalog/shared.css)
define utilitarios, grids de formulario, blocos neutros, glass panels e bases compartilhadas do catalogo

4. [static/css/catalog/students.css](../static/css/catalog/students.css)
define ajustes finais da area de alunos

5. [static/css/catalog/finance.css](../static/css/catalog/finance.css)
define layout, cards, rail, carteira, tendencia e comportamento responsivo do financeiro

6. [static/css/catalog/class-grid.css](../static/css/catalog/class-grid.css)
define a grade visual de aulas

## Regra de localizacao

Antes de criar ou editar uma classe, decida em qual camada ela pertence.

Use esta regra:

1. se a classe mexe com token global, input base, shell, topbar, sidebar ou componente universal, ela pertence ao design system
2. se a classe e utilitaria, neutra ou compartilhada entre alunos, financeiro e grade, ela pertence ao shared do catalogo
3. se a classe existe para uma tela ou modulo especifico, ela pertence ao arquivo da propria area
4. se a classe e importante para leitura daquela tela, ela deve existir no CSS local da area, mesmo quando tambem herda algo compartilhado

Traducao pratica:

1. `glass-panel` e base compartilhada
2. `finance-radar-card` e semantica local do financeiro
3. `student-focus-card` e semantica local de alunos

## Regra de naming

O projeto ja usa um padrão bom: namespace por area e nomes orientados a papel.

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
3. um namespace `finance-*` aparecer no HTML sem seletor em [static/css/catalog/finance.css](../static/css/catalog/finance.css) nem em [static/css/catalog/shared.css](../static/css/catalog/shared.css)

Exemplo do que e robusto:

1. o bloco tem base compartilhada
2. o bloco tem classe semantica propria
3. o CSS local define o que faz aquele bloco existir como entidade visual

Formula recomendada:

1. base compartilhada para comportamento neutro
2. classe local para papel do bloco
3. modificador curto apenas quando houver variacao real

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

## Anti-padroes que este projeto deve evitar

1. classe no template sem seletor nenhum no CSS relevante
2. seletor herdado de outro modulo sem contrato claro
3. bloco importante sem classe semantica propria
4. grid principal com filhos sem `grid-column` quando a distribuicao da tela depende disso
5. media query corrigindo estrutura que deveria nascer correta fora dela
6. regra local escondida em shared sem motivo real
7. CSS morto acumulado sem uso nem explicacao

## Checklist antes de subir alteracao de CSS

1. a classe nova esta no arquivo certo?
2. o nome dela descreve papel e nao so look?
3. o template usa alguma classe `finance-*`, `student-*` ou similar sem seletor correspondente?
4. o bloco principal tem contrato explicito de largura, hierarquia e papel?
5. desktop e mobile continuam previsiveis?
6. botoes de uma mesma familia continuam alinhados no mesmo lugar mental?
7. existe algum bloco competindo porque faltou espacamento ou porque a hierarquia da largura esta errada?

## Workflow de debug recomendado

Quando um CSS parecer “estranho”, siga esta ordem:

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

## Resumo operacional

Se precisar decidir rapido, siga esta regra curta:

1. shared para base neutra
2. arquivo da area para semantica local
3. classe importante sempre com contrato explicito
4. grid principal sempre com largura clara
5. debug primeiro em estrutura, depois em polimento

Se quiser a versao curta para rotina de PR, use [front-pr-checklist.md](front-pr-checklist.md).
