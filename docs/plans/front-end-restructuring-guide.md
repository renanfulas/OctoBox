<!--
ARQUIVO: guia oficial de reestruturacao do front-end para alinhar fachada visual, contratos de interface e desacoplamento progressivo do backend.

TIPO DE DOCUMENTO:
- plano estrutural de convergencia entre front-end, UX e arquitetura

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [../experience/front-display-wall.md](../experience/front-display-wall.md)

DOCUMENTOS IRMAOS:
- [../architecture/django-core-strategy.md](../architecture/django-core-strategy.md)
- [../architecture/center-layer.md](../architecture/center-layer.md)
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [catalog-page-payload-presenter-blueprint.md](catalog-page-payload-presenter-blueprint.md)
- [../reference/front-end-ownership-map.md](../reference/front-end-ownership-map.md)
- [front-beta-closure-board.md](front-beta-closure-board.md)

QUANDO USAR:
- quando a duvida for como reorganizar o front-end sem quebrar a operacao atual e sem criar uma frente desalinhada do core futuro do sistema

POR QUE ELE EXISTE:
- transforma a intencao de ter um front-end extremamente alinhado em trilha tecnica concreta.
- evita que a fachada do produto cresca como um conjunto de templates fortes por fora e acoplados por dentro.
- prepara a camada visivel para encaixar naturalmente no movimento maior de "Django fora do core".

O QUE ESTE ARQUIVO FAZ:
1. define a tese arquitetural do front-end do OctoBox.
2. estabelece a forma-alvo da camada visual.
3. compara alternativas reais de implementacao.
4. organiza a execucao por ondas com guardrails e criterio de pronto.

PONTOS CRITICOS:
- este guia nao recomenda SPA por reflexo; ele prioriza coerencia estrutural.
- a reestruturacao precisa reduzir acoplamento sem explodir custo operacional.
- o front-end precisa parecer um sistema unico, nao um conjunto de telas montadas por area.
-->

# Guia de reestruturacao do front-end

## Tese central

O front-end do OctoBox nao deve ser apenas uma camada de templates que renderiza bem.

Ele deve funcionar como a `Front Display Wall` viva do sistema:

1. uma frente unica
2. uma linguagem unica
3. uma hierarquia unica
4. uma conversa clara com o backend
5. uma estrutura interna preparada para crescer sem virar remendo

No eixo visual, a assinatura oficial do produto agora passa a ser governada por [../architecture/themeOctoBox.md](../architecture/themeOctoBox.md), com implantacao pratica em [theme-implementation-final.md](theme-implementation-final.md).

Em linguagem direta:

1. a fachada precisa parecer produto pronto
2. a montagem interna precisa parecer sistema maduro
3. a comunicacao com o backend precisa nascer de contratos claros
4. a troca futura de casca HTTP, API ou canal nao pode exigir reescrever a logica da tela inteira

O alvo nao e "ter telas bonitas".

O alvo e este:

1. experiencia visivel coesa
2. comportamento previsivel
3. baixo atrito para alterar
4. encaixe natural com `Center Layer`, `snapshots`, `facades` e `use cases`
5. caminho limpo para o dia em que Django deixar de ser o centro explicativo da entrega

## Regra oficial de velocidade percebida

O front-end do OctoBox nao pode apenas parecer organizado.

Ele precisa sustentar a sensacao de que o sistema e mais rapido do que o humano.

Em termos de produto:

1. a pessoa precisa sentir que a informacao ja chegou pronta antes de ela mesma tentar montar o contexto manualmente
2. a tela precisa carregar, consolidar e orientar em milissegundos nas rotinas centrais
3. backend e frontend precisam operar como um organismo vivo, com passagem curta, clara e eficaz de estado, acao e leitura

Consequencia direta para este guia:

1. payload bom nao e so payload limpo; e payload que reduz latencia percebida
2. presenter bom nao e so presenter organizado; e presenter que entrega leitura pronta sem inflar a borda
3. composicao visual boa nao e so bonita; e composicao que deixa a proxima acao obvia antes de o usuario precisar procurar demais
4. qualquer camada, include, script ou contrato que atrase a resposta percebida esta violando a tese do front

## Problema que estamos resolvendo agora

Hoje o projeto ja tem um backend caminhando para desacoplamento real.

Mas a frente visivel ainda carrega residuos tipicos de fase inicial:

1. templates grandes demais por pagina
2. JavaScript inline misturado com marcação
3. CSS carregado de forma ampla demais
4. contratos de tela implícitos em dicionarios e ids espalhados
5. comportamento de pagina acoplado ao DOM especifico em vez de nascer de contratos claros

Isso gera cinco dores praticas:

1. alterar uma tela custa mais leitura do que deveria
2. pequenos ajustes visuais carregam risco de quebrar interacao
3. o backend ja esta ficando limpo, mas o front ainda nao conversa com ele pela mesma disciplina
4. a identidade visual pode ficar coerente por fora, mas fraca por dentro
5. o sistema corre o risco de crescer como mosaico, e nao como organismo unico

## Imagem-alvo

Queremos que o front funcione como uma sinapse neural bem formada.

Traducao tecnica dessa ideia:

1. o sinal sai de uma fonte clara
2. passa por um corredor previsivel
3. chega num receptor explicito
4. dispara um comportamento local sem contaminar o resto do cerebro

No OctoBox isso significa:

1. a view ou API entrega um payload de tela explicito
2. o template compoe blocos visuais com responsabilidade clara
3. o JavaScript da pagina consome apenas os dados que a pagina declara
4. os componentes compartilham estilo e contrato, nao gambiarra de seletor
5. a alteracao de um bloco nao espalha ruído pelo sistema inteiro
6. o backend precisa ser enxuto, e o front precisa ser flúido e eficiente sem arquivos desnecessários, emaranhados ou coisas do tipo

## Tese oficial para a arquitetura do front

O front-end do OctoBox passa a obedecer esta frase:

1. fachada global unica
2. paginas compostas por modulos
3. modulos dirigidos por contratos
4. contratos alimentados por view models e snapshots
5. comportamento isolado por pagina ou componente

Regra de ouro:

1. o front nao deve descobrir a regra de negocio no HTML
2. o front deve receber uma representacao clara do estado e da acao possivel

## Regra de contrato enxuto

Quando um dado existe apenas para sustentar apresentacao, repeticao visual, amostragem auxiliar ou conveniencia de leitura, ele deve nascer uma vez e ser replicado no frontend.

O backend nao deve gastar contrato, payload e montagem com duplicacao de UI sem efeito interno.

### Principio oficial do contrato semantico enxuto

O back-end deve entregar apenas o minimo semantico necessario para a tela existir com verdade: dados reais, permissoes, estado, contexto e acoes possiveis.

O front-end assume a organizacao visual, a repeticao de leitura e a composicao da interface.

Assim, a aparencia pode evoluir sem inflar o back-end com responsabilidade de UI.

O resultado esperado e este:

1. rota mais limpa e sustentavel para o front-end
2. menos acoplamento visual entre backend e interface
3. menos risco de bug por duplicacao de apresentacao
4. menor sobrecarga desnecessaria no back-end

Regra pratica permanente:

