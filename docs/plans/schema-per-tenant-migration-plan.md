<!--
ARQUIVO: plano de implementacao da migracao para schema-per-tenant via django-tenants.

TIPO DE DOCUMENTO:
- plano de execucao arquitetural

AUTORIDADE:
- alta

DOCUMENTOS IRMAOS:
- [scale-transition-20-100-open-multitenancy-plan.md](scale-transition-20-100-open-multitenancy-plan.md)
- [student-access-invite-switch-corda.md](student-access-invite-switch-corda.md)
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [../rollout/first-box-system-setup-checklist.md](../rollout/first-box-system-setup-checklist.md)

QUANDO USAR:
- ao executar a transicao de "1 instancia = 1 box" para "schema-per-tenant em 1 instancia".
- ao decidir o que vai em SHARED_APPS vs TENANT_APPS.
- ao mexer no fluxo de signup/activate para criar Box automaticamente.
- ao refatorar student_identity para suportar 1 aluno em N boxes em produacao.

POR QUE ELE EXISTE:
- materializa a Fase 1 do scale-transition-plan com decisoes concretas de codigo.
- documenta a integracao com o fluxo Early Adopter (Stripe + magic link).
- formaliza o modelo Hibrido (Identity em public, Student per-tenant) ja parcialmente implementado.
- previne reescrita posterior na transicao para Fase 3 (multitenancy aberto).

O QUE ESTE ARQUIVO FAZ:
1. define classificacao SHARED_APPS vs TENANT_APPS para cada app Django existente.
2. desenha o model Box e o control plane minimo (control/).
3. especifica middleware de tenant identification por sessao (staff e aluno).
4. detalha o refactor de signup.activate_pending_signup para provisionar Box+schema.
5. detalha a migracao de student_identity para o modelo Hibrido (Identity em public).
6. lista os 6 sprints de implementacao com criterios de pronto MENSURAVEIS.
7. enumera contratos entre apps, riscos com mitigacao, e plano de rollback.

PONTOS CRITICOS:
- boxcore concentra TODAS as migracoes de dominio; classificacao e ao nivel boxcore, nao por app de fachada.
- schema creation no Postgres nao e transacional — provisioning precisa ser idempotente com BoxProvisioningEvent.
- StudentApp tem auth propria; precisa resolver tenant antes de qualquer query de dominio.
- StudentIdentity ja existe em codigo e modela 1 aluno em N boxes; migracao formaliza o que ja foi pensado.

DECISOES TRAVADAS (versao deste plano: V2):
- Tenant identification: session-based (Fase 1). Subdomain so na Fase 2.
- User pode ser Owner de multiplos boxes via Membership m:n.
- Student e per-tenant; StudentIdentity/Membership/Invitation/Transfer sao cross-tenant em public.
- Stripe: conta unica na Fase 1 (sem Connect).
- Dados em DEV: descartar e bootstrap do zero.
- Slug do box: slugify(box_name) + sufixo numerico em colisao.
- AuditEvent permanece per-tenant; PlatformAuditEvent novo em public.
- Group permanece global (papel universal); per-tenant via Membership.role.
- Healthcheck: /api/v1/health/ em public + /api/v1/health/tenant/ autenticado por tenant.
-->

# Plano de Implementacao — Migracao para `django-tenants` (Schema-per-Tenant)

> Versao: V2 (decisoes travadas; §3.5 sobre Student multi-box adicionada)

## Resumo executivo

OctoBox hoje opera em modo "1 instancia = 1 box" via `BOX_RUNTIME_SLUG` + `CACHE_KEY_PREFIX`. Com o programa Early Adopters (Stripe + magic link de onboarding) prestes a colocar ate 20 boxes pagos na MESMA instancia de producao, ha risco critico de vazamento de dados entre tenants.

A decisao arquitetural e migrar para **schema-per-tenant via `django-tenants`** com identificacao por sessao (User → Membership → Box → schema). Tres descobertas estruturais moldam o plano:

1. **`boxcore` e a ancora de TODAS as migracoes de dominio** — `students/`, `finance/`, `operations/`, `auditing/` sao facades de import sobre `boxcore.models`. Classificacao SHARED vs TENANT acontece ao nivel `boxcore` (vai inteiro para TENANT_APPS).
2. **O modelo "1 aluno em N boxes" ja esta parcialmente implementado** — `StudentIdentity`, `StudentBoxMembership`, `StudentAppInvitation`, `StudentTransfer` ja existem em `student_identity/models.py` com semantica de identidade-cross-box. A migracao formaliza isso movendo esses 7 models para SHARED_APPS e trocando `box_root_slug: CharField` por `box_id: FK control.Box`.
3. **Schema creation nao e transacional** no Postgres — provisioning precisa ser idempotente com checkpoint via `BoxProvisioningEvent` para suportar retry/recovery.

O plano cobre 6 sprints (~18-24 dias-dev), comecando pelo control plane (model `Box`), seguido pela integracao com `signup/services.py:activate_pending_signup`, refator de `student_identity` para SHARED_APPS, roteamento de webhooks Stripe via `metadata`, hardening de boundary tests e rollout invisivel com `box_pilot` antes do primeiro tenant pago.

**Esforco total: 18-24 dias-dev com 1 dev senior** (4-5 semanas calendar). Sem regressao no escopo de Early Adopter; o feature do `/obrigado/` continua intacto.

## 0. Mapa de documentos e arquivos de referencia

> Este indice existe para que QUALQUER leitor pule direto pro arquivo que importa, sem ter que adivinhar onde a logica vive. Caminhos sao relativos a raiz do repo (`OctoBox/`). Linhas citadas refletem o snapshot deste worktree; se voce le isso em outra branch, ajuste antes de patchear.

### 0.1 Documentos irmaos (arquitetura, plano, rollout)

| Topico | Documento canonico | Por que ler |
|---|---|---|
| Visao macro de scale (Fase 1 → Fase 3) | [docs/plans/scale-transition-20-100-open-multitenancy-plan.md](scale-transition-20-100-open-multitenancy-plan.md) | Este plano e a Fase 1 materializada do scale-transition. Conflitos resolvem-se a favor do scale-transition. |
| Closed beta operacional (20 boxes) | [docs/plans/phase1-closed-beta-20-boxes-corda.md](phase1-closed-beta-20-boxes-corda.md) | Define o gate "20 boxes em prod" que destrava o trabalho deste plano. |
| Onboarding/identidade do aluno | [docs/plans/student-access-invite-switch-corda.md](student-access-invite-switch-corda.md) | Modelo m:n Identity↔Box ja desenhado aqui; §3.5 deste plano formaliza. |
| Modelo arquitetural geral | [docs/architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md) | Vocabulario oficial OctoBox (Center Layer, Signal Mesh, etc.). |
| Center Layer (facades) | [docs/architecture/center-layer.md](../architecture/center-layer.md) | Onde formalizar fachadas como `student_identity/facade/`; usado pelo `resolve_tenant_for_student_oauth_callback`. |
| Signal Mesh (eventos cross-app) | [docs/architecture/signal-mesh.md](../architecture/signal-mesh.md) | `PlatformAuditEvent` em public usa o vocabulario aqui. |
| Red Beacon (snapshots/observabilidade) | [docs/architecture/red-beacon.md](../architecture/red-beacon.md) | Cache de tabelas conhecidas por schema (`beacon_snapshot.py`) precisa ser tenant-aware. |
| Estrategia Django (apps shared/tenant) | [docs/architecture/django-core-strategy.md](../architecture/django-core-strategy.md) | Base da decisao SHARED_APPS vs TENANT_APPS de §1.2. |
| Roadmap macro | [docs/architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md) | Justifica por que schema-per-tenant agora, microservices nunca cedo. |
| Domain ownership matrix | [docs/architecture/domain-model-ownership-matrix.md](../architecture/domain-model-ownership-matrix.md) | Lista de quem POSSUI cada model; informa §1.2. |
| App split plan | [docs/architecture/app-split-plan.md](../architecture/app-split-plan.md) | Historico da divisao boxcore → apps de fachada (students, finance, ...). |
| OctoPass (auth do aluno) | [docs/architecture/octopass-architecture.md](../architecture/octopass-architecture.md) | Auth do aluno desacoplada do Django auth; informa §3.5. |
| Setup de primeira box | [docs/rollout/first-box-system-setup-checklist.md](../rollout/first-box-system-setup-checklist.md) | Lista mecanica do que precisa existir pro provision rodar. |
| Sprint 5 rollout | [docs/rollout/sprint5-tenant-rollout-checklist.md](../rollout/sprint5-tenant-rollout-checklist.md) | Checklist operacional do Sprint 5 deste plano. |
| Backup/restore | [docs/rollout/backup-guide.md](../rollout/backup-guide.md), [docs/rollout/restore-and-rollback-drill.md](../rollout/restore-and-rollback-drill.md) | Pre-requisito do rollout invisivel; ver §14.7 (SQL) sobre pg_dump por schema. |
| ADR do invite-token do aluno | [docs/adr/ADR-001-invite-token-cookie.md](../adr/ADR-001-invite-token-cookie.md) | Decisao travada do cookie + token; informa §3.5.4. |
| ADR do StudentAuthMiddleware | [docs/adr/ADR-003-student-auth-middleware.md](../adr/ADR-003-student-auth-middleware.md) | Contrato do middleware; §3.5.4 estende ele. |
| Autoridade documental | [docs/map/documentation-authority-map.md](../map/documentation-authority-map.md) | Em caso de conflito entre docs, este define quem ganha. |

### 0.2 Arquivos de codigo afetados (mapa por capability)

Cada linha mapeia uma capability deste plano para o arquivo concreto onde a mudanca acontece. Use isto para pular direto pro patch sem reler o plano inteiro.

#### Control plane (NOVO)
- `control/__init__.py`, `control/apps.py` — app skel.
- `control/models.py` — `Box`, `Domain`, `Membership`, `BoxProvisioningEvent`, `PlatformAuditEvent` (ver §2).
- `control/middleware.py` — `TenantBySessionMiddleware` (ja existe em esboco; ver §3.1 + §3.4).
- `control/services.py` — `provision_box`, `derive_slug`, `archive_box`, `reprovision_box` (ver §4).
- `control/cache.py` — `tcache_get/set`, `tenant_cache_key` (ver §7.1).
- `control/logging.py` — `TenantContextFilter` (ver §7.3).

#### Identidade do aluno (cross-tenant em public)
- `student_identity/models.py` — 7 models a migrar pra SHARED (ver §3.5.1).
- `student_identity/views.py` — `StudentOAuthCallbackView`, `StudentInviteLandingView`; consumidores do facade (ver §3.5.4 e §12).
- `student_identity/facade/__init__.py` — porta publica do Center Layer.
- `student_identity/facade/tenant_resolver.py` — `resolve_tenant_for_student_oauth_callback`, `resolve_tenant_for_student_invite_landing`, 5 strategies (NOVO, ja implementado).
- `student_identity/oauth_actions.py`, `student_identity/oauth_journeys.py` — antigas casas da resolucao de tenant ad-hoc; mantidas mas chamando o facade.
- `student_identity/infrastructure/session.py` — cookie do aluno (read_student_session_value).
- `student_identity/infrastructure/repositories.py` — `DjangoStudentIdentityRepository.find_invitation_by_token`, `find_box_invite_link_by_token`.
- `student_identity/application/use_cases.py` — use cases que rodam DEPOIS do tenant resolvido.
- `student_identity/migrations/0001_initial.py` — base; novas migrations: `0XXX_promote_to_shared.py` e `0XXX_box_root_slug_to_fk.py` (ver §3.5.1 e §3.5.3).

#### App do aluno (per-tenant)
- `student_app/middleware/student_auth.py` — `StudentAuthMiddleware`, `_resolve_student_tenant`, `_has_active_membership` (ver §3.5.4).
- `student_app/workflows/attendance_workflows.py` — consumidor de `Student.app_identity` (shim ja adicionado em `students/model_definitions.py`).
- `student_app/views/membership_views.py` — `switch_box` (ver §3.5.5).
- `student_app/urls.py` — landing/auth/grade/wod/sw.js.

#### Signup + onboarding pago
- `signup/models.py` — `PendingSignup`, `PendingSignupStatus`.
- `signup/services.py` — `activate_pending_signup` (ver §4.1; refator critico).
- `signup/views.py` — `activate` view (post-pagamento → magic link).
- `signup/notifications.py`, `signup/email_sender.py` — envio do magic link.

#### Stripe + integracoes
- `integrations/stripe/router.py` — `_HANDLERS`, `_handle_early_adopter_signup`, novos handlers de `invoice.*` (ver §6.3).
- `integrations/middleware.py` — `WebhookIdempotencyMiddleware` (ver §13.1; ordem critica).
- `integrations/models.py` (cross-tenant) — `PaymentWebhookEvent`.

#### Settings / config / urls
- `config/settings/base.py` — SHARED_APPS, TENANT_APPS, MIDDLEWARE, TENANT_MODEL, DATABASES, CONN_MAX_AGE, SESSION_*  (ver §5.1 + §14.6).
- `config/urls.py` — ROOT_URLCONF (tenants).
- `config/urls_public.py` (NOVO) — PUBLIC_SCHEMA_URLCONF (ver §3.2).

#### Code legado "1 instancia = 1 box"
- `shared_support/box_runtime.py` — `get_box_runtime_slug` (ver §1.4; refator Sprint 4).
- `shared_support/background_jobs.py` — `submit_background_job` (ver §8.3).
- `jobs/dispatcher.py` — `dispatch_async_job` (ver §8.3).
- `monitoring/beacon_snapshot.py` — Red Beacon snapshot; cache de `known_tables` ja foi tornado tenant-aware via `cache.set/get` (commit 7a263d1).

#### Boundary tests
- `tests/test_tenant_boundary.py` (NOVO no Sprint 4) — B1..B11 (ver §9.2 e §3.5.6).
- `tests/conftest.py` — fixtures multi-tenant (`box_a`, `box_b`, `identity_joao`, `_class_tenant_schema_context`).
- `tests/broken-tests.txt` — quarentena com bypass via `OCTOBOX_RUN_BROKEN_TESTS=1`.
- `conftest.py` — fixture autouse de schema-context em escopo de classe (cobre `setUpTestData`).

### 0.3 Convencoes do plano

- `arquivo.py:NNN` cita o numero de linha no snapshot do worktree. Em outra branch confirme via `Grep` antes de aplicar patch.
- Caminhos sem prefixo (`control/...`, `student_identity/...`) sao relativos a raiz do repo.
- Caminhos com `../` sao relativos ao diretorio deste plano (`docs/plans/`).
- "(NOVO)" = arquivo precisa ser criado pelo sprint correspondente.
- "(PARCIAL)" = arquivo existe mas precisa de refactor para fechar contrato.

## Diagrama (ASCII) — Topologia alvo

