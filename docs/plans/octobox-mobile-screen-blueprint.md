<!--
ARQUIVO: blueprint de telas do aplicativo mobile do Octobox.

TIPO DE DOCUMENTO:
- execucao ativa de produto

AUTORIDADE:
- media

DOCUMENTO PAI:
- [../experience/octobox-mobile-guide.md](../experience/octobox-mobile-guide.md)

QUANDO USAR:
- quando a duvida for quais telas, hierarquias e fluxos concretos devem materializar a visao do app mobile

POR QUE ELE EXISTE:
- traduz o guia mobile em estrutura concreta de experiencia.
- define as telas base, a ordem mental da navegacao e os blocos que cada tela deve priorizar.

O QUE ESTE ARQUIVO FAZ:
1. organiza o mapa inicial de telas do app mobile.
2. define o papel de cada area principal e secundaria.
3. estabelece criterios de hierarquia, descoberta e expansao futura.

PONTOS CRITICOS:
- este blueprint nao pode inflar o app com estrutura de sistema web comprimida.
- as telas precisam preservar velocidade mental, limpeza visual e desejo de uso.
-->

# Blueprint de Telas do App Mobile do Octobox

## Objetivo deste blueprint

Este documento transforma a direcao do app mobile em arquitetura de telas.

Ele existe para responder, com precisao, o que deve aparecer no aplicativo, em que ordem mental isso deve ser lido e como o produto deve crescer sem perder simplicidade.

## Tese estrutural

O app mobile deve ser construido em tres aneis de experiencia:

1. rotina imediata
2. exploracao desejavel
3. profundidade futura

A rotina imediata precisa estar visivel sem esforco.

A exploracao desejavel precisa estar acessivel sem poluir.

A profundidade futura precisa sinalizar crescimento sem confundir o presente.

## Mapa inicial de navegacao

O blueprint parte de cinco destinos principais:

1. Home
2. Calendario e Check-in
3. Treino
4. Features expandidas
5. Configuracoes

Leitura de prioridade:

1. Home e o centro de retorno
2. Calendario e Check-in sustentam uso recorrente
3. Treino sustenta valor diario
4. Features expandidas sustentam curiosidade e desejo
5. Configuracoes ficam presentes, mas nao protagonistas

## Shell mobile

Toda tela deve nascer sobre uma shell simples e consistente.

Componentes fixos da shell:

1. topo limpo com identificacao curta da tela
2. area central com um foco principal por vez
3. base de navegacao com home a esquerda e configuracoes a direita
4. ponto de acesso discreto para features expandidas

Regra da shell:

Nada nela pode parecer painel tecnico.

Ela precisa parecer produto de uso frequente.

## Tela 1: Home

### Missao

Ser o lugar que resolve rapido e orienta o resto do app.

### O que deve aparecer primeiro

1. saudacao curta ou identificacao do usuario
2. acesso imediato ao RM
3. proxima acao relevante do dia
4. atalhos para calendario/check-in e treino

### O que pode aparecer abaixo

1. resumo leve da semana
2. proxima aula ou compromisso
3. card curto de progresso ou frequencia

### O que nao deve acontecer

1. excesso de cards concorrendo pela atencao
2. explicacoes longas
3. metricas frias ocupando o espaco nobre

### Sinal de acerto

Ao abrir o app, a pessoa entende em segundos onde tocar.

## Tela 2: Calendario e Check-in

### Missao

Transformar presenca e rotina em algo imediato, claro e confiavel.

### Blocos principais

1. calendario visual simples
2. destaque do dia atual
3. lista curta de aulas ou sessoes do dia
4. botao ou gesto obvio para check-in

### Regras de leitura

1. o dia atual precisa saltar aos olhos
2. o status de check-in precisa ser entendido sem interpretar legenda demais
3. a proxima aula precisa aparecer antes do restante da agenda

### O que nao deve acontecer

1. calendario com peso burocratico
2. excesso de marcacoes simultaneas
3. fluxo de check-in escondido em submenu

## Tela 3: Treino

### Missao

