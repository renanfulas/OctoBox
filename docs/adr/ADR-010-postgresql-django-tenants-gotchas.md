# ADR-010 — PostgreSQL + django-tenants: 3 gotchas resolvidos

**Status:** Aceito
**Data:** 2026-05-20
**Contexto:** Sprint 4 schema-per-tenant, Bucket C (SQL + introspecção)

## Decisão

Três regras operacionais para escrever código que interage com PostgreSQL +
django-tenants + EncryptedCharField sem cair em armadilhas:

### Regra 1: `SELECT FOR UPDATE` com `of=('self',)` em joins nullable

Quando `select_for_update()` é combinado com `select_related(<fk_nullable>)`,
o LEFT JOIN faz Postgres recusar lock no lado nullable
(`FeatureNotSupported: FOR UPDATE não pode ser aplicado ao lado com valores
nulos de uma junção externa`). Passar `of=('self',)` restringe o lock ao
registro principal.

Aplicado em 5 lugares:
- `students/infrastructure/django_payments.py:86, 100, 102`
- `students/infrastructure/django_enrollments.py:216`
- `operations/infrastructure/django_workspace_store.py:22`
- `onboarding/facade.py:91`
- `onboarding/intake_invite_actions.py:49`

### Regra 2: Queries em `EncryptedCharField` devem usar `phone_lookup_index` (blind index)

`EncryptedCharField` (com nonce aleatório) não é deterministico — `phone__exact=X`
ou `phone__in=[X, Y]` **nunca** casa porque cada criptografia produz cipher
diferente. Modelos com phone encrypted (`Student`, `StudentIntake`) mantêm
campo paralelo `phone_lookup_index` (blind index SHA-256 deterministico) com
populated automaticamente em `save()`.

Lookups devem usar `phone_lookup_index=generate_blind_index(phone)`:

```python
from shared_support.crypto_fields import generate_blind_index

Student.objects.get(phone_lookup_index=generate_blind_index('5511999990000'))
Student.objects.update_or_create(
    phone_lookup_index=generate_blind_index(phone),
    defaults={'phone': phone, ...},
)
```

Aplicado em:
- `students/infrastructure/django_intakes.py::DjangoStudentIntakeWorkflowPort.sync`
- `boxcore/management/commands/import_students_csv.py::Command.handle`
- Tests precisam fazer mesmo lookup.

### Regra 3: `introspection.table_names()` retorna só schema atual

Em schema-per-tenant, `connection.introspection.table_names()` lista **apenas**
tabelas do schema corrente — não percorre o search_path. SHARED_APP models
(ex.: `WebhookEvent` em `integrations`) vivem em `public`; check direto falha
quando connection está em `box_xxx`.

`monitoring/beacon_snapshot.py::_model_table_exists` agora cheque
**ambos** os schemas (current + public via `information_schema.tables`).

## Por quê

**Regra 1 (FOR UPDATE):** comportamento documentado do PostgreSQL desde 9.0.
Manifesta-se só quando join é com FK nullable; testes que sempre tinham FK
populada nunca pegaram. O bug fica latente até dado real ter NULL.

**Regra 2 (blind index):** decisão de criptografia da Sprint 3 (Ghost Hardening
contra dump de banco). EncryptedCharField protege PII em repouso; blind index
permite igualdade sem comprometer cifrado. Lookups por igualdade DEVEM passar
pelo índice — não há atalho.

**Regra 3 (introspecção):** quirk do django-tenants + introspection do Django.
Cache LRU per-tenant (criado durante o Bucket B em `monitoring/beacon_snapshot.py`)
já isola entre tenants; falta só estender o lookup ao schema `public`.

## Consequências

- Recuperou: regenerate_payment, intake reception reject, intake whatsapp invite
  (2), finance_communication blocked, sync_student_intake, import_students,
  dashboard_snapshot_serialization, student_source_capture (10 testes).
- Regra 1 e 3 podem ser **lint-encorajados** futuro (custom flake8 plugin) —
  ticket separado.
- Regra 2 reduz performance: blind index é 1 hash SHA-256 por lookup. Aceitável
  (microssegundos vs query em índice b-tree).

## Anti-pattern proibido

- `select_for_update()` com `select_related(<fk_nullable>)` sem `of=('self',)`.
- `Student.objects.filter(phone=raw_phone)` ou `update_or_create(phone=raw_phone)`.
- Confiar em `connection.introspection.table_names()` pra checar tabela de
  SHARED_APP em contexto de tenant.

## Referências

- `students/infrastructure/django_intakes.py` — patrão de blind index lookup.
- `monitoring/beacon_snapshot.py::_model_table_exists` — patrão de fallback public.
- `shared_support/crypto_fields.py::generate_blind_index` — função canonical.