```
                      ┌────────────────────────────────────────────────┐
                      │       CONTROL PLANE (schema=public)            │
                      │ ────────────────────────────────────────────  │
                      │  auth.User              (cross-tenant)        │
                      │  signup.PendingSignup                          │
                      │  control.Box            (django_tenants Tenant)│
                      │  control.Domain         (django_tenants Domain)│
                      │  control.Membership     (User ↔ Box, m:n)     │
                      │  control.BoxProvisioningEvent (recovery)       │
                      │  control.PlatformAuditEvent (eventos cross)    │
                      │  ─── Aluno cross-box ─────────────────────────  │
                      │  student_identity.StudentIdentity              │
                      │  student_identity.StudentBoxMembership         │
                      │  student_identity.StudentAppInvitation         │
                      │  student_identity.StudentBoxInviteLink         │
                      │  student_identity.StudentTransfer              │
                      │  student_identity.StudentInvitationDelivery*   │
                      │  student_identity.StudentPushSubscription      │
                      │  ─── Stripe ────────────────────────────────────│
                      │  integrations.PaymentWebhookEvent              │
                      │  django.contrib.sessions                       │
                      └────────────────┬───────────────────────────────┘
                                       │
              TenantBySessionMiddleware │ (staff:  Membership.is_primary_box)
              StudentAuthMiddleware     │ (aluno:  StudentBoxMembership.active)
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│ schema=box_001       │    │ schema=box_002       │... │ schema=box_020       │
│ ──────────────────── │    │ ──────────────────── │    │ ──────────────────── │
│ boxcore.*            │    │ boxcore.*            │    │ boxcore.*            │
│   Student            │    │   Student            │    │   Student            │
│   Payment            │    │   Payment            │    │   Payment            │
│   MembershipPlan     │    │   MembershipPlan     │    │   MembershipPlan     │
│   Enrollment         │    │   Enrollment         │    │   Enrollment         │
│   AuditEvent         │    │   AuditEvent         │    │   AuditEvent         │
│   WhatsappContact    │    │                      │    │                      │
│ student_app.*        │    │ student_app.*        │    │ student_app.*        │
│ catalog.*            │    │                      │    │                      │
│ communications.*     │    │                      │    │                      │
│ operations.*         │    │                      │    │                      │
│ jobs.*               │    │                      │    │                      │
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘

Joao Silva (1 ser humano, 1 conta OAuth) frequenta box_001 + box_002:
- StudentIdentity #7 em public (provider_subject unico)
- StudentBoxMembership: (#7, box_001, active) e (#7, box_002, active)
- box_001.Student #42 (identity_id=7) — matricula, pagamento, plano do Vila Mar
- box_002.Student #17 (identity_id=7) — matricula, pagamento, plano do Vila Madalena
- /aluno/box/switch/ alterna o cookie active_box_id; middleware seta o schema correto
```

## 1. Analise de impacto

### 1.1 Restricao estrutural descoberta

O Django app `boxcore` (definido em `boxcore/apps.py`, label `boxcore`) e a ancora historica de **todas** as migracoes de dominio. Os "apps de dominio" `students/`, `finance/`, `operations/`, `auditing/` sao **facades de import** sobre `boxcore.models` (ver `students/__init__.py`, `finance/__init__.py`, `operations/__init__.py`). As migracoes reais vivem em `boxcore/migrations/0001_initial.py` ate `0020+`. Contexto historico em [docs/architecture/app-split-plan.md](../architecture/app-split-plan.md) e [docs/architecture/boxcore-state-residue-inventory.md](../architecture/boxcore-state-residue-inventory.md).

**Consequencia**: a classificacao SHARED vs TENANT e feita ao nivel `boxcore` (o app inteiro), nao por subdominio. O app `boxcore` precisa virar TENANT_APP — o que e correto, pois `Student`, `Payment`, `Enrollment`, `AuditEvent`, `WhatsappContact`, `MembershipPlan` etc. todos pertencem a um tenant.

### 1.2 Classificacao definitiva dos apps

#### SHARED_APPS (schema `public`)

| App | Justificativa |
|---|---|
| `django_tenants` | Obrigatorio primeiro em SHARED_APPS por design da lib. |
| `django.contrib.contenttypes` | Obrigatorio em public por `django-tenants`. |
| `django.contrib.auth` | User cross-tenant; permite 1 owner gerenciar N boxes via Membership m:n. |
| `django.contrib.sessions` | `SESSION_ENGINE='cache'` em `base.py:186`; manter em public, prefix estavel. |
| `django.contrib.admin` | Admin de plataforma (Renan); admin de tenant atende rota `/admin-tenant/` separada. |
| `django.contrib.staticfiles` / `messages` | Stateless. |
| `signup` | `PendingSignup` cross-tenant por design: existe ANTES do tenant. |
| `integrations` | `PaymentWebhookEvent` cross-tenant; webhook chega antes de saber qual Box. |
| **`control`** (NOVO) | `Box`, `Domain`, `Membership`, `BoxProvisioningEvent`, `PlatformAuditEvent`. |
| **`student_identity`** (PARCIAL — ver §3.5) | Models de identidade do aluno migram para public; o app `INSTALLED_APPS` permanece. |

#### TENANT_APPS (schema `box_xxx`)

| App | Justificativa |
|---|---|
| `boxcore` | Onde TODAS as migracoes de dominio vivem. |
| `students`, `finance`, `operations`, `dashboard`, `catalog`, `auditing`, `communications` | Facades sobre `boxcore` ou dominios per-tenant. |
| `student_app` | Views/templates do aluno consomem dados per-tenant (matricula, WOD, RM, presencas). |
| `access` | Bootstrap de Group (mesmo Group em todos os schemas — intencional; ver §11 R3). |
| `quick_sales`, `guide`, `knowledge` | Operacao por box. |
| `jobs` | Historico de jobs e per-tenant. |
| `api` | Roteia para dominios per-tenant. |

#### `auditing` — split em duas direcoes

- `boxcore.AuditEvent` (per-tenant, atual): eventos de operacao (criou aluno, alterou plano, registrou presenca). Permanece em TENANT.
- `control.PlatformAuditEvent` (NOVO em public): eventos de plataforma (provisioning de Box, suspend, archive, criacao de Membership, escalada de role). Cross-tenant por natureza.

### 1.3 Cross-references conhecidas (auditar no Sprint 0)

| Caso | Impacto | Acao |
|---|---|---|
| `PendingSignup.activated_user → auth.User` | Ambos em public — OK. | Nada. |
| Models per-tenant referenciando `auth.User` | Postgres permite FK cross-schema; ORM da `django-tenants` aceita. | Sprint 0: `Grep -r "from django.contrib.auth.models import User" boxcore/` para enumerar. |
| `Group`/`Permission` em public | Codigo que filtra Permission per-tenant quebra. | Decisao §1.2: roles via `Membership.role`, nao via Group. |
| Cache prefix por box (`shared_support/box_runtime.py`) | Hoje vem de env-var; estatico por processo. | Sprint 3: wrapper `tcache_*` derivado de `connection.schema_name`. |
| Sessions em cache (`base.py:186`) | Prefix hoje = env-var BOX_RUNTIME_SLUG. | Sprint 3: prefix global `octobox:sessions:`; `request.session['active_box_id']` controla switch. |
| Webhook Stripe (`integrations/stripe/router.py:99`) | Chega sem tenant. | Sprint 2: `metadata.pending_signup_id` resolve Box em public via `pending.box`. |
| `STUDENT_APP_URL_PREFIX='/aluno/'` | Aluno tem auth propria. | Sprint 4: `StudentAuthMiddleware` resolve tenant ANTES de qualquer query de dominio (ver §3.5). |
| `O2O StudentIdentity.student → boxcore.Student` | FK cross-schema fragil. | Sprint 2: invertida — `Student.identity_id → public.StudentIdentity.id`. |

### 1.4 Codigo legado "1 instancia = 1 box"

| Local | Problema | Acao | Sprint |
|---|---|---|---|
| `shared_support/box_runtime.py:27-33` | `get_box_runtime_slug()` le env-var. | Refatorar: aceitar slug do tenant atual via `connection.tenant.schema_name`; env-var so vale em modo control. | 4 |
| `config/settings/base.py:149` | `build_box_cache_key_prefix()` chamado uma vez por processo. | Migrar para funcao runtime (cache-key prefix dinamico por request). | 3 |
| `base.py:186-187` | `SESSION_CACHE_ALIAS='default'`. | Manter session em public, prefix global estavel. | 3 |
| `api/v1/health/` | Healthcheck precisa NAO entrar em tenant. | Whitelist em `PUBLIC_SCHEMA_URLCONF`. | 1 |
| `student_app/middleware/student_auth.py:43-74` (`_resolve_student_tenant`) | Aluno autentica via cookie proprio; resolucao pre-auth (OAuth callback sem cookie) estava ad-hoc. | **Feito (parcial):** Center Layer facade `student_identity/facade/tenant_resolver.py` consolida 5 strategies. Restante do refactor (membership gating) — Sprint 4. | 4 |
| `student_identity/models.py:22` (`_default_box_root_slug`) | Le `BOX_RUNTIME_SLUG` para preencher campo. | Trocar por `box_id` FK; remover default global. | 2 |
| `student_identity/oauth_actions.py` (`_activate_identity_tenant`) e `student_identity/oauth_journeys.py` (`_activate_box_tenant`) | Cada lugar reimplementava parcialmente a resolucao de tenant pre-auth. | Substituir por chamada ao facade `resolve_tenant_for_student_oauth_callback`. | 2 (em curso) |
| `monitoring/beacon_snapshot.py` (Red Beacon) | `@lru_cache` em `_get_known_tables` poluia entre tenants (cache de tabelas do schema A retornado pra B). | **Feito** (commit 7a263d1): trocar `@lru_cache` por `django.core.cache` com chave `red_beacon:known_tables:v1:<using>:<schema>` e TTL 60s. | 0.5 |
| `students/model_definitions.py::Student.app_identity` | Reverse-name do antigo O2O `StudentIdentity.student` quebrou apos quebra de cross-schema FK. | **Feito** (commit b380f4e): `@property app_identity` shim consulta `StudentIdentity.objects.filter(student_id=self.id, status=ACTIVE)`. | 0.5 |
| `control/middleware.py::PUBLIC_SCHEMA_PATHS` | Webhooks de integracoes e PWAs publicas redirecionavam anonimo para `/login/` antes da view validar. | **Feito** (commit 28056ac): adicionar `/api/v1/integrations/`, `/renan/`. | 0.5 |
| `student_app/middleware/student_auth.py::AuditEvent.objects.create` em redirect anonimo | `AuditEvent` e TENANT_APP; em path publico (`/aluno/*`) schema=public, escrita quebra com 500. | **Feito** (commit 28056ac): wrap em `try/except` — audit anonimo e nice-to-have, nao bloqueia redirect. | 0.5 |

## 2. Model `Box` (control plane)

Novo Django app `control/` em SHARED_APPS contendo:

```python
# control/models.py
from django_tenants.models import TenantMixin, DomainMixin

class Box(TenantMixin):
    slug = models.SlugField(max_length=63, unique=True, db_index=True)
    display_name = models.CharField(max_length=120)

    class Status(models.TextChoices):
        PROVISIONING = 'provisioning'
        ACTIVE = 'active'
        SUSPENDED = 'suspended'   # billing falhou
        ARCHIVED = 'archived'     # offboarding
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PROVISIONING, db_index=True)

    owner_user = models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='owned_boxes')

    stripe_customer_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, db_index=True)
    plan = models.CharField(max_length=16, blank=True)  # 'monthly' | 'annual'

    pending_signup = models.OneToOneField(
        'signup.PendingSignup', on_delete=models.PROTECT,
        null=True, blank=True, related_name='box',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    provisioned_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    cell = models.CharField(max_length=32, default='cell-1', db_index=True)

    auto_create_schema = False  # provisioning explicito via control.services.provision_box
    auto_drop_schema = False    # offboarding via comando manual

class Domain(DomainMixin):
    pass  # padrao django-tenants; usado em Fase 2 quando subdominio entrar

class Membership(models.Model):
    """User <-> Box (m:n). Permite 1 user dono/membro de N boxes."""
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='memberships')
    box = models.ForeignKey(Box, on_delete=models.CASCADE, related_name='memberships')

    class Role(models.TextChoices):
        OWNER = 'owner'
        MANAGER = 'manager'
        COACH = 'coach'
        RECEPTION = 'reception'
    role = models.CharField(max_length=16, choices=Role.choices)
    is_primary_box = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'box')]
        indexes = [models.Index(fields=['user', 'is_primary_box'])]

class BoxProvisioningEvent(models.Model):
    """Checkpoint estruturado para retry/recovery do provisioning."""
    box = models.ForeignKey(Box, on_delete=models.CASCADE, related_name='provisioning_events')
    step = models.CharField(max_length=64)   # 'create_schema' | 'migrate' | 'bootstrap_roles' | 'seed_plans'
    status = models.CharField(max_length=16) # 'started' | 'ok' | 'failed'
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['box', 'step', 'status'])]

class PlatformAuditEvent(models.Model):
    """Eventos cross-tenant da plataforma. Operacoes per-tenant continuam em boxcore.AuditEvent."""
    actor_user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    target_box = models.ForeignKey(Box, on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=64)  # 'box.provisioned' | 'box.suspended' | 'membership.granted'
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
```

**Slug do box (decisao §6 travada)**: `control.services.derive_slug(box_name) -> slug`:
1. `slugify(box_name)` (ASCII-fold, lowercase, hyphens).
2. Se ja existe, sufixar `-2`, `-3`, etc.
3. Validar regex `^[a-z][a-z0-9-]{1,55}$` (Postgres aceita ate 63 chars com prefix `box_`).

## 3. Tenant identification middleware

### 3.1 Estrategia (decisao §1 travada): session-based

Subdomain identification fica para Fase 2. Na Fase 1, o tenant resolve via:
- **Staff** (User logado): `Membership.is_primary_box=True` ou `request.session['active_box_id']`.
- **Aluno** (StudentSession): `request.session['active_box_id']` (cookie do aluno) ou `StudentIdentity.primary_box_id`.

```python
# control/middleware.py
class TenantBySessionMiddleware:
    """
    Contrato:
    Input  : request com session iniciada (SessionMiddleware ja rodou).
    Output : connection.tenant setado para Box correspondente, OU PUBLIC se path whitelisted.
    Excecoes:
      - Path em PUBLIC_SCHEMA_PATHS  → fica em public (login, signup, webhook, healthcheck, admin de plataforma).
      - User autenticado sem Membership → 403 (caso anomalo: User existe mas nao tem Box).
      - User com active_box_id invalido → fallback para is_primary_box=True; se nao houver, 403.
      - Anonymous + path nao publico → redirect para login.
    Idempotencia: chamar duas vezes seguidas no mesmo request e equivalente; o ultimo valor vence.
    """
```

