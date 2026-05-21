# ADR-005 — Class-scope fixtures cobrem o lifecycle do Django TestCase

**Status:** Aceito
**Data:** 2026-05-18
**Contexto:** Sprint 4 schema-per-tenant, Fase 0.5 (Bucket A — 118 testes ERRORED)

## Decisão

`_class_tenant_schema_context` e `_auto_membership_for_test_users` em `conftest.py`
usam `scope='class'` com `autouse=True`, envolvendo o lifecycle completo do Django
`TestCase` (`setUpClass` + `setUpTestData` + `setUp` + test method + `tearDown`).

## Por quê

Django `TestCase.setUpTestData` é um classmethod que roda **1 vez** antes de qualquer
test method, **antes** de qualquer fixture pytest function-scoped. Em schema-per-tenant:

- Sem class scope: `setUpTestData` rodava em `schema=public`, onde tabelas
  `TENANT_APPS` (boxcore_classsession, boxcore_student, boxcore_auditevent…) **não
  existem**. INSERT estourava `ProgrammingError: relation … does not exist`.
- 118 dos 193 testes da baseline (61%) eram ERRORED por esse motivo (Bucket A do
  inventário em `docs/testing/broken-tests-inventory.md`).

Class-scope fixture entra **antes** de `setUpClass` (pytest hook order) e mantém
o `with schema_context(test_tenant.schema_name):` ativo até o `tearDown` do último
test method da classe.

Análogo: o `_auto_membership_for_test_users` precisa do mesmo scope para
interceptar `User.objects.create_user(...)` chamado em `setUpTestData` e
auto-criar `Membership(role=OWNER, is_primary_box=True)` para o `test_tenant`.
Função-scoped chegaria tarde demais.

## Consequências

- 118 testes recuperados com 1 commit (commit `4dde974`).
- Function-scoped fixtures permanecem como rede de segurança (cobrem caso de
  reset de search_path entre transações com pytest-randomly + xdist).
- Limite: testes que precisam mudar tenant entre test methods da mesma classe
  precisam explicitar `with schema_context(...)` internamente; o class-scope
  congela um único tenant pra toda a classe.
- Documentado no docstring do conftest.

## Anti-pattern proibido

Adicionar fixture com scope `'function'` para envolver tenant; o `setUpTestData`
do Django TestCase já terá rodado em public quando ela entrar.
