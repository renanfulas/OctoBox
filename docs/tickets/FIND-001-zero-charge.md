# FIND-001 — Análise: cobrança zerada silenciosa

> **Severidade:** HIGH → **rebaixado para NÃO-BUG**
> **Descoberto em:** 2026-05-28
> **Status:** ✅ FECHADO — resolvido por análise (2026-05-29). Não requer código.
> **Arquivo:** students/domain/enrollment_lifecycle.py
> **Teste que evidencia:** tests/test_students_use_cases.py::ResolveEnrollmentSyncDefaultsTest::test_base_amount_is_zero_when_no_initial_and_no_plan_price

---

## ⚑ Conclusão (2026-05-29) — FECHADO COMO NÃO-BUG

Após decisão de produto + verificação de schema, o risco original **não se sustenta**:

1. **Produto confirmou:** matrícula de lead sem plano (cobrança zerada) é um
   fluxo **legítimo**, não um acidente a bloquear.
2. **Schema garante invariante:** `finance/model_definitions.py:80` define
   `price = models.DecimalField(...)` **NOT NULL**. Um `MembershipPlan`
   selecionado **sempre** tem preço — o cenário "plano com `price=NULL` →
   cobrança zerada acidental" (hipótese original) **é impossível**.

### Recomposição dos caminhos possíveis

| Caminho | Resultado | Veredicto |
|---|---|---|
| Lead sem plano (`selected_plan=None`) | Early-return `django_enrollments.py:58` — não cria Payment | Legítimo (confirmado por produto) |
| Plano selecionado | `price` NOT NULL → `base_amount > 0` | Sem acidente possível |
| `initial_payment_amount=0.00` explícito | Cria Payment R$ 0 | Intencional (operador escolheu cobrar zero) |

### Por que NÃO criar validação

- **Opção A (`raise ValueError`)** seria código morto (price garantido) OU
  bloquearia leads válidos. Descartada.
- **Opções B/C** resolveriam um problema que não existe (acidente impossível
  pelo schema).
- O único Payment de R$ 0 possível é **intencional** — não há regressão a prevenir.

### Salvaguarda permanente

O teste `test_base_amount_is_zero_when_no_initial_and_no_plan_price` **permanece
na suíte** documentando que `resolve_enrollment_sync_defaults` retorna
`Decimal('0.00')` nesse caso — comportamento agora **confirmado como correto**,
não como bug. Se o schema mudar (`price` virar nullable), este teste + a
análise abaixo servem de ponto de partida para reabrir.

---

## Análise original (preservada para histórico)

## Resumo

`resolve_enrollment_sync_defaults` faz fallback silencioso para `Decimal('0.00')` quando tanto `initial_payment_amount` quanto `selected_plan_price` chegam como `None`. O valor zerado flui sem alerta até `Payment.objects.create(...)`, gerando cobrança real com `amount=0` sem nenhum guard intermediário.

## Evidência (código verbatim)

`students/domain/enrollment_lifecycle.py:72-77`:

```python
if initial_payment_amount is not None:
    base_amount = initial_payment_amount
elif selected_plan_price is not None:
    base_amount = selected_plan_price
else:
    base_amount = Decimal('0.00')
```

## Callsites de `resolve_enrollment_sync_defaults`

| Arquivo:Linha | Contexto | UI valida antes? |
|---|---|---|
| `students/infrastructure/django_enrollments.py:46` | Único callsite de produção. `DjangoStudentEnrollmentWorkflowPort.sync` passa `initial_payment_amount=command.initial_payment_amount` e `selected_plan_price=getattr(selected_plan, 'price', None)`. `selected_plan` é `None` quando `command.selected_plan_id is None`. | **Parcial.** O form `catalog/form_definitions/student_forms.py:370-371` rejeita `initial_payment_amount <= 0` apenas se `selected_plan is not None`. **Não há validação cruzada** exigindo "plano OU valor inicial" — ambos podem chegar `None`/`0` por outros entrypoints (facade pública, API, jobs). |
| `boxcore/tests/test_students_domain.py:41` | Teste legado de defaults comerciais. | n/a |
| `tests/test_students_use_cases.py:347` | Teste L1 que evidencia o bug atual. | n/a |

Cadeia upstream confirmada: `catalog/services/enrollments.py:21` → `students/facade/student_lifecycle.py:193` (`run_student_enrollment_sync`) → `execute_student_enrollment_sync_command` → `DjangoStudentEnrollmentWorkflowPort.sync` → `resolve_enrollment_sync_defaults`. **Nenhum nó da cadeia bloqueia `initial_payment_amount=None & selected_plan_id=None`.**