### 3.2 PUBLIC_SCHEMA_URLCONF

```python
# config/urls_public.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('signup/', include('signup.urls')),
    path('onboarding/<token>/', signup_views.activate, name='signup-activate'),
    path('financeiro/stripe/webhook/', stripe_webhook_view),
    path('api/v1/health/', health_view),
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
]
```

`PUBLIC_SCHEMA_URLCONF = 'config.urls_public'`; `ROOT_URLCONF = 'config.urls'` continua para tenants.

### 3.3 Webhooks Stripe (sem User no contexto)

`integrations/stripe/router.py:99` (`_handle_early_adopter_signup`) ja esta bem estruturado. Para webhooks recorrentes, adicionar handlers que consultam `Box.objects.get(stripe_subscription_id=...)` em public e usam `with schema_context(box.schema_name): ...` quando precisarem escrever no tenant.

### 3.4 Ordem do MIDDLEWARE

```python
# config/settings/base.py
MIDDLEWARE = [
    'integrations.stripe.middleware.WebhookIdempotencyMiddleware',  # le header antes do tenant
    'monitoring.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',         # antes do tenant para ler session
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',      # antes do tenant para resolver request.user
    'control.middleware.TenantBySessionMiddleware',                 # ← chave
    'shared_support.middleware.RequestTimingMiddleware',
    'shared_support.middleware.HoneypotMiddleware',
    'shared_support.middleware.SessionFingerprintMiddleware',
    'shared_support.middleware.RequestSecurityMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'student_app.middleware.student_auth.StudentAuthMiddleware',    # refatorado em §3.5
]
```

### 3.5 Aluno multi-box (Identity em public, Student per-tenant)

> Esta secao formaliza o modelo Hibrido (Opcao C). O caso "1 aluno em N boxes" ja esta parcialmente implementado em `student_identity/models.py`: a migracao **completa** o que ja foi pensado.

#### 3.5.1 Mover 7 models para SHARED_APPS

Os seguintes models, hoje em `student_identity/models.py`, migram para `public`:

| Model | Linhas atuais | Funcao |
|---|---|---|
| `StudentIdentity` | 79-115 | Pessoa-fisica (provider_subject unico, email, photo_url, primary_box_id). |
| `StudentBoxMembership` | 118-171 | Vinculo m:n Identity ↔ Box (status: pending_approval/active/suspended_financial/revoked). |
| `StudentAppInvitation` | (ver arquivo) | Convite com box_id, invited_email, token UUID. |
| `StudentBoxInviteLink` | (ver arquivo) | Magic link para auto-cadastro em open_box. |
| `StudentTransfer` | 255-282 | Audit-trail de transferencia entre boxes. |
| `StudentInvitationDelivery*` | (ver arquivo) | Status do envio (email/SMS) do invite. |
| `StudentPushSubscription` | (ver arquivo) | Web Push do aluno. Identidade global, segue identity_id. |

**Acao**: app `student_identity` permanece em INSTALLED_APPS. Os models acima passam a ter `class Meta: app_label = 'student_identity'` mas a migracao roda em SHARED via `migrate_schemas --shared`. Implementacao: criar nova migration `student_identity/migrations/0XXX_promote_to_shared.py` que:
1. Cria as tabelas em `public` (ja estavam no schema antigo).
2. Move dados existentes (`INSERT INTO public.student_identity_* SELECT * FROM <schema_legado>.student_identity_*`).
3. Drop tabelas no schema legado.

Dados em DEV: descartados (decisao §5 travada). Em prod: comando `migrate_existing_data_to_pilot` cuida (Sprint 5).

#### 3.5.2 Quebrar O2O cross-schema

Hoje (`student_identity/models.py:79+`):
```python
class StudentIdentity(models.Model):
    student = models.OneToOneField('boxcore.Student', on_delete=models.PROTECT, ...)
```

Cross-schema FK `public → tenant` e fragil: o ORM nao sabe em qual schema o Student vive. Acao: **inverter direcao**.

```python
# Depois (V2):
# StudentIdentity em public — sem FK para Student.
# boxcore.Student ganha FK para public.StudentIdentity:
class Student(models.Model):
    ...
    identity = models.ForeignKey(
        'student_identity.StudentIdentity',
        on_delete=models.PROTECT,
        null=True, blank=True,           # alunos legacy sem OAuth ainda existem
        related_name='student_records',  # plural — 1 identity tem N student records (1 por box)
    )
```

Migracao:
1. Adicionar campo `Student.identity_id` (nullable).
2. Backfill `UPDATE boxcore_student SET identity_id = (SELECT id FROM public.student_identity WHERE student_id = boxcore_student.id)` rodando em CADA schema de tenant.
3. Drop `StudentIdentity.student_id`.
4. Validar: nenhuma query existente referencia `identity.student` no codigo (Grep `\.identity\.student` em `student_app/`, `student_identity/`).

#### 3.5.3 Trocar `box_root_slug: CharField` por `box_id: FK control.Box`

4 models atualmente usam `box_root_slug`:

| Model | Campo atual | Campo novo |
|---|---|---|
| `StudentIdentity` | `primary_box_root_slug` | `primary_box` (FK) |
| `StudentBoxMembership` | `box_root_slug` | `box` (FK) |
| `StudentAppInvitation` | `box_root_slug` | `box` (FK) |
| `StudentTransfer` | `from_box_root_slug`, `to_box_root_slug` | `from_box`, `to_box` (FK) |

Migracao (rodar em SHARED apos §3.5.1 estar completo):
```python
# 0XXX_box_root_slug_to_fk.py
def forward(apps, schema_editor):
    Box = apps.get_model('control', 'Box')
    StudentBoxMembership = apps.get_model('student_identity', 'StudentBoxMembership')
    for m in StudentBoxMembership.objects.all():
        try:
            m.box_id = Box.objects.get(slug=m.box_root_slug).id
            m.save(update_fields=['box_id'])
        except Box.DoesNotExist:
            # alunos orfaos de boxes nao migrados — log + skip
            logger.warning('Membership %s aponta para slug inexistente: %s', m.pk, m.box_root_slug)
```

Apos backfill OK em todos os models: drop dos campos `box_root_slug`.

#### 3.5.4 Refator `StudentAuthMiddleware` + Center Layer facade

Hoje (`student_app/middleware/student_auth.py:105` — `StudentAuthMiddleware.__call__`): valida cookie do aluno → resolve `StudentSession` → chama `_resolve_student_tenant(request, session_payload)` (linha 43) → checa `_has_active_membership` (linha 77) → segue.

A resolucao pre-auth (OAuth callback sem cookie ainda, landing de convite) **NAO** vive mais espalhada em `student_identity/oauth_actions.py` / `oauth_journeys.py` / `student_identity/views.py`. Foi consolidada no **Center Layer facade**:

- `student_identity/facade/__init__.py` — porta publica.
- `student_identity/facade/tenant_resolver.py` — `resolve_tenant_for_student_oauth_callback`, `resolve_tenant_for_student_invite_landing`, classe `StudentAuthTenantStrategy` (Enum), dataclass `TenantResolution`.

5 strategies, em ordem de prioridade:
1. `INVITATION` — `invite_token` casa com `StudentAppInvitation` (`DjangoStudentIdentityRepository.find_invitation_by_token`).
2. `INVITE_LINK` — `invite_token` casa com `StudentBoxInviteLink` (`...find_box_invite_link_by_token`).
3. `EXISTING_IDENTITY_BY_SUBJECT` — `provider_subject` ja existe em `StudentIdentity` (cobre o gap do Bucket B: OAuth recorrente sem token).
4. `EXISTING_IDENTITY_BY_EMAIL` — match unico de email em `StudentIdentity.email__iexact` (so se houver exatamente 1).
5. `SINGLE_ACTIVE_BOX` — fallback de pilot: 1 Box ATIVO no sistema → usa ele. **Limite explicito**: em prod multi-tenant retorna `NONE`.

Apos retorno do facade, `connection.set_tenant(box)` ja foi chamado — o caller NAO precisa reativar. View consumidora (`student_identity/views.py::StudentOAuthCallbackView._handle_callback`) chama o facade ANTES de `authenticate_student_oauth_identity`, garantindo que o use case roda no schema correto.

Anti-pattern proibido (documentado em `student_identity/facade/tenant_resolver.py:22-25`): adicionar mais uma chamada `connection.set_tenant(...)` ad-hoc em outro modulo. Strategy nova entra no facade, nao espalhada no codigo.

Esboco do middleware p/ requests do aluno ja autenticado (post-cookie):
```python
# student_app/middleware/student_auth.py — esboco
class StudentAuthMiddleware:
    def __call__(self, request):
        # 1. Resolver StudentIdentity em public (cookie do aluno)
        student_session = self._resolve_session(request)
        if not student_session:
            return self.get_response(request)  # nao e request de aluno; passa adiante
        
        identity = student_session.identity  # public.StudentIdentity
        request.student_identity = identity
        
        # 2. Resolver active_box_id (do session do aluno OU primary_box_id da Identity)
        active_box_id = request.session.get('student_active_box_id') or identity.primary_box_id
        if not active_box_id:
            return redirect('student_no_active_box')
        
        # 3. Validar StudentBoxMembership ATIVA para essa identity+box
        try:
            membership = StudentBoxMembership.objects.get(
                identity=identity, box_id=active_box_id, status='active',
            )
        except StudentBoxMembership.DoesNotExist:
            return redirect('student_no_active_box')
        
        # 4. Ativar tenant ANTES de qualquer query de dominio
        from django.db import connection
        from control.models import Box
        connection.set_tenant(Box.objects.get(id=active_box_id))
        request.box = membership.box
        request.student_box_membership = membership
        
        return self.get_response(request)
```

Contrato:
- **Input**: `request` com SessionMiddleware ja executado.
- **Output**: `request.student_identity`, `request.box`, `request.student_box_membership` setados; `connection.tenant` ativo no schema do box.
- **Excecoes**:
  - Sem cookie de aluno → passa adiante (nao e request de aluno).
  - Cookie valido + sem Membership ativo → redirect para `/aluno/sem-box-ativo/`.
  - Cookie valido + Membership pending → redirect para `/aluno/aguardando-aprovacao/`.
- **Idempotencia**: chamar 2x no mesmo request e equivalente.

#### 3.5.5 Refator `/aluno/box/switch/`

Hoje: troca `active_box_root_slug` no cookie do aluno.

Depois (V2):
```python
# student_app/views/membership_views.py — esboco
def switch_box(request, target_box_id: int):
    identity = request.student_identity
    
    # 1. Validar membership ativo no target
    membership = get_object_or_404(
        StudentBoxMembership,
        identity=identity, box_id=target_box_id, status='active',
    )
    
    # 2. Trocar session — middleware vai re-resolver tenant na proxima request
    request.session['student_active_box_id'] = target_box_id
    
    # 3. Audit em public (log de switch)
    PlatformAuditEvent.objects.create(
        actor_user=None, target_box_id=target_box_id,
        kind='student.box_switched',
        payload={'identity_id': identity.id, 'from_box_id': request.box.id},
    )
    
    return redirect('/aluno/')  # middleware ativa novo tenant na proxima request
```

#### 3.5.6 Boundary tests especificos para Student multi-box

Adicionar em `tests/test_tenant_boundary.py` (Sprint 4). Suites adjacentes ja existentes:
- `tests/test_monitoring_beacon_snapshot.py` — isolamento do Red Beacon (commit 7a263d1).
- `student_identity/tests.py` — testes do facade.
- `student_app/tests/test_views_*.py` — coverage do middleware + redirects.
- `tests/broken-tests.txt` — quarentena de testes em Bucket B/C ainda nao migrados; bypass via `OCTOBOX_RUN_BROKEN_TESTS=1`.

Esquema de fixtures em `tests/conftest.py` + `conftest.py` (raiz) — `_class_tenant_schema_context` (escopo de classe, cobre `setUpTestData`) + `_tenant_schema_context` (escopo de funcao, backup contra rollback de transacao).


