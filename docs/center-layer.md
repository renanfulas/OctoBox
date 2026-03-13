<!--
ARQUIVO: formalizacao do Center Layer como andar de comunicacao entre acesso externo e nucleo interno.

POR QUE ELE EXISTE:
- transforma a ideia do novo andar em regra arquitetural oficial do projeto.
- organiza a separacao entre entradas externas e o nucleo interno por capacidade.

O QUE ESTE ARQUIVO FAZ:
1. define o que e o CENTER na arquitetura do OctoBox.
2. explica como ele se conecta com os niveis 1 e 2.
3. estabelece regras para caminhos normais e bypasses temporarios.

PONTOS CRITICOS:
- o CENTER nao pode virar uma camada generica confusa.
- bypasses fora do CENTER devem ser tratados como compatibilidade temporaria, nao como padrao.
-->

# Center Layer

## Tese central

O OctoBox entrou numa fase em que separar apenas `domain`, `application` e `infrastructure` nao basta mais para clarear a leitura do sistema.

Agora existe uma necessidade adicional:

1. criar um andar publico de comunicacao
2. separar o nivel de acesso do nivel de nucleo interno
3. dar um ponto de entrada estavel por capacidade do produto

Esse andar foi nomeado como `Center Layer`.

Em linguagem simples:

1. o CENTER e o hall do predio
2. o mundo externo entra por ele
3. o nucleo interno nao precisa mais ser conhecido diretamente pela borda

## Modelo mental do predio

O projeto agora passa a ser lido assim:

### Nivel 1: acesso

Aqui ficam as entradas que falam com o mundo externo ou com interfaces do produto.

Exemplos:

1. views
2. admin flows
3. API endpoints
4. jobs
5. integracoes de entrada
6. services historicos de compatibilidade

### CENTER: comunicacao publica por capacidade

Aqui ficam as entradas publicas organizadas por capacidade do produto.

Exemplos:

1. `operations/facade/class_grid.py`
2. futuros `operations/facade/workspace.py`, `students/facade/*`, `communications/facade/*`

Funcao do CENTER:

1. receber a intencao externa
2. montar command ou payload de entrada adequado
3. chamar o fluxo interno correto
4. devolver result estavel para a borda

### Nivel 2: nucleo interno

Aqui ficam as camadas que realmente executam o comportamento interno do app.

Exemplos:

1. `application`
2. `domain`
3. `infrastructure`
4. stores, audit, clock, adapters e wiring tecnico

## O que o CENTER faz

O CENTER existe para organizar comunicacao, nao para concentrar regra pesada.

Ele deve:

1. expor entradas estaveis por capacidade
2. esconder wiring interno da borda externa
3. devolver resultados pequenos e previsiveis
4. reduzir o conhecimento que views, API e services antigos precisam ter

Ele nao deve:

1. duplicar regra de negocio do dominio
2. virar repositorio generico de tudo
3. concentrar ORM pesado quando isso puder ficar abaixo dele
4. substituir `application` ou `domain`

## Regra de comunicacao

Nova regra oficial do projeto:

1. tudo que vier do mundo externo deve preferir entrar pelo CENTER
2. o caminho normal nao deve pular direto para infrastructure
3. o caminho normal nao deve conhecer wiring interno demais

Em forma curta:

1. Nivel 1 fala com o CENTER
2. o CENTER fala com o Nivel 2

## Os "rapeis"

Alguns fluxos antigos ainda nao vao passar pelo caminho principal.

Na metafora do predio, eles sao como pessoas descendo por fora com rapeis.

Tecnicamente, isso significa:

1. bypasses de compatibilidade
2. atalhos historicos ainda nao migrados
3. pontos em que a borda antiga ainda conhece mais do interior do que deveria

Os operadores temporarios desses caminhos agora foram formalizados como [scaffold-agents.md](scaffold-agents.md).

Esses rapeis podem existir nesta fase, mas so com estas condicoes:

1. precisam ser explicitos
2. precisam ser temporarios
3. nao podem virar novo padrao
4. devem ser gradualmente puxados para dentro do CENTER

## Regra de implementacao do CENTER

Cada facade do CENTER deve seguir estas regras:

1. representar uma capacidade real do produto, nao um tipo tecnico abstrato
2. ter interface pequena e facil de entender
3. usar commands/results estaveis quando fizer sentido
4. esconder detalhes como stores, audit, clock, writers e wiring concreto

Sinais de que a facade ficou boa:

1. a view nao precisa conhecer infrastructure
2. um service historico consegue ser reduzido a uma fachada fina
3. a mesma entrada pode ser reutilizada por web, API e job

Sinais de que a facade ficou ruim:

1. virou um modulo gigante e generico
2. passou a reimplementar regra que ja existe em `application` ou `domain`
3. obrigou a borda a continuar conhecendo metade do miolo interno

## Primeiro marco do CENTER

O primeiro corredor oficial desse novo andar nasceu em `operations`:

1. `operations/facade/class_grid.py`

Esse modulo ja cumpre a funcao de:

1. entrada publica estavel da grade
2. ponto de reancoragem para views e servicos historicos
3. separacao entre borda externa e wiring interno da grade

Esse marco passa a definir o primeiro terco arquitetural do projeto:

1. primeiro, separar o caos interno
2. depois, criar o CENTER
3. em seguida, puxar os acessos dispersos para dentro dele

## Regra de evolucao por terco

### Primeiro terco

Objetivo:

1. consolidar o CENTER como camada oficial
2. erguer os primeiros corredores por capacidade
3. reancorar pontos historicos mais importantes

Entregas-alvo:

1. `operations/facade/class_grid.py`
2. `operations/facade/workspace.py`
3. primeiras fachadas legadas redirecionadas para o CENTER

### Segundo terco

Objetivo:

1. reduzir rapeis e bypasses
2. expandir o CENTER para dominios mais importantes
3. fazer web, API e jobs convergirem para entradas mais parecidas

### Terceiro terco

Objetivo:

1. tornar o CENTER a entrada dominante do sistema
2. deixar bypasses apenas onde a compatibilidade historica ainda for inevitavel
3. preparar a base para mudancas maiores sem explodir a leitura arquitetural

## Regras objetivas do projeto a partir de agora

1. novos fluxos externos devem preferir entrar por uma facade do CENTER
2. novas fachadas devem ser organizadas por capacidade do produto
3. services historicos devem tender a virar adaptadores finos sobre o CENTER
4. bypasses diretos para infrastructure devem ser tratados como excecao de transicao
5. o CENTER organiza comunicacao, mas nao substitui o dominio

## Estado atual

Hoje o conceito ja nao e apenas teorico.

Ele ja existe de forma concreta em `operations`, onde a grade e o workspace ganharam entradas publicas estaveis. Com isso, `operations` passa a ter dois corredores reais dentro do CENTER.

O CENTER agora tambem tem uma estrutura complementar oficial para sinais, integracoes e expansao transversal. Para isso, leia [signal-mesh.md](signal-mesh.md).

Essa malha complementar tambem foi definida como elástica, mas com baseline fixo, expansao bounded e retracao de seguranca para proteger a estrutura.

No topo desse modelo, a camada de emissao visivel e confiavel do predio foi formalizada em [red-beacon.md](red-beacon.md).