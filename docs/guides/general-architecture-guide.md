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

Hoje o OctoBox deve ser lido como um `monolito modular multi-tenant orientado por dominios`, com cinco marcas de maturidade que nao estavam tao claras no inicio:

1. apps reais promovidos como corredores oficiais do runtime
2. separacao mais explicita entre borda HTTP, leitura, regra e apresentacao
3. contratos de tela mais disciplinados entre backend e frontend
4. telemetria, hardening e governanca documental mais proximos da operacao real
5. isolamento multi-tenant real via schema-per-tenant (`django-tenants`), com `control` plane proprio e o primeiro box ja provisionado em producao

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

1. `config/urls.py` virou a raiz HTTP canonica do runtime do tenant, e `config/urls_public.py` passou a servir o schema public (login, signup, webhook, healthcheck, auth do aluno)
2. `access`, `catalog`, `dashboard`, `operations`, `communications`, `students`, `finance`, `auditing`, `integrations`, `jobs`, `guide`, `quick_sales`, `knowledge` e `student_app` passaram a aparecer como corredores reais do produto
3. `boxcore` deixou de ser o centro explicativo do sistema e passou a ser lido mais como ancora historica de schema, migrations e compatibilidade — agora dentro dos schemas de tenant
4. fachadas promovidas e `facades` publicas passaram a reduzir acoplamento da borda com detalhes internos
5. `page payload`, `presentation` e assets declarados passaram a organizar melhor a conversa entre backend e frontend
6. seguranca deixou de ficar implícita e ganhou throttles, admin gate, CSP, bloqueios e regras de edge documentadas
7. performance deixou de ser um desejo difuso e ganhou probe, `Server-Timing`, budgets, sprints e telemetria
8. a documentacao deixou de ser so conteudo bom e passou a ter precedencia oficial entre tese, plano, referencia, rollout e historia
9. `control` nasceu como control plane multi-tenant (`Box` como tenant, `Domain`, `Membership`, `BoxProvisioningEvent`), `signup` passou a ser o funil Early Adopters cross-tenant (landing, checkout Stripe, magic link), e `django-tenants` passou a isolar cada box em seu proprio schema Postgres (`box_<slug>`)

## Como pensar o sistema hoje

Leia o projeto em sete blocos:

1. `Plataforma e tenancy` (schema public)
   `control` (control plane: `Box`, `Domain`, `Membership`), `signup` (funil Early Adopters + Stripe), `student_identity` (identidade do aluno cross-box)
2. `Entrada e acesso`
   `config`, `access`, `api`, `integrations`, `student_app`
3. `Dominios centrais` (schema do tenant)
   `students`, `finance`, `communications`, `onboarding`, `operations`, `quick_sales`
4. `Fachadas de produto`
   `catalog`, `dashboard`, `guide`, `operations/facade`
5. `Suporte transversal`
   `shared_support`, `model_support`, `monitoring`, `reporting`, `knowledge`
6. `Estado historico`
   `boxcore`
7. `Governanca e execucao`
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

### 6. Multi-tenancy e isolamento por box

A virada estrutural mais recente saiu do papel e entrou em producao:

1. `django-tenants` com schema-per-tenant: cada box vive em seu proprio schema Postgres (`box_<slug>`), provisionado por `control.services.provision_box`
2. control plane separado do tenant runtime: `control` (SHARED) cuida de `Box`, `Domain`, `Membership` e provisionamento; os apps de dominio rodam dentro do schema do tenant
3. Hybrid Identity Model: `StudentIdentity` vive em SHARED e `Student` vive no TENANT, ligados por referencia fraca, resolvendo "um aluno em N boxes" e o boundary multi-tenant de uma vez
4. resolucao de tenant em um lugar so: `TenantBySessionMiddleware` (staff, por sessao) e `student_identity/facade/tenant_resolver.py` (aluno, pre-auth)
5. isolamento sob teste: boundary tests (B1-B12) e cache namespaced por schema, escritos antes do primeiro cliente
6. primeiro box provisionado em producao em 2026-05-23, com o primeiro aluno real autenticando via OAuth

Detalhe canonico em [../architecture/center-layer.md](../architecture/center-layer.md), nos ADRs `ADR-005` a `ADR-010`, e no plano [../plans/schema-per-tenant-migration-plan.md](../plans/schema-per-tenant-migration-plan.md).

## O que ainda e transicao

Nem tudo virou estado final. Hoje ainda vale tratar como transicao:

1. parte da dependencia historica de `boxcore`
2. coexistencia entre estrutura antiga de catalogo e trilhas mais novas em `operations/application`, `domain`, `infrastructure` e `facade`
3. coexistencia entre CSS legado de `static/css/catalog/*` e a camada mais disciplinada de `static/css/design-system/*`
4. docs antigos em `.specs/codebase` que ainda explicam bem a fase anterior, mas nao capturam toda a maturidade atual
5. transicao de escala: o produto esta em closed beta de poucos boxes e ainda precisa percorrer o caminho ate multitenancy aberto (ver [../plans/scale-transition-20-100-open-multitenancy-plan.md](../plans/scale-transition-20-100-open-multitenancy-plan.md))

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