| Teste | O que valida |
|---|---|
| `test_student_records_with_same_identity_remain_isolated` | Joao em box_a (Student #42) e box_b (Student #17) NAO compartilham WOD/RM/Payment via `Student.objects.filter(identity_id=7)` em UM tenant. |
| `test_student_app_pages_require_active_membership` | Acesso a `/aluno/grade/` sem `StudentBoxMembership.status=active` retorna 302 para `student_no_active_box`. |
| `test_switch_box_redirects_and_does_not_carry_session` | Apos `/aluno/box/switch/<other_box_id>/`, o `request.box` no proximo request e o novo, e `connection.schema_name` muda. |
| `test_oauth_callback_resolves_identity_in_public` | OAuth callback (rota `/aluno/oauth/callback/`) executa em `public` (sem tenant), resolve Identity, soh ENTRA em tenant ao redirecionar para `/aluno/`. |
| `test_invitation_token_creates_membership_in_public` | `StudentAppInvitation` criada em public (Recepcao convida); aluno aceita → `StudentBoxMembership.status='active'` em public, sem entrar no schema do tenant ainda. |

## 4. Onboarding/provisioning automation

### 4.1 Refator de `signup/services.py:323` (`activate_pending_signup`)

```python
# signup/services.py
@transaction.atomic  # apenas operacoes em PUBLIC. DDL de schema nao e transacional.
def activate_pending_signup(*, pending_signup, username, raw_password):
    user = create_user(...)
    
    from control.services import provision_box
    box = provision_box(
        pending_signup=pending_signup,
        owner_user=user,
        slug=derive_slug(pending_signup.box_name),
        plan=pending_signup.plan,
        stripe_customer_id=pending_signup.stripe_customer_id,
        stripe_subscription_id=pending_signup.stripe_subscription_id,
    )
    
    Membership.objects.get_or_create(
        user=user, box=box,
        defaults={'role': Membership.Role.OWNER, 'is_primary_box': True},
    )
    
    pending_signup.status = PendingSignupStatus.ACTIVATED
    pending_signup.activated_user = user
    pending_signup.save(update_fields=['status', 'activated_user', 'updated_at'])
    return user
```

Contrato:
- **Input**: `PendingSignup` com `status=PAID`, `username` valido, `raw_password` >= 8 chars.
- **Output**: `User` ativo + `Box` em estado `ACTIVE` + `Membership` criada.
- **Excecoes**:
  - `UsernameTakenError` se username ja existe (atual).
  - `BoxProvisioningError` se schema falhar.
  - `IntegrityError` em race de `pending_signup` ja ativado.
- **Idempotencia**: re-execucao com mesmo `pending_signup` e no-op se `status=ACTIVATED`.

### 4.2 `provision_box` — idempotente, recoverable

```python
# control/services.py
def provision_box(*, pending_signup, owner_user, slug, plan,
                  stripe_customer_id, stripe_subscription_id) -> Box:
    """
    Idempotente: re-execucao com mesmo pending_signup nao duplica.
    BoxProvisioningEvent registra cada step; recovery consulta o ultimo step OK
    e retoma do proximo.
    """
    box, created = Box.objects.get_or_create(
        pending_signup=pending_signup,
        defaults={
            'slug': slug, 'display_name': pending_signup.box_name,
            'owner_user': owner_user, 'plan': plan,
            'stripe_customer_id': stripe_customer_id,
            'stripe_subscription_id': stripe_subscription_id,
            'schema_name': f'box_{slug}',
        },
    )
    
    _step(box, 'create_schema',     lambda: box.create_schema(check_if_exists=True))
    _step(box, 'run_migrations',    lambda: call_command('migrate_schemas', schema_name=box.schema_name))
    _step(box, 'bootstrap_roles',   lambda: bootstrap_roles_for_tenant(box))
    _step(box, 'seed_default_plans',lambda: seed_default_plans(box))
    _step(box, 'seed_initial_settings', lambda: seed_initial_settings(box))
    
    if box.status == Box.Status.PROVISIONING:
        box.status = Box.Status.ACTIVE
        box.provisioned_at = timezone.now()
        box.save(update_fields=['status', 'provisioned_at'])
        PlatformAuditEvent.objects.create(
            actor_user=owner_user, target_box=box, kind='box.provisioned',
            payload={'pending_signup_id': pending_signup.pk},
        )
    return box

def _step(box: Box, name: str, fn):
    """Executa fn() registrando started/ok/failed em BoxProvisioningEvent."""
    last = BoxProvisioningEvent.objects.filter(box=box, step=name, status='ok').first()
    if last:
        return  # idempotente: ja rodou OK
    BoxProvisioningEvent.objects.create(box=box, step=name, status='started')
    try:
        fn()
        BoxProvisioningEvent.objects.create(box=box, step=name, status='ok')
    except Exception as e:
        BoxProvisioningEvent.objects.create(box=box, step=name, status='failed', detail=str(e))
        raise BoxProvisioningError(f'step {name} failed: {e}') from e
```

### 4.3 Tratamento de erro

| Cenario | Comportamento |
|---|---|
| Falha em `run_migrations` | `BoxProvisioningEvent` `status=failed`. Box NAO entra ACTIVE. Comando `manage.py reprovision_box --slug=xxx` retoma do step pendente. |
| Rollback total | `manage.py archive_box --slug=xxx`: marca `status=ARCHIVED`, renomeia schema (`ALTER SCHEMA box_xxx RENAME TO archived_box_xxx_<ts>`). NAO drop. |
| User criado mas Box falhou | `User` permanece (em public, atomico). Cleanup periodico via `manage.py cleanup_orphan_users --older-than=24h`. |

## 5. Migrations strategy

### 5.1 Classificacao no settings

```python
# config/settings/base.py
SHARED_APPS = [
    'django_tenants',          # MUST BE FIRST
    'control',
    'student_identity',         # PARCIAL: 7 models migram para public (ver §3.5)
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'signup',
    'integrations',
]

TENANT_APPS = [
    'access', 'api', 'auditing', 'boxcore', 'catalog', 'communications',
    'dashboard', 'finance', 'guide', 'jobs', 'knowledge', 'operations',
    'quick_sales', 'student_app', 'students',
]

INSTALLED_APPS = list(dict.fromkeys(SHARED_APPS + TENANT_APPS))
DATABASE_ROUTERS = ('django_tenants.routers.TenantSyncRouter',)
TENANT_MODEL = 'control.Box'
TENANT_DOMAIN_MODEL = 'control.Domain'
DATABASES['default']['ENGINE'] = 'django_tenants.postgresql_backend'
```

### 5.2 Migracoes existentes

`boxcore/migrations/0001_initial.py` esta em TENANT_APPS → `django-tenants` roda em CADA schema. **Nada precisa ser reescrito**. Sprint 0: auditar `RunPython` em `boxcore/migrations/` (Grep) — se algum executa SQL raw que assume search_path padrao, marcar para revisao.

### 5.3 Migracao de dados em DEV

Decisao §5 travada: descartar e bootstrap.

```bash
# DEV (Postgres local):
psql -c "DROP DATABASE octobox_dev; CREATE DATABASE octobox_dev;"
python manage.py migrate_schemas --shared
python manage.py provision_box --slug=pilot --owner-email=dev@octobox.local
# manualmente em shell:
#   with schema_context('box_pilot'): seed_demo_data()
```

### 5.4 Comando de deploy

```bash
python manage.py migrate_schemas --shared       # public primeiro
python manage.py migrate_schemas --executor=multiprocessing  # tenants em paralelo
```

## 6. Stripe webhook integration

### 6.1 Webhook chega em public (`/financeiro/stripe/webhook/`)

`PaymentWebhookEvent` em SHARED_APP. Idempotencia ja garantida por `event_id` Stripe.

### 6.2 Fluxo `checkout.session.completed` para Early Adopter

```
[t0] Webhook → PendingSignup.status=PAID, stripe_subscription_id salvo (em public).
[t1] Email de magic link enviado.
[t2] User clica no link, escolhe username/senha.
[t3] activate_pending_signup → cria User, Box, schema, seed (em public + DDL no Postgres).
```

### 6.3 Webhooks recorrentes — adicionar handlers

```python
# integrations/stripe/router.py:155
_HANDLERS = {
    'checkout.session.completed': _handle_checkout_session_completed,
    'invoice.payment_succeeded':  _handle_invoice_paid,         # NOVO
    'invoice.payment_failed':     _handle_invoice_failed,       # NOVO
    'customer.subscription.deleted':  _handle_subscription_canceled,  # NOVO
    'customer.subscription.updated':  _handle_subscription_updated,   # NOVO
}
```

Cada handler:
1. Resolve `Box.objects.get(stripe_subscription_id=...)` em public.
2. Atualiza `Box.status` se necessario (ACTIVE → SUSPENDED em payment_failed).
3. Para escrever em tenant (ex.: registrar pagamento recorrente em `boxcore.Payment`):
   ```python
   with schema_context(box.schema_name):
       Payment.objects.create(...)
   ```

Contrato dos handlers:
- **Input**: `PaymentWebhookEvent` com payload Stripe valido + assinatura verificada.
- **Output**: `Box.status` consistente; `PlatformAuditEvent` registrado em public; opcional escrita em tenant.
- **Excecoes**: `Box.DoesNotExist` se webhook chega para Box deletado → log warning + ack 200 (Stripe nao precisa retry).

## 7. Cache, sessoes, logs

### 7.1 Cache namespace por tenant

```python
# control/cache.py
def tenant_cache_key(key: str) -> str:
    from django.db import connection
    schema = getattr(connection, 'schema_name', 'public')
    return f'octobox:{schema}:{key}'

def tcache_get(key, default=None):
    return cache.get(tenant_cache_key(key), default)

def tcache_set(key, value, timeout=None):
    cache.set(tenant_cache_key(key), value, timeout)
```

Migrar gradualmente call-sites de `cache.get/set` em codigo de dominio (Sprint 3).

### 7.2 Sessions

Manter em public (decisao §1 travada). `request.session['active_box_id']` (staff) e `request.session['student_active_box_id']` (aluno) controlam switch.

### 7.3 Logs com tenant_id

```python
# control/logging.py
class TenantContextFilter(logging.Filter):
    def filter(self, record):
        from django.db import connection
        record.tenant = getattr(connection, 'schema_name', 'public')
        return True

# config/settings/base.py LOGGING formatters
'tenanted': {'format': '%(asctime)s [%(tenant)s] %(name)s %(levelname)s %(message)s'},
```

## 8. Background jobs

### 8.1 Estado atual

Sem Celery. `shared_support/background_jobs.py` usa threading + Redis. `jobs/dispatcher.py:81` simula API estilo Celery (`task.delay`).

### 8.2 Pattern multi-tenant

Toda task recebe `schema_name` como argumento:

```python
# jobs/base.py
class BaseJob(ABC):
    def run(self, *, schema_name: str, **kwargs):
        with schema_context(schema_name):
            return self._run_in_tenant(**kwargs)
```

### 8.3 Mudancas necessarias (Sprint 3)

- `jobs/dispatcher.py:81` (`dispatch_async_job`): capturar `schema_name = connection.schema_name` no momento do dispatch.
- `shared_support/background_jobs.py:113` (`submit_background_job`): wrapper de thread abre `schema_context(schema_name)` ANTES do `job_fn`.
- Auditar tasks: `operations/tasks.py`, `knowledge/tasks.py`, `reporting/tasks.py`, `auditing/tasks.py` — cada `task.delay(...)` recebe `schema_name`.

## 9. Testing strategy

### 9.1 Setup

- `pytest.ini`: `DJANGO_SETTINGS_MODULE=config.settings.test`.
- Postgres obrigatorio (django-tenants nao suporta SQLite).
- CI: `docker-compose.test.yml` com Postgres.
- Test classes: `django_tenants.test.cases.FastTenantTestCase` (compartilha tenant entre testes da mesma classe).

### 9.2 Boundary tests (criticos)

Lista minima — V2 inclui §3.5.6 com testes especificos de Student multi-box:

| # | Teste | Sprint |
|---|---|---|
| B1 | `test_user_of_box_a_cannot_see_students_of_box_b` | 4 |
| B2 | `test_direct_pk_access_returns_404_in_other_tenant` | 4 |
| B3 | `test_cache_isolation_per_tenant` | 4 |
| B4 | `test_session_attached_box_persists_after_relogin` | 4 |
| B5 | `test_orm_filter_does_not_leak_across_schemas` | 4 |
| B6 | `test_raw_sql_query_in_dashboard_respects_search_path` | 4 |
| B7..B11 | (Student multi-box, ver §3.5.6) | 4 |

### 9.3 Migration tests

```bash
# CI step
python manage.py migrate_schemas --shared
python manage.py provision_box --slug=ci_test --owner-email=ci@test
python manage.py migrate_schemas --schema=box_ci_test
python manage.py test --tag=tenant
```

**Criterio de pronto Sprint 4**: 100% dos boundary tests acima passam em CI; tempo de execucao < 5 min.

## 10. Plano de execucao por sprints

### Sprint 0 — Preparacao (2-3 dias)

| Tarefa | Saida mensuravel |
|---|---|
| Instalar `django-tenants==3.7.0` em `requirements.txt` | `pip install -r requirements.txt` retorna exit 0; `python -c "import django_tenants"` funciona. |
| Setup Postgres em DEV | `psql -c "SELECT version()"` retorna PG 14+. `DATABASE_URL=postgres://...` no `.env`. |
| Auditar FK cross-schema | Arquivo `docs/audits/cross-schema-fk-report.md` com lista de todos os `from django.contrib.auth.models import` em apps TENANT. |
| Auditar uso de `cache.get/set` em apps TENANT | Arquivo `docs/audits/cache-call-sites.md` com lista de arquivos:linhas. |
| Auditar `RunPython` em migrations | Lista de migrations em `docs/audits/runpython-migrations.md`; cada uma com flag `safe-for-multi-schema | needs-review`. |
| Auditar uso de `BOX_RUNTIME_SLUG` | Lista de arquivos:linhas em `docs/audits/runtime-slug-usage.md`. |
| Decidir SHARED_APPS final | §1.2 deste documento aprovado por escrito (commit confirmando). |

**Criterio de pronto Sprint 0**: 5 arquivos de audit em `docs/audits/`; Postgres rodando local; `manage.py check` retorna exit 0.

### Sprint 1 — Control plane (3-4 dias)

| Tarefa | Saida mensuravel |
|---|---|
| Criar app `control/` | Diretorio `control/` com `apps.py`, `models.py`, `migrations/0001_initial.py`. |
| Models Box, Domain, Membership, BoxProvisioningEvent, PlatformAuditEvent | `manage.py makemigrations control` cria migration sem warnings. |
| Migration inicial | `manage.py migrate_schemas --shared` cria 5 tabelas em public. |
| `TenantBySessionMiddleware` | Test: request a `/admin/` (path publico) NAO seta tenant; request a `/dashboard/` autenticado seta. |
| `config/urls_public.py` | `curl /admin/` em qualquer schema retorna 200 sem entrar em tenant. |
| Atualizar `config/settings/base.py` | SHARED_APPS, TENANT_APPS, MIDDLEWARE, TENANT_MODEL setados. `manage.py check` retorna exit 0. |
| `derive_slug(box_name)` | Test: 3 boxes "Box Demo" geram `box-demo`, `box-demo-2`, `box-demo-3`. |
| Comando `manage.py provision_box --slug=pilot --owner-email=dev@octobox.local` | Exit 0. `\dt box_pilot.*` em psql lista 30+ tabelas. |
| Comando `manage.py archive_box --slug=pilot` | Exit 0. `Box.status=ARCHIVED`; schema `box_pilot` renomeado para `archived_box_pilot_<ts>`. |
| Comando `manage.py reprovision_box --slug=xxx` | Exit 0 retomando do step pendente em `BoxProvisioningEvent`. |

**Criterio de pronto Sprint 1**: `manage.py provision_box --slug=pilot ...` cria schema completo e popula. Em `manage.py shell`:
```python
from django_tenants.utils import schema_context
with schema_context('box_pilot'):
    from boxcore.models import Student
    Student.objects.count()  # retorna 0 sem erro
```

### Sprint 2 — Signup integration + Student multi-box (3-4 dias)

> Este sprint absorve +1 dia para os refactors de §3.5 (Student multi-box).

| Tarefa | Saida mensuravel |
|---|---|
| Refator `activate_pending_signup` | E2E em DEV: `signup → checkout (test mode) → webhook → magic link → activate` cria User+Box+Membership atomicamente. |
| `control.services.provision_box` | Idempotente; chamar 2x com mesmo `pending_signup` retorna mesmo Box; `BoxProvisioningEvent` nao duplica. |
| `bootstrap_roles_for_tenant`, `seed_default_plans` | Apos provision, schema tem Group Owner/Manager/Coach/Recepcao + 3 MembershipPlan default. |
| Atualizar `signup/views.py` (post-activation redirect) | Apos ativacao, login automatico + redirect para `/dashboard/`; dashboard ja roda no schema do tenant. |
| Migrar 7 models de `student_identity` para SHARED (§3.5.1) | `migrate_schemas --shared` cria tabelas em public; tabelas dropadas dos schemas legados. |
| Quebrar O2O `StudentIdentity.student → boxcore.Student` (§3.5.2) | Migration backfill `Student.identity_id` em todos os schemas; drop `StudentIdentity.student_id`. |
| Trocar `box_root_slug: CharField` por `box_id: FK` (§3.5.3) | Migration backfill via `Box.objects.get(slug=...)`. Drop campos `*_root_slug`. |
| Tests | `signup/tests/test_activation_creates_box.py` cobre idempotencia + recovery de step falho. |

**Criterio de pronto Sprint 2**: e2e em DEV passa:
1. `POST /signup/checkout/` com plano anual.
2. Stripe CLI confirma pagamento test mode.
3. Email com magic link recebido.
4. `GET /onboarding/<token>/` permite criar username/senha.
5. Login automatico → `GET /dashboard/` mostra dashboard vazio do tenant `box_<slug>`.
6. `Student.objects.count()` no schema do tenant retorna 0.
7. `connection.schema_name` em request autenticado retorna o schema correto.

### Sprint 3 — Webhooks, jobs, cache, logs (2-3 dias)

| Tarefa | Saida mensuravel |
|---|---|
| Adicionar handlers Stripe recorrentes | Webhook `invoice.payment_failed` muda `Box.status` para SUSPENDED em < 1s. |
| Refator `jobs/dispatcher.py:81` | Test: dispatch dentro de tenant_a executa job em tenant_a (verifica via `connection.schema_name` no log do job). |
| Refator `shared_support/background_jobs.py:113` | Thread abre `schema_context` antes de `job_fn`; sem isso, query falha. |
| Auditar tasks existentes | Lista em `docs/audits/tasks-with-schema.md`; cada `task.delay` chamada recebe `schema_name`. |
| Cache helpers (`control/cache.py`) | `tcache_get/set` retornam isolado por tenant; teste com `cache.set` em tenant_a, `cache.get` em tenant_b retorna None. |
| Logging filter `TenantContextFilter` | Logs em DEV mostram `[box_pilot]` ou `[public]` no prefixo. |

**Criterio de pronto Sprint 3**: webhook `invoice.payment_failed` atualiza `Box.status`; import CSV grande em tenant_a NAO escreve em tenant_b; logs prefixados com tenant em DEV.

### Sprint 4 — Boundary tests + hardening (3-4 dias)

> Este sprint absorve +1 dia para boundary tests especificos de Student multi-box (§3.5.6).

| Tarefa | Saida mensuravel |
|---|---|
| Suite de boundary tests B1-B11 | 11 testes passam em CI (ver §9.2 + §3.5.6). |
| Test fixtures multi-tenant | `tests/conftest.py` com factories `box_a`, `box_b`, `user_a`, `user_b`, `identity_joao`, `student_joao_em_a`, `student_joao_em_b`. |
| CI step: `migrate_schemas --shared` + `provision_box --slug=ci_test` + `test` | CI verde em < 5 min. |
| Revisao de queries de dashboard | `Grep -r "raw\(" dashboard/` enumera; cada raw query passa boundary test B6. |
| Refator `box_runtime.py:27-33` | `get_box_runtime_slug()` retorna `connection.schema_name` quando ha tenant; env-var so em modo control. |
| Refator `StudentAuthMiddleware` (§3.5.4) | Teste B8: `/aluno/grade/` requer `StudentBoxMembership.status=active`. |
| Refator `/aluno/box/switch/` (§3.5.5) | Teste B9: switch troca `connection.schema_name` na proxima request. |
| Healthcheck `/api/v1/health/` (public) | `curl /api/v1/health/` retorna `{'runtime':'control','tenants_active':<N>,'healthy':true}`. |
| Healthcheck `/api/v1/health/tenant/` (autenticado) | `curl -b session=... /api/v1/health/tenant/` retorna `{'tenant':'box_xxx','healthy':true}`. |

**Criterio de pronto Sprint 4**: 100% dos boundary tests passam em CI; CI < 5 min; dois healthcheck endpoints funcionam.

### Sprint 5 — Rollout invisivel (2-3 dias)

| Tarefa | Saida mensuravel |
|---|---|
| Backup de producao (full pg_dump) | Arquivo `/backups/pre-tenant/<ts>.sql.gz`. |
| Deploy com SHARED_APPS/TENANT_APPS ativos | `manage.py migrate_schemas --shared` em prod retorna exit 0. |
| Migrar dados existentes (se prod tem dados) | Comando `migrate_existing_data_to_pilot` move tabelas `boxcore_*` de public para schema `box_pilot`. Validar contagens. |
| Provisionar `box_pilot` em prod | `\dt box_pilot.*` lista 30+ tabelas. |
| Smoke tests por papel | 4 logins (Owner, Coach, Manager, Recepcao) renderizam dashboards sem erro. |
| Provisionar primeiro tenant pago via fluxo Early Adopter | E2E completo do Sprint 2 em prod. |
| 24h de observacao | 0 ERROR no Sentry/log; healthcheck verde. |
| Provisionar proximos 5 boxes | 5 schemas `box_xxx` ativos. |

**Criterio de pronto Sprint 5**: 5 boxes ativos em prod; 0 vazamento; healthcheck verde por 24h continuas.

## 11. Riscos com mitigacao

| # | Risco | Probab | Impacto | Mitigacao |
|---|---|---|---|---|
| R1 | Migration legada com `RunPython` quebra em N schemas | Alta | Alto | Sprint 0: auditar `boxcore/migrations/`. Reescrever ou marcar shared-only. |
| R2 | FK tenant→`auth.User` confunde ORM em reverse lookups | Media | Alto | User em SHARED. Boundary test B5 valida. |
| R3 | Group/Permission globais nao casam com roles per-tenant | Media | Medio | Decisao §8 travada: roles via `Membership.role`, nao via Group. |
| R4 | Cache `KEY_PREFIX` estatico no settings | Alta | Medio | Wrapper `tcache_*` + migracao gradual (Sprint 3). |
| R5 | StudentApp middleware nao sabe tenant | Alta | Alto | §3.5.4 refator. Boundary test B8 valida. |
| R6 | Sessions: chave hoje tem prefix do env-var BOX_RUNTIME_SLUG | Baixa | Medio | Sessions em public, prefix global estavel. |
| R7 | Migracao de dados existentes em PROD | Alta | Alto (PROD) | Comando `migrate_existing_data_to_pilot` Sprint 5; backup full antes. |
| R8 | Schema creation nao transacional | Media | Medio | `BoxProvisioningEvent` + `provision_box` idempotente. |
| R9 | Webhook Stripe race antes do Box existir | Baixa | Baixo | Idempotencia em `mark_pending_signup_paid`; Box criado em activate, nao em webhook. |
| R10 | `migrate_schemas` lento em 20 schemas | Media | Medio | `--executor=multiprocessing`. |
| R11 | O2O cross-schema `StudentIdentity.student` quebra ORM | Alta | Alto | §3.5.2 inverte direcao para `Student.identity_id`. |
| R12 | `box_root_slug` legacy referenciado em codigo | Media | Medio | Sprint 2 backfill + Grep para referencias remanescentes. |
| R13 | Aluno em transicao perde acesso durante migracao | Baixa | Alto | Sprint 5: provisionar `box_pilot` ANTES de quebrar dados; smoke test do app aluno. |

## 12. Contratos entre apps (cross-references)

| Origem (arquivo) | Destino (arquivo) | Contrato |
|---|---|---|
| `signup/services.py::activate_pending_signup` | `control/services.py::provision_box(pending_signup, owner_user, slug, plan, stripe_*)` | Input: PendingSignup PAID. Output: Box ACTIVE. Idempotente. Excecoes: `BoxProvisioningError`. |
| `control/services.py::provision_box` | `django_tenants` + `boxcore/migrations/*` via `with schema_context(box.schema_name)` | Input: schema_name valido. Output: queries no schema correto. Excecoes: `SchemaDoesNotExist`. |
| `integrations/stripe/router.py::_HANDLERS` | `control/models.py::Box.objects.get(stripe_subscription_id=...)` | Input: subscription_id Stripe. Output: Box. Excecoes: `Box.DoesNotExist` (log + ack 200). |
| `student_app/middleware/student_auth.py::_resolve_student_tenant` | `control/models.py::Box.objects.filter(pk=..., status=ACTIVE)` | Input: `box_id` do cookie do aluno. Output: Box ativo. Read-only. Idempotente. |
| `student_identity/views.py::StudentOAuthCallbackView` | `student_identity/facade/tenant_resolver.py::resolve_tenant_for_student_oauth_callback` | Input: `invite_token`, `provider_subject`, `email`. Output: `TenantResolution` com `connection.set_tenant` ja chamado. Sem efeitos colaterais alem de ativar tenant. |
| `student_identity/views.py::StudentInviteLandingView` | `student_identity/facade/tenant_resolver.py::resolve_tenant_for_student_invite_landing` | Input: `invite_token`. Output: `TenantResolution` ou `strategy=NONE`. |
| `student_identity/facade/tenant_resolver.py` | `student_identity/infrastructure/repositories.py::DjangoStudentIdentityRepository` | Lookups por token (invitation, link). Read-only em public. |
| `control/middleware.py::TenantBySessionMiddleware` | `django.db.connection.set_tenant(box)` | Input: Box ativo da session. Output: `search_path` setado. Idempotente. Reset explicito em paths de `PUBLIC_SCHEMA_PATHS`. |
| `control/services.py::provision_box` | `signup/models.py::PendingSignup` via `related_name='box'` | Read-only. Apos activate, `pending.box` retorna o Box criado. |
| `monitoring/beacon_snapshot.py::_get_known_tables` | `django.core.cache.cache` (chave `red_beacon:known_tables:v1:<using>:<schema>`) | TTL 60s. Isolado por schema (chave inclui `connection.schema_name`). |

## Estimativa total de esforco

| Sprint | Foco | Dias-dev (senior) |
|---|---|---|
| Sprint 0 | Auditoria + Postgres DEV | 2-3 |
| Sprint 1 | Control plane + middleware + comandos | 3-4 |
| Sprint 2 | Signup integration + Student multi-box (§3.5) | 3-4 |
| Sprint 3 | Webhooks, jobs, cache, logs | 2-3 |
| Sprint 4 | Boundary tests + hardening (Student tests inclusos) | 3-4 |
| Sprint 5 | Rollout invisivel em prod | 2-3 |
| **Total** | | **15-21 dias-dev** + **3 dias buffer** = **18-24 dias-dev** (4-5 semanas calendar com 1 dev senior) |

## Proximos passos recomendados

1. **HOJE**: aprovar V2 deste plano via PR.
2. **Esta semana**: Sprint 0 (auditoria + Postgres DEV). Saida: 5 arquivos de audit.
3. **Semana 2**: Sprint 1. Saida: `provision_box --slug=pilot` funciona em DEV.
4. **Semana 3**: Sprint 2. Saida: e2e Early Adopter em DEV; Student multi-box formalizado.
5. **Semana 4**: Sprints 3 + 4. Saida: webhooks recorrentes, boundary tests verdes em CI.
6. **Semana 5**: Sprint 5. Provisionar primeiro tenant pago em prod. **Nao vender o 2o tenant antes desse rollout estar 24h estavel.**

---

## 13. Revisao arquitetural (Software Architecture Chief)

> Esta secao foi adicionada apos o draft V2 do plano. Cada item questiona pressupostos, identifica falhas implicitas e propoe correcoes pontuais. Decisoes ficam com o usuario; o objetivo aqui e expor o que esta escondido.

### 13.1 Middleware ordering — problema critico identificado

A ordem proposta em §3.4 tem um defeito de isolamento. Verificacao no codigo:

`integrations/middleware.py:78-80` — `WebhookIdempotencyMiddleware` executa:
```python
existing_event = WebhookEvent.objects.filter(
    query, status=WebhookDeliveryStatus.PROCESSED, ...
).exists()
```

Esta query roda ANTES de `TenantBySessionMiddleware` definir o tenant. Em `django-tenants`, `connection.schema_name` herda o valor do request anterior do mesmo worker (gunicorn worker reutilizado). Se request anterior foi para `box_007` e o webhook entra agora, a query de idempotencia executa em `box_007`, nao em `public`.

**Consequencia**: tabela `WebhookEvent` (que estara em SHARED, schema `public`) pode nao ser encontrada via search_path do tenant atual, ou pior — silenciosamente cria duplicatas porque o INSERT vai para a tabela errada se ela existir em ambos os schemas (improvavel mas possivel via migracoes mal-classificadas).

**Correcao obrigatoria**: o middleware deve forcar reset para public ANTES de tocar no DB. Duas opcoes:

```python
# Opcao A — reset explicito no inicio do middleware
def __call__(self, request):
    from django.db import connection
    connection.set_schema_to_public()  # garante public para qualquer query subsequente
    if request.method == 'POST' and '/api/v1/integrations/' in request.path:
        return self.process_webhook(request)
    return self.get_response(request)

# Opcao B — mover WebhookIdempotencyMiddleware para DEPOIS de TenantBySessionMiddleware,
# e fazer TenantBySessionMiddleware whitelistar o path de webhook como public
```

**Recomendo Opcao A** porque preserva a propriedade "idempotencia checada antes de qualquer processamento" e nao acopla `WebhookIdempotencyMiddleware` ao `TenantBySessionMiddleware`.

**Adendum ao plano (Sprint 1)**: adicionar `connection.set_schema_to_public()` no inicio de `WebhookIdempotencyMiddleware.__call__`. Boundary test em Sprint 4: `test_webhook_idempotency_runs_in_public_after_tenant_request`.

### 13.2 Transaction boundaries — `@transaction.atomic` e enganoso aqui

§4.1 do plano diz:
```python
@transaction.atomic  # apenas operacoes em PUBLIC. DDL de schema nao e transacional.
def activate_pending_signup(...):
```

O comentario admite o problema mas nao resolve. O detalhe critico: PostgreSQL **suporta DDL em transacoes** (diferente do MySQL). Mas `box.create_schema()` da `django-tenants` chama `schema_editor().execute("CREATE SCHEMA")` na conexao corrente, e `call_command('migrate_schemas', ...)` abre transacoes proprias por migration. Isso significa:

| Cenario | Resultado |
|---|---|
| User criado, `create_schema` falhou | Atomic rollback remove User. Schema nao existe. **OK**. |
| User criado, schema criado, primeira migration falhou | Atomic outer block tenta rollback. Mas `migrate_schemas` ja COMMITOU primeiras migrations. **Schema fica parcial e User e removido**. Box record fica em `PROVISIONING`. |
| User criado, schema OK, migrations OK, `bootstrap_roles` falha | Atomic rollback remove User+Box record. Schema fica orfao (`box_xxx` no Postgres sem dono). |
| User criado, tudo OK, mas crash de processo entre `provision_box` retornar e `Membership.create` | Tudo rolled back. **OK**. |

Os cenarios 2 e 3 sao os perigosos. `BoxProvisioningEvent` cobre cenario 2 (re-rodar `provision_box`), mas cenario 3 deixa schema orfao e `BoxProvisioningEvent` tambem some.

**Correcao**: nao usar `@transaction.atomic` envolvendo `provision_box`. Em vez disso:

```python
def activate_pending_signup(...):
    # Step 1: User + Membership em transacao atomica (so public)
    with transaction.atomic():
        user = create_user(...)
        # NAO criar Membership ainda — depende do Box
    
    # Step 2: Box + schema FORA do atomic (DDL precisa de commits independentes)
    try:
        box = provision_box(pending_signup=pending_signup, owner_user=user, ...)
    except Exception:
        # NAO deletar User automaticamente — pode ser retry valido
        # User orfao e cleanup periodico
        raise
    
    # Step 3: Membership + status em transacao atomica
    with transaction.atomic():
        Membership.objects.get_or_create(user=user, box=box, defaults={...})
        pending_signup.status = ACTIVATED
        pending_signup.activated_user = user
        pending_signup.save(...)
    
    return user
```

**Adendum ao plano (Sprint 2)**: reescrever `activate_pending_signup` removendo o `@transaction.atomic` outer e quebrando em 3 fases. Adicionar comando `manage.py cleanup_orphan_users --older-than=24h` mencionado em §4.3.

### 13.3 Failure modes nao cobertos no plano V2

Cinco modos de falha implicitos que precisam tratamento explicito:

#### F1. Stripe webhook duplicado em concorrencia

`integrations/stripe/router.py` ja tem `PaymentWebhookEvent` para idempotencia, mas **a janela entre `WHERE event_id=X` e `INSERT` nao tem lock**. Se dois workers recebem o mesmo evento simultaneamente (Stripe retry):

- Worker A: `SELECT WHERE event_id='evt_123'` → vazio
- Worker B: `SELECT WHERE event_id='evt_123'` → vazio
- Worker A: `INSERT ... event_id='evt_123'` → OK
- Worker B: `INSERT ... event_id='evt_123'` → IntegrityError (unique constraint), MAS antes do erro, `_handle_early_adopter_signup` ja foi chamado. Side-effect duplicado.

**Mitigacao**: envolver handler em `transaction.atomic()` + `select_for_update()` no `PaymentWebhookEvent.objects.filter(event_id=...)`. OU usar `INSERT ... ON CONFLICT DO NOTHING` e verificar `affected_rows` antes de chamar handler.

#### F2. Email do magic link nao e idempotente

`mark_pending_signup_paid` chama `send_onboarding_email`. Se webhook chega 2x (ex.: Stripe retry apos timeout), email vai 2x. Confunde o Owner.

**Mitigacao**: `PendingSignup.magic_link_sent_at` (datetime, nullable). `send_onboarding_email` checa: se ja enviado nas ultimas 24h, skip.

#### F3. Aluno aceita invite mas Box ainda em PROVISIONING

Sequencia possivel:
- t0: Owner Renan provisiona box `endorfina`. Status=PROVISIONING.
- t1: Recepcao manda invite para joao@email.com (em public, OK).
- t2: Joao aceita invite. `StudentBoxMembership` criada em public, status=active.
- t3: Joao acessa `/aluno/`. `StudentAuthMiddleware` resolve membership, faz `connection.set_tenant(box)`. Mas schema ainda nao existe → erro 500.

**Mitigacao**: `StudentBoxMembership` deveria checar `box.status='ACTIVE'` antes de aceitar invite. Adicionar validacao em `StudentAppInvitation.accept()`.

#### F4. Box.status muda durante request em flight

- t0: Owner faz GET `/dashboard/`. Middleware le Box.status=ACTIVE.
- t1: Stripe webhook chega `invoice.payment_failed`. Box.status=SUSPENDED.
- t2: Owner submete POST de operacao critica. Middleware (novo request) le SUSPENDED → bloqueia. **OK**.
- t1': MAS entre t0 e t1, o request original ainda esta processando. Owner pode ter feito operacao "ilegal".

**Mitigacao**: este e um trade-off aceitavel para Fase 1 (janela de poucos segundos). Em Fase 2, validar status no commit final da operacao critica.

#### F5. Reprovision_box concorrente com provision_box

Se admin chama `manage.py reprovision_box --slug=endorfina` enquanto o webhook tambem disparou re-execucao automatica, dois processos rodam `_step_run_migrations` simultaneamente. `migrate_schemas` nao e thread-safe.

**Mitigacao**: lock em `BoxProvisioningEvent` via `select_for_update`:
```python
def _step(box, name, fn):
    with transaction.atomic():
        Box.objects.select_for_update().get(pk=box.pk)  # lock no Box
        last = BoxProvisioningEvent.objects.filter(box=box, step=name, status='ok').first()
        if last:
            return
        ...
```

**Adendum ao plano (Sprint 2)**: criar §13.3 dentro do plano original (atualizar §4.3) cobrindo F1-F5.

### 13.4 Contratos entre apps — implicit contracts faltando

Tres contratos implicitos nao documentados em §12:

#### C1. `provision_box` exige `connection.schema_name='public'`

Se chamado dentro de outro `schema_context`, vai criar `Box` no schema errado e falhar de forma confusa. O contrato precisa documentar:

```
PRECONDITION: connection.schema_name == 'public'
```

E a funcao deveria assertar:
```python
def provision_box(...):
    from django.db import connection
    if connection.schema_name != 'public':
        raise RuntimeError('provision_box deve ser chamado em public schema')
```

#### C2. `Box` deletado x `auth.User` orfao

`Box.owner_user.on_delete=PROTECT` — Django nao permite deletar User se ele e dono de algum Box. Mas se um User tem Membership em multiplos boxes e um deles e arquivado:
- `archive_box` muda `Box.status` mas nao deleta nem o Box nem o User.
- Se Owner sai da plataforma (cancelou subscription, sem upgrade), o que fazer com `auth.User`?

**Decisao implicita**: User permanece ate cleanup explicito. Adicionar contrato em §12: "User.delete() bloqueia se ha Box ativo. Para offboarding, primeiro `archive_box`, depois cleanup periodico de Users sem memberships."

#### C3. `StudentBoxMembership.status='revoked'` x sessao do aluno em flight

Se Recepcao revoga membership do Joao enquanto Joao esta logado em `/aluno/grade/`:
- t0: middleware leu membership ativo, setou tenant, request processa.
- t1: Recepcao revoga.
- t2: proximo request do Joao → middleware le revoked, redireciona.

OK, mas **nao invalida sessao ativa**. Joao consegue submeter forms ate o token expirar. Em Fase 1, aceitavel; em Fase 2, considerar `StudentSession.invalidated_at` quando membership e revogado.

**Adendum ao plano (§12)**: adicionar 3 linhas com C1, C2, C3.

### 13.5 Sprint 2 vs Sprint 3 — dependencia oculta

Sprint 2 muda models de `student_identity` (mover para SHARED). Sprint 3 mexe em `jobs/dispatcher.py` para passar `schema_name`. Entre os dois sprints, **jobs em flight podem usar models antigos**:

- Sprint 2 deploya: `StudentBoxMembership.box_root_slug` → `box_id`.
- Job assincrono em fila Redis foi enfileirado ANTES do deploy. Job tenta `membership.box_root_slug` → AttributeError.

**Mitigacao**:
1. Sprint 2 deve drenar fila de jobs antes do deploy (`shared_support/background_jobs.py` precisa de comando `drain` ou sleep ate fila vazia).
2. Sprint 3 NAO PODE comecar antes de Sprint 2 estar 100% deployado em prod (mas o plano so deploya tudo em Sprint 5; Sprints 0-4 sao DEV/staging — ok).
3. Mas Sprint 5 deploya tudo de uma vez. Risco real e neste momento. Adicionar pre-deploy step: "drenar fila de jobs antes de aplicar migrations".

**Adendum ao plano (Sprint 5)**: adicionar tarefa "Drenar fila de jobs (validar Redis vazio)" como pre-requisito do passo "Deploy com SHARED_APPS/TENANT_APPS ativos".

### 13.6 Rollback strategy — bloqueador identificado

V2 menciona `archive_box --slug=xxx` mas nao detalha rollback de TODA a migracao. Cenario: Sprint 5 deploya, primeiro tenant pago entra, e em D+3 descobrimos bug critico que vaza dados entre tenants.

**Caminho de volta possivel**:

1. **Soft rollback (sem perder dados)**: parar de aceitar novos signups. Owners existentes continuam usando. Hotfix do bug em paralelo. Tempo: dias.

2. **Hard rollback (volta para "1 instancia = 1 box")**: extremamente custoso.
   - Para cada tenant ativo: `pg_dump --schema=box_xxx > box_xxx.sql`.
   - Provisionar instancia dedicada para cada um (servidores separados).
   - Restaurar dump em cada instancia, ajustando schema_name de `box_xxx` para `public`.
   - Reconfigurar DNS, sessoes, OAuth callbacks por instancia.
   - Tempo: semanas.

**Conclusao**: hard rollback NAO e viavel apos Sprint 5 ter rodado por mais de 7 dias com tenants pagantes. Migration e effectively one-way.

**Adendum ao plano (Sprint 5)**:
- Adicionar gate explicito: "antes de Sprint 5 deploy, validar que Sprint 4 boundary tests passam **3 vezes consecutivas em CI**".
- Criar runbook `docs/rollout/schema-per-tenant-rollback-procedure.md` documentando:
  - Soft rollback procedure (gating de signups).
  - Procedimento de extracao de tenant para instancia dedicada (caso isolado).
  - Janela de "no-tenant-paid" de 7 dias apos deploy onde rollback ainda e barato.

### 13.7 Stripe webhook `Box.status=SUSPENDED` — comportamento nao definido

O plano §6.3 muda `Box.status` para SUSPENDED em `invoice.payment_failed`, mas nao define o que isso SIGNIFICA na pratica. Quatro perguntas:

| Pergunta | Recomendacao arquitetural |
|---|---|
| Owner perde acesso ao painel? | **Soft block**: redirect de toda rota staff para `/billing/renew/` exceto `/billing/*`, `/logout/`, `/admin/`. |
| Recepcao/Coach perdem acesso? | **Sim** — mesmo soft block. So Owner pode renovar. |
| Aluno do box continua acessando? | **Sim** durante 7 dias (carencia). Apos 7 dias, soft block para alunos tambem. |
| Webhooks continuam processando? | **Sim** — sempre. Para detectar pagamento da renovacao. |

**Implementacao**: `TenantBySessionMiddleware` checa `Box.status` apos resolver tenant:
```python
if box.status == Box.Status.SUSPENDED:
    if request.user.is_authenticated and request.path not in BILLING_WHITELIST:
        return redirect('/billing/renew/')
```

**Adendum ao plano (Sprint 3)**: adicionar §6.4 `Box.status=SUSPENDED` policy. Adicionar tarefa "Implementar soft-block em TenantBySessionMiddleware". Adicionar boundary test B12: `test_suspended_box_redirects_staff_to_billing_renewal`.

### 13.8 Performance assumption — falta benchmark

V2 menciona `migrate_schemas --executor=multiprocessing` para 20 schemas. Sem benchmark, nao sabemos se deploy demora 5 minutos ou 50.

**Estimativa rude**:
- Migration de schema vazio: ~10-30s (ContentType + auth + boxcore migrations).
- Migration de schema com dados (~1000 alunos, 5000 payments): pode ate dobrar (data migrations RunPython).
- 4 workers em paralelo, 20 schemas: 5 batches × 30s = ~2.5 min para schemas vazios; ate ~10 min com dados pilots.

**Adendum ao plano (Sprint 5)**: adicionar tarefa "Benchmark `migrate_schemas` em DEV com `box_pilot` populado":
- Comando: `time python manage.py migrate_schemas --executor=multiprocessing`
- Critério mensuravel: deploy em prod nao deve travar requests > 30s. Se benchmark mostrar > 30s, considerar zero-downtime via `migrate_schemas --tenant=box_xxx` em paralelo com requests servindo da versao antiga.

### 13.9 Resumo de adendos a aplicar no plano V3

Os 8 itens acima geram 11 adendos pontuais no plano (nao reescrita). Recomendacao: aplicar como V3 ou listar como "issues conhecidas" se o usuario preferir avancar com V2 e tratar em Sprint 0-1.

| # | Adendo | Sprint afetado | Esforco extra |
|---|---|---|---|
| A1 | `connection.set_schema_to_public()` em `WebhookIdempotencyMiddleware` | 1 | 0.5 dia |
| A2 | Reescrever `activate_pending_signup` em 3 fases (sem outer atomic) | 2 | 0.5 dia |
| A3 | Comando `cleanup_orphan_users` | 2 | 0.5 dia |
| A4 | F1: lock em PaymentWebhookEvent | 3 | 0.5 dia |
| A5 | F2: `magic_link_sent_at` idempotencia | 2 | 0.25 dia |
| A6 | F3: validar `box.status='ACTIVE'` no `accept invite` | 2 | 0.25 dia |
| A7 | F5: lock em `BoxProvisioningEvent` | 2 | 0.25 dia |
| A8 | C1: assert `provision_box` em public | 1 | 0.1 dia |
| A9 | Drenar fila de jobs no Sprint 5 deploy | 5 | 0.5 dia |
| A10 | Runbook de rollback + soft-block SUSPENDED | 3-5 | 1 dia |
| A11 | Benchmark `migrate_schemas` | 5 | 0.5 dia |
| **Total** | | | **~5 dias extras** |

Esforco total ajustado: **18-24 dias-dev** (V2) → **23-29 dias-dev** (V3 com adendos). Calendar time: 5-6 semanas.

**Conclusao**: V2 esta solido em premissas mas tem buracos operacionais que aparecem na execucao real. V3 e necessaria antes de comecar Sprint 0. As 11 mudancas sao pontuais — nao alteram a arquitetura, so endurecem failure modes.

---

## 14. Revisao SQL/schema (octobox-sql-architect)

> Foco: comportamento real do PostgreSQL 14+ sob 20-100 schemas. Cada subsecao distingue **Evidencia** (verificada no codigo/docs do PG), **Inferencia** (deducao tecnica) e **Desconhecido** (precisa benchmark/teste). Decisoes ficam com o usuario.

### 14.1 FK cross-schema `Student.identity_id → public.student_identity.id`

**Evidencia**: PostgreSQL aceita FK cross-schema desde versoes antigas. Internamente o constraint vira uma entrada em `pg_constraint` com `confrelid` apontando para a tabela em `public`. O query planner trata como FK normal — sem custo extra de planning.

**Inferencia (custos reais)**:

| Aspecto | Comportamento | Implicacao para o plano |
|---|---|---|
| `JOIN` ORM cross-schema | Quando `connection.schema_name='box_001'` faz `Student.objects.select_related('identity')`, Postgres resolve `identity` em `public` via search_path (`SET search_path TO box_001, public`). Funciona. | OK. Mas confirmar que `django-tenants` seta search_path como `box_001, public` (com public no fim), nao apenas `box_001`. Se for soh `box_001`, JOIN quebra. **Verificar em Sprint 0**: `SHOW search_path` apos `connection.set_tenant`. |
| Indice na PK alvo | `public.student_identity.id` ja e PK → indice unique gratuito. Suficiente. | Nada a fazer. |
| `ON DELETE` propagation | `on_delete=PROTECT` (Django) → constraint Postgres `ON DELETE NO ACTION`. Quando tenta deletar `StudentIdentity #7`, Postgres precisa varrer **todas as tabelas** com FK apontando para `public.student_identity.id`. Com 20 schemas, sao 20 tabelas `boxcore_student`. **Linear no numero de schemas**. | Para 20 boxes, delete de Identity custa ~50-100ms. Para 100 boxes, ~500ms. Aceitavel. Soft-delete (status='archived' em StudentIdentity) e mais barato e e o que o codigo ja faz (linha 89-91 `student_identity/models.py`). Recomendar: NUNCA fazer DELETE fisico de Identity; sempre soft-delete. |
| Reverse `related_name='student_records'` | `identity.student_records.all()` em `connection.schema_name='box_001'` so retorna registros de `box_001`. **Para listar TODOS os boxes que o aluno frequenta, nao da pra usar reverse** — precisa iterar via `StudentBoxMembership` (em public). | **Isso e feature de isolamento, nao bug.** Documentar explicitamente em §3.5: "para listar todos os boxes do aluno, query `StudentBoxMembership.objects.filter(identity_id=7)`. NUNCA `identity.student_records.all()` cross-tenant — so retorna o tenant ativo." |

**Desconhecido**: comportamento de `select_related('identity')` quando `student.identity_id` e NULL (alunos legacy sem OAuth). ORM deveria gerar LEFT JOIN, mas confirmar via `EXPLAIN`.

**Adendo SQL-1 (Sprint 0)**: rodar em DEV apos primeiro `provision_box`:
```sql
SHOW search_path;  -- deve ser: "box_pilot", public
EXPLAIN ANALYZE SELECT s.*, i.* FROM boxcore_student s LEFT JOIN public.student_identity_studentidentity i ON s.identity_id = i.id LIMIT 10;
```

### 14.2 Migrations em N schemas — `migrate_schemas --executor=multiprocessing`

**Evidencia**: `django-tenants` 3.7+ usa `multiprocessing.Pool` (default 4 workers ou `os.cpu_count()`). Cada worker faz `fork()` e abre conexao propria.

**Inferencia (numeros)**:

| Aspecto | Calculo | Resultado |
|---|---|---|
| Conexoes simultaneas em prod | 4 workers + 1 Django master + 4 gunicorn workers × 1 conn cada (CONN_MAX_AGE=60) | ~9 conexoes durante deploy |
| `max_connections` default Postgres | 100 | Folga grande em Fase 1 (20 boxes). Em Fase 2 (100 boxes), considerar PgBouncer. |
| Lock contention | Cada worker mexe em schema DIFERENTE → tabela diferente → `ACCESS EXCLUSIVE LOCK` em escopo isolado. **Sem contencao entre workers.** | OK. |
| WAL contention | 4 workers escrevendo paralelo → 4 streams concorrentes para `pg_wal/`. PG 14+ tem `wal_compression=on` e parallel WAL writers. Bottleneck real: fsync (`wal_sync_method=fdatasync` default). | Aceitavel em SSD; em HDD, deploy 2-3x mais lento. **Confirmar tipo de disco em prod.** |
| `ANALYZE` automatico | `migrate` nao roda ANALYZE automaticamente. Autovacuum vai pegar com delay default 1 min. | Apos `migrate_schemas`, queries do primeiro request podem ter plano ruim ate autovacuum estatisticar. **Adendo SQL-2 (Sprint 1)**: comando `provision_box` chama `ANALYZE` no schema novo apos seed: `cursor.execute(f'ANALYZE {schema_name}.boxcore_student, {schema_name}.boxcore_membershipplan, ...')`. |

**Desconhecido (precisa benchmark)**: tempo real de migrate em schema vazio (estimativa 10-30s) vs schema com 1000 alunos + 5000 payments + 50000 attendance records (estimativa 60-180s). Sprint 5 deve medir.

### 14.3 search_path — comportamento de tabelas duplicadas

**Evidencia**: `SET search_path TO box_001, public` faz Postgres resolver tabela na ORDEM. Primeira ocorrencia ganha. Comprovavel via:
```sql
CREATE TABLE public.test (id int);
CREATE TABLE box_001.test (id int);
SET search_path TO box_001, public;
SELECT * FROM test;  -- vai pegar box_001.test
```

**Risco real durante migracao §3.5.1**: ao mover models de `student_identity` de TENANT para SHARED, criar tabelas em `public` ANTES de dropar tabelas vestigiais nos schemas legados. Se ordem inverter:
- Tabela vestigial `box_001.student_identity_studentidentity` ainda existe.
- Migration cria `public.student_identity_studentidentity`.
- Codigo Django (em `box_001` request) faz `StudentIdentity.objects.filter(...)` → resolve para `box_001.student_identity_studentidentity` (vazio ou stale).

**Adendo SQL-3 (Sprint 2)**: migration de promote-to-shared deve seguir ordem ESTRITA:
```python
# student_identity/migrations/0XXX_promote_to_shared.py
def forward(apps, schema_editor):
    # 1. Cria tabelas em public (idempotente)
    # 2. Backfill: copia dados de TODOS schemas legados para public
    #    (em transacao por schema; rollback se algum falhar)
    # 3. SOMENTE DEPOIS de validacao COUNT(*) coincidir, droppa tabelas legadas
    pass
```

E validar com query antes do drop:
```sql
SELECT 'box_001' AS schema, COUNT(*) FROM box_001.student_identity_studentidentity
UNION ALL
SELECT 'public', COUNT(*) FROM public.student_identity_studentidentity;
-- esperado: contagem por schema soma para o total em public
```

**Funcoes/triggers cross-schema**: criadas em `public` SAO visiveis a partir de qualquer schema (search_path inclui public no fim). Ao contrario nao funciona — funcao em `box_001` nao e visivel de `box_002`. **Para o plano**: nenhuma funcao customizada e referenciada; OK por enquanto. Se `auditing` ou `signal_mesh` adicionarem triggers, verificar.

**Sequences**: `box_001.boxcore_student_id_seq` e INDEPENDENTE de `box_002.boxcore_student_id_seq`. Cada schema tem sua propria. **Joao em box_001 pode ser Student #42; em box_002 pode ser Student #42 tambem.** PKs nao colidem porque vivem em namespaces diferentes. OK e desejado.

### 14.4 Indices e estatisticas — gaps no V2

**Evidencia (codigo atual)**: `student_identity/models.py:81` — `box_root_slug` ja tem `db_index=True`. Migration backfill em §3.5.3 trocara por FK `box_id` (que automaticamente cria indice).

**Inferencia (gaps que V2 nao cobre)**:

| Tabela | Indice faltante | Justificativa |
|---|---|---|
| `control.Box` | `stripe_subscription_id` deveria ser `unique=True`, nao apenas `db_index=True` (V2 §2 linha 162) | 1 subscription Stripe = 1 Box. Sem unique, race condition pode duplicar. **Adendo SQL-4 (Sprint 1)**: trocar para `models.CharField(..., unique=True, null=True, blank=True)`. |
| `control.Box` | `slug` ja unique. OK. | — |
| `control.Membership` | `(user, is_primary_box)` filtrado por `is_primary_box=True` — query frequente do middleware | V2 §2 linha 192 ja tem `Index(fields=['user', 'is_primary_box'])`. Considerar **partial index**: `Index(fields=['user'], condition=Q(is_primary_box=True))` reduz tamanho do indice em 50%+. **Adendo SQL-5 (Sprint 1)**. |
| `control.BoxProvisioningEvent` | V2 propoe `Index(fields=['box', 'step', 'status'])` (linha 200) | Query mais frequente: "ja rodou step=X com status=ok?". Partial index `Index(fields=['box', 'step'], condition=Q(status='ok'))` e mais eficiente. **Adendo SQL-6**. |
| `Student.identity_id` (em CADA schema apos §3.5.2) | FK indice automatico via Django (`db_index=True` implicito em FK) | Confirmar via `\d boxcore_student` no Postgres apos migration. |
| `boxcore.AuditEvent` (per tenant) | Hoje provavelmente sem indice composto em `(actor_user_id, created_at)` | Audit query "ultimas 100 acoes do user X" e comum no painel. **Verificar em Sprint 0** — fora do escopo do plano de tenant, mas apontar como tech debt. |

### 14.5 Migration data heavy — backfill em N schemas

**Cenario hipotetico (calibrar com dados reais em Sprint 0)**: 20 boxes × 1000 students = 20.000 rows; 20 × 5000 payments = 100.000 rows.

**Operacoes propostas em §3.5.2 e §3.5.3**:

| Operacao | Custo Postgres | Risco em prod |
|---|---|---|
| `ALTER TABLE boxcore_student ADD COLUMN identity_id INTEGER NULL` | PG 11+: metadata-only, **instantaneo** | OK. Sem table rewrite. |
| `UPDATE boxcore_student SET identity_id = (SELECT id FROM public.student_identity_studentidentity WHERE student_id = boxcore_student.id)` | Subquery por linha → **table scan + 20.000 lookups por schema**. ~30-60s por schema. Bloqueio de UPDATE em rows tocadas. | Em prod com app rodando, bloqueia escrita por minuto+. **Risco real.** |
| `DROP COLUMN student_id FROM public.student_identity_studentidentity` | PG 11+: metadata-only **se sem indice unique**; mas tem `OneToOneField` → unique. **Drop unique pode rewriter**. | Median 5-30s. |
| `DROP COLUMN box_root_slug FROM ...` (4 tabelas) | Metadata-only quando coluna sem indice; aqui tem `db_index=True` → indice tambem dropado. | OK, mas indice fica em `pg_stat_user_indexes` ate `VACUUM FULL` ou `pg_repack`. Espaco em disco nao recuperado imediatamente. |

**Adendo SQL-7 (Sprint 2)**: backfill de `identity_id` deve ser **batched**, nao single UPDATE:
```python
# control/migrations/0XXX_backfill_student_identity.py
BATCH = 500
def backfill_per_schema(apps, schema_editor):
    Student = apps.get_model('boxcore', 'Student')
    while True:
        ids = list(Student.objects.filter(identity_id__isnull=True).values_list('pk', flat=True)[:BATCH])
        if not ids:
            break
        with connection.cursor() as cur:
            cur.execute("""
                UPDATE boxcore_student s
                SET identity_id = i.id
                FROM public.student_identity_studentidentity i
                WHERE i.student_id = s.id AND s.id = ANY(%s)
            """, [ids])
        # commit por batch — libera locks
```

E rodar em janela de baixo trafego com flag de feature `MIGRATION_IN_PROGRESS=True` que avisa staff.

**Adendo SQL-8 (Sprint 5)**: apos drop de colunas, agendar `pg_repack` ou `VACUUM FULL` em janela de manutencao para recuperar espaco em disco. Nao bloqueante se usar `pg_repack`.

### 14.6 Connection pooling com django-tenants

**Evidencia (settings/base.py:137)**: `conn_max_age=60` (segundos). Conexao Postgres mantida idle por 60s, reutilizada entre requests do mesmo gunicorn worker.

**Risco critico**: cada conexao retem ultima `SET search_path`. Sem reset entre requests:

```
[req1] worker_a, conn_pool[0] → set_tenant(box_001) → search_path=box_001,public → query → done
[req2] worker_a, conn_pool[0] reusada → middleware NAO chama set_tenant (path publico) → search_path AINDA box_001,public → query em public ESCAPA para box_001!
```

**Mitigacao em django-tenants**: `TenantBySessionMiddleware` deve **sempre** chamar `connection.set_tenant(box)` OU `connection.set_schema_to_public()` no inicio. Nunca deixar conexao com search_path "herdado". V3 §13.1 ja propoe isso para o webhook middleware; aplicar globalmente.

**Adendo SQL-9 (Sprint 1)**: `TenantBySessionMiddleware` deve ter um `_reset_search_path_first` no inicio de `__call__`:
```python
def __call__(self, request):
    from django.db import connection
    # SEMPRE reset antes de decidir tenant — evita herança de request anterior
    connection.set_schema_to_public()
    if request.path.startswith(PUBLIC_PATHS):
        return self.get_response(request)
    box = self._resolve_tenant(request)
    if box:
        connection.set_tenant(box)
    return self.get_response(request)
```

**PgBouncer compatibilidade**:

| Modo | search_path comportamento | Compativel com django-tenants? |
|---|---|---|
| **session pooling** | search_path persiste por toda a sessao do client | OK |
| **transaction pooling** | search_path resetado a cada COMMIT/ROLLBACK | **QUEBRA** se request faz multiplas transacoes |
| **statement pooling** | search_path so vale 1 statement | **QUEBRA** total |

**Adendo SQL-10 (Sprint 5/Fase 2)**: documentar que se PgBouncer for adicionado em Fase 2, **DEVE ser session pooling**. Transaction pooling com `django-tenants` requer hooks customizados (lib tem suporte parcial via `set_tenant_callback`).

### 14.7 Backups e restore por tenant

**Evidencia**: `pg_dump --schema=box_001` exporta apenas o schema. **NAO inclui** dependencias em outros schemas. FK de `box_001.boxcore_student.identity_id` para `public.student_identity_studentidentity.id` vira referencia orfa no dump.

**Resultado**: dump de tenant isolado **nao restaura sozinho**. Tentativa retorna erro "relation public.student_identity_studentidentity does not exist".

**Estrategia obrigatoria**:

| Cenario | Comando |
|---|---|
| Backup full diario | `pg_dump --format=custom --file=/backups/$(date).dump octobox` (DB inteira) |
| Restore um tenant inteiro (ex.: corrupcao em box_007) | 1) `pg_restore --schema=public` (Identity + Membership records do box_007); 2) `DROP SCHEMA box_007 CASCADE`; 3) `pg_restore --schema=box_007`. |
| Backup de offboarding (cliente saindo) | `pg_dump --schema=box_007 --schema=public --table=public.student_identity_*` para um arquivo. Cliente pode importar em sua propria infra (com adaptacoes). |
| Backup ponto-no-tempo (PITR) | WAL archiving + base backup. **Nada muda com schema-per-tenant** — PITR opera em DB inteira. |