1. o back-end entrega verdade, acesso, estado e acao possivel
2. o front-end organiza hierarquia, distribuicao, repeticao visual e experiencia
3. o mesmo dado pode aparecer em varios pontos da interface sem exigir duplicacao de payload
4. o back-end nao deve enviar variantes cosmeticas do mesmo valor so para sustentar layout
5. o front-end nao deve adivinhar regra de negocio, permissao ou estado critico

Use esta regra:

1. se o dado altera regra, permissao, navegacao, decisao operacional, escrita ou leitura real do sistema, ele tem prioridade no backend
2. se o dado so precisa aparecer em mais de um ponto visual da mesma tela, o backend deve entregar a fonte semantica uma vez
3. a repeticao visual, espelhamento, badge auxiliar, contagem redundante e composicao de apoio devem ser resolvidos no frontend
4. o frontend pode replicar o mesmo valor em mais de um elemento quando isso acelerar leitura sem inflar o contrato

Traducao pratica:

1. backend entrega `count`, `summary`, `href`, estado e acesso
2. frontend decide se o mesmo `count` aparece no numero principal, no hint visual ou em outro ponto de apoio
3. backend nao deve enviar variantes redundantes do mesmo valor so para poupar uma interpolacao simples no template ou no JavaScript

Anti-padrao proibido por esta regra:

1. enviar do backend um numero bruto e uma segunda copia textual desse mesmo numero apenas para exibir em outro ponto da interface
2. mandar textos auxiliares diferentes quando o frontend pode compor a repeticao a partir da mesma fonte semantica
3. inflar payload de tela com duplicacao de apresentacao que nao muda regra nem comportamento interno

## Mandamentos planetarios para o front-end do OctoBox

Estas regras viram norma do projeto. Sempre que houver duvida entre duas abordagens, a que mais respeitar estes principios deve vencer.

### 1. Uma tela precisa ter uma fonte de verdade

1. toda tela rica deve nascer de um unico page payload oficial
2. esse payload e a fronteira publica entre backend e frontend
3. dados equivalentes nao podem chegar por caminhos paralelos no mesmo render
4. template, CSS e JS devem orbitar o payload, nao contexto casual montado na view

### 2. Backend simples, frontend forte

1. backend deve ser fino na borda HTTP e forte em regra, permissao, leitura e contrato
2. view HTTP deve coordenar request, chamar builder, anexar payload e sair do caminho
3. presenter ou page builder monta contexto, dados, acoes, capacidades, comportamento e assets da tela
4. frontend assume composicao visual, repeticao de leitura e progressao de interface sem empurrar regra de negocio para o browser
5. backend nao deve carregar copy redundante, variacoes cosmeticas do mesmo dado ou duplicacao de badge que o frontend pode compor sozinho

### 3. Namespacing antes de espalhamento

1. o contrato canonico da tela e namespaced: `page.context`, `page.data`, `page.actions`, `page.behavior`, `page.capabilities`, `page.assets`
2. espalhar chaves planas no contexto so e aceitavel como ponte temporaria para templates legados
3. qualquer bridge legado deve morar em helper compartilhado, nunca repetido em varias views
4. nova tela nasce namespaced; tela antiga pode usar alias temporario enquanto migra

### 4. Um arquivo, um papel claro

1. template principal define composicao macro da pagina
2. include define um modulo visual ou funcional da pagina
3. CSS de pagina define contrato visual da pagina
4. JS de pagina define comportamento da pagina
5. utilitario compartilhado so nasce quando o reuso for real e comprovado

### 5. Sem mini framework caseiro

1. helpers compartilhados devem reduzir repeticao real, nao criar uma plataforma paralela dentro do projeto
2. se um helper exige mais explicacao do que a duplicacao que ele remove, ele provavelmente esta errado
3. o sistema deve continuar legivel por leitura direta de pasta, arquivo e funcao

### 6. Performance, acessibilidade e robustez sao requisitos de entrada

1. toda tela importante deve partir de HTML semantico, foco visivel, contraste suficiente e navegacao por teclado
2. JS deve ser progressivo: a pagina precisa continuar compreensivel sem interacao rica sempre que a tarefa permitir
3. assets devem ser carregados por necessidade real da pagina, nao por conveniencia global
4. estado de loading, erro, vazio e sucesso fazem parte do contrato da tela e nao entram como improviso tardio

## Prioridades imediatas para manter o front facil de localizar, corrigir e evoluir

Estas prioridades passam a ter precedencia pratica no projeto porque aumentam diretamente a capacidade de encontrar elementos, entender ownership e fazer manutencao com baixo atrito.

### Prioridade 1. Hooks estruturais explicitos no DOM

Toda interface importante deve distinguir claramente:

1. classe visual para aparencia
2. id para ancora, relacionamento e acessibilidade
3. `data-*` para comportamento, automacao, busca de elementos, smoke tests e futuras integracoes

Regra pratica:

1. JS nao deve localizar elemento por classe puramente visual quando um hook estrutural puder existir
2. testes e automacoes nao devem depender da cosmetica do CSS
3. elementos relevantes do shell e das paginas devem receber atributos de descoberta estavel como `data-ui`, `data-slot`, `data-panel`, `data-action` ou equivalente padronizado

Nivel de esforco:

1. simples a medio se feito por ondas
2. alto apenas se tentarem converter tudo de uma vez sem padrao unico

### Prioridade 2. Contrato fixo de composicao por pagina

Toda tela importante deve ser encontravel por uma estrutura previsivel:

1. template principal da pagina
2. includes da pagina por papel claro
3. CSS da pagina
4. JS da pagina
5. page payload unico

Regra pratica:

1. nenhuma tela rica deve depender de descoberta informal espalhada entre varios arquivos sem ownership claro
2. quem abrir uma tela precisa conseguir responder rapido onde esta a composicao, onde esta o comportamento e onde esta o contrato

Nivel de esforco:

1. medio
2. baixo nas telas novas
3. medio nas telas antigas ja parcialmente migradas

### Prioridade 3. Vocabulario estrutural unico

O projeto deve repetir os mesmos nomes para os mesmos papeis visuais e funcionais.

Exemplos de nomes preferenciais:

1. `hero`
2. `context`
3. `workspace`
4. `summary`
5. `queue`
6. `rail`
7. `panel`
8. `modal`
9. `form`
10. `table`
11. `state-empty`

Regra pratica:

1. se dois blocos fazem o mesmo papel em telas diferentes, devem usar nomenclatura estrutural equivalente
2. nomes de include, CSS e hooks devem convergir para o mesmo vocabulário

Nivel de esforco:

1. simples
2. exige mais disciplina do que tempo tecnico

### Prioridade 4. Estados de interface virarem contrato oficial

Toda tela importante deve declarar estados previsiveis, legiveis e localizaveis:

1. loading
2. empty
3. success
4. error
5. readonly
6. editable
7. disabled

Regra pratica:

1. esses estados devem existir no payload, no template ou no DOM quando forem relevantes
2. estado nao pode aparecer como improviso local escondido em condicao solta

Nivel de esforco:

1. medio
2. simples nas novas telas
3. medio nas telas antigas com muitos fluxos condicionais

### Prioridade 5. Ownership curto e visivel do front

Deve existir documentacao curta e objetiva dizendo onde mora cada parte critica do front:

1. shell global
2. payload helper compartilhado
3. pagina principal de cada dominio
4. CSS e JS de cada area
5. componentes compartilhados reais

