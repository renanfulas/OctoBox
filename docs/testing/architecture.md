# Arquitetura de Testes — OctoBox

> **Status:** vivo — atualizar quando convenção mudar
> **Última revisão:** 2026-05-28
> **Doc complementar:** [README.md](./README.md) (como rodar) · [e2e-guide.md](./e2e-guide.md) (Playwright)
> **Autoridade:** este documento define **o que é teste válido** em OctoBox; conflitos com outros guias resolvem aqui.

---

## Princípio diretor

> Um teste que passa apenas em SQLite local mas não roda em PostgreSQL **não protege a produção**. PostgreSQL é o caminho padrão da suite; SQLite fica só como escape legado explícito.

Três regras absolutas:

1. **Teste verde sem assert real é dívida**, não cobertura.
2. **Skip silencioso é bug**, não exceção.
3. **Mock do SUT é fraude**, não isolamento.

---

## Status de implementação (2026-05-28)

| Sprint | Fase | Status | Entregas |
|---|---|---|---|
| Sprint 1 | Fase 0 — Estancar | ✅ Concluído | Markers registrados, `-ra`, `OCTOBOX_REQUIRE_POSTGRES`, age policy do broken-tests |
| Sprint 2 | Fase 1 — Paridade | ✅ Concluído | `provision_test_tenants.sh`, job `tenant-boundary` no CI |
| Sprint 3 | Fase 4 — Gates | ✅ Concluído | `ci-gates.yml` (migration check + markers lint) |
| Sprint 4 | Fase 3 — Cobertura inicial | ✅ Concluído | `student_identity/use_cases` (18) + `control/services` (17, refeito no Sprint 9) |
| Sprint 5 | Fase 3 — `signup/services` | ✅ Concluído | 38 testes: `verify_magic_token` (6 branches) + `activate_pending_signup` (3 branches) + Stripe |
| Sprint 6 | Fase 3 — `auditing/services` | ✅ Concluído | 14 testes: `_ensure_tenant_for_audit_write` (7 branches) + signals (refeito no Sprint 9) |
| Sprint 7 | Fase 3 — `students/use_cases` | ✅ Concluído | 25 testes: use_cases + defaults comerciais |
| Sprint 8 | Fase 3 — `student_identity` views/OAuth | ✅ Concluído | 13 testes: rate limit + anomaly + OAuth callback |
| Sprint 9 | Fase 3 — Refazer control + auditing para PostgreSQL | ✅ Concluído | marker `public_schema` no conftest; 31 testes validados em PostgreSQL real **e** SQLite |

> **✅ Resolvido (2026-05-29) — `test_control_services.py` e `test_auditing_services.py`.**
> Foram removidos no #108 por falharem em PostgreSQL (validados só em SQLite — caíram no anti-pattern AP5 deste doc). **Refeitos no Sprint 9** e validados em **PostgreSQL real** (cluster local na 5433) além de SQLite:
> - Novo marker `@pytest.mark.public_schema` (conftest): classe roda no schema `public`, opt-out do `schema_context` autouse — necessário para `provision_box`/`archive_box`.
> - `patch('django.db.connection')` (em vez do frágil `patch.object(connection, ..., create=True)`) para controlar `schema_name`/`set_tenant` sem tocar o wrapper do django-tenants.
> - Usernames únicos (uuid) + neutralização do box de fundo do fixture `test_tenant`.

**Suite atual:** PostgreSQL é o baseline operacional. `control` (17) + `auditing` (14) já foram confirmados em PostgreSQL real.

**Findings descobertos nos Sprints 5–8:** 4 itens — FIND-001 fechado (não-bug), FIND-002/003/004 corrigidos. Relatório em `tests/sprint-5-8-findings.md`.

---

## Estrutura atual

### Mapa de diretórios

