<!--
ARQUIVO: C.O.R.D.A. para simplificar a superficie de Smart Paste e promover Templates ao corredor principal de WOD.

TIPO DE DOCUMENTO:
- plano arquitetural e operacional
- trilho de UX e implementacao incremental

AUTORIDADE:
- alta para a evolucao do corredor de WOD entre Smart Paste, Templates, Planner e Aprovacoes

DOCUMENTOS PAIS:
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)
- [operations-workspace-views-refactor-corda.md](operations-workspace-views-refactor-corda.md)
- [coach-wod-approval-corda.md](coach-wod-approval-corda.md)
- [../reference/operations-wod-ownership-map.md](../reference/operations-wod-ownership-map.md)

QUANDO USAR:
- quando a duvida for como limpar a UX do Smart Paste sem amputar capacidade
- quando quisermos promover Templates para navegacao principal do corredor de WOD
- quando precisarmos conectar Planner e catalogo de templates com atalhos rapidos e baixo atrito

POR QUE ELE EXISTE:
- evita que o Smart Paste siga carregando explicacao visual redundante
- impede a criacao de uma tela paralela de Templates quando a rota canonica ja existe
- organiza a feature em camadas claras de navegacao, UX, ownership e validacao

O QUE ESTE ARQUIVO FAZ:
1. formaliza o problema atual de UX no corredor de WOD
2. define a direcao de produto e arquitetura para Templates como tab principal
3. registra riscos de acoplamento, duplicacao e atrito operacional
4. organiza a execucao por ondas pequenas e testaveis
5. entrega um prompt operacional reutilizavel para a implementacao

PONTOS CRITICOS:
- o corredor de Templates ja existe em `/operacao/wod/templates/`; a feature deve promover, nao duplicar
- atalhos do Planner devem abrir ou acionar o corredor canonico, sem mover o editor pesado para dentro do cockpit
- a simplificacao do Smart Paste nao pode apagar contexto critico de parse, confirmacao e replicacao
-->

# C.O.R.D.A. - Templates no corredor principal do WOD

## C - Contexto

O corredor atual de WOD ja tem pecas importantes prontas:

1. `Smart Paste` em `templates/operations/workout_smart_paste.html`
2. `Planner` em `templates/operations/workout_planner.html`
3. `Templates` persistentes em `templates/operations/workout_template_management.html`
4. navegacao compartilhada em `operations/workout_corridor_navigation.py`

Hoje, porem, a experiencia ainda carrega friccao desnecessaria.

Estado observado:

1. o `Smart Paste` ainda abre com um stepper visual de 3 cards que ocupa altura nobre da tela
2. esse stepper repete algo que o proprio fluxo ja explica por titulo, formulario e preview
3. a tela de `Templates` existe, mas ainda nao foi promovida ao primeiro trilho mental do usuario
4. o `Planner` ja mostra ranking de templates quentes, mas sem atalhos rapidos de manutencao

Em linguagem simples:

1. ja temos cozinha, despensa e balcao
2. o problema e que a placa da cozinha esta escondida e o balcao ainda fala demais antes de servir

### Leitura de produto correta

O usuario operacional nao pensa em "feature isolada".
Ele pensa em um corredor:

1. colar uma semana
2. transformar uma semana boa em template
3. revisar templates prontos
4. aplicar template no planner
5. mandar para fila ou publicar conforme a politica

Se a interface separar essas partes sem costura:

1. o usuario reaprende o produto toda vez
2. o catalogo de templates parece secundario
3. o Planner perde forca como cockpit

### Leitura arquitetural correta

Pelo ownership atual:

1. `Smart Paste` continua dono do fluxo de parse e confirmacao
2. `Templates` continua dono da edicao persistente pesada
3. `Planner` continua dono do cockpit semanal e dos atalhos contextuais
4. a navegacao do corredor deve expor isso sem criar rota paralela ou editor duplicado

## O - Objetivo

Simplificar o `Smart Paste`, promover `Templates` para a navegacao principal do corredor de WOD e adicionar atalhos contextuais no `Planner`, sem criar arquitetura paralela e sem empurrar logica pesada para a tela errada.

### Sucesso significa

1. o bloco `<section class="smart-paste-stepper">` deixa de existir no Smart Paste
2. a tab `Templates` aparece entre `Smart Paste` e `Aprovacoes`
3. a tab aponta para a rota canonica ja existente `workout-template-management`
4. o `Planner` ganha atalhos rapidos para `Editar`, `Duplicar` e `Ver templates`
5. o usuario entende o ciclo `colar -> salvar template -> aplicar no planner -> aprovar/publicar`
6. mobile continua usavel nas tres superficies: Smart Paste, Templates e Planner