Regra pratica:

1. quem entra no projeto deve conseguir navegar pela arquitetura do front sem depender de memoria oral
2. qualquer melhoria futura deve comecar por esse mapa antes de abrir busca cega

Nivel de esforco:

1. simples
2. retorno muito alto para manutencao e engenharia reversa

## Leitura franca de complexidade

Estas prioridades nao sao complexas no sentido de regra de negocio profunda.

O custo delas e principalmente de disciplina estrutural, padrao e consistencia.

Traducao direta:

1. prioridade 1 e 3 sao simples a medias e podem avancar rapido
2. prioridade 2 e 4 sao medias, porque pedem revisao de ownership e estados em telas reais
3. prioridade 5 e simples e deveria andar junto das outras
4. o erro seria tratar isso como mutirao gigante em vez de aplicar como norma incremental em cada tela tocada

Regra executiva:

1. sempre que uma tela for alterada, ela deve sair mais localizavel do que entrou
2. sempre que um JS tocar no DOM, ele deve deixar hooks mais claros do que encontrou
3. sempre que um include crescer, seu nome e seu papel precisam ficar mais obvios do que antes

## Regra de fixacao do front-end para beta

O produto entrou numa fase em que o front-end ja nao deve ser tratado como laboratorio aberto.

Ele deve ser tratado como fachada em consolidacao para beta assistido.

Traducao pratica:

1. o foco agora nao e inventar mais frente visual
2. o foco agora e fechar leitura, previsibilidade, robustez e confianca nas telas centrais
3. mudanca nova so entra se aumentar clareza, reduzir risco ou destravar uso real do beta
4. toda energia de front deve servir ao objetivo de deixar o produto pronto para ser visto, usado e validado no mundo real

### O que significa fixar o front-end

Fixar o front-end nao significa congelar o produto cedo demais.

Significa isto:

1. parar de girar estrutura sem necessidade
2. consolidar a linguagem visual e estrutural que ja provou valor
3. fechar as superficies principais do produto com criterio de beta
4. reduzir ambiguidade antes de abrir novas frentes visuais

### Regra executiva do beta

Entramos oficialmente na logica de beta quando estas perguntas passarem a mandar mais do que vontade de experimentar:

1. a tela esta clara o suficiente para uso real?
2. a proxima acao esta obvia em poucos segundos?
3. o fluxo aguenta erro humano comum?
4. a pagina esta facil de localizar, corrigir e evoluir sem caça cega?
5. a mudanca melhora beta real ou so reabre exploracao estetica?

Se a resposta da quinta pergunta for negativa, a mudanca nao deve entrar nesta fase.

## Superficies que precisam ficar prontas para beta antes de novas expansoes visuais

Estas superficies viram prioridade de acabamento e confianca:

1. shell global autenticado
2. login e busca global
3. dashboard principal
4. alunos
5. ficha leve do aluno
6. financeiro
7. edicao de plano
8. grade de aulas

## Estado atual de readiness do front

Neste momento, o front do produto ja pode ser tratado como pronto para beta assistido com vigilancia operacional.

Isto significa:

1. shell, login, dashboard, alunos, ficha leve, financeiro, edicao de plano, grade e recepcao ja passaram por consolidacao estrutural real
2. payloads, hooks e ownership das superficies centrais ja estao suficientemente estabilizados para sustentar beta assistido sem reabrir arquitetura
3. a passada visual assistida foi concluida nas superficies simbolicas do beta
4. a rodada assistida de saves leves ja confirmou persistencia real em recepcao, grade, ficha leve do aluno e edicao de plano
5. a passada complementar de viewport e fallback no ambiente assistido nao abriu novo bloqueador estrutural de beta
6. a energia restante deve ir para leitura sob uso acelerado, viewport estreita, acessibilidade curta e observacao assistida de uso real
7. a confirmacao mobile fisica em navegador externo ou dispositivo real continua pendente porque o browser integrado nao sustentou emulacao fisica estreita com confianca suficiente

Tambem significa o que nao fazer:

1. nao reabrir layout-base ou contratos centrais sem motivo operacional forte
2. nao confundir refinamento final com nova fase de exploracao visual
3. nao confundir pronto para beta assistido com pronto absoluto sem vigilancia
4. nao tratar validacao mobile do browser integrado como substituto automatico de uma passada fisica real quando a emulacao se mostrar limitada
9. recepcao

Regra de prioridade:

1. tela central usada toda semana vence tela nova
2. fluxo que orienta dinheiro, agenda, atendimento e leitura do box vence refinamento periferico
3. tudo que entra no beta precisa ser legivel para owner e para operacao real, nao apenas para quem construiu

## Criterio de pronto do front para beta

Uma tela so pode ser considerada pronta para beta quando passar nestes blocos ao mesmo tempo:

### 1. Clareza

1. em ate tres segundos fica claro o que a tela mostra
2. em ate tres segundos fica claro o que pede acao agora
3. a acao principal aparece sem leitura longa

### 2. Estrutura

1. a tela tem payload unico e ownership claro
2. template principal, includes, CSS e JS estao localizaveis
3. hooks estruturais principais existem no DOM

### 3. Robustez

1. erro humano comum nao desmonta o fluxo
2. estados vazio, erro, sucesso e bloqueio orientam o proximo passo
3. formulario limita, mascara, valida e explica antes do submit quando fizer sentido

### 4. Consistencia

1. a tela fala a mesma lingua visual e estrutural do resto do produto
2. prioridades, pendencias e proximas acoes seguem a mesma logica mental
3. nomenclatura estrutural nao inventa dialeto proprio sem necessidade

### 5. Beta real

1. a tela aguenta uso assistido com usuario real
2. a triagem de bug consegue localizar rapido rota, papel, painel e acao
3. pequenos ajustes futuros podem ser feitos sem reabrir a arquitetura da pagina

## O que ainda pode mudar nesta fase

Mudancas permitidas:

1. clareza de hierarquia
2. copy operacional
3. hooks estruturais
4. estados de interface
5. acessibilidade
6. responsividade
7. robustez contra erro humano
8. acabamento das superficies centrais do beta

Mudancas que devem ser tratadas com mais desconfiança:

1. trocar linguagem visual base sem motivo forte
2. reabrir arquitetura de pagina que ja convergiu para payload claro
3. criar componente compartilhado sem reuso comprovado
4. abrir nova frente visual antes de consolidar o nucleo do beta

## Regra de congelamento inteligente

Congelamento inteligente significa:

1. a estrutura central para de oscilar
2. o acabamento continua
3. correcoes continuam
4. confianca sobe
5. exploracao cai

Traducao pratica:

1. shell, payload, ownership e vocabulario estrutural devem ficar mais estaveis a partir daqui
2. ajustes visuais agora devem refinar a obra, nao reinventar a base
3. toda refatoracao deve justificar por que melhora readiness de beta

## Regra de validação de beta para toda mudanca de front

Toda mudanca relevante no front, a partir desta fase, deve responder explicitamente:

1. qual superficie do beta ela melhora?
2. qual ambiguidade ela remove?
3. qual risco real ela reduz?
4. como essa mudanca ajuda um usuario real a operar melhor?
5. ela deixa a tela mais pronta ou apenas mais diferente?

## Formula curta desta fase