**Adendo SQL-11 (Sprint 5)**: criar `docs/runbook/backup-restore-multi-tenant.md` com 4 cenarios acima documentados.

### 14.8 VACUUM e autovacuum

**Evidencia (PG defaults)**:
```
autovacuum_max_workers = 3
autovacuum_naptime = 1min
autovacuum_vacuum_threshold = 50
autovacuum_vacuum_scale_factor = 0.2
```

**Inferencia para 20 schemas**:
- Cada schema tem ~30 tabelas → 600 tabelas no DB.
- Autovacuum daemon agendar visitas baseado em `pg_stat_all_tables.n_dead_tup`.
- Com 3 workers e 600 tabelas, **cada tabela e visitada com delay maior**. Tabelas hot (Payment, Attendance) podem acumular bloat.

**Adendo SQL-12 (Sprint 5/operacao)**:
```ini
# postgresql.conf — quando atingir 20+ schemas
autovacuum_max_workers = 6        # 2x default
autovacuum_naptime = 30s          # mais agressivo
maintenance_work_mem = 512MB      # workers vacuum mais rapidos
```

E monitorar `pg_stat_all_tables.last_autovacuum` por schema. **Adendo SQL-13 (Sprint 4)**: query de healthcheck que retorna tabelas com `last_autovacuum > 24h ago` → alert.

