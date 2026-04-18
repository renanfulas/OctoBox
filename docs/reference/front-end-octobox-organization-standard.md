<!--
ARQUIVO: padrao oficial de organizacao do front-end e CSS do OctoBox.

TIPO DE DOCUMENTO:
- referencia estrutural de front-end
- padrao operacional de organizacao e crescimento

AUTORIDADE:
- alta para organizacao de CSS, templates, assets por superficie e criterio de split

DOCUMENTOS PAIS:
- [documentation-authority-map.md](documentation-authority-map.md)
- [../plans/front-end-restructuring-guide.md](../plans/front-end-restructuring-guide.md)
- [front-end-city-map.md](front-end-city-map.md)
- [front-end-card-architecture.md](front-end-card-architecture.md)

QUANDO USAR:
- antes de criar ou refatorar CSS novo
- antes de decidir se um estilo entra no design system, no shell da pagina ou numa superficie local
- quando houver duvida entre organizacao saudavel e overengineering

POR QUE ELE EXISTE:
- evita puxadinho visual fora do padrao OctoBox
- reduz risco de monolitos CSS por tela ou por persona
- deixa explicito como uma feature nova nasce no padrao atual sem travar a evolucao futura
- cria guardrails contra gambiarra e tambem contra excesso de arquitetura

O QUE ESTE ARQUIVO FAZ:
1. define o padrao oficial de organizacao do front-end OctoBox
2. explica a arvore de decisao para CSS, templates e comportamento
3. fixa regras de split saudavel e limites contra overengineering
4. documenta sinais de alerta para evitar divida tecnica futura

PONTOS CRITICOS:
- este doc nao substitui o city map nem a card architecture; ele funciona como o manual de construcao
- o padrao oficial precisa acompanhar o runtime real do projeto
- se a estrutura real mudar, este doc deve mudar junto
-->

# Padrao oficial de organizacao do front-end OctoBox

## Tese central

Toda feature nova de front-end do OctoBox deve nascer no padrao de organizacao do produto, e nao como excecao local improvisada.

Em linguagem direta:

1. primeiro entra no corredor certo
2. depois ganha forma visual
3. so depois, se crescer de verdade, merece split proprio

Metafora simples:

1. nao montamos um quarto novo no quintal so porque faltou espaco numa tarde
2. primeiro vemos em qual andar do predio ele pertence
3. so construimos uma ala nova quando o quarto realmente deixou de caber

## O que significa "nascer no padrao OctoBox"

Uma interface nasce no padrao OctoBox quando respeita estes quatro pontos:

1. usa os tokens e componentes do design system existentes antes de inventar estrutura nova
2. entra no shell e na superficie certa do produto
3. mantem CSS, template e comportamento com ownership claro
4. cresce por camadas, sem pular cedo demais para mini-frameworks ou abstrações desnecessarias

## Principio-mestre

`global antes de local, shell antes de excecao, split apenas quando a anatomia realmente mudou`

Essa frase deve decidir quase toda duvida estrutural de front-end no projeto.

## Arquitetura oficial por camadas

O front-end do OctoBox deve ser lido em cinco camadas.

### 1. DNA global

Arquivos tipicos:

1. `static/css/design-system/tokens.css`
2. `static/css/design-system/shell.css`
3. `static/css/design-system/spacing.css`
4. `static/css/design-system/responsiveness.css`

Responsabilidade:

1. tema
2. espaco
3. tipografia
4. superficies base
5. linguagem de contraste e sombra

Regra:

1. so mexa aqui se a mudanca valer para muitas telas
2. nao resolva problema local alterando DNA global por reflexo

### 2. Componentes compartilhados

Arquivos tipicos:

1. `static/css/design-system/components/*.css`
2. `static/css/design-system/components/dashboard/*.css`

Responsabilidade:

1. cards
2. pills
3. hero
4. actions
5. states
6. tabelas

Regra:

1. se o comportamento visual e reutilizavel em mais de uma tela, ele pertence aqui
2. se o caso e unico de uma superficie, ainda nao pertence aqui

### 3. Manifesto de superficie

Arquivos tipicos:

1. `static/css/design-system/operations.css`
2. `static/css/design-system/dashboard.css`
3. `static/css/design-system/financial.css`

Responsabilidade:

1. declarar a entrada publica da superficie
2. importar os modulos internos em ordem previsivel
3. manter a cascade oficial daquela familia de telas

Regra:

1. novo trabalho dentro de `operations` entra por `operations.css`
2. nao inventar um segundo manifesto paralelo para a mesma superficie

### 4. Subsuperficie por persona ou dominio

Arquivos tipicos:

1. `static/css/design-system/operations/dev-coach.css`
2. `static/css/design-system/operations/manager.css`
3. `static/css/design-system/operations/reception.css`

Responsabilidade:

1. organizar um subconjunto da superficie por papel ou cena
2. agrupar modulos especificos sem vazar regra para outras personas

Regra:

1. se a feature e claramente de `coach`, ela nasce no trilho `operations/dev-coach`
2. se depois virar algo compartilhado entre coach, manager e owner, ela pode subir de camada

### 5. Modulo local da feature

Arquivos tipicos:

1. `static/css/design-system/operations/dev-coach/coach.css`
2. futuros arquivos como `coach-wod-editor.css`, `coach-wod-approval.css`

Responsabilidade:

1. resolver a feature concreta
2. aplicar o clima local
3. acomodar layout proprio da experiencia

Regra:

1. comeca pequeno aqui
2. cresce aqui enquanto ainda for coeso
3. faz split apenas quando o modulo deixa de ser legivel ou coerente

## Regra oficial para novas features

Toda feature nova deve seguir esta ordem de decisao:

1. existe token ou componente compartilhado que ja resolve?
2. se nao, ela pertence a qual superficie do produto?
3. dentro dessa superficie, ela pertence a qual persona ou cena?
4. ela cabe no modulo local existente sem virar emaranhado?
5. se nao couber, precisa splitar em submodulo local, nao subir direto para o global

## Arvore de decisao para CSS novo

### Caso 1. Ajuste de cor, spacing ou comportamento visual amplo

Lugar certo:

1. token
2. componente compartilhado

### Caso 2. Ajuste de clima visual ou composicao de uma familia de telas

Lugar certo:

1. manifesto ou shell da superficie

### Caso 3. Ajuste de uma feature de uma persona especifica

Lugar certo:

1. modulo local da persona

Exemplo atual:

1. WOD do coach em `static/css/design-system/operations/dev-coach/coach.css`

### Caso 4. A feature local cresceu demais

Lugar certo:

1. split interno dentro da mesma subsuperficie

Exemplo recomendado para o futuro:

1. `operations/dev-coach/coach-session.css`
2. `operations/dev-coach/coach-wod-editor.css`
3. `operations/dev-coach/coach-wod-approval.css`

### Caso 5. A feature passou a ser padrao reutilizavel entre superficies

Lugar certo:

1. componente compartilhado
2. ou camada superior da superficie

Regra dura:

1. nao promova cedo demais algo para o compartilhado so porque parece elegante
2. promova apenas quando o reuso for real

## Regra contra overengineering

O OctoBox nao deve preparar um tiro de missil para resolver uma porta de armario.

Em pratica:

1. nao criar 5 arquivos para uma feature com 30 linhas
2. nao criar "framework de componentes internos" sem necessidade comprovada
3. nao criar naming teatral para esconder um problema simples de ownership
4. nao mover para o global algo que ainda nao provou reuso

### Sinais de overengineering

1. a explicacao da estrutura ficou maior que a feature
2. a feature nova exige importar muitos arquivos para entender uma mudanca simples
3. o time precisa navegar por muitas camadas para alterar algo local
4. surgem wrappers e manifestos demais para pouco valor real

### Regra pratica

1. features pequenas nascem no modulo local existente
2. features medias podem ganhar um split local dentro da mesma pasta
3. so features consolidadas e reutilizadas sobem para shared

## Regra contra gambiarra

Tambem nao vale o extremo oposto: jogar tudo num arquivo so e chamar isso de simplicidade.

### Sinais de gambiarra

1. um arquivo local com responsabilidades demais
2. seletores profundos demais para forcar contexto
3. reuso copiado e colado entre personas
4. classe visual servindo como hook de JS e teste ao mesmo tempo
5. ajuste local brigando com o host ou o token global
6. dark mode local reescrevendo o componente inteiro

### Regra pratica

1. se o arquivo ainda esta coeso, mantenha
2. se virou armario de tudo, split local
3. se a mesma regra apareceu em dois ou tres lugares diferentes, promova

## Ownership obrigatorio por eixo

Toda entrega de front-end precisa deixar claro quem e dono de cada parte.

### 1. Template

Responsavel por:

1. composicao da pagina
2. semantica
3. estrutura dos blocos
4. `data-*` hooks estaveis

Nao deve carregar:

1. CSS inline
2. JS inline complexo
3. regra de negocio escondida no markup

### 2. CSS

Responsavel por:

1. layout
2. estado visual
3. responsividade
4. clima visual da superficie

Nao deve carregar:

1. dependencia de markup frágil demais
2. override caotico da camada global

### 3. JS

Responsavel por:

1. comportamento
2. interacao
3. progressive enhancement

Deve localizar elementos por:

1. `data-ui`
2. `data-slot`
3. `data-panel`
4. `data-action`

Nao deve localizar por:

1. classe puramente visual quando houver hook estrutural mais estavel

## Convencao oficial de naming

O naming deve ser contextual e honesto.

### Bom

1. `coach-wod-editor-card`
2. `coach-wod-review-signal-card`
3. `coach-session-toolbar`

### Ruim

1. `special-card`
2. `new-panel`
3. `custom-box`
4. `temp-style`

### Regra de naming

1. prefixo da superficie ou persona
2. nome da feature
3. papel do bloco

Formula pratica:

`superficie-feature-bloco`

## Regra oficial de split de arquivo CSS

Um arquivo local pode continuar unico enquanto mantiver estas tres caracteristicas:

1. um assunto predominante
2. leitura continua sem caca ao tesouro
3. alteracao comum cabendo em contexto curto

### Deve splitar quando houver 2 ou mais sinais

1. o arquivo mistura duas features diferentes
2. a persona ganhou mais de uma cena forte
3. a secao de responsividade ficou grande demais
4. o arquivo passou a concentrar editor, board, detalhe e aprovacao ao mesmo tempo
5. uma mudança simples exige rolar muito para achar ownership

### Nao precisa splitar ainda quando

1. a feature ainda esta amadurecendo
2. os estilos estao altamente relacionados
3. a complexidade ainda e local e controlada

## Regra especial para `operations`

Como `operations` ja trabalha por personas, a regra oficial e:

1. compartilhar so o que for realmente transversal
2. manter o resto por persona
3. promover comportamento para camada superior apenas quando existir evidencia de uso cruzado

### Exemplo aplicado ao coach

Estado atual saudavel:

1. WOD e aprovacao no trilho `operations/dev-coach/coach.css`

Melhoria futura recomendada:

1. manter dentro de `operations/dev-coach/`
2. dividir em modulos quando a densidade passar do ponto

Melhoria nao recomendada agora:

1. jogar WOD de coach direto em `components/`
2. criar uma pasta global de `workout/` fora da estrutura atual sem necessidade comprovada

## Regra de acoplamento entre docs e runtime

Se o runtime real estiver mais avancado do que o doc, o doc precisa subir.

Se o doc estiver mais sofisticado do que o runtime precisa, o doc esta exagerando.

Este padrao deve acompanhar:

1. `docs/plans/front-end-restructuring-guide.md`
2. `docs/reference/front-end-city-map.md`
3. `docs/reference/front-end-card-architecture.md`
4. `docs/reference/pr-front-end-checklist.md`

## Checklist rapido antes de subir uma feature de front-end

1. esta feature entrou na superficie certa?
2. ela reutiliza tokens e componentes existentes?
3. o CSS ficou no menor lugar util possivel?
4. o arquivo novo realmente precisava nascer?
5. o split foi feito por necessidade real, nao por ansiedade arquitetural?
6. o template usa hooks estruturais estaveis?
7. o JS, se existir, esta isolado de classes visuais?
8. a feature ficou legivel para a proxima pessoa mexer?

## Aplicacao pratica ao caso atual do coach WOD

Leitura honesta do estado atual:

1. a feature esta no corredor certo
2. conversa com o design system
3. ainda esta saudavel
4. mas ja merece vigiar densidade do arquivo `coach.css`

Decisao correta agora:

1. manter dentro da superficie do coach
2. nao promover cedo demais
3. preparar split local quando a proxima onda crescer

## Resumo executivo

O padrao oficial do OctoBox e:

1. comecar local no corredor certo
2. reutilizar o que ja existe
3. splitar apenas quando houver anatomia nova de verdade
4. promover para o compartilhado apenas com reuso real
5. evitar tanto puxadinho quanto arquitetura de foguete

Em linguagem simples:

1. nem improviso
2. nem teatro de arquitetura
3. organizacao sobria, progressiva e legivel
