<!--
ARQUIVO: guia canonico para transformar a Front Display Wall na aparencia real do produto.

TIPO DE DOCUMENTO:
- guia oficial de experiencia visual e aplicacao de fachada

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [front-display-wall.md](front-display-wall.md)

QUANDO USAR:
- sempre que a duvida for como desenhar, revisar, refatorar ou expandir a aparencia do produto
- antes de criar tela nova, redesenhar tela existente ou mexer na hierarquia visual de qualquer superficie importante

POR QUE ELE EXISTE:
- substitui o guia generico de UI/UX por uma direcao unica, propria e acionavel para o OctoBox
- transforma a Front Display Wall de conceito artistico em linguagem visual, regra de decisao e roteiro de implementacao
- impede que a fachada do produto vire mosaico de cards neutros, remendo visual ou painel sem alma

O QUE ESTE ARQUIVO FAZ:
1. traduz o conceito artistico da Front Display Wall para regras concretas de aparencia
2. define o que a fachada do produto deve transmitir visualmente
3. organiza um passo a passo de implementacao por camadas
4. cria criterio de revisao para saber se a experiencia ficou realmente pronta para uso

PONTOS CRITICOS:
- a fachada precisa parecer produto pronto, mesmo quando a arquitetura interna ainda estiver evoluindo
- magnetismo visual nunca pode virar ruido, maquiagem ou cenografia vazia
- prioridade, pendencia e proxima acao continuam sendo a verdade central da tela
-->

# Guia canonico da Front Display Wall

## Tese central

O OctoBox nao deve parecer um conjunto de telas corretas.

Ele deve parecer um produto com fachada propria.

Essa fachada foi formalizada em [front-display-wall.md](front-display-wall.md).

Este guia existe para transformar esse conceito em aparencia real, componente real, ritmo real de tela e plano real de execucao.

Regra mestra:

1. a frente do produto precisa parecer pronta antes de estar totalmente pronta por dentro
2. a fachada precisa ser limpa sem ser fria
3. a fachada precisa ser viva sem ser barulhenta
4. a fachada precisa mostrar operacao real sem expor o canteiro de obra como linguagem dominante
5. a pessoa precisa entender rapidamente o que esta acontecendo e sentir vontade de continuar olhando

Se uma tela for apenas organizada, mas nao tiver presenca, ela ainda nao encarnou a Front Display Wall.

Se uma tela for apenas bonita, mas esconder tensao operacional, ela tambem falhou.

## O conceito artistico em linguagem pratica

### 1. Fachada, nao bastidor

A interface e o rosto do produto.

Ela deve mostrar:

1. decisao
2. prioridade
3. estado real
4. proxima acao

Ela nao deve mostrar como linguagem dominante:

1. remendo
2. debug
3. transicao crua
4. estrutura improvisada
5. telemetria solta sem traducao humana

### 2. Continuidade, nao mosaico

As telas precisam parecer partes do mesmo edificio visual.

Isso exige unidade em:

1. tipografia
2. escala de espacamento
3. hierarquia de contraste
4. familia de superficies
5. ritmo entre hero, contexto, fila e profundidade

### 3. Magnetismo, nao enfeite

A Front Display Wall pede brilho, cor, energia e presenca.

Isso nao autoriza exagero.

Significa:

1. luz localizada, nao carnaval visual
2. cor com funcao, nao acento gratuito
3. atmosfera para atrair o olho, nao para competir com a leitura
4. hero com massa visual real, nao bloco burocratico maior

### 4. Verdade operacional, nao maquiagem

Limpeza nao significa esconder problema.

A fachada deve deixar claro:

1. o que esta saudavel
2. o que esta pressionado
3. o que esta em risco
4. o que precisa ser feito agora

### 5. Pertencimento, nao neutralidade corporativa

O produto precisa parecer algo do qual o usuario quer fazer parte.

Isso exige:

1. linguagem visual propria
2. calor controlado
3. confianca visivel
4. memoria emocional
5. impressao de produto vivo, valioso e em evolucao bonita

## O que deve desaparecer da experiencia

Qualquer redesenho orientado por este guia deve reduzir de forma agressiva os seguintes anti-padroes:

1. paginas que parecem apenas grade de cards iguais
2. heros neutros demais, com pouca assinatura visual
3. acoes principais visualmente timidas
4. blocos concorrendo no mesmo nivel de importancia
5. excesso de branco morto sem tensao visual
6. pills tentando resolver sozinhas uma hierarquia que o layout nao resolveu
7. paginas que informam bem, mas nao conduzem decisao
8. componentes com aparencia funcional, porem sem familia visual coerente com a fachada

## O que a aparencia do produto deve transmitir

Cada tela principal precisa comunicar ao mesmo tempo:

1. produto consolidado
2. operacao viva
3. leitura rapida
4. energia controlada
5. confianca
6. desejo de aproximacao

Em termos visuais, isso significa:

1. um centro de gravidade claro na pagina
2. poucos pontos de alto contraste realmente importantes
3. camadas de profundidade perceptiveis
4. respiro consistente entre blocos
5. estados com personalidade sem perder semantica

## A gramatica visual da fachada

## 1. Superficie

A fachada nao pode ser um tapete plano de cards brancos.

Ela deve trabalhar em camadas.

Camadas oficiais:

1. fundo atmosferico da cena
2. superficie principal da pagina
3. hero de comando
4. cards de decisao e fila
5. cards de contexto e apoio
6. estados compactos e sinais locais

Regra:

1. o fundo pode ter atmosfera sutil
2. a superficie principal precisa sustentar a leitura sem virar textura barulhenta
3. o hero deve parecer parte dominante da fachada, nao um card comum escalado
4. cards de apoio devem ser mais silenciosos do que cards de decisao

## 2. Luz e cor

Cor aqui e ferramenta de presenca e hierarquia.

Nao e decoracao solta.

Direcao:

1. base clara e mineral para legibilidade longa
2. um acento principal energico para comando e foco
3. cores semanticas de estado para risco, atencao, estabilidade e progresso
4. halos, gradients e brilhos apenas em pontos de comando, nunca espalhados por tudo

Regra pratica:

1. se o brilho nao ajuda a orientar o olho, ele nao deve existir
2. se a cor nao reforca papel ou estado, ela esta sobrando

## 3. Tipografia

A tipografia precisa separar produto vivo de painel generico.

Papeis tipograficos:

1. display para hero, comando do dia e grandes numeros
2. titulo editorial para secoes e cards importantes
3. texto operacional para copy, apoio e formulario
4. microtexto para sinalizacao e metadado

Regras:

1. o topo da tela precisa ter mais presenca tipografica do que o corpo
2. numeros estrategicos precisam respirar e aparecer como decisao, nao como detalhe tecnico
3. microcopy sempre humana, direta e em portugues correto

## 4. Hierarquia visual

Toda tela precisa responder em ate poucos segundos:

1. onde comeca a leitura
2. o que esta pressionado
3. o que merece acao agora
4. o que pode esperar

Ordem visual recomendada:

1. hero de comando
2. fila ou decisao principal
3. rail de contexto
4. profundidade analitica
5. detalhes secundarios

Se tudo parecer do mesmo peso, a fachada falhou.

## 5. Motion

Movimento deve reforcar presenca e feedback, nao virar distracao.

Permitido:

1. entrada suave por blocos principais
2. hover com elevacao curta e controlada
3. foco visivel com energia clara
4. transicao curta de estado para sinais importantes

Proibido:

1. animacao continua decorativa sem funcao
2. elementos pulsando o tempo todo
3. efeitos que comprometam leitura, contraste ou performance

## 6. Verdade operacional na superficie

A fachada precisa mostrar tensao real de forma humana.

Cada tela principal deve deixar visivel:

1. prioridade
2. pendencia
3. proxima acao

Essa triade vale para hero, cards, trilhos e estados vazios.

## Familias oficiais de componente

Estas familias devem governar a evolucao visual do produto.

## 1. Hero de comando

E a grande massa frontal da tela.

Deve ter:

1. titulo com presenca
2. copy curta e certeira
3. CTA principal evidente
4. contexto lateral compacto com pulso do dia
5. atmosfera visual propria