O front-end agora precisa sair do modo "vamos descobrir" e entrar no modo "vamos consolidar".

O produto ja mostrou maturidade suficiente para isso.

Entao a regra e simples:

1. menos abertura estrutural
2. mais fixacao de linguagem
3. mais robustez de uso
4. mais clareza operacional
5. mais confianca para o beta

Documento operacional desta fase:

1. o quadro de status, ambiguidade restante e ondas curtas de fechamento do beta mora em [front-beta-closure-board.md](front-beta-closure-board.md)

## Regra oficial do page payload

Toda tela relevante do OctoBox deve convergir para este contrato:

1. `context`: identidade da tela, titulo, subtitulo, modo e papel atual
2. `shell`: dados do shell global que a tela quer substituir ou enriquecer
3. `data`: leitura principal da tela
4. `actions`: destinos, anchors, exports, endpoints e submits oficiais
5. `behavior`: dados operacionais para JS progressivo
6. `capabilities`: o que o usuario pode ou nao pode fazer
7. `assets`: CSS e JS especificos da tela

Regra de implementacao:

1. a view nao monta manualmente cada chave plana desse contrato
2. a view chama um helper compartilhado para anexar o payload no contexto
3. se uma tela antiga ainda precisar de aliases planos, esses aliases saem do helper compartilhado e nao da view
4. o objetivo final continua sendo template e include consumirem o payload namespaced diretamente

## Regra oficial para backend enxuto

Quando houver conflito entre conveniencia imediata e simplicidade estrutural, o backend deve ficar menor e mais claro.

Isso significa:

1. view HTTP curta e previsivel
2. regra de negocio fora da view
3. QuerySet de leitura fora da view quando alimentar tela rica
4. page builder fora da view quando a tela tiver contrato relevante
5. duplicacao de montagem proibida quando puder ser encapsulada com clareza em helper pequeno
6. nada de contexto ad hoc crescendo sem ownership

Heuristica pratica para decidir:

1. se a view esta fazendo mais de coordenar request, carregar base_context, chamar builder e devolver response, ela ja esta pesada demais
2. se o template precisa de vinte chaves soltas e sem agrupamento, o contrato ainda esta informal
3. se o mesmo merge de payload aparece em varias views, o bridge ainda nao virou infraestrutura oficial

## Como usar este guia na pratica

Este documento nao foi escrito para ser lido uma vez e arquivado.

Ele deve ser usado em quatro momentos:

1. antes de mexer numa tela importante
2. antes de abrir uma nova frente de front-end
3. durante uma refatoracao estrutural
4. na revisao final para decidir se a mudanca realmente deixou o sistema mais alinhado

Ordem recomendada de uso:

1. releia a tese central
2. identifique em qual camada a mudanca pertence
3. defina o contrato da tela antes de mexer no HTML
4. so depois reorganize template, CSS e JS
5. valide a conversa final com backend, shell e identidade visual

Documento de apoio operacional:

1. para localizar ownership real de shell, payload, templates principais, CSS e JS, consulte [../reference/front-end-ownership-map.md](../reference/front-end-ownership-map.md)

Se a equipe pular o passo do contrato e for direto para markup ou CSS, a chance de reorganizar por fora e continuar acoplado por dentro sobe muito.

## Como isso encaixa no plano maior do projeto

### Relacao com a Front Display Wall

Este guia e a traducao estrutural da tese descrita em [../experience/front-display-wall.md](../experience/front-display-wall.md).

Se aquele documento define o que a fachada precisa parecer, este documento define como construir essa fachada sem bagunca interna.

Leitura pratica:

1. `Front Display Wall` define a face
2. este guia define a ossatura da face

### Relacao com o Django deixar de ser o core

O documento [../architecture/django-core-strategy.md](../architecture/django-core-strategy.md) diz que Django deve deixar de ser o cerebro do sistema.

No front isso se traduz assim:

1. template nao pode ser dono da regra sensivel
2. view nao pode ser dona informal do contrato de tela
3. JavaScript nao pode depender de detalhes acidentais do render
4. a camada visual deve depender de payloads estaveis e documentados

### Relacao com o Center Layer

O `Center Layer` e o hall publico entre acesso e nucleo.

No front, isso significa que a interface nao deve se ligar em tudo ao mesmo tempo.

Ela deve falar com entradas oficiais:

1. facade
2. use case
3. snapshot
4. presenter ou page builder

Nao deve falar com:

1. regra espalhada em view
2. varios QuerySets montados ad hoc para cada detalhe visual
3. string solta de URL ou comportamento hardcoded sem contrato

## Estrutura-alvo do front-end

## Camada 1: shell global

Responsabilidade:

1. navegacao principal
2. sidebar
3. topbar
4. tema
5. busca global
6. design tokens
7. componentes transversais reais

O shell global nao deve carregar comportamento que pertence so a uma tela especifica.

Ele existe para sustentar o predio inteiro, nao para resolver a vida de cada sala.

## Camada 2: pagina como composicao

Cada pagina forte deve ser uma composicao de blocos e nao um arquivo gigante.

Cada pagina deve ter:

1. um template casca
2. includes por bloco funcional
3. CSS de pagina
4. JS de pagina
5. um payload de tela explicito vindo do backend

Exemplos de blocos:

1. hero
2. filtro
3. tabela principal
4. rail lateral
5. painel de acao
6. formulario principal
7. modal declarativo

Aplicacao pratica atual:

1. [templates/catalog/finance.html](../../templates/catalog/finance.html) virou uma casca que compoe blocos em [templates/includes/catalog/finance](../../templates/includes/catalog/finance)
2. [templates/catalog/student-form.html](../../templates/catalog/student-form.html) virou uma casca que compoe blocos em [templates/includes/catalog/student_form](../../templates/includes/catalog/student_form)
3. [templates/catalog/class-grid.html](../../templates/catalog/class-grid.html) virou uma casca que compoe hero, contexto, workspace e modal em [templates/includes/catalog/class_grid](../../templates/includes/catalog/class_grid)

Regra operacional para templates densos:

1. o template raiz da pagina deve descrever a ordem da leitura
2. cada include deve representar um bloco visual ou funcional reconhecivel
3. includes nao devem esconder contrato de dados novo; eles consomem o contexto oficial da pagina
4. se mexer em hero, rail, formulario ou overview nao deve exigir varrer o template inteiro

Quando um mesmo subbloco visual reaparecer em varios includes da mesma area, ele deve ser promovido para `templates/includes/ui`.

Aplicacao pratica atual:

1. [templates/includes/ui/layout/operation_card_head.html](../../templates/includes/ui/layout/operation_card_head.html) concentra o cabecalho recorrente dos cards operacionais do financeiro
2. [templates/includes/ui/class_grid/class_grid_panel_head.html](../../templates/includes/ui/class_grid/class_grid_panel_head.html) concentra o cabecalho recorrente dos paineis arrastaveis da grade
3. [templates/includes/ui/finance/finance_action_item.html](../../templates/includes/ui/finance/finance_action_item.html) concentra o card recorrente de acao semiassistida do financeiro
4. [templates/includes/ui/finance/finance_alert_item.html](../../templates/includes/ui/finance/finance_alert_item.html) concentra o card recorrente de alerta financeiro
5. [templates/includes/ui/finance/finance_plan_stat.html](../../templates/includes/ui/finance/finance_plan_stat.html) concentra o bloco curto de estatistica do portfolio de planos
6. [templates/includes/ui/finance/finance_snapshot_chip.html](../../templates/includes/ui/finance/finance_snapshot_chip.html) concentra o chip de leitura curta usado no recorte ativo e no radar