```
OctoBox/
├── conftest.py                          # Fixtures globais (tenant, schema_context, membership)
├── pytest.ini                           # Markers, addopts, ignores
├── config/settings/test.py              # Settings de teste (PostgreSQL default; SQLite só com flag legada)
│
├── tests/                               # Suite centralizada — 74 arquivos
│   ├── test_tenant_boundary.py          # B1–B12: isolamento multi-tenant
│   ├── test_*.py                        # Unit + integration
│   └── e2e/
│       ├── conftest.py                  # Fixtures Playwright
│       └── test_*.py                    # E2E browser
│
├── boxcore/tests/                       # 33 arquivos — testes do núcleo
├── access/tests/                        # 4 arquivos — auth/permissões
├── operations/domain/tests/             # 1 arquivo — domínio operations
│
├── student_app/tests.py                 # ⚠️ Legado single-file
├── student_identity/tests.py            # ⚠️ Legado single-file
├── onboarding/tests.py                  # ⚠️ Legado single-file
│
└── test_*.py (raiz)                     # ⚠️ Scripts ad-hoc ignorados no pytest.ini
    ├── test_csv_injection.py
    ├── test_whale.py
    ├── test_fire.py
    ├── test_rate_limit.py
    └── test_whatsapp_webhook.py
```

### Inventário numérico

| Categoria | Arquivos | Status |
|---|---|---|
| `tests/` (centralizado) | 74 | ✅ Convenção atual |
| `boxcore/tests/` | 33 | ✅ Convenção atual |
| `access/tests/` | 4 | ✅ Convenção atual |
| `operations/domain/tests/` | 1 | ✅ Convenção atual |
| Legado single-file (3 apps) | 3 | ⚠️ Migrar para `<app>/tests/` |
| Scripts raiz ignorados | 5 | ⚠️ Mover para `scripts/` ou apagar |
| **Total auditável** | **115** | |

### Snapshot legado em SQLite local (2026-05-28)

- `tests/`: **344 pass / 0 fail / 5 skipped** (boundary tests B1–B7 — esperado, exigem PostgreSQL)
- `access/tests/`: **10 pass / 0 fail**
- `boxcore/tests/`: histórico de segfault na execução completa — em investigação
- E2E (`tests/e2e/`): ignorada por default, roda em job dedicado

---

## Camadas de teste — especificação por tipo

Toda função de teste em OctoBox pertence a **exatamente uma** das camadas abaixo. A camada determina o contrato.

### L1 — Unit

**Contrato:**
- Testa uma função/método isolado
- Zero I/O (sem DB, sem HTTP, sem filesystem)
- Roda em < 50ms
- Não usa Django TestCase — usa `SimpleTestCase` ou pytest funcional
- Mocks permitidos APENAS para dependências externas ao módulo testado

**Assinatura típica:**
```python
class FeatureCalculatorTest(SimpleTestCase):
    def test_calculates_X_when_Y_is_Z(self):
        result = calculate(input=Y_eq_Z)
        self.assertEqual(result, expected_X)
```

**Veto:** sem `@pytest.mark.django_db`, sem `Client()`, sem `self.client`.

---

### L2 — Integration

**Contrato:**
- Exercita 2+ camadas reais (view + service + ORM, ou view + middleware)
- DB real (transaction rollback automático)
- Externo SEMPRE mockado (Stripe, WhatsApp, Mailchimp) com `responses` ou `unittest.mock`
- Roda em < 500ms por teste

**Assinatura típica:**
```python
class SignupFlowIntegrationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(...)

    def test_signup_creates_user_and_membership(self):
        response = self.client.post(reverse('signup'), data={...})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Membership.objects.filter(user=self.user).exists())
```

**Veto:** sem chamadas HTTP reais para domínios externos.

---

### L3 — Tenant Boundary (B1–B12)

**Contrato:**
- Requer PostgreSQL + `django-tenants` + schemas `box_test_a`, `box_test_b` provisionados
- Marker obrigatório: `@tag('tenant', 'isolation', 'requires-postgres')`
- Guard obrigatório no início do método:
  ```python
  from django.db import connection
  if connection.vendor != 'postgresql':
      self.skipTest('Requer PostgreSQL com django-tenants')
  ```
- Skip apenas por **incompatibilidade de ambiente**, nunca por exceção genérica

**Veto explícito:**
- ❌ `except Exception: self.skipTest(...)` — converte bug real em verde
- ❌ Skip por `ImportError` sozinho — não cobre `AttributeError` em runtime

**Localização canônica:** `tests/test_tenant_boundary.py` (não dispersar por apps).

---

### L4 — E2E (Playwright)