### 14.9 Tipo de dados — slug max_length inconsistente

**Evidencia**: 
- `student_identity/models.py:81`: `box_root_slug = CharField(max_length=64)` (codigo atual).
- V2 §2 linha 149: `slug = SlugField(max_length=63)` (proposta para `control.Box`).
- V2 §2 nota: "Postgres aceita ate 63 chars com prefix `box_`" — afirmacao **incorreta**.

**Verdade tecnica**: `NAMEDATALEN` em Postgres = 64. Identifier max **e 63 chars** (NAMEDATALEN-1 para terminator). Schema name `box_xxx` precisa caber em 63 → `xxx` max **59 chars**.

**Adendo SQL-14 (Sprint 1)**: corrigir V2 §2:
```python
# control/models.py — Box
class Box(TenantMixin):
    slug = models.SlugField(max_length=59, unique=True, db_index=True)
    # ↑ era 63, mas schema_name = f'box_{slug}' precisa <= 63 chars
    # ↑ regex ja limita a 56, mas explicitar limite no campo evita bug futuro
```

E migration de `box_root_slug` (max_length=64) para `box_id` (FK) — quando dropar `box_root_slug`, validar que nenhum slug em uso excede 59 chars.

### 14.10 Query observability por tenant

**Evidencia**: `pg_stat_statements` agrega queries por `queryid` (hash da query normalizada). A mesma query (`SELECT * FROM boxcore_student WHERE id=?`) gera **mesmo queryid** em `box_001` e `box_002` porque o schema e parte do search_path, nao do SQL. Resultado: nao da pra saber qual tenant gerou query lenta.