### Nao objetivo desta onda

1. reescrever o editor de templates
2. mover toda a manutencao de template para dentro do Planner
3. criar workflow novo de aprovacao
4. reinventar a rota de Templates

## R - Riscos

### 1. Duplicar o corredor de Templates

Se criarmos uma nova mini-tela de templates dentro do Planner ou do Smart Paste:

1. ownership fica turvo
2. manutencao dobra
3. o usuario encontra duas verdades para a mesma coisa

### 2. Tirar contexto demais do Smart Paste

Se removermos o stepper e nao deixarmos nenhuma hierarquia boa no topo:

1. a tela pode ficar mais limpa
2. mas pode perder orientacao para usuario novo

Regra:

1. remover redundancia visual
2. manter clareza textual no hero e no card principal

### 3. Transformar o Planner em editor pesado

Se os atalhos do ranking abrirem formularios grandes ali mesmo:

1. o cockpit perde foco
2. a tela fica densa demais
3. mobile degrada

Regra:

1. o Planner aponta e acelera
2. o corredor de Templates continua editando de verdade

### 4. Ordem de tabs incoerente por papel

Hoje `Aprovacoes` e restrita a `owner` e `manager`.
`Templates` e `Smart Paste` aceitam `coach` e `owner`.

Se a navegacao nao respeitar isso:

1. a ordem visual quebra por papel
2. o usuario perde previsibilidade

Regra:

1. manter ordem canonica
2. esconder apenas o que o papel nao pode usar
3. nao embaralhar a sequencia restante

### 5. Atalho sem contexto de permissao

Se um coach clicar em `Editar` num template que nao e dele:

1. a UX pode frustrar
2. mesmo que a view proteja o backend

Regra:

1. a UI deve antecipar quando a acao e so leitura ou redirecionamento
2. quando houver restricao, deixar isso claro no proprio card

## D - Direcao

### Tese central

Promover `Templates` como corredor oficial reutilizavel e usar o `Planner` como cockpit de acesso rapido, enquanto o `Smart Paste` fica mais silencioso e mais direto.

### Regra-mestra

1. uma tela faz onboarding do fluxo
2. outra persiste e edita
3. outra acelera a operacao contextual

Traducao:

1. `Smart Paste` organiza
2. `Templates` governa
3. `Planner` despacha

### Contrato de UX por superficie

#### 1. Smart Paste

Papel:

1. receber texto cru
2. organizar a semana
3. confirmar preview
4. oferecer ponte clara para transformar isso em template

Mudanca estrutural:

1. remover o stepper visual de 3 cards
2. fortalecer hero, titulo do card e copy curta
3. manter o fluxo concentrado no formulario e preview

#### 2. Templates

Papel:

1. ser o catalogo canonico de templates prontos
2. concentrar edicao persistente, duplicacao, toggle e metadata
3. virar a tab oficial para "biblioteca reutilizavel"

Mudanca estrutural:

1. promover a rota atual para a navegacao principal
2. melhorar leitura operacional da listagem se necessario
3. deixar actions rapidas visiveis e escaneaveis

#### 3. Planner

Papel:

1. mostrar onde existe oportunidade de reutilizacao
2. aplicar template rapidamente
3. dar acesso contextual ao catalogo e a manutencao dos templates quentes

Mudanca estrutural:

1. adicionar CTAs leves no ranking de templates
2. manter o modal de aplicar template como acao rapida
3. mandar edicao profunda para a tela canonica de Templates

### Ordem recomendada das tabs

Ordem canonica:

1. `Planner`
2. `Smart Paste`
3. `Templates`
4. `Aprovacoes`
5. `Historico`
6. `Resumo executivo`

Observacao:

1. por papel, alguns itens somem
2. mas a ordem relativa do que sobra deve continuar a mesma

### Melhorias recomendadas junto da feature

Estas melhoram o valor da onda sem inflar demais o escopo:

1. CTA `Salvar como template` depois da confirmacao bem-sucedida do Smart Paste
2. badge de origem e governanca nos templates: `Confiavel`, `Vai para aprovacao`, `Criado por mim`, `Frio`
3. CTA `Ver todos os templates` no painel do Planner
4. empty state mais pedagogico na tela de Templates

