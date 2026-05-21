# ADR-006 — Center Layer facade para tenant resolution pre-auth

**Status:** Aceito
**Data:** 2026-05-19
**Contexto:** Sprint 4 schema-per-tenant, Bucket B (auth do aluno + audit staff)

## Decisão

Resolução de tenant em fluxos pre-auth (sem cookie de sessão ainda) entra
**exclusivamente** por uma facade do Center Layer:

- `student_identity/facade/tenant_resolver.py` — fluxos do aluno (OAuth callback,
  invite landing).
- `auditing/services.py::_ensure_tenant_for_audit_write` — fluxos staff (login
  signal, webhook integration).

Cada facade aplica strategies ordenadas (primeira que resolver vence):

1. Tenant já ativo (no-op).
2. Identificador explícito (invite_token, provider_subject, email, primary_box do actor).
3. `SINGLE_ACTIVE_BOX` (pilot fallback): se há **exatamente 1** Box ACTIVE no
   sistema, ativa esse.

## Por quê

Antes do Bucket B, resolução de tenant pre-auth estava espalhada em:

- `student_identity/oauth_actions.py::_activate_identity_tenant`
- `student_identity/oauth_journeys.py::_activate_box_tenant`
- `student_identity/views.py` (chamadas ad-hoc)

Cada lugar implementava 1-2 strategies; combinações de input caíam em buracos:
- OAuth callback recorrente sem invite_token + identity já existente → não ativava
- Invite landing com token inválido → schema=public → AuditEvent falhava
- Login staff com user que tem primary_box → mesma falha

`SINGLE_ACTIVE_BOX` justifica-se em piloto (1 box). Em prod multi-tenant retorna
NONE, e o caller cai em try/except (audit best-effort — ver ADR-008) ou recusa
explícita (token inválido sem fallback).

Center Layer (`docs/architecture/center-layer.md`) prescreve que fluxos externos
**devem** entrar por uma facade por capacidade — não reimplementar regra em
borda nem chamar core diretamente.

## Consequências

- Recuperou 3 testes do OAuth callback (Bucket B cluster 1).
- Recuperou 7 testes de invite landing (Bucket B cluster 1, com fallback).
- Recuperou 3 testes de audit staff (Bucket C cluster 1).
- Strategy `SINGLE_ACTIVE_BOX` precisa ser **explicitamente desativada** em prod
  multi-tenant via subclasse ou settings flag (ticket separado, pré-Sprint 5).
- Cada strategy nova entra como função `_resolve_from_*` no resolver, com docstring
  e ordem de prioridade documentada.

## Anti-pattern proibido

- Chamar `connection.set_tenant(...)` ad-hoc em outro módulo.
- Reimplementar lookup de Box em view para "atalho" — sempre passa pela facade.

## Referências

- `student_identity/facade/tenant_resolver.py` — facade do aluno.
- `auditing/services.py::_ensure_tenant_for_audit_write` — facade do staff.
- `docs/architecture/center-layer.md::Estado atual` — registro oficial do corredor.
