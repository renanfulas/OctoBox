# ADR-013 — Superdev: acesso de suporte em todo box provisionado

**Status:** Aceito
**Data:** 2026-06-20
**Contexto:** Funil Early Adopter (Stripe → Owner → Box) + necessidade de suporte da equipe OctoBox em qualquer box. Implementado no PR #131 (`af02724`).

## Decisão

Todo box provisionado anexa **automaticamente** uma conta única de suporte — o **superdev** — como `Membership`, para a equipe OctoBox dar suporte sem pedir credencial ao cliente.

- **Hook:** `_attach_support_membership(box)` roda dentro de `control.services.reprovision_box` (não em `provision_box`). `reprovision_box` é o chokepoint comum do caminho novo e do resume idempotente — boxes provisionados antes da conta superdev existir também são curados num reprovision/backfill posterior.
- **Papel:** anexado como `Membership.Role.OWNER` com **`is_primary_box=False`**. Sem novo papel/migration.
- **Identidade:** conta dedicada (`is_superuser=True`), resolvida por `SUPERDEV_USERNAME` (default `superdev`). Como `auth` é SHARED_APP (vive em `public`), **um único usuário serve a todos os boxes**.
- **Ciclo de vida operacional:**
  - `manage.py bootstrap_superdev` cria/garante a conta (senha via `SUPERDEV_PASSWORD`).
  - `manage.py attach_superdev_to_boxes [--dry-run]` faz backfill dos boxes ACTIVE existentes.
  - `SUPERDEV_AUTO_ATTACH=False` é o **kill-switch** (desliga o anexo automático).
- **Navegação:** seletor de box de staff em `/box/` (`access.views.BoxSwitchView`, rota em `PUBLIC_SCHEMA_PATHS`). Sem box ativo, o middleware manda para `/box/` em vez de `403` quando o usuário tem Membership (ou é superuser).
- **À prova de falha:** superdev indisponível **nunca** quebra o provisionamento — apenas loga e audita (`membership.support_skipped` / `_failed`). Sucesso audita `membership.support_granted`.

## Por quê

- O `TenantBySessionMiddleware` libera acesso a um box **via `Membership`**. Sem membership, suporte não entra — e pedir a senha do cliente é inaceitável.
- `is_primary_box=False` é **crítico**: o superdev tem Membership em *todos* os boxes; se algum fosse primary, o login dele resolveria para um box de cliente aleatório.
- Anexar no provisionamento (vs. conceder sob demanda) garante o "sempre com o superdev" sem passo manual por cliente.
- OWNER (em vez de um papel novo) é coerente **hoje** porque `access.roles.get_user_role` faz short-circuit `is_superuser → OWNER`: para uma conta superuser o papel do Membership é, na prática, cosmético.

## Consequências

- **Raio de explosão alto:** a conta superdev é superuser com acesso OWNER a *todos* os boxes. A senha precisa de proteção forte (cofre/SSO); idealmente MFA.
- **Ativação é por ambiente:** a feature está no código, mas só vale após rodar `bootstrap_superdev` (+ backfill) em cada ambiente (homolog/produção).
- **Auditoria:** todo anexo gera `PlatformAuditEvent` em `public`, visível na trilha cross-tenant.

## Caminho futuro (least-privilege)

Quando o multitenancy amadurecer, trocar para uma conta superdev **não-superuser**:

1. Adicionar papel `DEV` em `control.models.Membership.Role` (migration) e usá-lo no anexo.
2. Garantir o grupo público `DEV` (ver `boxcore` `bootstrap_roles`) para `access.roles.get_user_role` resolver DEV (suporte read-mostly, alinhado a `access/roles/dev.py`).
3. Criar a conta dedicada, apontar `SUPERDEV_USERNAME` para ela e rodar `attach_superdev_to_boxes`.

Nenhum código de provisionamento muda — o seam é `get_superdev_user()` + `SUPERDEV_USERNAME`.

## Anti-pattern proibido

- Anexar o superdev com `is_primary_box=True`.
- Deixar a indisponibilidade do superdev **propagar** e quebrar o provisionamento do box.
- Reusar o superuser pessoal de um humano como a conta de suporte compartilhada — use a conta dedicada resolvida por `SUPERDEV_USERNAME`.
- Hardcode de username/credencial de suporte fora das settings.

## Referências

- `control/services.py::_attach_support_membership`, `::get_superdev_user`, `::reprovision_box`.
- `control/management/commands/bootstrap_superdev.py`, `::attach_superdev_to_boxes.py`.
- `access/views.py::BoxSwitchView`; `control/middleware.py` (redirect para `/box/`).
- `config/settings/base.py` — `SUPERDEV_USERNAME` / `SUPERDEV_EMAIL` / `SUPERDEV_AUTO_ATTACH`.
- `tests/test_superdev_workflow.py`, `tests/test_control_services.py`.
