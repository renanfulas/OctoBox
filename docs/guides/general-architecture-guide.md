<!--
ARQUIVO: guia geral da arquitetura viva do OctoBox.

TIPO DE DOCUMENTO:
- guia arquitetural geral

AUTORIDADE:
- media para orientacao geral
- baixa para substituir docs canonicos de architecture

DOCUMENTO PAI:
- [README.md](./README.md)

DOCUMENTOS IRMAOS:
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [../architecture/octobox-conceptual-core.md](../architecture/octobox-conceptual-core.md)
- [../architecture/promoted-public-facades-map.md](../architecture/promoted-public-facades-map.md)
- [../reference/reading-guide.md](../reference/reading-guide.md)

QUANDO USAR:
- quando a duvida for qual e a forma atual do sistema
- quando for explicar o projeto sem entrar primeiro em detalhes demais
- quando for comparar o inicio do projeto com a fase atual

POR QUE ELE EXISTE:
- traduz a arquitetura viva para uma leitura simples, pratica e atual
- mostra o que amadureceu de verdade no runtime e na documentacao
- ajuda a separar base estrutural de experimentos, legado e planos

PONTOS CRITICOS:
- este documento resume o predio; os docs profundos continuam sendo a planta tecnica
-->

# Guia geral da arquitetura

## Resumo executivo

Hoje o OctoBox deve ser lido como um `monolito modular orientado por dominios`, com quatro marcas de maturidade que nao estavam tao claras no inicio:

1. apps reais promovidos como corredores oficiais do runtime
2. separacao mais explicita entre borda HTTP, leitura, regra e apresentacao
3. contratos de tela mais disciplinados entre backend e frontend
4. telemetria, hardening e governanca documental mais proximos da operacao real

Metafora simples:

1. no inicio, o projeto era uma casa muito boa levantada muito rapido
2. agora ele ja virou um predio com corredores nomeados, mapa de manutencao e sala tecnica
3. ainda existe obra em alguns andares, mas ja existe um jeito oficial de circular sem quebrar parede toda vez

## O que mudou em relacao ao inicio

### No inicio

O projeto acertou cedo em pontos valiosos:

1. foco em fluxo operacional real
2. separacao por dominio em vez de despejar tudo em `views.py`
3. uso forte do stack nativo do Django
4. preocupacao com papeis, auditoria e rastreabilidade desde cedo

### Agora

O projeto ficou mais eficiente porque ganhou camadas de disciplina que reduzem custo mental e custo de manutencao:

1. `config/urls.py` virou a raiz HTTP canonica do runtime
2. `access`, `catalog`, `dashboard`, `operations`, `communications`, `students`, `finance`, `auditing`, `integrations`, `jobs` e `student_app` passaram a aparecer como corredores reais do produto
3. `boxcore` deixou de ser o centro explicativo do sistema e passou a ser lido mais como ancora historica de schema, migrations e compatibilidade
4. fachadas promovidas e `facades` publicas passaram a reduzir acoplamento da borda com detalhes internos
5. `page payload`, `presentation` e assets declarados passaram a organizar melhor a conversa entre backend e frontend
6. seguranca deixou de ficar implícita e ganhou throttles, admin gate, CSP, bloqueios e regras de edge documentadas
7. performance deixou de ser um desejo difuso e ganhou probe, `Server-Timing`, budgets, sprints e telemetria
8. a documentacao deixou de ser so conteudo bom e passou a ter precedencia oficial entre tese, plano, referencia, rollout e historia

## Como pensar o sistema hoje

Leia o projeto em seis blocos:

1. `Entrada e acesso`
   `config`, `access`, `api`, `integrations`, `student_app`
2. `Dominios centrais`
   `students`, `finance`, `communications`, `onboarding`, `operations`, `quick_sales`
3. `Fachadas de produto`
   `catalog`, `dashboard`, `guide`, `operations/facade`
4. `Suporte transversal`
   `shared_support`, `model_support`, `monitoring`, `reporting`
5. `Estado historico`
   `boxcore`
6. `Governanca e execucao`
   `docs`, `.specs`, `tests`, `scripts`, `tools`

