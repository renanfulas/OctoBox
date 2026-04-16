<!--
ARQUIVO: mapa consolidado das fachadas reais ja promovidas.

TIPO DE DOCUMENTO:
- mapa de referencia arquitetural

AUTORIDADE:
- media

DOCUMENTO PAI:
- [django-core-strategy.md](django-core-strategy.md)

QUANDO USAR:
- quando a duvida for qual facade, surface ou namespace deve ser tratado como caminho canonico do runtime atual

POR QUE ELE EXISTE:
- Evita regressao de imports historicos ao registrar, em um unico lugar, quais caminhos sao canonicos no runtime atual.

O QUE ESTE ARQUIVO FAZ:
1. Lista as superficies publicas ja promovidas por dominio.
2. Diz qual namespace historico elas substituem.
3. Define uma regra simples para codigo novo.

PONTOS CRITICOS:
- Este mapa precisa acompanhar cada nova fachada promovida para continuar util.
-->

# Mapa de fachadas reais promovidas

Este documento responde a uma pergunta simples:

Qual caminho novo deve ser usado no runtime atual quando existir concorrencia entre um namespace real e um namespace historico em boxcore?

## Regra curta

Se existir fachada real promovida fora de boxcore, codigo novo deve importar dela.

Use `boxcore/*` apenas em tres casos:

1. migrations e app state historico do Django
2. fachadas de compatibilidade ainda nao substituidas por uma superficie real
3. testes legados que ainda nao foram reancorados

## Fachadas canonicas ja promovidas

### Models de dominio

- students/models.py
  substitui imports diretos de boxcore.models.students
- finance/models.py
  substitui imports diretos de boxcore.models.finance
- operations/models.py
  substitui imports diretos de boxcore.models.operations
- auditing/models.py
  substitui imports diretos de boxcore.models.audit
- onboarding/models.py
  substitui imports diretos de boxcore.models.onboarding
- communications/models.py
  substitui imports publicos de intake e WhatsApp antes espalhados em boxcore.models.onboarding e boxcore.models.communications

### Bases e utilitarios neutros

- model_support/base.py
  substitui boxcore.models.base para bases abstratas sem schema proprio
- shared_support/phone_numbers.py
  substitui boxcore.shared.phone_numbers para normalizacao e reconciliacao de telefone

### Acesso e auditoria

- access/roles/__init__.py
  substitui boxcore.access.roles no runtime
- auditing/__init__.py
  substitui boxcore.auditing no runtime para escrita de eventos

### Operations

- operations/actions.py
  substitui boxcore.operations.actions como porta publica e implementacao canonica das actions operacionais
- operations/facade/class_grid.py
  cria a entrada publica estavel da grade dentro do CENTER
- operations/facade/workspace.py
  cria a entrada publica estavel do workspace operacional dentro do CENTER
- operations/session_snapshots.py
  substitui boxcore.session_snapshots como superficie canonica da serializacao compartilhada de aulas para grade e dashboard

### Dashboard

- dashboard/urls.py
  substitui boxcore.dashboard.urls como entrada HTTP canonica do painel principal
- dashboard/dashboard_views.py
  substitui boxcore.dashboard.dashboard_views como camada HTTP canonica do dashboard
- dashboard/dashboard_snapshot_queries.py
  substitui boxcore.dashboard.dashboard_snapshot_queries como montagem canonica do snapshot do painel

### Guide

- guide/urls.py
  substitui boxcore.guide.urls como entrada HTTP canonica do mapa interno do sistema
- guide/views.py
  substitui boxcore.guide.views como camada canonica da pagina pedagógica Mapa do Sistema

### Students

- students/facade/student_lifecycle.py
  substitui o acesso direto do catalogo historico a students.infrastructure para cadastro rapido, intake, matricula e cobrancas do aluno

### Communications

- communications/facade/messaging.py
  substitui o acesso direto de integracoes e services historicos a communications.infrastructure para inbound WhatsApp, toque operacional e fila financeira

### Reporting

- reporting/facade/__init__.py
  cria a entrada publica estavel das exportacoes HTTP de relatorio e substitui imports diretos de reporting.infrastructure nas cascas consumidoras

### Integrations

- integrations/whatsapp/contracts.py
  substitui boxcore.integrations.whatsapp.contracts
- integrations/whatsapp/services.py
  substitui boxcore.integrations.whatsapp.services

### Roteamento HTTP

- config/urls.py
  substitui boxcore.urls como raiz canonica do roteamento HTTP do projeto

### Catalog

As entradas publicas abaixo agora sao canonicas no runtime e nao passam mais por `boxcore.catalog.services`.

O proprio pacote legado `boxcore/catalog/services/*` agora atua majoritariamente como compatibilidade fina sobre estas entradas publicas, em vez de concentrar implementacao propria.