## Camada 3: componentes compartilhados

Componentes compartilhados devem existir quando a repeticao for real e o contrato for estavel.

Nao criar componente compartilhado so porque duas telas parecem ter a mesma forma hoje.

Criar quando estas tres coisas forem verdadeiras:

1. mesma responsabilidade
2. mesmo contrato de entrada
3. mesma semantica de uso

Exemplos naturais no OctoBox:

1. state notice
2. state empty
3. metric card
4. quick action card
5. paines de leitura curta
6. chips operacionais

Aplicacao pratica atual no CSS:

1. [static/css/design-system/components.css](../../static/css/design-system/components.css) fica como manifesto estavel
2. hero compartilhado mora em [static/css/design-system/components/hero.css](../../static/css/design-system/components/hero.css)
3. cards e grids compartilhados moram em [static/css/design-system/components/cards.css](../../static/css/design-system/components/cards.css)
4. tabelas compartilhadas moram em [static/css/design-system/components/tables.css](../../static/css/design-system/components/tables.css)
5. pills e badges moram em [static/css/design-system/components/pills.css](../../static/css/design-system/components/pills.css)
6. botoes e action bars moram em [static/css/design-system/components/actions.css](../../static/css/design-system/components/actions.css)
7. notices, empty states e mensagens moram em [static/css/design-system/components/states.css](../../static/css/design-system/components/states.css)
8. quick cards e accent bar moram em [static/css/design-system/components/quick-cards.css](../../static/css/design-system/components/quick-cards.css)

Regra operacional:

1. se o pedido for "mudar um card", o ponto de entrada e cards.css
2. se o pedido for "mudar um botao ou barra de acoes", o ponto de entrada e actions.css
3. se o pedido for "mudar mensagens ou alertas", o ponto de entrada e states.css
4. o manifesto components.css nao deve voltar a acumular regra concreta

## Camada 4: modulos de comportamento

Comportamento de front deve ficar em modulos pequenos e previsiveis.

Divisao recomendada:

1. `core` para shell e utilitarios realmente globais
2. `pages` para comportamento exclusivo de cada pagina
3. `components` para comportamento reutilizavel entre blocos
4. `lib` para utilitarios puros de DOM, formatacao, storage e contracts

Regra dura:

1. script inline em template passa a ser excecao rarissima

## Camada 5: contrato de interface

Toda pagina rica deve ter um contrato de interface explicito.

Esse contrato deve responder:

1. qual estado a pagina recebe
2. quais blocos ela deve renderizar
3. quais acoes o usuario pode disparar
4. quais endpoints ou destinos fazem parte oficial dessa pagina
5. quais dados o JavaScript pode consumir

Esse contrato pode chegar por:

1. contexto do template
2. `json_script`
3. `data-*` declarativo

Mas sempre de forma documentada e previsivel.

## Artefatos obrigatorios de uma tela madura

Toda tela relevante do OctoBox deve poder ser descrita por um pequeno conjunto de artefatos claros.

Se uma tela ainda depende de intencao implícita para ser entendida, ela ainda nao esta madura.

Artefatos esperados:

1. `page purpose`
2. `page payload`
3. `page template shell`
4. `page modules`
5. `page stylesheet`
6. `page behavior module`
7. `page tests`

Para o catalogo, o blueprint especifico desses artefatos e da linguagem de `page payload` e `presenter` foi detalhado em [catalog-page-payload-presenter-blueprint.md](catalog-page-payload-presenter-blueprint.md).

### 1. page purpose

Responde:

1. por que a tela existe
2. para quem ela existe
3. qual decisao humana ela acelera
4. qual papel operacional ela cumpre no predio

Se essa resposta for vaga, a tela tende a acumular bloco demais e foco de menos.

### 2. page payload

Responde:

1. qual e o contexto da tela
2. quais blocos de leitura existem
3. quais acoes sao oficiais
4. quais dados o JavaScript pode consumir

### 3. page template shell

Responsabilidade:

1. organizar a ordem dos modulos
2. ligar assets da pagina
3. manter a semantica macro da tela

O shell nao deve enterrar regra de interacao pesada.

### 4. page modules

Responsabilidade:

1. quebrar a pagina em partes legiveis
2. reduzir o custo de alteracao por bloco
3. impedir que uma tela gigante vire um buraco negro de manutencao

### 5. page stylesheet

Responsabilidade:

1. declarar o contrato visual da pagina
2. impedir vazamento visual desnecessario
3. sustentar a identidade da tela dentro da identidade do sistema

### 6. page behavior module

Responsabilidade:

1. ligar comportamento apenas aos elementos e dados oficiais da tela
2. isolar validacao, interacao e manipulacao de estado local
3. impedir que o comportamento viva como script espalhado

### 7. page tests

Responsabilidade:

1. proteger conteudo visivel principal
2. proteger contratos estruturais minimos
3. proteger interacoes criticas quando houver comportamento relevante

## Contrato-padrao de page payload

Para evitar que cada tela invente sua propria lingua, o projeto deve convergir para um payload de pagina com forma parecida.

Ele nao precisa ser uma classe unica agora.

Mas precisa seguir a mesma ideia.

Modelo conceitual:

```text
page_payload
|-- context
|   |-- page_key
|   |-- title
|   |-- subtitle
|   |-- mode
|   `-- role
|-- data
|   |-- hero
|   |-- metrics
|   |-- panels
|   |-- forms
|   `-- states
|-- actions
|   |-- primary
|   |-- secondary
|   |-- internal_anchors
|   `-- endpoints
|-- behavior
|   |-- flags
|   |-- datasets
|   `-- json_blocks
```

Exemplo orientativo:

```python
page_payload = {
	'context': {
		'page_key': 'class-grid',
		'title': 'Grade de aulas',
		'subtitle': 'Veja onde o dia aperta e onde o mes pede ajuste.',
		'mode': 'management' if can_manage_classes else 'read-only',
		'role': current_role.slug,
	},
	'data': {
		'metrics': class_metrics,
		'today_schedule': today_schedule,
		'weekly_calendar': weekly_calendar,
		'monthly_calendar': monthly_calendar,
		'selected_session': selected_session,
	},
	'actions': {
		'primary': {'href': '#today-board', 'label': 'Ler o dia primeiro'},
		'secondary': [
			{'href': '#weekly-board', 'label': 'Ver pico da janela'},
			{'href': '#planner-board', 'label': 'Ajustar recorrencia'},
		],
		'endpoints': {
			'submit_planner': '/grade-aulas/',
		},
	},
	'behavior': {
		'flags': {
			'can_manage_classes': can_manage_classes,
			'has_monthly_modal': True,
		},
		'json_blocks': {
			'workspace_order': default_panel_order,
		},
	},
}
```

Regra pratica:

1. o template nao precisa receber apenas `page_payload`
2. mas a montagem da tela precisa convergir mentalmente para esse shape
3. a pagina deve poder ser explicada por esse contrato sem depender de leitura arqueologica do template

