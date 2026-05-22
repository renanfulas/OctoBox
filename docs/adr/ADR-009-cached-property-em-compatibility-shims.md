# ADR-009 — `@cached_property` em compatibility shims pós schema-per-tenant

**Status:** Aceito
**Data:** 2026-05-19
**Contexto:** Sprint 4 schema-per-tenant, Bucket B (Student.app_identity)

## Decisão

Shims de compatibilidade que substituem reverse-relations removidas durante o
schema-per-tenant **devem usar `django.utils.functional.cached_property`**, não
`@property` simples.

Caso concreto: `Student.app_identity` substitui o reverse `StudentIdentity.student`
(OneToOneField removido por ser cross-schema). Implementação em
`students/model_definitions.py:123-145`.

## Por quê

Reverse OneToOneField do Django **cacheia o objeto na instância Python** após o
primeiro acesso — comportamento idiomatico do ORM que callers assumem
implicitamente. Substituir por `@property` quebra esse contrato:

- `student.app_identity.box_root_slug` em template renderizando 10 sessões
  → 10 queries (1 por session.student.app_identity).
- Use cases que acessam `student.app_identity` múltiplas vezes (dashboard,
  workflows) → cada chamada uma query.
- `test_student_rm_snapshot_reuses_cached_record_for_workout_prescription`
  esperava 0 queries em segundo acesso (cache hit). Com `@property`, fica 1.

Side effect documentado durante o Bucket B: o teste
`test_student_grade_places_tomorrow_sessions_inside_amanha_section`
(antigo Bucket A straggler) também foi recuperado como **efeito colateral** do
fix — confirmando que múltiplos callers da grade iteravam sessões e disparavam
queries redundantes em `.app_identity`.

`@cached_property` cacheia o lookup na instância Python (mesmo comportamento
do reverse OneToOneField original):

- Primeira chamada executa o método, cacheia resultado no `__dict__` da instância.
- Chamadas seguintes retornam o cache sem query.
- Invalidação implícita: `Student.objects.get(pk=...)` cria nova instância sem
  o cache populado.

## Consequências

- Recuperou 2 testes do RM snapshot (Bucket B cluster final).
- Recuperou 1 teste regressão da grade tomorrow (efeito colateral).
- Reduz N+1 queries em qualquer caller que toca `student.app_identity` repetido.
- Limite: cache de instância **não** propaga entre threads/requests; o caller
  precisa recarregar `Student` se sabe que `StudentIdentity` mudou desde o
  primeiro acesso. Aceitável (mesmo limite do reverse OneToOneField original).

## Anti-pattern proibido

- `@property` em shim de compatibility relation (especialmente OneToOne/ForeignKey
  reverse) — quebra contrato implícito do ORM e gera N+1 silencioso.
- `select_related('app_identity')` — `@cached_property` não é Django field, o
  ORM rejeita com `FieldError`. Acesso via property continua funcionando, só
  perde o JOIN antecipado.

## Referências

- `students/model_definitions.py::Student.app_identity` — shim com cached_property.
- ADR-006 — Center Layer facade (contexto de schema-per-tenant).