**Contrato:**
- Roda contra `live_server` Django + browser real
- Marker `@pytest.mark.e2e`
- Ignorado por default no `pytest.ini` — só roda com `pytest tests/e2e/ --create-db --migrations`
- Fixtures em `tests/e2e/conftest.py`
- Cobre **happy paths críticos**, não regressão exaustiva

**Veto:** sem teste de validação de campo individual em E2E — isso é L2.

---

### L5 — Contract / Snapshot

**Contrato:**
- Serialização de API permanece estável entre releases
- Usa `syrupy` ou snapshot manual versionado no repo
- Quebra de snapshot exige revisão humana, não auto-update

**Exemplo:** `tests/test_dashboard_snapshot_serialization.py`

---

### L6 — Performance / Benchmark

**Contrato:**
- Usa `pytest-benchmark`
- Threshold definido como `--benchmark-max-time=0.2` (200ms p95)
- Quebra de baseline > 2x falha o CI
- Localização: `tests/test_*_latency_benchmark.py`

---

## Convenções obrigatórias

### Nomenclatura

| Elemento | Padrão | Exemplo |
|---|---|---|
| Arquivo | `test_<feature>.py` | `test_tenant_boundary.py` |
| Classe | `<Feature><Cenário>Test` | `B1CrossTenantStudentIsolationTest` |
| Método | `test_<expectativa>_<condição>` | `test_student_objects_scoped_to_current_schema` |
| Marker | kebab-case via `@tag` ou `pytest.mark` | `@tag('tenant', 'requires-postgres')` |

### Fixtures

**Permitido:**
- `conftest.py` por diretório (escopo local)
- Fixture com escopo `function` (default) — isolamento garantido
- Fixture com escopo `session` APENAS para setup imutável (criar tenant, registrar Box)

**Proibido:**
- Fixture com escopo `module` ou `class` que muta estado
- Fixture autouse global sem comentário `# POR QUE EXISTE`

### Assertions

**Permitido:**
```python
self.assertEqual(response.status_code, 200)               # exato
self.assertContains(response, 'texto-específico-único')   # conteúdo específico
self.assertTrue(Membership.objects.filter(...).exists())  # existência checada
```

**Proibido (assert fraco):**
```python
self.assertIn(response.status_code, [200, 302])  # ❌ sucesso e redirect são DIFERENTES
self.assertContains(response, 'error')           # ❌ "error" é genérico demais
self.assertIsNotNone(result)                     # ❌ Mock() também não é None
```

### Mocks

**Permitido:**
```python
@patch('integrations.stripe.client.charge', autospec=True)  # ✅ autospec valida assinatura
def test_X(self, mock_charge):
    mock_charge.return_value = {'id': 'ch_test', 'status': 'succeeded'}
```

**Proibido:**
```python
@patch('signup.services.create_user')        # ❌ mockou a função sob teste
def test_signup_creates_user(self, mock_create):
    ...                                       # Está testando o quê?

m = Mock()                                    # ❌ sem autospec — aceita qualquer assinatura
```

### Skips

**Permitido:**
```python
from django.db import connection
if connection.vendor != 'postgresql':
    self.skipTest('Requer PostgreSQL com django-tenants')  # ✅ condição clara

@pytest.mark.skip(reason='OCT-1234: bloqueado por bug X')   # ✅ com ticket
```

**Proibido:**
```python
try:
    schema_context('box_a').__enter__()
except Exception as exc:                                    # ❌ esconde bug real
    self.skipTest(f'erro: {exc}')

@pytest.mark.skip                                           # ❌ sem motivo
```

---

## Matriz de execução

| Job | Banco | Quando roda | Tempo alvo | Comando |
|---|---|---|---|---|
| `unit-pg` | PostgreSQL | Todo push | < 60s | `pytest -m "not requires_postgres and not e2e"` |
| `integration-pg` | PostgreSQL | Todo PR | < 3min | `pytest --create-db --migrations` |
| `tenant-pg` | PG + tenants provisionados | Todo PR | < 90s | `pytest tests/test_tenant_boundary.py -m requires_postgres` |
| `e2e-playwright` | PostgreSQL | Nightly + tag `e2e` | < 10min | `pytest tests/e2e/ --create-db --migrations` |
| `migrations-full` | PostgreSQL | Nightly | < 3min | `pytest --migrations --create-db boxcore/tests/test_migrations.py` |
| `benchmark` | PostgreSQL | Weekly | < 5min | `pytest --benchmark-only --benchmark-compare` |