Fazer o treino parecer acessivel, vivo e retornavel.

### Blocos principais

1. treino do dia ou da semana em destaque
2. status claro do que e hoje
3. progresso ou conclusao de forma leve
4. acesso a detalhes apenas quando a pessoa quiser aprofundar

### Regras de leitura

1. o que precisa ser feito hoje aparece acima de tudo
2. a semana pode existir, mas sem esmagar o foco do dia
3. o app nao pode exigir rolagem longa para mostrar a parte principal

### O que nao deve acontecer

1. linguagem de planilha
2. excesso de campos tecnicos logo de entrada
3. densidade visual que transforme treino em obrigacao pesada

## Tela 4: Features expandidas

### Missao

Abrir o segundo plano do produto com curiosidade, nao com ruido.

### O que esta aqui

1. IA
2. predicao
3. futuras areas de exploracao inteligente

### Forma correta de entrada

Essas features devem nascer minimizadas ou discretamente sinalizadas na shell.

Quando abertas, precisam parecer uma descoberta desejavel.

### Regras de composicao

1. manter uma tela mais contemplativa e menos utilitaria
2. mostrar capacidade sem virar vitrine vazia
3. explicar pouco e demonstrar bem
4. deixar claro que se trata de camada adicional, nao obrigatoria

### Sinal de acerto

A pessoa toca porque quer ver mais, nao porque esta tentando achar o basico e se perdeu.

## Tela 5: Configuracoes

### Missao

Oferecer controle previsivel sem roubar energia do restante do app.

### Blocos principais

1. perfil e identificacao
2. preferencias essenciais
3. notificacoes e privacidade quando existirem
4. ajuda ou suporte quando fizer sentido

### Regra de tom

Configuracoes devem ser claras, compactas e sem dramatizacao visual.

Elas sao importantes, mas nao sao o palco principal do produto.

## Acesso ao RM

O RM nao deve ficar enterrado como funcao administrativa.

Ele precisa existir como acesso imediato e reconhecivel.

Diretrizes:

1. pode aparecer na Home como atalho nobre
2. precisa usar rotulo obvio
3. nao pode depender de busca profunda
4. se houver documento, codigo ou identificador alternativo, o RM continua sendo o nome mental principal para quem o procura

## Hierarquia visual por tela

Cada tela mobile precisa obedecer a esta piramide:

1. o que eu preciso agora
2. o que talvez eu faca em seguida
3. o que posso explorar depois

Quando essa ordem se inverte, o app perde a magia de parecer facil.

## Regra de blocos

Cada tela deve operar com poucos blocos dominantes.

Referencia inicial:

1. um bloco principal
2. um bloco secundario
3. um acesso lateral ou complementar

Se a tela precisar de mais do que isso, o mais provavel e que ela esteja querendo resolver assuntos demais de uma vez.

## Regra de crescimento do segundo andar

O app mobile e o segundo andar porque ele aprofunda a relacao com o usuario final.

Isso exige disciplina.

Toda nova feature deve responder estas perguntas antes de entrar:

1. ela melhora a rotina imediata ou amplia a exploracao desejavel?
2. ela cabe como area secundaria ou precisa de uma nova tela principal?
3. ela preserva a sensacao clean do aplicativo?
4. ela aumenta preferencia ou apenas adiciona volume?

Se a resposta nao sustentar essas quatro perguntas, a feature ainda nao esta pronta para nascer no mobile.

## Ordem recomendada de prototipacao

Para sair do documento e ir para tela, a ordem inicial deve ser:

1. shell mobile
2. Home
3. Calendario e Check-in
4. Treino
5. Features expandidas
6. Configuracoes

Essa ordem preserva o essencial primeiro e deixa a profundidade entrar sem baguncar a base.

## Formula curta do blueprint

No app mobile do Octobox:

1. o basico precisa ser imediato
2. o importante precisa ser bonito
3. o avancado precisa ser curioso
4. o todo precisa parecer leve

Quando isso acontecer, o celular deixa de ser apenas mais um canal.

Ele vira o lugar onde o produto ganha intimidade diaria.