## Regra de divisao entre template, CSS, JS e backend

Para impedir que a reorganizacao vire apenas redistribuicao cosmetica, use esta divisao:

### O que fica no backend

1. regra de negocio
2. regra de permissao
3. definicao de contexto oficial da tela
4. dados prontos para leitura humana
5. destinos oficiais de acao

### O que fica no template

1. semantica HTML
2. ordem dos blocos
3. composicao da fachada
4. declaracao de dados para o comportamento da pagina

### O que fica no CSS

1. contrato visual
2. ritmo, respiro, hierarquia e responsividade
3. aparencia dos blocos e variacoes de estado visivel

### O que fica no JavaScript

1. comportamento local da pagina
2. validacao e interacao progressiva
3. leitura de `data-*` e `json_script`
4. persistencia local e manipulacao de UI que nao seja regra de negocio

### O que nao pode ficar ambiguo

1. URL critica perdida no script
2. regra comercial escondida em if de template
3. validacao duplicada em tres lugares sem estrategia
4. estado da pagina deduzido por seletor incidental

## Workflow oficial para reestruturar uma tela

Quando a equipe for reorganizar qualquer tela importante, seguir esta sequencia.

## Passo 1: declarar o papel da tela

Responder por escrito:

1. quem usa
2. o que decide
3. o que precisa ver primeiro
4. o que precisa poder fazer sem friccao

## Passo 2: mapear os blocos reais da tela

Separar em:

1. contexto
2. leitura principal
3. leitura secundaria
4. acoes
5. interacoes progressivas
6. estados de erro, vazio e sucesso

## Passo 3: desenhar o page payload

Antes de mexer no template, nomear:

1. context
2. data
3. actions
4. behavior

## Passo 4: quebrar o template em composicao

Separar:

1. shell da pagina
2. includes por modulo
3. pontos de asset
4. pontos de dados declarativos

## Passo 5: extrair o comportamento

Mover:

1. listeners
2. validacoes
3. modal
4. local storage
5. comportamento de widget

para modulo de pagina ou componente.

## Passo 6: isolar o estilo

Garantir:

1. classes semanticas locais
2. contrato visual da pagina
3. ausencia de dependencia acidental de CSS global da area errada

## Passo 7: fechar os testes certos

Minimo esperado:

1. teste HTTP para conteudo e estrutura visivel critica
2. teste de contrato para payload ou flags relevantes
3. teste de comportamento para interacao critica quando houver JS relevante

## Mapa de decisao para cada mudanca de front

Toda mudanca relevante deve ser classificada antes de ser implementada.

### Tipo A: mudanca de fachada

Exemplos:

1. hierarquia visual
2. composicao da pagina
3. ordem dos blocos
4. linguagem de CTA

Destino principal:

1. template shell
2. includes
3. stylesheet da pagina

### Tipo B: mudanca de contrato

Exemplos:

1. novos dados da tela
2. novo estado operacional
3. nova acao oficial
4. novo endpoint de interacao

Destino principal:

1. backend presenter ou page builder
2. view model
3. declaracao de `json_script` ou `data-*`

### Tipo C: mudanca de comportamento

Exemplos:

1. validacao progressiva
2. modal
3. drag and drop
4. autocomplete
5. persistencia local de layout

Destino principal:

1. JS de pagina
2. JS de componente
3. utilitario compartilhado quando o uso for real

### Tipo D: mudanca de regra de negocio

Exemplos:

1. condicao comercial
2. permissao
3. calculo financeiro
4. criterio operacional

Destino principal:

1. application
2. domain
3. facade
4. snapshot ou builder de leitura

Regra dura:

1. se a mudanca for Tipo D, ela nao pode nascer no template nem no JavaScript

## Alternativas reais de implementacao

## Alternativa A: Django templates modulares com JS progressivo por pagina

### Descricao

Manter server-rendered como canal principal.

Reorganizar a camada visual em:

1. template casca
2. includes por modulo
3. JS externo por pagina
4. CSS externo por pagina
5. page payload explicito

### Vantagens

1. encaixa naturalmente na base atual
2. baixo risco de reescrita
3. reaproveita a maturidade atual do backend
4. combina bem com a trilha de desacoplamento do Django sem forcar duas migracoes ao mesmo tempo
5. reduz bug estrutural sem trocar de paradigma de entrega

### Riscos

1. exige disciplina forte de contratos para nao continuar sendo template grande repartido em varios arquivos pequenos sem ganho real

### Veredito

1. esta e a direcao recomendada agora

## Alternativa B: ilhas progressivas de interacao

### Descricao

Manter server-rendered, mas permitir que algumas areas virem ilhas com comportamento mais rico e ciclo proprio.

Exemplos possiveis no futuro:

1. grade de aulas
2. planner recorrente
3. busca e filtros dinamicos
4. rails operacionais com refresh fino

### Vantagens

1. melhora experiencia sem exigir SPA integral
2. cria caminho para fronteiras mais inteligentes de front
3. permite mover zonas mais interativas por prioridade

### Riscos

1. se entrar cedo demais, pode virar front hibrido sem criterio
2. pode introduzir duas linguagens mentais antes de o baseline estar organizado

### Veredito

1. boa alternativa para a segunda fase, depois da base modular estar pronta

## Alternativa C: SPA completa com backend em API-first

### Descricao

Separar completamente front e backend agora.

### Vantagens

1. altissima independencia de entrega no longo prazo

### Riscos

1. dobra a complexidade cedo demais
2. exige reabrir roteamento, autenticacao, validacao, contratos e observabilidade ao mesmo tempo
3. drena energia estrutural justamente quando o backend ainda esta terminando sua propria transicao de ownership

### Veredito

1. nao recomendada para esta fase

## Decisao oficial recomendada

O OctoBox deve seguir agora com:

1. server-rendered disciplinado
2. modularizacao real de templates, CSS e JS
3. payloads de pagina explicitos
4. entradas oficiais do backend por facade, snapshot, presenter ou use case
5. preparacao progressiva para ilhas interativas futuras

## Forma-alvo de pastas

Esta estrutura e um alvo de convergencia, nao uma exigencia de mover tudo de uma vez:

```text
templates/
|-- layouts/
|-- includes/
|   |-- ui/
|   |-- shell/
|   `-- pages/
|       |-- students/
|       |-- finance/
|       `-- class_grid/
|-- catalog/
|   |-- students.html
|   |-- student-form.html
|   |-- finance.html
|   `-- class-grid.html

static/
|-- css/
|   |-- design-system.css
|   |-- pages/
|   |   |-- students.css
|   |   |-- student-form.css
|   |   |-- finance.css
|   |   `-- class-grid.css
|   `-- components/
|-- js/
|   |-- core/
|   |   |-- shell.js
|   |   |-- forms.js
|   |   `-- search.js
|   |-- pages/
|   |   |-- student-form.js
|   |   `-- class-grid.js
|   `-- components/

catalog/
|-- presentation/
|   |-- student_pages.py
|   |-- finance_pages.py
|   `-- class_grid_pages.py
|-- views/
|-- queries/
`-- facade/
```

Observacao importante:

1. `presentation/` aqui representa page builders ou presenters de tela
2. a nomenclatura exata pode variar
3. o principio nao pode variar: view nao deve carregar sozinha a montagem inteira da tela