### Markers registrados (obrigatório em `pytest.ini`)

```ini
markers =
    e2e: Testes Playwright end-to-end
    tenant: Testes que envolvem multi-tenant
    isolation: Testes de isolamento de dados
    requires_postgres: Exige backend PostgreSQL com django-tenants
    slow: Roda em > 1s
    flaky: Conhecido como instável (exige ticket vinculado)
```

---

## Anti-patterns proibidos

Lista canônica. Qualquer PR que introduza um destes deve ser rejeitado em review.

### AP1 — Skip silencioso por exceção genérica

```python
# ❌ PROIBIDO
try:
    do_something_with_postgres()
except Exception as exc:
    self.skipTest(str(exc))
```

**Por quê:** transforma qualquer bug (NullPointerException, regressão de API, erro de migração) em "amarelo no CI" — invisível.

**Correção:** check de ambiente explícito ANTES do try, e raise no except.

---

### AP2 — Mock do System Under Test

```python
# ❌ PROIBIDO
@patch('signup.services.create_user')
def test_signup_creates_user(self, mock_create):
    response = self.client.post('/signup/', data={...})
    mock_create.assert_called_once()  # Você testou que mockou. Só.
```

**Por quê:** não exercita código real — só prova que o mock foi chamado.

**Correção:** mockar apenas dependências externas (Stripe, e-mail), não o serviço sob teste.

---

### AP3 — Assert permissivo demais

```python
# ❌ PROIBIDO
self.assertIn(response.status_code, [200, 201, 302])
```

**Por quê:** sucesso (200), criação (201) e redirect (302) têm semânticas diferentes. Aceitar qualquer um esconde mudança de comportamento.

**Correção:** assert exato. Se a rota REALMENTE pode retornar dois códigos, há dois testes — um por código.

---

### AP4 — Teste sem assert

```python
# ❌ PROIBIDO
def test_signup_works(self):
    response = self.client.post('/signup/', data={...})
    # FIM — sem assert
```

**Por quê:** prova apenas que a chamada não levanta exceção. View pode retornar 500 e o teste passa.

**Correção:** mínimo de 1 assert sobre `status_code` + 1 sobre estado pós-condição (DB, sessão, redirect target).

---

### AP5 — Backend mismatch

```python
# ❌ PROIBIDO
def test_schema_isolation(self):
    with schema_context('box_a'):  # Quebra em SQLite
        ...
```

**Por quê:** depende silenciosamente de PostgreSQL. Em SQLite levanta `AttributeError` cru.

**Correção:** guard `connection.vendor != 'postgresql'` + skipTest com motivo.

---

### AP6 — Mock sem autospec

```python
# ❌ PROIBIDO
mock_service = Mock()
mock_service.charge(amount=100)  # E se charge() agora exigir currency?
```

**Por quê:** Mock aceita qualquer assinatura. Refactor da função real não quebra o teste.

**Correção:** `Mock(spec=ServiceClass)` ou `@patch(..., autospec=True)`.

---

### AP7 — Tempo não-determinístico

```python
# ❌ PROIBIDO
def test_session_expires_after_24h(self):
    session = Session.objects.create(expires_at=now() + timedelta(hours=24))
    # Roda à meia-noite: passa. Roda 1s antes da meia-noite: falha aleatória.
```

**Correção:** `@freeze_time('2026-01-01 12:00:00')` em todo teste sensível a relógio.

---

### AP8 — Order dependence

```python
# ❌ PROIBIDO
class TestA(TestCase):
    def test_creates(self):
        self.obj = SomeModel.objects.create(...)
    def test_uses(self):
        # depende de self.obj — quebra se rodar isolado
        self.assertEqual(self.obj.field, ...)
```

**Correção:** cada teste cria seu estado em `setUp` ou fixture.

---

## Plano de hardening — fases com critérios

### Fase 0 — Estancar (3–5 dias) **[bloqueante]**

**Objetivo:** parar de gerar falsos positivos.