Observação importante: no callsite de produção, quando `selected_plan is None`, o adapter retorna cedo (`django_enrollments.py:58-59`) sem criar Payment. **A cobrança zerada só ocorre quando `selected_plan_price=None` mas `selected_plan` existe** — cenário possível se `MembershipPlan` tiver `price=NULL` no banco, ou se `initial_payment_amount=Decimal('0.00')` for passado explicitamente (zero é truthy, mas o ramo `is not None` o aceita).

## Consumidores downstream de `base_amount`

1. `students/infrastructure/django_enrollments.py:84` — Caso "primeira matrícula": `StudentPaymentScheduleCommand(amount=sync_defaults.base_amount, ...)`.
2. `students/infrastructure/django_enrollments.py:114` — Caso "mesmo plano sem cobrança ainda": idem.
3. `students/infrastructure/django_payments.py:50` — `build_payment_schedule_plan(amount=Decimal(command.amount), ...)`. **Não há validação `amount > 0`.**
4. `students/infrastructure/django_payments.py:58-71` — `Payment.objects.create(amount=planned_payment.amount, ...)`. Persiste no model `finance.models.Payment` sem checagem.

Caminho completo: domain → `EnrollmentSyncDefaults.base_amount` → `StudentPaymentScheduleCommand.amount` → `PlannedPayment.amount` → `Payment.amount` (linha persistida em produção).

No fluxo de pro-rata (`django_enrollments.py:165`), `base_amount` é substituído por `prorata_decision.new_charge_amount`, então esse ramo não é afetado pelo bug. O ramo afetado é estritamente o "primeira matrícula" e "mesmo plano sem payment prévio".

## 3 Opções de correção

### Opção A — ValueError no domain (defesa em profundidade)

**Como:**
```python
if initial_payment_amount is None and selected_plan_price is None:
    raise ValueError('base_amount-required-or-plan-required')
```

**Prós:** garantia absoluta — bug nunca passa do domain. Cobre todos os callsites futuros (API, jobs, importações). Falha rápido e explícito.
**Contras:** quebra fluxos onde 0 é intencional (importação de leads sem plano, MVP de cadastro mínimo). Como o adapter já retorna cedo quando `selected_plan is None`, o ValueError só explodiria no edge case `plan.price=NULL`, que provavelmente já é inválido.
**Quem decide:** time de produto + engenharia.

### Opção B — `status='incomplete'` em vez de criar pagamento

**Como:** quando `base_amount == 0` e nenhum dos inputs foi explicitamente 0, marcar enrollment como `incomplete` e **não** chamar `execute_student_payment_schedule_command`. Exigir intervenção manual antes de gerar cobrança.

**Prós:** UX preservada (matrícula persiste, secretaria corrige depois). Dados financeiros consistentes (zero Payments fantasmas).
**Contras:** introduz novo status `incomplete` no enum `EnrollmentStatus` — migration + atualização de relatórios + filtros de dashboard. Mais complexo de auditar.
**Quem decide:** PM.

### Opção C — Validação no form/serializer da UI

**Como:** estender `StudentForm.clean` (`catalog/form_definitions/student_forms.py:355+`) com validador cruzado: exigir `selected_plan` OU `initial_payment_amount > 0`. Adicionar mesma regra em qualquer serializer DRF que use `StudentEnrollmentSyncCommand`.

**Prós:** falha cedo na borda, mensagem amigável ao usuário, zero risco de regressão em testes de domain. Aproveita o pattern já existente em `student_forms.py:367-371`.
**Contras:** **não defende contra outros callsites** (facade `run_student_enrollment_sync`, jobs importadores, eventual API mobile). Apenas tampa o buraco visível.
**Quem decide:** front + back.

## Recomendação

**Combinar A + C.** A opção C cobre 100% do tráfego web atual com a melhor UX, mas deixa a facade pública e jobs vulneráveis. A opção A garante defesa em profundidade ao custo de 1 linha — e, dado que o callsite de produção já retorna cedo quando `selected_plan is None` (`django_enrollments.py:58-59`), o ValueError só dispara em cenários genuinamente inválidos (plano com `price=NULL`, command corrompido). Opção B é overkill: cria status novo e migration sem resolver a causa-raiz (falta de invariante).

A opção A isolada também é defensável se o time decidir que **nunca** existe caso de uso legítimo para matrícula com cobrança zerada — nesse caso, a invariante de domínio é a forma mais limpa.

## Próximos passos

- [ ] Alinhamento com PM: existe fluxo legítimo de "matrícula sem cobrança"?
- [ ] Aprovação técnica da opção escolhida (A, A+C ou C)
- [ ] Implementação + atualização do teste `test_base_amount_is_zero_when_no_initial_and_no_plan_price` para refletir nova invariante (assertRaises ou novo branch)
- [ ] Auditoria: query em produção por `Payment` com `amount=0` para medir impacto histórico
- [ ] Validação em staging antes de prod
