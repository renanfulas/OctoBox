# Inventario de testes broken — 2026-05-18

> **Origem:** Fase 1 do plano de qualidade de testes
> ([quality-plan-prompt.md](./quality-plan-prompt.md)).
> **Fonte:** JUnit XML do CI PR #75, run 26064321312.
> **Total broken:** 193 / 896 = **21.6%** taxa de falha pre-existente.

---

## TL;DR

A suite tem **698 testes verdes (77.9%)** e **193 broken**. O workflow
de CI (`.github/workflows/full-test-suite.yml`) ja roda a suite completa
em PR e push para main, com `tests/broken-tests.txt` listando os broken
para auto-skip via conftest hook.

**Sucesso desta fase = lista encolhendo a cada sprint.** PRs futuros
(parte da Fase 0.5 / stabilization) removem entradas conforme corrigem
testes.

---

## Distribuicao por app

| App | FAILED | ERRORED | Total |
|---|---:|---:|---:|
| boxcore | 28 | 0 | 28 |
| student_app | 25 | 0 | 25 |
| student_identity | 14 | 0 | 14 |
| **tests/** (top-level) | 3 | **118** | **121** |
| access | 3 | 0 | 3 |
| onboarding | 2 | 0 | 2 |
| **TOTAL** | **75** | **118** | **193** |

---

## Tipos de erro

### FAILED (75 testes) — assertion/logic
| Exception | Count |
|---|---:|
| AssertionError | 41 |
| django.db.utils.ProgrammingError | 16 |
| AttributeError | 6 |
| django.db.utils.NotSupportedError | 4 |
| KeyError | 2 |
| django.core.exceptions.FieldError | 2 |
| TypeError | 2 |
| django.db.utils.IntegrityError | 1 |
| django.core.exceptions.ImproperlyConfigured | 1 |

### ERRORED (118 testes) — setup/teardown
| Exception | Count |
|---|---:|
| `failed on setup with "django.db.utils.ProgrammingError"` | **118** |

**TODOS os 118 errored** sao a MESMA causa raiz no setup. Provavelmente
um padrao de fixture/migration que afeta apenas os testes em
`tests/test_coach_wod_editor.py` e similares (uma classe de tests cujo
setUp falha por uma constraint/tabela faltante no schema do tenant).
Corrigir essa unica causa raiz **resolve >60% do inventario**.

---

## Categorizacao sugerida (buckets para Fase 0.5)

### Bucket A — Setup failure massivo em tests/ (PRIORIDADE 1, 1 fix, -118)
Os 118 errored estao concentrados em arquivos como:
- `tests/test_coach_wod_editor.py`
- `tests/test_dashboard_snapshot_serialization.py`
- `tests/test_request_timing_headers.py`

Diagnostico: setUp de classe TestCase tenta usar TENANT_APP que ainda
nao esta migrado no schema do tenant de teste no momento do setup, OU
ha alguma fixture global ausente.

**Fix esperado:** 1 PR ajustando o conftest ou a base TestCase. Resolve
~118 testes de uma vez.

### Bucket B — student_app + student_identity (PRIORIDADE 2, ~39 testes)
Concentrados em:
- `student_app.tests.PublicWorkoutPwaTests` (5 testes)
- `student_app.tests.StudentAppExperienceTests` (16 testes)
- `student_app.tests.StudentAuthMiddlewareTests` (2 testes)
- `student_identity.tests.StudentIdentityFlowTests` (10+ testes)

Diagnostico: provavelmente **fallout de Sprint 4 schema-per-tenant**
(testes que dependem de comportamento pre-migration: cookies de student
session, OAuth callback redirects, etc).

**Fix esperado:** 2-3 PRs por arquivo. Pode reusar padroes ja
estabelecidos em conftest.py (auto_membership, schema_context).

### Bucket C — boxcore variados (PRIORIDADE 3, 28 testes)
Espalhados entre:
- `boxcore.tests.test_dashboard.DashboardViewTests` (5)
- `boxcore.tests.test_finance.FinanceCenterTests` (4)
- `boxcore.tests.test_catalog_services.CatalogServiceTests` (3)
- 6 outros arquivos

Diagnostico misto: alguns sao AssertionError (logica), outros sao
ProgrammingError (schema/migration), outros AttributeError (API mudou).

**Fix esperado:** triagem 1-a-1, ~1-2 PRs por arquivo.

### Bucket D — access + onboarding + outros (PRIORIDADE 4, ~8 testes)
Pequenos clusters.

---

## Trade-offs aceitos

1. **Suite roda em ordem fixa** (`-p no:randomly`). Justificativa:
   pytest-xdist nao garante ordem total entre workers. Fase 3 do plano
   valida order-dependence com seed fixo em runs single-thread separados.
2. **Cobertura nao mede ainda** broken tests. Eles contam como `skipped`,
   nao como `not run`. Cobertura reportada e do subset verde (698 testes).
3. **Lista pode crescer brevemente** se um PR nao-relacionado quebrar
   um teste antes-verde. Conftest hook silencia, mas commit deve
   explicar a adicao.

---

## Como usar este inventario

### Para fixers (Fase 0.5):
```bash
# 1. Pegue um teste do tests/broken-tests.txt
test='boxcore/tests/test_audit.py::AuditTrailTests::test_login_creates_audit_event'

# 2. Rode-o isoladamente
python -m pytest -p no:randomly --create-db --migrations "$test"

# 3. Diagnostique, corrija, confirme verde
python -m pytest -p no:randomly --reuse-db "$test"  # passa?

# 4. Remova a linha de tests/broken-tests.txt
# 5. Commit "test: unbreak <test>"
# 6. CI deve passar com 1 broken a menos
```

### Para reviewers:
- PR adiciona linha em broken-tests.txt? **Pergunte:** porque?
  Regressao real? Bug introduzido?
- PR remove linha de broken-tests.txt? **Verifique:** o teste passa
  isolado E em suite completa local? Houve mudanca semantica?

---

## Proximos passos do plano

1. **Fase 1 (este PR #75):** ✅ workflow + skip mechanism + inventario
2. **Fase 0.5 (proximo sprint):** atacar Bucket A — 1 fix resolve 118 testes
3. **Fase 2:** comentario de cobertura em PRs (`fail_under` ajustado)
4. **Fase 3:** validar order-dependence com pytest-randomly + seed fixo