## Forma arquitetural atual

A leitura mais fiel hoje e esta:

1. `Django continua sendo a casca principal de entrega`
2. `o centro conceitual ja nao deve ser descrito so por Django apps ou por boxcore`
3. `a explicacao mais madura do sistema esta em capacidades, facades, snapshots, payloads e dominios`

Em termos praticos:

1. a borda recebe a requisicao
2. um corredor oficial decide o que aquela capacidade faz
3. a leitura pesada ou regra acontece no dominio certo
4. a fachada de tela entrega um contrato de pagina previsivel
5. a interface monta a experiencia sem descobrir regra no susto

## O que hoje parece consolidado

### 1. Modularidade por dominio

A base nao esta mais organizada apenas por pastas; ela esta organizada por ownership.

Isso aparece em:

1. apps dedicados por dominio
2. docs de ownership e leitura
3. mapa de fachadas promovidas
4. fronteiras mais claras entre legado e caminho canonico

### 2. Separacao entre leitura, mutacao e apresentacao

Esse e um dos maiores saltos de maturidade.

Hoje o projeto ja mostra este desenho:

1. `queries` e `snapshots` para leitura
2. `services`, `actions`, `workflows` e `use_cases` para mutacao e regra
3. `presentation` e `page_payloads` para a fachada de tela
4. `facade` para entrada publica estavel em partes mais sensiveis

### 3. Frontend como sistema e nao como remendo

O frontend cresceu de "templates fortes" para "fachada com contrato".

Sinais disso:

1. design system em camadas
2. manifestos por superficie
3. ownership visual por dominio e persona
4. page payload com assets criticos, diferidos e de enhancement

### 4. Seguranca e operacao

O projeto saiu de um modo mais artesanal para uma postura bem mais institucional:

1. caminho privado de admin
2. rate limits por escopo
3. blind index para telefone
4. auditoria mais forte
5. runbooks e checklists de deploy, restore e rollback
6. edge playbooks e baseline de producao

### 5. Performance orientada por evidencia

O projeto ganhou linguagem e instrumentos para nao otimizar no escuro:

1. `RequestTimingMiddleware`
2. `Server-Timing`
3. Prometheus middleware
4. probes de pagina publicada
5. planos de sprint para reduzir custo de shell, CSS e assets
6. commits recentes focados em batching e telemetria de snapshot

## O que ainda e transicao

Nem tudo virou estado final. Hoje ainda vale tratar como transicao:

1. parte da dependencia historica de `boxcore`
2. coexistencia entre estrutura antiga de catalogo e trilhas mais novas em `operations/application`, `domain`, `infrastructure` e `facade`
3. coexistencia entre CSS legado de `static/css/catalog/*` e a camada mais disciplinada de `static/css/design-system/*`
4. docs antigos em `.specs/codebase` que ainda explicam bem a fase anterior, mas nao capturam toda a maturidade atual

## Regra pratica para evolucao

Se formos criar algo novo, a prioridade correta hoje e:

1. usar o app real do dominio quando ele existir
2. preferir fachada publica promovida em vez de descer direto no legado
3. manter view fina, regra fora da borda e contrato explicito de tela
4. documentar o corredor oficial antes de deixar bypass parecer normal

## Riscos de divida tecnica que ainda pedem cuidado

1. deixar `boxcore` voltar a ser import padrao no runtime novo
2. duplicar logica entre presenter, query e template
3. inflar payload com cosmetica de UI que o frontend pode compor sozinho
4. criar CSS novo fora da camada certa so por pressa local
5. otimizar performance quebrando localizacao de ownership
6. chamar de arquitetura final o que ainda e fase de consolidacao

## Leitura seguinte recomendada

1. se o foco for organizacao do time e metodo, siga para [methodology-and-organization-guide.md](./methodology-and-organization-guide.md)
2. se o foco for regra de negocio e backend, siga para [backend-architecture-guide.md](./backend-architecture-guide.md)
3. se o foco for fachada visual e contratos de tela, siga para [frontend-architecture-guide.md](./frontend-architecture-guide.md)