| Tarefa | Critério de aceite | Owner |
|---|---|---|
| Investigar segfault da suite completa | Bisect com `pytest --forked`; ADR com causa identificada | Backend |
| Registrar markers no `pytest.ini` | Zero `PytestUnknownMarkWarning` na saída | Backend |
| Adicionar `OCTOBOX_REQUIRE_POSTGRES=1` em CI | Skip de boundary tests vira ERROR no CI | DevOps |
| Visibilidade de skips: rodar com `-ra` | CI imprime sumário; falha se skips > 30 | DevOps |
| Formato auditável para `broken-tests.txt` | Cada linha tem `owner=@x since=YYYY-MM-DD ticket=#NNN` | Backend |

**Definition of Done da fase:** suite roda sem segfault no CI; skips são intencionais e datados.

---

### Fase 1 — Paridade prod (1–2 semanas)

**Objetivo:** local ≡ produção em comportamento, não em velocidade.

| Tarefa | Critério de aceite |
|---|---|
| Matriz de CI com 4 jobs (unit/integration/tenant/e2e) | Todos rodam em todo PR exceto e2e (nightly) |
| `docker-compose.postgres.yml` com PG + Redis | `docker compose -f docker-compose.postgres.yml up -d && pytest -m requires_postgres` funciona |
| Script `scripts/provision_test_tenants.sh` | Idempotente; cria `box_test_a` e `box_test_b` |
| Política de idade no `broken-tests.txt` | CI falha se algum item > 30 dias |

---

### Fase 2 — Determinismo (1 semana)

| Categoria | Solução | Aceite |
|---|---|---|
| Tempo | `freezegun` autouse opcional + explicit | Zero `datetime.now()` em data de teste |
| HTTP externo | `responses` lib + cassettes versionadas | Zero requests reais (verificável via mitmproxy no CI) |
| Random | `random.seed(0)` no conftest | Roda 10× consecutivas, mesmo resultado |
| Order | `pytest-randomly` no CI | Suite passa em ordem aleatória |
| Cache | `cache.clear()` autouse | Sem leakage entre testes |

---

### Fase 3 — Cobertura de paths críticos (3–4 semanas)

**Não medir % — medir paths.** Cada sprint tem branches específicas identificadas em auditoria forense de 2026-05-28.

#### Sprint 5 — `signup/services.py` (path de monetização)

**Por que primeiro:** 0 testes atuais. Quebra silenciosa bloqueia receita.

| Função | Branches a cobrir | Arquivo:Linha |
|---|---|---|
| `verify_magic_token` | 6 branches: `token-vazio`, `token-expirado`, `token-invalido`, `pending-nao-encontrado`, `ja-ativado`, `status-invalido` | `signup/services.py:234` |
| `activate_pending_signup` | `username-obrigatorio` (vazio), `UsernameTakenError` (colisão), Owner Group não existe | `signup/services.py:324` |
| `create_checkout_session` | plano desconhecido (`ValueError`), `StripeNotConfiguredError` (sem env var), erro da API Stripe | `signup/services.py:75` |
| `mark_pending_signup_paid` | webhook duplicado (idempotência), update parcial de stripe_customer_id, status já `ACTIVATED` | `signup/services.py:187` |
| `query_stripe_session_status` | `secret_key` vazio, `ImportError` do stripe, exceção da API → retorna `None` | `signup/services.py:140` |

**Mock obrigatório:** `responses` lib para Stripe HTTP. Nunca chamar `stripe.checkout.Session.create()` de verdade.

#### Sprint 6 — `auditing/services.py` (trilha regulatória)

**Por que importa:** auditoria perdida em schema `public` viola conformidade — atualmente silencioso.

| Função | Branches a cobrir | Arquivo:Linha |
|---|---|---|
| `_ensure_tenant_for_audit_write` | 7 branches: já em tenant, membership primária resolve, pilot fallback (1 box ativa), nenhuma strategy funciona | `auditing/services.py:29` |
| `async_log_audit_event` | actor `None` em PUBLIC_SCHEMA, falha de `_ensure_tenant_for_audit_write` retorna `None` sem explodir | `auditing/services.py:76` |
| Signal handlers | `user_logged_in` e `user_logged_out` chamam `log_audit_event` corretamente | `auditing/signals.py:23,36` |

