# Findings — Sprints 5–8 (2026-05-28)

Bugs e inconsistências reais descobertos no código de produção durante a
implementação dos testes dos Sprints 5–8. **Nenhum foi corrigido** — esse
relatório existe para virar tickets e ser priorizado pelo time.

---

## FIND-001 — Cobrança zerada silenciosa em `resolve_enrollment_sync_defaults`

**Severidade:** HIGH
**Arquivo:** `students/domain/enrollment_lifecycle.py:79`
**Função:** `resolve_enrollment_sync_defaults`
**Sprint:** 7
**Teste que evidencia:** `tests/test_students_use_cases.py::ResolveEnrollmentSyncDefaultsTest::test_base_amount_is_zero_when_no_initial_and_no_plan_price`

### Evidência (código verbatim)

```python
# students/domain/enrollment_lifecycle.py:79
base_amount=initial_payment_amount or selected_plan_price or Decimal('0.00'),
```

### Por que é bug

Quando `initial_payment_amount=None` E `selected_plan_price=None` (ou ambos
`Decimal('0.00')`), o `base_amount` resolve para `Decimal('0.00')` sem
qualquer validação ou alerta. Combinado com a UI permitindo submeter
formulário sem plano selecionado, isso pode criar matrículas com cobrança
zerada que **passam por toda a pipeline** sem nenhum warning.

### Caminho de impacto

1. Usuário cria aluno sem selecionar plano
2. UI envia `initial_payment_amount=None` + `selected_plan_id=None`
3. `resolve_enrollment_sync_defaults` retorna `base_amount=Decimal('0.00')`
4. Cobrança é criada com valor 0,00 sem alerta
5. Receita perdida silenciosamente

### Sugestão (NÃO implementar sem decisão de produto)

```python
# Opção A: levantar ValueError no domain
if (initial_payment_amount or Decimal('0')) <= 0 and \
   (selected_plan_price or Decimal('0')) <= 0:
    raise ValueError('base_amount-required')

# Opção B: marcar enrollment como 'incomplete' em vez de criar pagamento
```

---

## FIND-002 — `Decimal('0.00')` tratado como falsy

**Severidade:** MEDIUM
**Arquivo:** `students/domain/enrollment_lifecycle.py:79`
**Função:** `resolve_enrollment_sync_defaults`
**Sprint:** 7
**Teste que evidencia:** `tests/test_students_use_cases.py::ResolveEnrollmentSyncDefaultsTest::test_initial_payment_zero_decimal_is_treated_as_falsy`

### Evidência

```python
>>> bool(Decimal('0.00'))
False
>>> Decimal('0.00') or Decimal('99.00')
Decimal('99.00')
```

### Por que é bug (ou comportamento intencional sem documentação)

Se a UI envia explicitamente `initial_payment_amount=Decimal('0.00')` (intenção
clara: "cobrar zero por algum motivo"), o operador `or` coalesce para o plano,
sobrescrevendo a decisão explícita.

Esse comportamento é **indistinguível** do caso de `initial_payment_amount=None`.

### Sugestão

Trocar `or` por checagem explícita de `is None`:
```python
base_amount = (
    initial_payment_amount if initial_payment_amount is not None
    else (selected_plan_price if selected_plan_price is not None else Decimal('0.00'))
)
```

---

## FIND-003 — Order-dependence em `test_wod_template_archive`

**Severidade:** MEDIUM (qualidade de teste, não código de produção)
**Arquivo:** `tests/test_wod_template_archive.py::ArchiveTemplateServiceTests::test_build_archived_template_list_returns_correct_shape`
**Sprint:** Descoberto durante validação final dos Sprints 5–8

### Evidência

- Teste passa em isolamento: `pytest <test_node_id>` → PASS
- Teste falha em suite completa: `pytest tests/` → FAIL com `25 != 24`
- Confirmado pré-existente: falha ocorre mesmo SEM os arquivos novos
  dos Sprints 5–8 (verificado com `--ignore=tests/test_student_identity_staff_views.py`)

### Por que é bug

O teste assume um número fixo (`25`) de templates arquivados que provavelmente
depende de estado criado por outros testes ou seeders. Quando a ordem dos
testes muda (pytest-randomly), o estado esperado não está mais lá.

Viola **AP8 — Dependência de ordem de execução** definido em `docs/testing/architecture.md`.

### Sugestão

Refatorar o teste para usar `setUpTestData` ou factory_boy para criar
exatamente os templates que vai contar, em vez de depender de estado
acumulado.

```python
class ArchiveTemplateServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Cria EXATAMENTE 25 templates explicitamente
        cls.templates = [
            WodTemplate.objects.create(...) for _ in range(25)
        ]
```

---

## FIND-004 — `query_stripe_session_status` aceita session_id só com whitespace

**Severidade:** LOW
**Arquivo:** `signup/services.py:156`
**Função:** `query_stripe_session_status`
**Sprint:** 5
**Teste que evidencia:** `tests/test_signup_services.py::QueryStripeSessionStatusTest::test_returns_none_when_session_id_is_whitespace_only`

### Evidência

```python
# signup/services.py:156
if not secret_key or not session_id:
    return None
```

`secret_key` é `.strip()` na linha 155, mas `session_id` NÃO. Strings só com
espaços (`'   '`) são truthy em Python — passam pela validação e chegam ao
`stripe.checkout.Session.retrieve()`, gerando erro de API que cai no
`except Exception` da linha 168.

### Por que é bug (menor)

Não causa dano (a API rejeita e retorna `None` via fallback), mas:
- Gasta 1 chamada HTTP desnecessária ao Stripe
- Loga warning enganoso (parece falha de rede, é input inválido)

### Sugestão

```python
secret_key = (getattr(settings, 'STRIPE_SECRET_KEY', '') or '').strip()
session_id = (session_id or '').strip()
if not secret_key or not session_id:
    return None
```

---

## Sumário

| ID | Severidade | Sprint | Tipo |
|----|------------|--------|------|
| FIND-001 | HIGH | 7 | Bug de produção (cobrança zerada) |
| FIND-002 | MEDIUM | 7 | Bug de produção (semantic do `or`) |
| FIND-003 | MEDIUM | descoberto na validação | Bug de teste (order-dependence) |
| FIND-004 | LOW | 5 | Bug menor (input não normalizado) |

**Decisão:** nenhum dos achados foi corrigido durante a implementação dos
testes. Cada um deve virar ticket no backlog para priorização pelo time.