## Convention map para nomes e ownership

Para evitar nomes aleatorios e ownership difuso, a base deve convergir para estas convencoes.

### Templates

1. `templates/catalog/students.html` para shell da pagina
2. `templates/includes/pages/students/*.html` para modulos internos

### CSS

1. `static/css/pages/students.css` para contrato visual da pagina
2. `static/css/components/*.css` apenas quando houver componente realmente transversal

### JS

1. `static/js/pages/students.js` para comportamento da pagina
2. `static/js/components/*.js` para comportamento reutilizavel
3. `static/js/core/*.js` para shell e utilitarios base

### Backend

1. `catalog/presentation/student_pages.py` para payload ou builder da tela
2. `catalog/views/student_views.py` para casca HTTP
3. `catalog/queries/*` para leitura estruturada
4. `students/application/*` e afins para regra real de negocio

## Governanca da reestruturacao

Como estamos numa fase mais complexa, a reestruturacao do front precisa seguir governanca clara para nao se perder.

## Toda frente de tela deve nascer com quatro perguntas respondidas

1. qual dor estrutural estamos removendo
2. qual contrato de tela estamos formalizando
3. qual acoplamento atual estamos proibindo de voltar
4. como essa tela conversa com o plano maior do sistema

## Toda refatoracao deve deixar um residuo menor, nao so diferente

Isso significa que cada onda precisa reduzir pelo menos um destes pontos:

1. tamanho do template principal
2. quantidade de script inline
3. dependencia de CSS amplo demais
4. dependencia de URL hardcoded
5. dependencia de contexto ad hoc montado sem forma clara

## Toda tela refatorada deve ganhar criterio de ownership explicito

Depois da refatoracao, deve ficar claro:

1. quem monta o payload
2. quem compoe a fachada
3. quem define o comportamento
4. quem sustenta o visual
5. quem protege a regra de negocio

## Matriz de prioridade para a execucao

Quando houver duvida sobre qual tela atacar primeiro, usar esta ordem de desempate.

Priorizar a tela que tiver maior soma destes fatores:

1. maior volume de interacao
2. maior risco de regressao por acoplamento atual
3. maior importancia operacional no dia a dia
4. maior dependencia futura de contratos claros com o backend
5. maior valor pedagogico para definir padrao do resto do sistema

Por essa matriz, a ordem atual continua correta:

1. grade de aulas
2. ficha do aluno
3. financeiro
4. dashboard
5. operations por papel

## Contrato recomendado entre backend e front

Toda pagina rica deve nascer de tres objetos conceituais:

1. `screen context`
2. `screen data`
3. `screen actions`

### 1. screen context

Explica o que a tela e.

Exemplos:

1. titulo
2. subtitulo
3. modo atual
4. papel atual
5. foco principal

### 2. screen data

Entregue os blocos de leitura da pagina em estruturas claras.

Exemplos:

1. metricas
2. lista principal
3. rail lateral
4. estados vazios
5. dados para graficos
6. opcoes de formulario

### 3. screen actions

Declare os destinos oficiais da tela.

Exemplos:

1. submit principal
2. links secundarios
3. endpoint de autocomplete
4. endpoint de refresh
5. anchors oficiais de navegacao interna

Regra de ouro:

1. URL hardcoded em JS deve ser excecao curta e explicitamente justificada

## Regras de organizacao obrigatorias

## 1. Pagina grande demais vira composicao

Se uma pagina misturar:

1. hero
2. tabela
3. rail
4. formulario
5. modal
6. validacao JS

ela deve ser quebrada.

## 2. Comportamento inline vira modulo

Qualquer pagina com interacao relevante deve mover o script para arquivo proprio.

## 3. Estilo de pagina nao deve ser global por padrao

O CSS da pagina deve carregar apenas onde a pagina existe.

## 4. Utilitario compartilhado precisa ser realmente compartilhado

Se data, hora, moeda, storage ou helper de DOM sao usados em mais de uma area, eles devem sair da pagina e entrar em `core` ou `lib`.

## 5. HTML nao e banco de regra

O DOM nao deve ser usado como deposito informal de regra de negocio escondida.

## 6. A view nao pode ser o ultimo buraco negro da tela

Se uma view cresce ao ponto de virar dona de contexto inteiro, copy inteira, links inteiros e detalhes interativos da pagina, ela precisa perder peso para um page builder.

## Plano de acao imediato para o tradeoff estrutural

O projeto entra agora numa fase em que organizacao estrutural vale mais do que microganho local.

Nao vamos remendar views grandes nem aceitar payload inflado so porque a tela ja funciona.

Vamos perseguir este tradeoff:

1. backend cada vez mais fino na borda HTTP
2. presenter cada vez mais claro como fronteira semantica da tela
3. frontend cada vez mais dono da composicao visual e da repeticao de leitura
4. zero tolerancia a montagem visual residual espalhada em view quando ela puder ser promovida para uma camada propria

Sequencia obrigatoria daqui para frente:

1. remover montagem visual residual das views que ainda carregam contexto demais
2. convergir essas telas para presenter ou page builder explicito
3. podar duplicacao cosmetica do payload antes de aceitar nova copy, novo card ou nova variante visual
4. fechar ownership de template, CSS e JS por tela antes de qualquer refinamento lateral

Anti-objetivos explicitos:

1. nao abrir reescrita geral do front so por zelo arquitetural
2. nao empurrar para o browser regra, permissao ou decisao operacional
3. nao inflar presenter com mini framework, fabrica de copy ou decoracao redundante
4. nao esconder backlog estrutural atras de pequenos ajustes de interface

## Ondas de execucao

## Onda 1: retirar montagem visual residual das views

Objetivo:

1. eliminar os ultimos pontos em que a view HTTP ainda monta a tela de forma informal

Entradas:

1. extrair a edicao de plano de [../../catalog/views/finance_views.py](../../catalog/views/finance_views.py) para um presenter proprio
2. extrair a montagem do dashboard de [../../dashboard/dashboard_views.py](../../dashboard/dashboard_views.py) para uma camada de presentation
3. extrair a montagem do guia de [../../guide/views.py](../../guide/views.py) para uma camada de presentation ou builder estatico
4. deixar cada view restrita a request, autorizacao, chamada de snapshot ou query, attach do payload e resposta

Criterio de pronto:

1. nenhuma dessas views continua dona de listas visuais, copy estrutural e montagem extensa de blocos da pagina
2. cada uma passa a anexar um payload oficial em vez de espalhar contexto informal
3. a leitura da tela deixa de depender de abrir a view inteira

## Onda 2: convergir os payloads para contrato semantico enxuto

Objetivo:

1. garantir que o backend entregue so verdade semantica e pare de carregar cosmetica de tela sem necessidade

Entradas:

1. revisar cada presenter novo para separar com rigidez context, shell, data, actions, behavior, capabilities e assets
2. retirar variacoes cosmeticas redundantes do payload quando o frontend puder compor a partir da mesma fonte
3. promover links, ancoras, estados e capacidades para secoes corretas do contrato
4. manter aliases legados apenas no helper compartilhado, nunca na view ou no template por conveniencia

Criterio de pronto:

