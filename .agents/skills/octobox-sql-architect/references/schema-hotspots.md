# Schema Hotspots

Use this map to jump to the real database surface quickly.

## Foundational reading

1. `config/settings/base.py`
2. `shared_support/box_runtime.py`
3. `shared_support/models.py`
4. `boxcore/migrations/`

## Domain models

### Students

- `students/model_definitions.py`
- Hotspots:
- encrypted PII in `phone` and `cpf`
- blind index in `phone_lookup_index`
- uniqueness rule on non-blank phone lookup index
- acquisition-source fields for attribution and resolution

### Onboarding

- `onboarding/model_definitions.py`
- Hotspots:
- intake lifecycle
- encrypted `phone` and `email`
- `linked_student`
- `raw_payload` for ingestion history

### Finance

- `finance/model_definitions.py`
- Hotspots:
- `MembershipPlan`, `Enrollment`, `Payment`, `FinanceFollowUp`
- optimistic concurrency via `Payment.version`
- overdue/read-path pressure on `due_date`, `status`, follow-up timestamps

### Communications / WhatsApp

- `communications/model_definitions/whatsapp.py`
- Hotspots:
- encrypted phone/body fields
- unique blind index and external ids
- webhook idempotency hints via `webhook_fingerprint`

### Operations

- `operations/model_definitions.py`
- Hotspots:
- `ClassSession`, `Attendance`, `BehaviorNote`, `LeadImportJob`
- unique attendance per `(student, session)`
- async import workflow persistence

### Student Identity

- `student_identity/models.py`
- Hotspots:
- `box_root_slug` and `primary_box_root_slug`
- identity vs membership vs invitation separation
- early multi-box semantics without open multitenancy

### Auditing

- `auditing/model_definitions.py`
- Hotspots:
- operational traceability
- intent and metadata enrichment
- avoid treating audit as the final hot read model

## Important architectural nuance

Many model implementations live in promoted apps such as `students`, `finance`, `operations`, and `communications`, but still preserve historical Django state through `app_label = 'boxcore'`.

Meaning:

1. code ownership moved
2. schema ownership may still be historically anchored
3. migration advice must respect both

## What to inspect when SQL performance matters

1. model field indexes and unique constraints
2. queryset-heavy read paths in `catalog`, `operations`, `dashboard`, `finance`
3. `*_queries.py`, `*_snapshot*.py`, and presenters
4. migrations that introduced blind indexes, idempotency, or follow-up tables

## What to inspect when multitenancy matters

1. `shared_support/box_runtime.py`
2. `api/v1/views.py`
3. `student_identity/models.py`
4. `docs/plans/scale-transition-20-100-open-multitenancy-plan.md`
5. `docs/plans/unit-cascade-architecture-plan.md`

## Quick warning signs

- recommending `tenant_id` everywhere without understanding current box isolation
- ignoring encrypted fields and blind-index lookup patterns
- proposing destructive migrations without restore and rollback path
- confusing `runtime_slug` with canonical future `tenant_id`
- using `AuditEvent` as the long-term answer for hot operational reads