Nao deve ter:

1. aparencia de card comum
2. ruido decorativo excessivo
3. tres ou quatro CTAs disputando protagonismo igual

## 2. Card de decisao

Bloco que responde o que deve acontecer agora.

Deve ter:

1. cabeca forte
2. numero ou estado dominante
3. justificativa curta
4. CTA unico ou trilha curta de acao

## 3. Card de fila

Bloco de pressao operacional.

Serve para cobrancas, alunos em risco, entradas e ocorrencias.

Deve comunicar:

1. volume
2. ordem
3. urgencia
4. proxima acao

## 4. Card de contexto

Bloco de apoio que nao compete com a decisao principal.

Serve para:

1. agenda lateral
2. radar resumido
3. leitura complementar
4. apoio de navegacao

Regra:

1. ele deve ser visualmente mais silencioso do que decisao e fila

## 5. Card de mudanca

Bloco que mostra variacao desde ontem, desde o ultimo turno ou desde a ultima leitura importante.

Serve para tirar o produto do estado de fotografia parada e revelar dinamica real da operacao.

Funcao:

1. comunicar tendencia: melhora, piora ou estabilidade
2. reforcar decisao: vale a pena investigar isso?
3. criar senso de movimento no produto

Aparencia:

1. numero ou valor principal em destaque
2. indicador de variacao com seta para cima ou para baixo e percentual ou valor absoluto
3. escala de cor semantica: verde para variacao positiva, vermelho para variacao negativa e cinza ou azul para neutro ou informativo
4. sparkline opcional de sete dias para contexto temporal, quando houver leitura historica suficiente

Exemplos descritivos:

1. card de alunos ativos: numero 17 em tipografia display, abaixo um badge com variacao positiva e uma sparkline suave mostrando crescimento na semana
2. card de inadimplencia: numero 7 em vermelho, badge de alta desde ontem e apoio contextual curto para explicar a pressao

Quando usar:

1. sempre que uma metrica puder ser comparada com um periodo anterior relevante
2. no dashboard, nos cards de decisao e nos cards de fila, quando a variacao ajudar a priorizar
3. em visoes de evolucao como crescimento de base, receita, risco ou pressao operacional

Regras de implementacao:

1. a variacao deve vir de calculo no backend, via snapshot, query ou presenter, nunca de conta improvisada no front
2. a sparkline, se usada, deve nascer de historico leve, como os ultimos sete pontos, e chegar ao template pronta para renderizacao simples
3. o tom da cor precisa respeitar a semantica de negocio: crescimento, lucro, risco, queda ou estabilidade nao compartilham a mesma leitura

## 6. Estado vazio aspiracional

Estado vazio aqui nao e buraco sem conteudo.

Ele deve comunicar:

1. o que ainda nao existe
2. por que isso importa
3. qual o proximo passo sensato
4. qual e o tom emocional daquele vazio

## Aplicacao por tipo de tela

## Dashboard

O dashboard e a fachada frontal mais pura do produto.

Ele deve parecer uma mesa de comando editorial com hierarquia curta, acao clara e profundidade analitica sem repeticao.

Estrutura recomendada:

1. hero dominante
2. trilho superior com 3 cards iguais de prioridade do box
3. pulso do box em numeros com 2 cards lideres e uma grade de suporte sem redundancia
4. rail lateral apenas de agenda e contexto vivo
5. profundidade analitica abaixo da linha de comando

Regra estrutural do dashboard owner:

1. o card da esquerda do topline sempre representa urgencia e fala de perda ou ganho direto de caixa
2. o card do meio sempre representa emergencia e fala de perda ou ganho indireto do negocio, nunca de rotina operacional neutra
3. o card da direita sempre representa risco e fala de desorganizacao, ruido operacional ou fragilidade estrutural
4. os 3 cards do topline devem manter a mesma largura e a mesma altura visual
5. o rail lateral do dashboard deve ficar restrito a agenda e nao competir com a linha principal de decisao
6. a grade de metricas abaixo nao pode repetir o que ja esta no topline nem o que os 2 cards lideres ja resolveram
7. cada metrica da grade de suporte deve responder uma pergunta diferente do owner: comercial, agenda, engajamento ou carteira
8. se uma metrica nao muda uma decisao diaria do box, ela nao deve ocupar a grade principal do dashboard
9. ajustes de espacamento no dashboard devem ser conservadores e manter uma cadencia proxima de 8, 13 e 21 sempre que isso nao deformar a responsividade