1. o payload de cada tela explica a pagina por semantica, nao por acidente de render
2. nenhum presenter novo carrega duplicacao de badge, resumo ou copy so para sustentar layout
3. a fronteira backend versus frontend fica defensavel por leitura direta do arquivo

## Onda 3: fechar ownership de composicao por tela

Objetivo:

1. fazer cada superficie relevante ficar facil de localizar, alterar e testar sem caca cega

Entradas:

1. garantir template principal fino, includes por papel claro, CSS proprio e JS proprio para cada tela tocada
2. revisar hooks estruturais para que JS e testes nao dependam de classe visual
3. revisar estados de interface para que empty, error, readonly, editable e success aparecam de forma localizavel
4. consolidar vocabulary estrutural unico entre dashboard, guide e catalogo

Criterio de pronto:

1. quem abrir uma tela responde rapido onde esta a composicao, o contrato e o comportamento
2. o JS da pagina consome contrato e hooks estaveis, nao DOM improvisado
3. a manutencao deixa de depender de memoria oral da montagem

## Onda 4: congelar a regra estrutural para o restante do projeto

Objetivo:

1. impedir regressao para contexto informal e remendo estrutural nas proximas entregas

Entradas:

1. transformar este plano em regra de entrada para qualquer tela nova ou tela revisitada
2. atualizar blueprint e ownership map sempre que uma nova fronteira estrutural ficar canonica
3. adicionar testes ou smoke checks onde a nova fronteira reduzir risco real
4. recusar qualquer nova mudanca que reintroduza montagem visual pesada em view HTTP

Criterio de pronto:

1. a regra deixa de ser intencao e passa a ser comportamento padrao do repositorio
2. novas telas nascem no contrato certo sem depender de mutirao futuro

## Frentes prioritarias do OctoBox agora

Pela pressao estrutural atual, a ordem recomendada e:

1. `membership-plan`
2. `dashboard`
3. `guide`
4. `finance-center` apenas para poda semantica fina se sobrar resquicio
5. `operations` e outras telas novas somente sob a regra nova, sem reabrir as ja estabilizadas

Motivo:

1. a edicao de plano ainda concentra montagem de tela dentro da view e oferece o melhor ganho estrutural por baixo risco
2. o dashboard ja tem payload, mas ainda mistura borda HTTP com modelagem visual e merece separar isso antes de crescer mais
3. o guia ainda usa a view como deposito de blocos visuais estaticos e precisa servir de exemplo de organizacao
4. o centro financeiro principal ja esta mais maduro e deve receber apenas poda semantica, nao nova cirurgia ampla
5. operations ja esta bem encaixado no shape atual e deve ser protegido, nao reaberto sem motivo forte

## Ordem operacional imediata

Para nao dispersar energia, a execucao imediata passa a ser esta:

1. extrair presenter da edicao de plano
2. extrair presenter do dashboard
3. extrair builder do system map
4. revisar payloads dessas tres frentes para eliminar copy e derivacoes cosmeticas desnecessarias
5. so depois disso refinar qualquer composicao visual residual que ainda atrapalhe leitura ou manutencao

Definicao de sucesso dessa rodada:

1. menos logica de tela dentro das views
2. menos contexto informal por pagina
3. contrato mais curto, mais semantico e mais facil de localizar
4. nenhum aumento desnecessario de arquivos ou camadas sem funcao clara

## Guardrails para nao perder alinhamento

## 1. Nao quebrar a fachada para organizar o bastidor

Toda reorganizacao interna deve preservar a leitura principal do produto.

## 2. Nao criar um mini framework improvisado dentro do projeto

Se a modularizacao começar a exigir mais infraestrutura que produto, a direcao saiu do eixo.

## 3. Nao antecipar SPA por ansiedade arquitetural

Separar tudo cedo demais pode enfraquecer justamente o alinhamento que queremos proteger.

## 4. Nao deixar o backend limpo e o front informal

Se o backend fala em `use case`, `facade` e `snapshot`, o front precisa aprender a falar em `page payload`, `screen action` e `module boundary`.

## 5. Nao confundir componente com repeticao visual casual

Componente compartilhado sem contrato estavel vira acoplamento bonito.

## Definicao de pronto para o front-end alinhado

Vamos considerar que a reestruturacao atingiu base boa quando estas afirmacoes forem verdadeiras:

1. as telas principais parecem partes do mesmo predio
2. as paginas centrais nao dependem de scripts inline grandes
3. cada pagina possui contratos visuais explicitos
4. os estilos de pagina nao vazam de forma imprevisivel para outras areas
5. o backend entrega payload de interface mais claro do que simples contexto ad hoc
6. o comportamento de front pode mudar sem redesenhar a regra de negocio
7. a conversa entre tela e backend acontece por fronteiras pequenas e oficiais
8. a troca futura de delivery ou canal nao obriga reescrever tudo

## Checklist de decisao para qualquer mudanca futura no front

Antes de aprovar qualquer mudanca relevante de front, responder:

1. esta mudanca fortalece ou enfraquece a Front Display Wall?
2. a responsabilidade nova ficou no shell, na pagina, no componente ou no contrato?
3. o backend esta entregando a informacao certa ou a tela esta compensando desorganizacao por conta propria?
4. esse comportamento pertence mesmo a esta pagina?
5. essa regra deveria viver em utilitario, componente, page module ou presenter?
6. esta alteracao reduz custo futuro ou cria mais um ponto especial?
7. a tela continua parecendo parte do mesmo sistema?

## Checklist de pronto para uma tela reestruturada

Antes de considerar uma tela realmente alinhada, conferir:

1. o papel da tela esta descrito com clareza
2. o payload da tela pode ser explicado sem abrir o template inteiro
3. o template principal ficou fino o suficiente para leitura rapida
4. os blocos internos possuem includes com responsabilidade clara
5. o comportamento interativo saiu do template quando a interacao e relevante
6. o CSS da tela mora no lugar certo e nao depende de vazamento casual
7. links, endpoints e anchors oficiais nao estao espalhados sem contrato
8. a conversa com o backend ficou mais explicita do que antes
9. a tela preservou a identidade da Front Display Wall
10. a mudanca deixou menos residuo estrutural do que havia antes

## Template mental de review para o front do OctoBox

Quando revisar uma alteracao de front, usar esta lente:

1. isso fortalece a fachada ou so maquilha o problema?
2. isso reduz acoplamento ou apenas muda o acoplamento de lugar?
3. a tela ficou mais explicavel por contrato?
4. o backend e o front ficaram mais proximos na linguagem estrutural?
5. o sistema esta mais organico depois desta mudanca?

## Proxima execucao recomendada

Depois deste guia, a ordem mais inteligente e:

1. executar a Onda 1 na grade de aulas
2. aplicar o mesmo padrao na ficha do aluno
3. migrar o financeiro para o mesmo modelo
4. consolidar o contrato-padrao de page payload
5. revisar o dashboard como fachada unificadora final

## Frase de fechamento

O OctoBox nao quer um front que apenas apareca na frente do backend.

Quer uma frente viva, organica, clara e estruturalmente honesta.

Quando essa reestruturacao estiver madura, front e backend vao parecer menos dois lados colados e mais um unico sistema nervoso:

1. um centro que pensa
2. uma fachada que expressa
3. corredores que comunicam
4. sinais que chegam onde precisam chegar
5. mudancas locais que nao lesionam o corpo inteiro
