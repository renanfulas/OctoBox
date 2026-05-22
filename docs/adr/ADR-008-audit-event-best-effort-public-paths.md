# ADR-008 — AuditEvent best-effort em paths públicos

**Status:** Aceito
**Data:** 2026-05-19
**Contexto:** Sprint 4 schema-per-tenant, Bucket B+C (audit em fluxos pre-auth)

## Decisão

Escrita de `boxcore.AuditEvent` em paths públicos (login, logout, anonymous
redirect, webhook integration) segue o protocolo:

1. **Resolução de tenant primeiro** via facade do Center Layer
   (ADR-006). Em pilot ativa `SINGLE_ACTIVE_BOX`; em multi-tenant pode retornar
   NONE.
2. **`transaction.atomic()` savepoint** ao redor do `AuditEvent.objects.create`.
   Falha do INSERT não propaga rollback pra transação principal.
3. **`try/except Exception` defensivo** envolvendo o savepoint. Audit é
   nice-to-have nesses fluxos — **não pode bloquear** login/logout/webhook
   retornar resposta válida.

Combinação implementada em:

- `student_app/middleware/student_auth.py` — anonymous redirect audit.
- `student_identity/oauth_loader.py::enforce_student_oauth_callback_rate_limit`
  — rate limit audit.
- `student_identity/views.py` — invite landing audits (token inválido, rate limit).
- `student_identity/resend_webhooks.py::_activate_tenant_for_delivery` — webhook audit.
- `auditing/services.py::log_audit_event` — staff audit centralizado.

## Por quê

`AuditEvent` vive em `TENANT_APPS` (boxcore_auditevent só existe em `box_xxx`,
não em `public`). Quando view roda em path PUBLIC_SCHEMA, `connection.schema_name
== 'public'` e INSERT falha com `ProgrammingError: relation "boxcore_auditevent"
does not exist`.

Sem savepoint, esse INSERT failed corrompe a transação Django inteira: queries
subsequentes (incluindo asserções do test) falham com
`TransactionManagementError: An error occurred in the current transaction`.

Sem try/except defensivo, falha de audit bloqueia o redirect/response — efeito
colateral inaceitável para auditoria (audit não é fluxo crítico).

## Consequências

- Em pilot (1 box ativo): audit funciona normalmente após Center Layer ativar
  o tenant. **Cobertura completa.**
- Em multi-tenant prod sem identificador: audit silenciosamente perde o evento.
  **Aceito** porque login/logout/webhook são fluxos críticos que precisam
  responder mesmo com auditoria degradada. Workaround documentado: rota deve
  passar por identificador que casa em alguma strategy do facade (invite_token,
  actor_id com primary_box, etc.).
- Plano `schema-per-tenant-migration-plan.md` §1.2 prevê migração futura para
  `PlatformAuditEvent` (em SHARED_APPS) para auditoria cross-tenant — esse
  refactor resolve a degradação multi-tenant.

## Anti-pattern proibido

- `AuditEvent.objects.create()` direto em view de path público sem o trio
  (facade + savepoint + try/except).
- `try/except` sem savepoint — transação fica corrompida mesmo com a exception
  pega.
- Bloquear redirect/response em falha de audit.

## Referências

- `auditing/services.py::log_audit_event` — centraliza padrão para staff.
- `auditing/services.py::_ensure_tenant_for_audit_write` — facade Center Layer.
- `docs/plans/schema-per-tenant-migration-plan.md` §1.2 — PlatformAuditEvent futuro.
