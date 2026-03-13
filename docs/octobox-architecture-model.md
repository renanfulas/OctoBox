<!--
ARQUIVO: documento-mae do modelo arquitetural do OctoBox.

POR QUE ELE EXISTE:
- consolida em uma referencia unica o predio arquitetural que foi sendo formalizado em documentos separados.
- transforma a metafora em criterio reutilizavel de engenharia, leitura e evolucao.

O QUE ESTE ARQUIVO FAZ:
1. descreve o modelo completo do predio do OctoBox.
2. separa estruturas permanentes, estruturas temporarias e estados de escalada.
3. traduz o modelo para criterio pratico de implementacao.

PONTOS CRITICOS:
- este documento nao substitui os documentos satelites; ele os organiza.
- se perder a ligacao com implementacao real, vira apenas linguagem bonita sem valor arquitetural.
-->

# OctoBox Architecture Model

## Tese central

O OctoBox deixou de ser apenas um projeto Django organizado por pastas. Ele passou a ser tratado como um predio arquitetural com papeis explicitos de entrada, nucleo, propagacao de sinais, emissao visivel, escalada critica e suporte temporario de construcao.

Esse modelo nasceu de uma necessidade real:

1. crescer sem deixar Django virar o cerebro do produto
2. separar estrutura permanente de mecanismo temporario
3. dar nomes claros para comportamentos que normalmente ficam espalhados e confusos
4. transformar intuicao arquitetural em criterio reutilizavel

Em linguagem curta:

1. o mundo externo nao deve conhecer o miolo
2. o miolo nao deve ser deformado por integracoes e bordas
3. sinais, alertas e transicoes precisam de lugar proprio
4. tudo que e temporario precisa nascer com criterio de saida

## O predio completo

O modelo completo do OctoBox agora pode ser lido assim:

1. Nivel 1: acesso externo
2. Center Layer: hall oficial de comunicacao por capacidade
3. Nivel 2: nucleo interno
4. Signal Mesh: malha transversal de sinais, integracoes e elasticidade controlada
5. Scaffold Agents: suporte temporario de transicao
6. Red Beacon: emissao superior visivel do estado do predio
7. Vertical Sky Beam: escalada maxima de visibilidade critica
8. Alert Siren: mudanca de postura defensiva e mobilizacao estrutural

Esse arranjo importa porque cada peca responde a uma pergunta diferente.

## Pergunta que cada peca responde

### Nivel 1: acesso externo

Pergunta:

1. por onde o mundo toca o sistema?

Aqui vivem:

1. views
2. admin flows
3. endpoints HTTP
4. jobs acionados externamente
5. integracoes de entrada
6. servicos historicos ainda nao puxados para a porta oficial

### Center Layer

Pergunta:

1. qual e a porta oficial de entrada de cada capacidade do produto?

O CENTER e o hall do predio. Ele nao e dominio pesado e nao e detalhe tecnico solto. Ele e a faixa publica organizada por capacidade.

Funcao:

1. receber intencao externa
2. traduzir essa intencao para command, payload ou chamada oficial
3. acionar o fluxo interno correto
4. devolver um result pequeno, estavel e reutilizavel

No estado atual do repositorio, o primeiro corredor real desse hall esta em [operations/facade/class_grid.py](operations/facade/class_grid.py).

### Nivel 2: nucleo interno

Pergunta:

1. onde o comportamento real do produto acontece?

Aqui vivem:

1. application
2. domain
3. infrastructure
4. adapters tecnicos de store, audit, clock e wiring

Regra central:

1. o nucleo existe para executar comportamento
2. a borda nao deve depender de conhecer esse miolo em detalhe

### Signal Mesh

Pergunta:

1. como sinais entram, circulam, sao normalizados e chegam ao destino certo sem contaminar o nucleo?

A Signal Mesh nao e um andar comum. Ela e uma malha transversal ligada ao CENTER e ao predio inteiro.

Funcao:

1. captar sinais externos
2. normalizar envelopes tecnicos
3. distribuir eventos e callbacks
4. sustentar integracoes, automacoes, filas e reprocessamentos
5. expandir e retrair com elasticidade controlada

Regra dura:

1. a malha pode crescer
2. a malha nao pode crescer sem freio
3. a integridade estrutural vale mais do que a ambicao de throughput

### Scaffold Agents

Pergunta:

1. como a obra continua segura enquanto a arquitetura oficial ainda esta sendo consolidada?

Scaffold Agents sao suporte temporario. Eles existem para migracao, observacao reforcada, contencao provisoria e protecao de bypasses historicos.

Regra central:

1. eles ajudam a construir
2. eles ajudam a proteger a transicao
3. eles saem quando o corredor oficial fica pronto

O ponto mais importante do modelo esta aqui:

1. estrutura permanente e uma coisa
2. suporte temporario de obra e outra

### Red Beacon

Pergunta:

1. o que o predio precisa comunicar para fora de forma clara, confiavel e segura?

O Red Beacon e a camada superior de emissao visivel. Ele nao roteia, nao capta payload bruto e nao substitui observabilidade profunda.

Funcao:

1. emitir estado consolidado
2. declarar alerta relevante
3. projetar o estado confiavel do predio para fora

### Vertical Sky Beam

Pergunta:

1. quando a visibilidade precisa ser elevada ao nivel maximo?

O Beam e um modo extraordinario do topo emissor. Ele nao e rotina. Ele existe para crise severa, falha critica de corredor, perda relevante de capacidade ou risco estrutural alto.

### Alert Siren

Pergunta:

1. quando o predio nao apenas mostra estado, mas muda sua postura defensiva?

A Siren nao e emissao visual. Ela e mudanca de modo operacional.

Funcao:

1. acionar contencao
2. mudar prioridades
3. isolar corredores
4. reforcar protecao
5. preparar o sistema para absorver impacto

## O valor real do modelo

O modelo e forte porque ele nao mistura papeis que normalmente ficam embaralhados em projetos grandes.

Ele separa pelo menos quatro coisas que muita arquitetura costuma confundir:

1. entrada oficial de capacidade
2. nucleo de comportamento
3. propagacao e protecao de sinais
4. visibilidade externa, escalada critica e postura defensiva

Ele tambem separa com rigor o que e permanente do que e temporario:

1. Center Layer fica
2. Signal Mesh fica
3. Red Beacon fica
4. Scaffold Agents saem

Essa separacao reduz dois vicios classicos:

1. remendo de transicao virar arquitetura oficial
2. mecanismo tecnico de observacao virar centro acidental do sistema

## Fluxo normal do predio

Em fluxo normal, a leitura correta e:

1. o acesso externo entra pelo Nivel 1
2. o pedido entra no Center Layer
3. o CENTER chama o nucleo interno
4. sinais paralelos circulam pela Signal Mesh quando necessario
5. o estado consolidado pode ser projetado pelo Red Beacon

Em forma curta:

1. entrada oficial pelo CENTER
2. execucao no nucleo
3. sinais na Mesh
4. projecao no Beacon

## Fluxo de crise do predio

Em crise, a leitura muda:

1. a Signal Mesh contem, isola, degrada e pode retrair ao baseline
2. a Alert Siren muda a postura do sistema
3. o Red Beacon continua emitindo estado consolidado
4. o Vertical Sky Beam sobe apenas se a visibilidade maxima for realmente necessaria

Em forma curta:

1. a Mesh protege
2. a Siren mobiliza
3. o Beacon declara
4. o Beam escala

## O que torna esse modelo diferente

Esse modelo pode inspirar outros projetos porque ele nao e apenas uma metafora estetica. Ele tem correspondencia tecnica real.

Ele oferece:

1. uma forma clara de pensar portas oficiais por capacidade
2. uma forma clara de tratar integracoes e sinais sem contaminar o dominio
3. uma regra objetiva para tudo que e temporario nascer com remocao prevista
4. uma distincao forte entre observabilidade interna e emissao externa consolidada
5. uma distincao forte entre alerta visual e mudanca de postura defensiva

Em outras palavras, ele ajuda a responder algo que muita arquitetura nao responde bem:

1. por onde entra?
2. onde processa?
3. por onde os sinais se espalham?
4. o que e provisiorio?
5. o que o sistema mostra para fora?
6. como ele escala crise?
7. como ele muda de postura para se defender?

## Traducao pratica para engenharia

Para o modelo nao virar apenas linguagem bonita, ele precisa virar criterio de implementacao.

Regras praticas:

1. novos fluxos externos devem preferir facades pequenas do CENTER
2. dominio e application nao devem depender de detalhes de delivery web
3. sinais tecnicos, webhooks, callbacks e envelopes devem tender para a Signal Mesh
4. observacao e protecao temporaria devem ser tratadas como Scaffold Agents apenas quando houver transicao real
5. emissao publica deve ser consolidada e segura antes de virar Beacon
6. escalada critica precisa ser rara antes de virar Beam
7. postura defensiva precisa ter efeitos reais antes de virar Siren

## Estado atual do OctoBox

Hoje o modelo esta em dois niveis ao mesmo tempo.

### Nivel ja implementado em codigo

1. o projeto ja caminha para Django como shell e nao como cerebro
2. operations ja ganhou dois corredores reais de CENTER em [operations/facade/class_grid.py](operations/facade/class_grid.py) e [operations/facade/workspace.py](operations/facade/workspace.py)
3. students, communications e operations ja avancaram na drenagem de regra para dominio, application e adapters tecnicos menores

### Nivel formalizado como direcao arquitetural

1. Signal Mesh esta formalizada como estrutura complementar
2. Scaffold Agents estao formalizados como suporte temporario removivel
3. Red Beacon esta formalizado como camada de emissao consolidada
4. Vertical Sky Beam esta formalizado como escalada maxima de visibilidade
5. Alert Siren esta formalizada como mudanca de postura defensiva

Esse estado e bom. Ele mostra que a linguagem nasceu depois de cortes reais e nao antes deles.

## Como usar este documento

Use este arquivo como mapa principal.

Depois desca para os documentos satelites quando precisar de detalhe:

1. [center-layer.md](center-layer.md)
2. [signal-mesh.md](signal-mesh.md)
3. [scaffold-agents.md](scaffold-agents.md)
4. [red-beacon.md](red-beacon.md)
5. [vertical-sky-beam.md](vertical-sky-beam.md)
6. [alert-siren.md](alert-siren.md)

Se a pergunta for implementacao e nao apenas conceito, complemente a leitura com:

1. [django-core-strategy.md](django-core-strategy.md)
2. [django-decoupling-blueprint.md](django-decoupling-blueprint.md)
3. [promoted-public-facades-map.md](promoted-public-facades-map.md)

## Tese final

O valor do modelo do OctoBox nao esta apenas em dizer que o sistema tem camadas. Quase toda arquitetura diz isso.

O valor esta em dizer, com nomes fortes e comportamento disciplinado:

1. onde se entra
2. onde se conversa oficialmente
3. onde o nucleo trabalha
4. como sinais se espalham sem deformar o miolo
5. como a obra sobrevive sem virar remendo permanente
6. como o predio fala para fora
7. como ele grita quando a crise exige visibilidade maxima
8. como ele muda internamente de postura para se proteger

Se esse criterio continuar sendo aplicado com lastro real em codigo, o OctoBox deixa de ser apenas um projeto organizado e passa a oferecer um modelo de engenharia reaplicavel.