- catalog/forms.py
  substitui boxcore.catalog.forms como superficie publica canonica dos formularios do catalog e agora aponta para implementacao real em catalog/form_definitions/*
- catalog/student_queries.py
  substitui boxcore.catalog.student_queries para leituras da area de alunos e agora concentra a implementacao canonica desses snapshots
- catalog/finance_queries.py
  substitui boxcore.catalog.finance_queries para leituras do financeiro e virou a entrada publica canonica do snapshot financeiro
- catalog/finance_snapshot/*
  substitui a montagem real historica em boxcore.catalog.finance_snapshot e concentra a implementacao canonica do snapshot financeiro no app real catalog
- catalog/class_grid_queries.py
  substitui boxcore.catalog.class_grid_queries para leituras da grade e agora concentra a implementacao canonica desse snapshot
- catalog/services/student_enrollment_actions.py
  substitui boxcore.catalog.services.student_enrollment_actions
- catalog/services/enrollments.py
  substitui boxcore.catalog.services.enrollments
- catalog/services/student_payment_actions.py
  substitui boxcore.catalog.services.student_payment_actions
- catalog/services/student_workflows.py
  substitui boxcore.catalog.services.student_workflows
- catalog/services/intakes.py
  substitui boxcore.catalog.services.intakes
- catalog/services/payments.py
  substitui boxcore.catalog.services.payments
- catalog/services/reports.py
  substitui boxcore.catalog.services.reports
- catalog/services/finance_communication_actions.py
  substitui boxcore.catalog.services.finance_communication_actions
- catalog/services/membership_plan_workflows.py
  substitui boxcore.catalog.services.membership_plan_workflows
- catalog/services/operational_queue.py
  substitui boxcore.catalog.services.operational_queue
- catalog/services/class_grid_commands.py
  substitui boxcore.catalog.services.class_grid_commands
- catalog/services/class_schedule_workflows.py
  substitui boxcore.catalog.services.class_schedule_workflows
- catalog/services/class_grid_dispatcher.py
  substitui boxcore.catalog.services.class_grid_dispatcher
- catalog/services/class_schedule_actions.py
  substitui boxcore.catalog.services.class_schedule_actions
- catalog/services/communications.py
  substitui boxcore.catalog.services.communications

## O que ainda nao esta promovido do mesmo jeito

Nem todo namespace em boxcore deve ser trocado imediatamente.

Pontos que ainda pertencem mais ao estado historico do que a uma API publica nova:

- boxcore/apps.py
- boxcore/migrations/*
- boxcore/models/* como origem concreta de varios models historicos
- boxcore/models/__init__.py como compatibilidade historica
- boxcore/urls.py como agregador legado de compatibilidade, nao mais como raiz do projeto

## Heuristica para futuras decisoes

Antes de criar mais uma fachada, responda:

1. ja existe consumo recorrente fora de boxcore que se beneficiaria de um caminho canonico?
2. o modulo alvo e runtime puro, sem impacto em schema, app_label ou migrations?
3. a nova fachada reduz acoplamento real ou so muda o nome do import?

Se a resposta for sim para as tres, a fachada provavelmente vale a pena.

## Regra de revisao para evitar regressao

Ao revisar codigo novo:

1. prefira imports por students, finance, operations, auditing, onboarding, communications, integrations, access e catalog quando houver superficie ja promovida
2. trate imports de boxcore.* no runtime como suspeitos por padrao
3. so aceite boxcore.* quando o uso for claramente historico, estrutural ou ainda sem substituto real

## Guardrail de revisao para bordas externas

Quando o codigo novo tocar qualquer fluxo externo ou casca de entrega, use esta ordem:

1. view HTTP, endpoint de API, webhook, admin action, job disparado externamente e adaptador de integracao devem preferir facade publica ou adaptador fino ja promovido
2. a borda nao deve importar `*.infrastructure` diretamente quando existir corredor oficial promovido
3. se ainda nao existir facade boa o bastante, o bypass deve nascer explicitamente classificado em plano ou inventario ativo

Traducao pratica:

1. a borda pode conhecer contrato estavel, payload normalizado e resultado pequeno
2. a borda nao deve conhecer adapter concreto, detalhe tecnico de transporte ou wiring interno
3. se a borda precisar descer para `infrastructure`, isso deixa de ser detalhe e vira excecao documentada

## Checklist curto de PR para fronteiras

Antes de aprovar um PR que toca borda externa, conferir:

1. o novo fluxo entra por facade publica quando ela ja existe
2. o modulo de borda nao importou `*.infrastructure` sem justificativa escrita
3. o eventual bypass foi registrado em doc ativo com motivo, risco e corredor desejado
4. a mudanca preservou compatibilidade por adaptador fino quando o corte nao podia ser brusco

Se qualquer item acima falhar, a regra padrao e:

1. pedir reancoragem para facade publica
2. ou pedir classificacao explicita do bypass antes de aprovar