**Teste obrigatório:** rodar dentro de `schema_context('public')` + sem actor + verificar que não levanta `ProgrammingError`.

#### Sprint 7 — `students/application/use_cases.py` (dados comerciais)

**Por que importa:** student criado sem enrollment = dados inconsistentes. Rollback nunca testado.

| Função | Branches a cobrir | Arquivo:Linha |
|---|---|---|
| `execute_create_student_quick_use_case` | sucesso completo, falha em `enrollment_sync.sync` → audit NÃO chamado, falha em `intake_sync.sync` → student persistido mas resultado parcial | `students/application/use_cases.py:48` |
| `execute_update_student_quick_use_case` | mudanças comerciais (`changed_fields`) registradas no audit, branches de erro de sync | `students/application/use_cases.py:73` |
| `resolve_enrollment_sync_defaults` | 7 defaults vazios → especialmente `base_amount = 0` (cobrança zerada), `billing_strategy='single'`, `installment_total=1` | `students/domain/enrollment_lifecycle.py:60` |

**Mock obrigatório:** todos os ports (`UnitOfWorkPort`, `StudentWriterPort`, `StudentEnrollmentSyncPort`, `StudentIntakeSyncPort`, `StudentQuickAuditPort`) via `create_autospec`.

#### Sprint 8 — `student_identity` views e OAuth (abuso e edge cases)

| Função | Branches a cobrir | Arquivo:Linha |
|---|---|---|
| `StudentInvitationOperationsView.post` | rate limit excedido → `maybe_emit_student_anomaly_alert` é chamado, score threshold > limite | `student_identity/staff_views.py:199` |
| `finalize_student_oauth_callback` | fluxos especiais (reativação, transfer entre boxes), rate limit no callback, device fingerprint | `student_identity/oauth_actions.py:68` |

#### Sprint 9 — Restantes

| Tier | Módulo | Cobertura mínima |
|---|---|---|
| 1 | `integrations/stripe/` webhook | Idempotência, falha de pagamento, cancelamento |
| 1 | `access/` middleware | Membership ativa exigida (B8 já cobre) |
| 2 | `student_app/` signals | post_save/post_delete + side effects |
| 2 | `control/archive_box` | Renomeação de schema + audit (requer PostgreSQL) |
| 3 | API v1 | Snapshot tests para todas as respostas |
| 3 | Dashboard/finance | Benchmark regression gate |

---

### Top 10 testes — ROI máximo (consolidado da auditoria forense)

Lista priorizada por **risco de regressão silenciosa em produção**:

| # | Teste | Linhas em risco | Sprint |
|---|---|---|---|
| 1 | `verify_magic_token` com 6 branches | 50 | 5 |
| 2 | `activate_pending_signup` com colisão de username | 40 | 5 |
| 3 | `_ensure_tenant_for_audit_write` em PUBLIC_SCHEMA | 153 | 6 |
| 4 | `execute_create_student_quick_use_case` com rollback | 70 | 7 |
| 5 | `create_checkout_session` com Stripe não configurado | 60 | 5 |
| 6 | `StudentInvitationOperationsView.post` rate limit + anomaly | 90 | 8 |
| 7 | `resolve_enrollment_sync_defaults` com `base_amount=0` | 30 | 7 |
| 8 | `finalize_student_oauth_callback` fluxos especiais | 60 | 8 |
| 9 | `mark_pending_signup_paid` idempotência webhook | 50 | 5 |
| 10 | `archive_box` ALTER SCHEMA + audit | 40 | 9 |

**~643 linhas de código crítico sem teste** identificadas. Sprints 5–8 cobrem 80% do risco.

---

### Fase 4 — Gates de produção (1 semana)

| Gate | Configuração |
|---|---|
| Coverage por módulo | `student_identity ≥ 85`, `integrations/stripe ≥ 90`, `access ≥ 95` |
| Migration check | `makemigrations --check --dry-run` falha CI se faltam |
| Lint de testes | `ruff` regra: proibir `except Exception` sem `# noqa: justificativa` |
| Pre-push hook | `pytest -m "not requires_postgres and not slow" --maxfail=3` |

---