**Mitigacao**: setar `application_name` por tenant via parametro de conexao Postgres:

```python
# control/middleware.py — TenantBySessionMiddleware
def set_tenant_with_observability(self, box):
    from django.db import connection
    connection.set_tenant(box)
    with connection.cursor() as cur:
        cur.execute(f"SET application_name = 'octobox:tenant:{box.schema_name}'")
```

E configurar `log_line_prefix` em `postgresql.conf`:
```
log_line_prefix = '%t [%p] [app=%a] [user=%u] '
log_min_duration_statement = 200ms
```

Resultado: log do Postgres mostra `[app=octobox:tenant:box_007] SELECT ...` para queries lentas, permitindo debug por tenant.

**Adendo SQL-15 (Sprint 4)**: implementar `set_application_name` no middleware. Documentar em runbook.

### 14.11 Resumo de adendos SQL para V3

| # | Adendo | Sprint | Esforco |
|---|---|---|---|
| SQL-1 | Validar `search_path` apos `set_tenant` (test em DEV) | 0 | 0.1d |
| SQL-2 | `provision_box` roda `ANALYZE` apos seed | 1 | 0.1d |
| SQL-3 | Migration de promote-to-shared com validacao COUNT(*) antes de drop | 2 | 0.5d |
| SQL-4 | `Box.stripe_subscription_id` vira `unique=True` | 1 | 0.05d |
| SQL-5 | `Membership` partial index `(user) WHERE is_primary_box=True` | 1 | 0.1d |
| SQL-6 | `BoxProvisioningEvent` partial index `(box, step) WHERE status='ok'` | 1 | 0.1d |
| SQL-7 | Backfill de `Student.identity_id` em batches de 500 | 2 | 0.5d |
| SQL-8 | `pg_repack` apos drop de colunas em janela de manutencao | 5 | 0.25d |
| SQL-9 | `TenantBySessionMiddleware` reset search_path no inicio | 1 | 0.25d |
| SQL-10 | Documentar PgBouncer = session pooling apenas (Fase 2) | 5 | 0.1d |
| SQL-11 | Runbook `backup-restore-multi-tenant.md` com 4 cenarios | 5 | 0.5d |
| SQL-12 | Tunar autovacuum em prod (max_workers=6, naptime=30s) | 5 | 0.1d |
| SQL-13 | Healthcheck monitora `last_autovacuum > 24h` | 4 | 0.25d |
| SQL-14 | Box.slug max_length=59 (nao 63) | 1 | 0.05d |
| SQL-15 | `set application_name` por tenant para observability | 4 | 0.25d |
| **Total** | | | **~3.3 dias extras** |

