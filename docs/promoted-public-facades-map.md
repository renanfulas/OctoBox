<!--
ARQUIVO: mapa consolidado das fachadas reais ja promovidas.

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
  substitui boxcore.operations.actions como porta publica das actions operacionais

### Integrations

- integrations/whatsapp/contracts.py
  substitui boxcore.integrations.whatsapp.contracts
- integrations/whatsapp/services.py
  substitui boxcore.integrations.whatsapp.services

### Roteamento HTTP

- config/urls.py
  substitui boxcore.urls como raiz canonica do roteamento HTTP do projeto

### Catalog

- catalog/forms.py
  substitui boxcore.catalog.forms para a casca HTTP do app real catalog
- catalog/student_queries.py
  substitui boxcore.catalog.student_queries para leituras da area de alunos
- catalog/finance_queries.py
  substitui boxcore.catalog.finance_queries para leituras do financeiro
- catalog/class_grid_queries.py
  substitui boxcore.catalog.class_grid_queries para leituras da grade
- catalog/services/student_enrollment_actions.py
  substitui boxcore.catalog.services.student_enrollment_actions
- catalog/services/student_payment_actions.py
  substitui boxcore.catalog.services.student_payment_actions
- catalog/services/student_workflows.py
  substitui boxcore.catalog.services.student_workflows
- catalog/services/intakes.py
  substitui boxcore.catalog.services.intakes
- catalog/services/payments.py
  substitui boxcore.catalog.services.payments
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