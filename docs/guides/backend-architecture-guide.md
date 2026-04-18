<!--
ARQUIVO: guia de arquitetura backend viva do OctoBox.

TIPO DE DOCUMENTO:
- guia de backend

AUTORIDADE:
- media para orientacao de implementacao backend

DOCUMENTO PAI:
- [README.md](./README.md)

DOCUMENTOS IRMAOS:
- [../reference/reading-guide.md](../reference/reading-guide.md)
- [../architecture/promoted-public-facades-map.md](../architecture/promoted-public-facades-map.md)
- [../architecture/django-core-strategy.md](../architecture/django-core-strategy.md)
- [../plans/catalog-page-payload-presenter-blueprint.md](../plans/catalog-page-payload-presenter-blueprint.md)
-->

# Guia de arquitetura backend

## Tese backend atual

O backend do OctoBox hoje funciona melhor quando segue esta frase:

1. `Django entrega`
2. `o dominio decide`
3. `a query le`
4. `o service ou use case muta`
5. `a fachada publica protege a borda`

## O que ficou mais eficiente

### 1. Menos acoplamento ao legado

O começo do projeto ja era forte em separacao por dominio, mas ainda explicava muita coisa a partir de `boxcore`.

Hoje o backend esta mais eficiente porque:

1. existem apps reais promovidos para varios dominios
2. o mapa de facades promovidas deixa claro qual import novo deve vencer
3. a borda esta mais protegida contra conhecer `infrastructure` cedo demais

### 2. Mais clareza entre leitura e mutacao

Hoje ja aparece melhor:

1. `queries`, `snapshots` e `selectors` para leitura
2. `services`, `actions`, `workflows` e `use_cases` para comportamento e escrita
3. `presentation` e payload builders para montagem de tela

Isso reduz aquele problema classico de backend cansativo:

1. regra escondida em view
2. leitura pesada misturada com escrita
3. template decidindo o que deveria ter sido decidido antes

### 3. Evolucao de dominios mais sensiveis

Em `operations`, por exemplo, ja existe uma trilha mais madura:

1. `application`
2. `domain`
3. `infrastructure`
4. `facade`

Isso e uma melhoria importante porque mostra um corredor mais pronto para partes onde a complexidade e maior.

## Como criar backend novo hoje

### Caso 1. Nova leitura

Se o trabalho e montar leitura rica:

1. primeiro ver se o dominio ja tem `queries` ou `snapshot`
2. depois montar contrato serializavel e previsivel
3. so entao alimentar `presentation` ou `page payload`

### Caso 2. Nova escrita ou regra de negocio

Se o trabalho muda estado do sistema:

1. a view deve ser fina
2. a regra deve nascer em `service`, `action`, `workflow` ou `use_case`
3. a borda deve receber resultado pequeno e previsivel

### Caso 3. Nova capacidade sensivel ou transversal

Se a funcionalidade sera consumida por mais de uma borda:

1. vale considerar `facade`
2. a borda nao deve conhecer detalhes internos sem necessidade

## Regra de ouro para `boxcore`

Hoje a leitura correta e esta:

1. `boxcore` ainda importa
2. mas ele nao deve voltar a ser a resposta automatica para codigo novo

Use `boxcore` principalmente quando for:

1. schema historico
2. migrations
3. compatibilidade ainda nao promovida

Prefira apps reais quando ja houver superficie promovida.

## Desenho backend mais saudavel hoje

### Borda

Arquivos tipicos:

1. `views.py`
2. `urls.py`
3. `api/views.py`
4. `admin.py`

Responsabilidade:

1. receber request
2. validar fluxo
3. chamar corredor oficial
4. devolver resposta

### Leitura

Arquivos tipicos:

1. `*_queries.py`
2. `*_snapshot*.py`
3. `presentation/*.py`

Responsabilidade:

1. consolidar dados
2. evitar ida e volta desnecessaria
3. entregar forma pronta para consumo

### Regra

Arquivos tipicos:

1. `services/*.py`
2. `actions.py`
3. `workflows.py`
4. `application/use_cases.py`

Responsabilidade:

1. mutacao
2. validacao de regra
3. orquestracao transacional
4. efeitos colaterais controlados

### Infraestrutura

Arquivos tipicos:

1. `infrastructure/*.py`
2. integracoes
3. adaptadores de store, audit, clock, cache

Responsabilidade:

1. falar com mundo externo ou detalhe tecnico
2. nao mandar na regra de negocio

## O que evitar

1. view fazendo query pesada, regra e montagem visual ao mesmo tempo
2. borda importando `infrastructure` direto quando ja existe `facade`
3. retornar objeto cru de ORM em contratos que deveriam ser serializaveis
4. espalhar mensagens, copy e estados sem dono tecnico claro

## O que ja e um bom sinal de maturidade

1. `shared_support/page_payloads.py` centraliza shape de contrato de tela
2. `operations/facade/*` mostra um corredor oficial mais limpo
3. `catalog/presentation/*` tira bastante montagem de tela da view
4. `config/urls.py` publica as entradas canonicas

## Riscos de divida tecnica

1. duplicar a mesma regra em `catalog/services` e em trilhas novas de `operations/application`
2. deixar presenter virar service disfarçado
3. empilhar fachada nova que so troca nome de import sem reduzir acoplamento real

## Regra curta para decidir onde algo novo nasce

Pergunte nesta ordem:

1. qual e o dominio dono disso?
2. isso e leitura, mutacao ou apresentacao?
3. a borda precisa de um corredor estavel?
4. isso pertence ao app real ou e compatibilidade historica?

Se essas quatro respostas estiverem claras, a chance de nascer no lugar certo sobe muito.