**Esforco acumulado V3 (incluindo §13)**:
- V2 base: 18-24 dias
- §13 Software Architecture Chief: +5 dias
- §14 SQL Architect: +3.3 dias
- **Total V3: 26-32 dias-dev** (5.5-6.5 semanas calendar)

### 14.12 Conclusao SQL

V2 + §13 cobrem arquitetura macro. §14 adiciona o "como o Postgres realmente vai responder" sob carga. Os 15 adendos SQL nao mudam topologia — endurecem migrations, fixam bugs latentes (search_path heritage, slug max_length), e adicionam observabilidade necessaria para debugar 20+ tenants em prod.

**Tres alertas operacionais que merecem destaque**:

1. **search_path heritage** (§14.6): bug silencioso, vazamento de dados sem stack trace. Adendo SQL-9 e obrigatorio antes do primeiro tenant pago.
2. **Backfill de identity_id em prod** (§14.5): UPDATE single-statement bloqueia escritas por minutos. Adendo SQL-7 (batched) e obrigatorio se prod tem >5000 students.
3. **Slug max_length=63** (§14.9): bug iminente quando alguem cadastrar box com slug de 60 caracteres. Adendo SQL-14 (max=59) e fix de 5 minutos que evita debug de 2 horas.

**Recomendacao final SQL**: aplicar V3 com os adendos §13 + §14 antes de Sprint 0. Custo extra (~8 dias) e baixo comparado ao custo de descobrir problemas em prod com tenants pagantes ja onboarded.

---

## 15. Ordem de execucao priorizada (criticos primeiro)

> Decisao do usuario: priorizar os adendos criticos antes de avancar. Esta secao define a ordem de ataque dos 26 adendos (V2 + §13 + §14), agrupados por urgencia.

### 15.1 Tier 1 — CRITICOS (devem entrar em Sprint 0-1, ~2 dias)

Bugs latentes que vazariam dados ou criariam estado inconsistente em prod. Nao avancar sem cobrir todos.

| # | Adendo | Sprint | Fix | Justificativa |
|---|---|---|---|---|
| C1 | **search_path heritage** (SQL-9) — `TenantBySessionMiddleware` reset search_path no inicio | 1 | 0.25d | Vazamento silencioso entre tenants se conexao idle herda schema do request anterior. Sem stack trace. Impossivel debugar depois. |
| C2 | **WebhookIdempotencyMiddleware** (A1) — `connection.set_schema_to_public()` antes da query | 1 | 0.5d | Idempotencia de webhook quebra se middleware roda em schema errado. Eventos duplicados ou perdidos. |
| C3 | **Slug max_length=59** (SQL-14) — corrigir `Box.slug = SlugField(max_length=59)` | 1 | 0.05d | `box_<slug>` > 63 chars → Postgres rejeita CREATE SCHEMA → provisioning falha em runtime. 5min de fix evita 2h de debug. |
| C4 | **`activate_pending_signup` em 3 fases** (A2) — sem outer atomic envolvendo DDL | 2 | 0.5d | Schema orfao se migrations falham mid-way. User+Box rollback mas schema persiste. |
| C5 | **Backfill `Student.identity_id` batched** (SQL-7) — UPDATE em batches de 500 | 2 | 0.5d | UPDATE single-statement bloqueia escritas por minutos em prod com 5000+ students. |
| C6 | **Email idempotente** (A5) — `PendingSignup.magic_link_sent_at` | 2 | 0.25d | Webhook duplicado manda email 2x. Confunde Owner. UX critica no primeiro contato. |
| C7 | **Runbook de rollback** (A10, parcial) — soft-block + procedimento de extracao | 3 | 0.5d | Apos Sprint 5+7d, hard rollback e one-way. Sem runbook, qualquer incidente vira crise. |

**Total Tier 1**: ~2.5 dias dentro de Sprint 1-3 (absorvido nos sprints existentes).

### 15.2 Tier 2 — IMPORTANTES (Sprint 1-2 quando der, ~1.5 dia)

Reduzem risco operacional e melhoram observability. Nao bloqueiam mas evitam dor.

| # | Adendo | Sprint | Fix | Beneficio |
|---|---|---|---|---|
| I1 | `Box.stripe_subscription_id` unique=True (SQL-4) | 1 | 0.05d | 1 sub Stripe = 1 Box. Race condition impossibilita duplicar. |
| I2 | Membership partial index (SQL-5) | 1 | 0.1d | Query do middleware (filter por `is_primary_box=True`) 50% mais rapida. |
| I3 | BoxProvisioningEvent partial index (SQL-6) | 1 | 0.1d | Recovery query em provision_box `WHERE status='ok'` mais eficiente. |
| I4 | `provision_box` chama ANALYZE (SQL-2) | 1 | 0.1d | Primeiro request apos provisioning sem plano ruim. |
| I5 | `assert provision_box em public` (A8) | 1 | 0.1d | Bloqueia bug obvio: chamar provision_box dentro de schema_context. |
| I6 | Lock em PaymentWebhookEvent (A4) | 3 | 0.5d | Webhook duplicado em concorrencia nao chama handler 2x. |
| I7 | Lock em BoxProvisioningEvent (A7) | 2 | 0.25d | reprovision_box concorrente com retry automatico nao corrompe state. |
| I8 | Validar Box.ACTIVE no accept invite (A6) | 2 | 0.25d | Aluno nao entra em schema que ainda esta PROVISIONING. |
| I9 | `set application_name` por tenant (SQL-15) | 4 | 0.25d | Logs de queries lentas mostram qual tenant. Debug em prod fica viavel. |

**Total Tier 2**: ~1.7 dias.

### 15.3 Tier 3 — OPERACIONAIS (Sprint 4-5, ~3.3 dias)

Hardening de produção e operação. Pode ser tratado em Sprint 5 ou pos-rollout sem bloquear go-live.

| # | Adendo | Sprint | Fix | Beneficio |
|---|---|---|---|---|
| O1 | `cleanup_orphan_users` command (A3) | 2 | 0.5d | Limpa Users criados antes de Box falhar. |
| O2 | Drenar fila de jobs em Sprint 5 deploy (A9) | 5 | 0.5d | Jobs em flight nao quebram apos schema migration. |
| O3 | `Box.status=SUSPENDED` policy + soft-block (A10, completar) | 3 | 0.5d | Define UX de Owner com pagamento atrasado. |
| O4 | Benchmark `migrate_schemas` (A11) | 5 | 0.5d | Mede tempo real de deploy com 20 schemas. |
| O5 | Validar search_path em DEV (SQL-1) | 0 | 0.1d | Confirma que `django-tenants` configura `box_xxx, public` (nao apenas `box_xxx`). |
| O6 | Migration de promote-to-shared com COUNT(*) (SQL-3) | 2 | 0.5d | Valida que dados copiaram OK antes de droppar tabelas legadas. |
| O7 | `pg_repack` apos drop columns (SQL-8) | 5 | 0.25d | Recupera espaco em disco apos migrations destrutivas. |
| O8 | PgBouncer doc (SQL-10) | 5 | 0.1d | Quando ativar PgBouncer em Fase 2, evita modo errado. |
| O9 | Runbook backup-restore multi-tenant (SQL-11) | 5 | 0.5d | 4 cenarios documentados (full/tenant/offboarding/PITR). |
| O10 | Tunar autovacuum em prod (SQL-12) | 5 | 0.1d | `max_workers=6, naptime=30s` quando atingir 20 schemas. |
| O11 | Healthcheck monitora autovacuum (SQL-13) | 4 | 0.25d | Alert se tabela passa 24h sem vacuum. |

**Total Tier 3**: ~3.85 dias.

### 15.4 Cronograma final V3

| Sprint | Foco original | + Tier 1 (criticos) | + Tier 2 (importantes) | + Tier 3 (operacionais) | Total |
|---|---|---|---|---|---|
| Sprint 0 | 2-3d | — | — | +0.1d (O5) | 2-3d |
| Sprint 1 | 3-4d | +0.8d (C1,C2,C3) | +0.45d (I1-I5) | — | 4.25-5.25d |
| Sprint 2 | 3-4d | +1.25d (C4,C5,C6) | +0.5d (I7,I8) | +1d (O1,O6) | 5.75-6.75d |
| Sprint 3 | 2-3d | +0.5d (C7) | +0.5d (I6) | +0.5d (O3) | 3.5-4.5d |
| Sprint 4 | 3-4d | — | +0.25d (I9) | +0.25d (O11) | 3.5-4.5d |
| Sprint 5 | 2-3d | — | — | +1.85d (O2,O4,O7-O10) | 3.85-4.85d |
| **Total** | **15-21d** | **+2.55d** | **+1.7d** | **+3.7d** | **~23-30d** |

(estimativa V3 anterior era 26-32; ordenacao por tier reduz ligeiramente porque Tier 3 tem alguns dias ja absorvidos em buffer.)

### 15.5 Gates de avanco

Criterios objetivos antes de avancar entre tiers:

- **Sprint 1 → 2**: Tier 1 itens C1, C2, C3 implementados com testes em DEV. Boundary test `test_search_path_heritage_cleared_between_requests` passa.
- **Sprint 2 → 3**: Tier 1 itens C4, C5, C6 + boundary test e2e Early Adopter completo (signup → activate → dashboard isolado).
- **Sprint 4 → 5**: Tier 1 item C7 documentado em `docs/runbook/`. Gate `boundary tests passam 3x consecutivas em CI`.
- **Sprint 5 → produzir clientes pagantes**: 24h de observacao com `box_pilot` + 1 tenant pago.

### 15.6 Itens descartados/adiados para Fase 2

Adendos que foram identificados mas decididos como Fase 2 (apos 100 boxes):
- F4 (Box.status race window): aceitavel em Fase 1, fix complexo demais para o ganho.
- C3 contrato (StudentSession invalidation): cookie expira naturalmente; OK para Fase 1.
- Subdomain identification: confirmado §1 decisao.

**Conclusao 15**: V3 com priorizacao por tier mantem foco nos 7 bugs criticos sem aumentar significativamente o calendar time. Os 3 tiers podem ser executados sequencialmente dentro dos 6 sprints existentes — nao precisa adicionar sprint extra.
