# Architecture Decision Records (ADRs)

Registro curto e versionado de decisões arquiteturais relevantes do OctoBox.
Cada ADR documenta **uma decisão**, **por que** foi tomada, **consequências**
aceitas, e **anti-patterns proibidos** (quando aplicável).

## Convenções

- Formato curto (1 página, max ~80 linhas).
- Numerados sequencialmente (`ADR-NNN-slug-curto.md`).
- Status: Aceito | Em revisão | Superado por ADR-XXX.
- Não rescrever um ADR existente — superar com um novo, citando o anterior.

## Índice

### Auth & onboarding do aluno

- [ADR-001](ADR-001-invite-token-cookie.md) — Invite token fora da query string observável (cookie HttpOnly).
- [ADR-003](ADR-003-student-auth-middleware.md) — StudentAuthMiddleware: separação do auth staff.
- [ADR-004](ADR-004-provider-unavailable-hide-not-disable.md) — Provider OAuth indisponível: esconder, não desabilitar.

### Audit & hygiene

- [ADR-002](ADR-002-audit-event-hash-hygiene.md) — Hash de identificadores em AuditEvent metadata.
- [ADR-008](ADR-008-audit-event-best-effort-public-paths.md) — AuditEvent best-effort em paths públicos (Center Layer + savepoint + try/except).

### Schema-per-tenant (Sprint 4)

- [ADR-005](ADR-005-test-fixtures-schema-per-tenant.md) — Class-scope fixtures cobrem lifecycle do Django TestCase.
- [ADR-006](ADR-006-center-layer-tenant-resolution.md) — Center Layer facade para tenant resolution pre-auth.
- [ADR-007](ADR-007-public-schema-paths-hygiene.md) — Higiene de PUBLIC_SCHEMA_PATHS (save/restore + exact match).
- [ADR-009](ADR-009-cached-property-em-compatibility-shims.md) — `@cached_property` em compatibility shims.
- [ADR-010](ADR-010-postgresql-django-tenants-gotchas.md) — PostgreSQL + django-tenants: 3 gotchas (SELECT FOR UPDATE, blind index, table_exists).
- [ADR-011](ADR-011-signal-handlers-defensivos.md) — Signal handlers defensivos a valores cru.
- [ADR-012](ADR-012-test-design-structural-asserts.md) — Test design: structural asserts > mega-copy asserts.

## Como criar um novo ADR

1. Encontre o próximo número disponível (`ls docs/adr/ | sort -V | tail -1`).
2. Copie o template:

   ```markdown
   # ADR-NNN — Título curto

   **Status:** Em revisão
   **Data:** YYYY-MM-DD
   **Contexto:** (sprint, projeto, ou problema raiz)

   ## Decisão

   ## Por quê

   ## Consequências

   ## Anti-pattern proibido

   ## Referências
   ```

3. Adicione entrada neste README.
4. Linka do código que implementa (comentário inline ou docstring), e da
   doc canonical do framework (ex.: `docs/architecture/center-layer.md`).

## Manutenção

Quando uma decisão é superada (mudança fundamental, não evolução), criar
novo ADR e marcar o anterior como `Status: Superado por ADR-NNN`. Não deletar
ADRs antigos — historia decisões.