### Antialvos oficiais

Nao fazer agora:

1. CRUD novo de templates fora do corredor atual
2. drawer modal gigante de edicao dentro do Planner
3. nova semantica de aprovacao
4. abstrair tabs para um framework generico novo

## A - Acoes por ondas

## Onda 0 - Costura do corredor

### Objetivo

Alinhar navegacao e ownership antes de polir layout.

### Acoes

1. adicionar a tab `Templates` em `operations/workout_corridor_navigation.py`
2. apontar para `workout-template-management`
3. revisar ordem por papel para `coach`, `owner` e `manager`

### Check de pronto

1. o corredor fica navegavel sem criar rota nova
2. a sequencia mental do produto passa a aparecer na UI

## Onda 1 - Limpeza do Smart Paste

### Objetivo

Remover ruido visual sem perder orientacao.

### Acoes

1. excluir o bloco `smart-paste-stepper`
2. reforcar copy do hero e do card principal se necessario
3. revisar espacamento acima da area de colagem
4. validar mobile da dobra inicial

### Check de pronto

1. a tela abre mais rapido cognitivamente
2. a primeira acao visivel e colar/organizar texto

## Onda 2 - Promocao visual de Templates

### Objetivo

Transformar a tela existente em catalogo principal do corredor.

### Acoes

1. revisar hierarquia da tela `workout_template_management.html`
2. destacar actions de uso frequente
3. melhorar empty state e leitura de badges
4. garantir que a tela converse bem com mobile

### Check de pronto

1. o usuario entende que ali vivem os templates prontos
2. a edicao continua centralizada num lugar so

## Onda 3 - Atalhos no Planner

### Objetivo

Dar velocidade operacional sem deslocar ownership.

### Acoes

1. adicionar CTAs leves em `wod-planner__usage-ranking-list`
2. expor pelo menos `Editar` e `Duplicar`
3. adicionar acesso para `Ver todos os templates`
4. manter os atalhos consistentes com permissao e ownership do template

### Check de pronto

1. o Planner vira balcao de despacho, nao editor pesado
2. o caminho para manutencao de template cai para poucos cliques

## Onda 4 - Fechamento do loop Smart Paste -> Template

### Objetivo

Conectar autoria semanal com reutilizacao futura.

### Acoes

1. desenhar o CTA `Salvar como template` no momento certo do Smart Paste
2. definir se a acao nasce com modal leve ou redirect assistido
3. garantir que nome, descricao curta e confianca inicial tenham fluxo claro

### Check de pronto

1. uma semana boa pode virar template sem friccao
2. o usuario sente continuidade entre as telas

## Prompt operacional de execucao

Versao:

1. `wod-smart-paste-templates-corridor-v1`

Objetivo:

1. implementar a promocao de `Templates` no corredor principal de WOD
2. simplificar a abertura do `Smart Paste`
3. adicionar atalhos contextuais de templates no `Planner`

Modelo alvo:

1. agente de implementacao no repo do OctoBox com leitura de docs e validacao real de UI mobile

Inputs:

1. `templates/operations/workout_smart_paste.html`
2. `templates/operations/workout_planner.html`
3. `templates/operations/workout_template_management.html`
4. `operations/workout_corridor_navigation.py`
5. CSS e JS locais das superficies tocadas

Assumptions:

1. a rota canonica de templates continua sendo `workout-template-management`
2. o Planner nao deve absorver edicao pesada
3. mobile e parte obrigatoria do aceite

Non-goals:

1. criar um CRUD novo
2. redesenhar a aprovacao do WOD
3. trocar a arquitetura de ownership entre Smart Paste, Templates e Planner

Constraints:

1. ler docs do projeto antes de editar
2. preservar o ownership atual de cada superficie
3. usar mudancas pequenas e testaveis
4. validar mobile em runtime real

Output contract:

1. listar contexto e suposicoes
2. implementar por ondas pequenas
3. validar a UI no browser
4. rodar checks locais relevantes
5. registrar riscos ou debito tecnico residual

Quality bar:

1. a feature reduz atrito em vez de apenas mover botoes
2. a navegacao fica mais previsivel
3. o corredor continua com ownership claro
4. mobile continua bonito e utilizavel

Fallback behavior:

1. se existir conflito entre docs e runtime, o runtime vence e o doc drift deve ser apontado
2. se a acao exigir ampliar escopo para backend pesado, parar na onda atual e registrar o corte