## Owner

O owner nao quer navegar para descobrir o que importa.

Ele quer decidir rapido.

Estrutura recomendada:

1. uma prioridade urgente
2. uma leitura emergente
3. um risco estrutural
4. dois cards lideres de pulso do negocio
5. uma grade secundaria sem redundancia e so depois profundidade adicional

## Coach

O coach opera o turno.

Estrutura recomendada:

1. abertura do dia
2. turma ativa ou proxima turma
3. presenca e ocorrencia como acao central
4. bloco de fechamento da aula

## Recepcao

Recepcao precisa acolher, orientar e resolver sem travar.

Estrutura recomendada:

1. quem chegou
2. qual aula importa agora
3. qual cobranca cabe no balcao
4. quais respostas precisam ser dadas rapidamente

## Grade de aulas

A grade nao deve ser apenas agenda bonita.

Ela deve parecer centro de orquestracao.

Estrutura recomendada:

1. agenda do agora
2. gargalos de ocupacao
3. janelas subutilizadas
4. acoes de ajuste rapido

## Plano de implementacao por camadas

O produto nao deve ser redesenhado no improviso.

Aplicacao correta segue esta ordem.

## Etapa 1. Definir a gramatica da fachada

Objetivo:
traduzir o conceito artistico em tokens, regras de contraste, escala de profundidade e papeis de componente.

Entregaveis:

1. paleta oficial da fachada
2. escala de superficies e bordas
3. escala de sombra e brilho
4. escala tipografica por papel
5. regras de uso de gradiente e halo

Done criteria:

1. qualquer tela nova consegue nascer do sistema, nao de improviso local

## Etapa 2. Refazer o hero compartilhado

Objetivo:
transformar o hero em grande superficie de comando.

Aplicar em:

1. estrutura base de hero compartilhado
2. variantes de dashboard, owner, coach e recepcao

Mudancas esperadas:

1. mais presenca tipografica
2. mais atmosfera visual controlada
3. CTA principal mais obvio
4. painel lateral menos burocratico e mais vivo

Done criteria:

1. o topo da tela ja parece produto proprio sem depender do resto da pagina

## Etapa 3. Criar as familias de cards da fachada

Objetivo:
parar de depender de um mesmo card neutro para todos os papeis de leitura.

Criar familias:

1. comando
2. fila
3. contexto
4. mudanca
5. estado vazio

Done criteria:

1. cada familia tem contrato visual claro e papel reconhecivel

## Etapa 4. Reorganizar a composicao macro das paginas

Objetivo:
trocar mosaico por cena.

Regras:

1. uma area de destaque principal por tela
2. rail lateral mais silencioso
3. profundidade analitica sempre abaixo do comando, nunca acima
4. grids empilham antes de esmagar conteudo

Done criteria:

1. a pessoa entende a hierarquia da pagina sem precisar ler tudo

## Etapa 5. Aplicar primeiro no dashboard

Objetivo:
usar o dashboard como laboratorio principal da nova fachada.

Por que primeiro aqui:

1. e a vitrine mais direta do produto
2. concentra hero, decisao, fila, rail e profundidade
3. permite validar a linguagem antes de expandir

Done criteria:

1. o dashboard passa a parecer a frente oficial do OctoBox

## Etapa 6. Expandir para owner, coach e recepcao

Objetivo:
adaptar a mesma linguagem de fachada ao ritual de cada papel.

Regra:

1. o edificio visual continua o mesmo
2. o ritmo da operacao muda conforme o papel

Done criteria:

1. cada workspace parece parte do mesmo produto, mas com compasso proprio

## Etapa 7. Levar a linguagem para catalogo e grade

Objetivo:
fazer financeiro, alunos e grade sairem da logica de paineis soltos e entrarem na logica da fachada.

Prioridades:

1. grade como centro de orquestracao
2. financeiro como centro de pressao e decisao
3. alunos como centro de vinculo, risco e acompanhamento

Done criteria:

1. as areas de catalogo deixam de parecer anexos com visual paralelo

## Etapa 8. Fechar estados, acessibilidade e responsividade

Objetivo:
garantir que a fachada continue forte fora do desktop ideal.

Validacoes obrigatorias:

1. mobile e tablet preservam hierarquia
2. foco continua visivel
3. contrastes seguem legiveis
4. motion nao atrapalha leitura
5. estados vazios, loading e erro mantem a identidade da fachada

Done criteria:

1. a experiencia continua viva e usavel em qualquer largura relevante

## Passo a passo para aplicar em uma tela real

Use esta sequencia sempre.

## 1. Defina a verdade da tela

Responda antes de desenhar:

1. o que essa tela resolve
2. qual e a prioridade central
3. qual e a pendencia mais sensivel
4. qual e a proxima acao que precisa ficar obvia

Se isso nao estiver claro, ainda e cedo para mexer no visual.

## 2. Escolha a cena principal

Decida qual bloco vai dominar a fachada da tela:

1. comando
2. fila
3. agenda
4. risco
5. decisao numerica

So existe uma cena principal por tela.

## 3. Monte o hero como porta de entrada

O hero precisa:

1. declarar o contexto
2. anunciar a decisao principal
3. oferecer a primeira acao
4. mostrar um pulso lateral do recorte atual

## 4. Organize a hierarquia abaixo do hero

Regra:

1. decisao ou fila principal primeiro
2. contexto ao lado ou logo abaixo
3. profundidade analitica depois

Nunca coloque apoio competindo com o bloco que deveria mandar.

## 5. Escolha a familia certa de componente

Pergunta pratica:

1. isto e comando
2. isto e fila
3. isto e contexto
4. isto e mudanca
5. isto e estado

Se nao souber responder, o componente ainda esta sem papel claro.

## 6. Aplique magnetismo controlado

Antes de adicionar atmosfera, confirme:

1. onde o olho deve pousar primeiro
2. qual superficie pode receber energia visual
3. qual superficie deve ficar silenciosa

So depois disso use:

1. gradiente
2. halo
3. elevacao
4. brilho
5. acento forte

## 7. Revise a verdade operacional

Cheque se a tela mostra:

1. o que esta bem
2. o que esta ruim
3. o que pede acao agora
4. o que pode esperar

Se a tela estiver bonita mas neutra demais, ela ainda nao esta pronta.

## 8. Revise responsividade e foco

Cheque:

1. hero continua dominante no mobile sem virar bloco esmagado
2. CTA principal continua facil de tocar
3. grids empilham antes de comprimir
4. rails laterais viram segunda camada, nao bagunca

Responsividade do hero: mantendo a dominancia em telas pequenas

O hero e a ancora visual da tela.

Em mobile e tablet, ele nao pode simplesmente encolher ou virar mais um card na pilha.

E preciso adaptar a composicao sem perder a funcao de comando.

Estrategias de adaptacao:

1. empilhamento vertical controlado: titulo, copy, CTA e painel lateral devem reorganizar a leitura sem comprimir blocos lado a lado
2. reducao tipografica progressiva: use escalas fluidas para manter o titulo como maior elemento da tela mesmo em larguras menores
3. painel lateral vira card de contexto abaixo: o pulso lateral pode descer para uma mini grade mais silenciosa depois do CTA
4. CTA adaptado para toque: altura minima de 48px e largura total quando isso melhorar o uso em mobile
5. esconder elementos nao essenciais: decoracao ou apoio secundario podem sair da primeira dobra se houver alternativa clara

Exemplo de transformacao do hero no mobile:

1. no desktop, titulo grande, copy curta, CTA principal e painel lateral convivem na mesma cena
2. no mobile, titulo medio, copy curta e CTA principal aparecem primeiro, e o painel lateral vira uma camada abaixo com os mesmos numeros em mini cards

Diretrizes de codigo:

1. use CSS Grid ou Flex com rearranjo por media query em vez de so reduzir largura e esperar que caiba
2. defina breakpoints pelo comportamento do conteudo, nao apenas por classes genericas de dispositivo
3. teste em emuladores ou dispositivos reais para validar se o hero ainda e a primeira leitura da tela

Checklist de responsividade do hero:

1. o titulo ainda e o elemento de maior contraste
2. o CTA principal continua acessivel e facil de tocar
3. as informacoes laterais nao competem visualmente com o comando
4. a hierarquia visual se mantem mesmo com empilhamento
5. nenhum conteudo essencial foi cortado ou escondido sem alternativa

## 9. Revise consistencia com o edificio visual

Pergunte:

1. essa tela parece parte do mesmo OctoBox?
2. ela parece produto ou experimento local?
3. a fachada continua limpa, viva e humana?

## A camada de dados da fachada: page payloads e presenters

A fachada so existe de verdade se os dados que ela exibe forem precisos, pontuais e ricos o suficiente para sustentar a hierarquia visual.

O backend nao deve apenas entregar numeros crus.

Ele deve preparar o terreno para a decisao.

O que presenters, services e snapshot queries precisam entregar:

1. valores principais: os numeros que vao aparecer nos cards
2. variacoes temporais: comparacao com periodos anteriores, incluindo variacao percentual, variacao absoluta e tendencia
3. sparklines: arrays curtos de historico para graficos simples quando a leitura temporal fizer diferenca
4. status semanticos: classificacoes como critico, atencao, estavel ou bom para orientar cor e prioridade
5. metadados de acao: proxima acao sugerida, URL, rotulo e prioridade da CTA

Exemplo de payload para um card de inadimplencia:

```json
{
	"titulo": "Cobrancas atrasadas",
	"valor": 7,
	"variacao": {
		"percentual": 40,
		"absoluta": 2,
		"direcao": "up",
		"periodo": "desde ontem"
	},
	"status": "critico",
	"sparkline": [3, 4, 5, 5, 6, 7, 7],
	"acoes": [
		{
			"rotulo": "Ver cobrancas",
			"url": "/financeiro?filtro=atrasadas",
			"primaria": true
		}
	]
}
```

Onde isso deve ser implementado:

1. nos apps dashboard, operations e catalog, conforme a superficie e a responsabilidade de cada pagina
2. em services, queries ou presenters dedicados, seguindo o padrao de arquivos como snapshot queries e presenters especificos
3. no backend, antes da renderizacao, deixando o template responsavel por compor a fachada e nao por decidir regra de negocio

Vantagem:

1. com payloads ricos, a fachada pode variar dinamicamente sem exigir mudanca estrutural no HTML
2. o mesmo card pode ganhar sparkline, mudanca de estado ou CTA diferente sem reinventar o componente
3. a decisao visual continua no front, mas apoiada em dados ja preparados para leitura humana

## Criterios de aprovacao da fachada

Uma tela esta pronta quando:

1. parece produto consolidado e nao estrutura remendada
2. tem um centro de gravidade claro
3. mostra prioridade, pendencia e proxima acao sem esforco
4. usa energia visual com criterio
5. transmite presenca sem comprometer clareza
6. continua legivel em mobile, tablet e desktop
7. pertence claramente ao mesmo edificio visual das outras superficies

## Relacao com os outros guias

Este e o guia principal para pensar a aparencia do produto.

Use [front-display-wall.md](front-display-wall.md) para a base conceitual e arquitetural da metafora.

Use [css-guide.md](css-guide.md) para decidir onde cada classe deve morar, como manter contrato explicito e como evitar remendo estrutural no CSS.

Use [front-pr-checklist.md](front-pr-checklist.md) para revisar PRs curtos de front antes de subir mudancas.

Use [front-display-wall-implementation-checklist.md](front-display-wall-implementation-checklist.md) para acompanhar a implantacao da fachada por etapas.

## Regra final

Se houver duvida entre deixar a tela apenas correta ou faze-la parecer uma fachada viva, escolha a fachada viva.

Mas faca isso sem sacrificar:

1. clareza
2. prioridade
3. verdade operacional
4. acessibilidade
5. disciplina estrutural

Esse equilibrio e o trabalho.