### Fase 5 — Hardening longo prazo (contínuo)

- `factory_boy` substituindo `Model.objects.create()` ad-hoc
- `mutmut` trimestral em `student_identity` + `integrations/stripe`
- `hypothesis` fuzzing para boundary tests
- `pytest-xdist -n auto` após Fase 0 resolvida

---

## Governança

### Guardrail local de migrations (pre-commit)

Causa raiz do susto do Follow-up B (Sprint 9): migrations geradas localmente e **nunca commitadas** ficaram como órfãs no working tree, enganaram o `makemigrations` local e bloquearam o PostgreSQL de dev. O hook `.githooks/pre-commit` fecha isso com fail-fast local.

**Ativação (uma vez por clone):**
```bash
git config core.hooksPath .githooks
```

**O que bloqueia:**
1. Arquivos `*/migrations/*.py` **não rastreados** (o caso exato do Follow-up B) — rápido, sem Django.
2. Drift model↔migration (`makemigrations --check`) quando o ambiente Django está disponível — tolerante a erro de setup (não bloqueia por falta de env; o gate do CI ainda cobre).

**Bypass pontual:** `git commit --no-verify`. Complementa (não substitui) o `migration-check` do `ci-gates.yml`.

### Broken tests — formato canônico

```
# tests/broken-tests.txt
tests/test_X.py::TestClassY::test_method_Z  owner=@renan  since=2026-05-01  ticket=OCT-1234  reason="bloqueado por migração de schema"
```

**Regras:**
- Item sem `owner` ou `ticket`: CI falha
- Item com `since` > 30 dias: CI falha
- Item resolvido: PR remove a linha, não comenta

### Checklist de review de testes (obrigatório em PR)

- [ ] Teste tem assert sobre estado, não só sobre "não-exceção"?
- [ ] Mocks usam `autospec=True` ou `spec=`?
- [ ] Nenhum `except Exception` no corpo do teste?
- [ ] Skip tem motivo claro + ticket (se aplicável)?
- [ ] Nome reflete o comportamento testado, não a implementação?
- [ ] Roda em < 500ms (L2) ou < 50ms (L1)?
- [ ] Independente de ordem? (rodar com `pytest --randomly-seed=last`)

### Owner por diretório

| Diretório | Owner |
|---|---|
| `tests/test_tenant_boundary.py` | @backend-lead |
| `boxcore/tests/` | @core-team |
| `access/tests/` | @backend-lead |
| `tests/e2e/` | @qa |

---

## Auditoria de qualidade — prompt executável

Quando suspeitar que testes estão "verdes mas frágeis", rodar prompt de auditoria.

📄 **Referência:** [docs/testing/quality-plan-prompt.md](./quality-plan-prompt.md)

**Resumo do contrato:**
- Read-only (sem editar testes)
- Saída obrigatória com `file:line` + trecho verbatim
- Classifica em 10 categorias (C1 tautologia → C10 segfault candidates)
- Severidade ancorada em critério objetivo
- Sem coverage % na saída
- Veredicto final: `trustworthy | partial | untrustworthy`

---

## Apêndice — Decisões tomadas

| Data | Decisão | Justificativa |
|---|---|---|
| 2026-05-28 | Guard `connection.vendor != 'postgresql'` obrigatório em L3 | `except ImportError` não cobre `AttributeError` em runtime de `schema_context.__enter__()` |
| 2026-05-28 | Skip silencioso vira AP1 (proibido) | Bug real virava "amarelo" e passava no CI |
| 2026-05-21 | `--reuse-db --nomigrations` default | Velocidade de feedback em dev |
| 2026-05-21 | E2E ignorado no default | Lento, dependência de Playwright |

---

## Referências

- [pytest.ini](../../pytest.ini) — configuração canônica
- [conftest.py](../../conftest.py) — fixtures globais
- [config/settings/test.py](../../config/settings/test.py) — settings de teste
- [tests/broken-tests.txt](../../tests/broken-tests.txt) — registro de testes quebrados
- [docs/testing/README.md](./README.md) — como rodar
- [docs/testing/e2e-guide.md](./e2e-guide.md) — guia Playwright
- [docs/testing/quality-plan-prompt.md](./quality-plan-prompt.md) — prompt de auditoria
