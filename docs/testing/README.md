# Guia de Qualidade de Testes — OctoBox

> **Consolidado em:** 2026-05-21 (Fase 9 do plano de qualidade).
> **Plano completo:** [quality-plan-prompt.md](./quality-plan-prompt.md)

---

## Índice

1. [Como rodar a suite](#como-rodar-a-suite)
2. [Como adicionar um novo teste](#como-adicionar-um-novo-teste)
3. [Trade-offs explícitos atuais](#trade-offs-explícitos-atuais)
4. [Como subir o fail_under](#como-subir-o-fail_under)
5. [TO-DOs — próximas oportunidades](#to-dos--próximas-oportunidades)
6. [Referências rápidas](#referências-rápidas)

---

## Como rodar a suite

### Fluxo 1 — Suite rápida local (desenvolvimento diário)

```bash
# Reutiliza o banco de teste existente, sem migrations
python -m pytest boxcore/ tests/ -q
```

Usa `--reuse-db --nomigrations` do `addopts` em `pytest.ini`.
Ideal para ciclo de feedback rápido. **Não cobre testes E2E.**

---

### Fluxo 2 — Suite completa com cobertura (antes de abrir PR)

```bash
python -m pytest \
  --create-db --migrations \
  -n 4 \
  --cov --cov-report=term:skip-covered --cov-report=html \
  -q
```

- `--create-db --migrations` — garante schema `box_test` migrado (obrigatório para django-tenants)
- `-n 4` — paraleliza em 4 workers (pytest-xdist)
- `htmlcov/index.html` — relatório visual de cobertura

---

### Fluxo 3 — Suite com ordem aleatória (detectar order-dependence)

```bash
# Testa com 3 seeds fixos validados na Fase 3
python -m pytest --create-db --migrations -n 4 --randomly-seed=42   -q
python -m pytest --create-db --migrations -n 4 --randomly-seed=137  -q
python -m pytest --create-db --migrations -n 4 --randomly-seed=9999 -q
```

Todos os 3 seeds devem passar. Se um seed específico falhar, use
`--randomly-seed=<seed>` para reproduzir e `pytest-bisect` para isolar.

---

### Fluxo 4 — Testes E2E com browser real

```bash
# Instalar browser uma vez (não commitar o binário)
playwright install chromium

# Rodar suite E2E
python -m pytest tests/e2e/ --create-db --migrations -v

# Rodar com browser visível (debug)
python -m pytest tests/e2e/ --create-db --migrations --headed -v

# Rodar com slow-motion (ação por ação, 500ms entre steps)
python -m pytest tests/e2e/ --create-db --migrations --headed --slowmo=500 -v
```

Ver guia completo: [e2e-guide.md](./e2e-guide.md)

---

### Fluxo 5 — Subconjunto por app ou arquivo

```bash
# Só testes de um app
python -m pytest boxcore/tests/test_finance.py -v

# Só testes de constraints de banco
python -m pytest tests/test_db_constraints.py -v

# Só testes de error scenarios
python -m pytest tests/test_error_scenarios.py -v

# Só um teste específico
python -m pytest tests/test_db_constraints.py::test_attendance_unique_student_session_blocks_duplicate -v

# Excluir testes lentos (benchmark)
python -m pytest -m "not benchmark" -q
```

---

## Como adicionar um novo teste

### Padrão 1 — Factory (modelo novo)

```python
# tests/factories.py — adicione ao lado dos factories existentes

class MinhaEntidadeFactory(factory.django.DjangoModelFactory):
    """
    Explique por que esta factory existe e qual modelo cobre.
    Documente qualquer LazyAttribute não-trivial.
    """
    class Meta:
        model = MinhaEntidade

    # Campos únicos usam Sequence para evitar colisões entre testes
    campo_unico = factory.Sequence(lambda n: f'valor-{n}')
    # FKs obrigatórias usam SubFactory
    relacao = factory.SubFactory(OutraFactory)
    # Campos com default não precisam ser declarados
```

Factories existentes em `tests/factories.py`:
`UserFactory`, `StudentFactory`, `ClassSessionFactory`, `SessionWorkoutFactory`, `PaymentFactory`.

---

### Padrão 2 — Parametrize (matriz de roles ou casos)

```python
import pytest
from django.urls import reverse

# NÃO funciona em métodos de TestCase — use função standalone
@pytest.mark.django_db
@pytest.mark.parametrize("role, url_name, expected_status", [
    ('owner',     'minha-rota', 200),
    ('manager',   'minha-rota', 200),
    ('coach',     'minha-rota', 403),
    ('reception', 'minha-rota', 403),
])
def test_minha_rota_por_role(client, role, url_name, expected_status):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group
    User = get_user_model()
    user = User.objects.create_user(username=f'param-{role}', password='pass')
    user.groups.add(Group.objects.get(name=role))
    client.force_login(user)
    assert client.get(reverse(url_name)).status_code == expected_status
```

Template já em uso: `boxcore/tests/test_operations.py::test_cross_role_workspace_access_matrix`.

---

### Padrão 3 — Cenário de erro

```python
from django.test import TestCase
from django.urls import reverse

class MeuEndpointErrorTests(TestCase):
    def setUp(self):
        # Ver test_error_scenarios.py para exemplo completo com bootstrap_roles
        ...

    def test_anonimo_redireciona_para_login(self):
        response = self.client.get(reverse('minha-rota'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_papel_errado_retorna_403(self):
        self.client.force_login(self.usuario_sem_permissao)
        response = self.client.get(reverse('minha-rota'))
        self.assertEqual(response.status_code, 403)

    def test_recurso_inexistente_retorna_404(self):
        self.client.force_login(self.usuario_autorizado)
        response = self.client.get(reverse('minha-rota', args=[999_999]))
        self.assertEqual(response.status_code, 404)
```

Template completo: `tests/test_error_scenarios.py`.

---

### Padrão 4 — Constraint de banco

```python
import pytest
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

@pytest.mark.django_db
def test_constraint_unica(self):
    """Nome descritivo do que a constraint protege."""
    from tests.factories import MinhaFactory
    MinhaFactory(campo='valor')
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            MinhaFactory(campo='valor')  # duplicata

@pytest.mark.django_db
def test_campo_not_null_via_update():
    """Usa update() para bypassar validação Python e testar a constraint do banco."""
    from finance.models import Payment
    from tests.factories import PaymentFactory, StudentFactory
    payment = PaymentFactory(student=StudentFactory())
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Payment.objects.filter(pk=payment.pk).update(amount=None)
```

Template completo: `tests/test_db_constraints.py`.

---

## Trade-offs explícitos atuais

| Decisão | O que foi escolhido | Por que | Quando revisar |
|---|---|---|---|
| **Tempo de CI (PR)** | Suite completa em ~12-15 min com `-n 4` | Baseline medido na Fase 0: 125 min single-thread. `-n 4` reduz para ~15 min, abaixo do limite de 8 min (aceitável). | Se ultrapassar 20 min: dividir em smoke subset para PRs + full suite só em main |
| **`fail_under = 72`** | Baseline 74,7% − 2 pp de margem | Folga de 2 pp evita quebrar PRs legítimos de refactoring que reduzem cobertura temporariamente | A cada sprint: se a cobertura atual estiver > 5 pp acima do fail_under, subir o threshold |
| **E2E só em main + nightly** | `--ignore=tests/e2e` no addopts padrão | `playwright install --with-deps chromium` leva ~2 min + cada teste E2E leva 10-30s. Overhead injustificável para todo PR | Quando a suite E2E tiver > 10 testes e a regressão E2E se tornar mais frequente que 1/sprint |
| **`broken-tests.txt`** | Opt-out explícito de testes pre-existentes quebrados | Gate da Fase 0 acionado (>5% falhas). Skip declarado é melhor que CI permanentemente vermelho | A cada sprint: cada linha removida da lista = 1 teste consertado. Lista deve zerar antes da Fase 9 final |
| **`--nomigrations` no addopts** | Migrations puladas para desenvolvimento local | Criação de schema + migrations leva ~30s. Para desenvolvimento local, o banco reutilizável é suficiente | Não mudar — testes que precisam de migrations explicitam `--create-db --migrations` |
| **Seed de parallelismo** | `-p no:randomly` no CI full-suite, seeds validados separadamente | pytest-randomly + xdist: a ordem aleatória não é garantida entre workers. Seeds são validados no job `order-dependence-check` (seeds 42, 137, 9999) | Sempre que um novo teste order-dependente for detectado |

---

## Como subir o `fail_under`

O `fail_under` está em `.coveragerc`:

```ini
[run]
fail_under = 72
```

**Passo a passo:**

```bash
# 1. Medir cobertura atual
python -m pytest --create-db --migrations -n 4 --cov --cov-report=term -q 2>&1 | grep "TOTAL"

# Exemplo de saída:
# TOTAL    3421    847    75%

# 2. Calcular novo threshold: cobertura_atual - 2pp
# Se cobertura atual é 78%, novo fail_under = 76

# 3. Atualizar .coveragerc
# fail_under = 76

# 4. Verificar que CI ainda passa
python -m pytest --create-db --migrations -n 4 --cov -q

# 5. Commitar
git add .coveragerc
git commit -m "test: subir fail_under para 76 (cobertura atual 78%)"
```

**Regra:** nunca subir `fail_under` para um valor maior que `cobertura_atual − 2`.
A margem de 2 pp protege contra flutuações naturais entre branches.

---

## TO-DOs — próximas oportunidades

### Factories a criar

| Modelo | Frequência estimada | Arquivo sugerido |
|---|---|---|
| `Enrollment` | Alta (finance tests) | `tests/factories.py` |
| `MembershipPlan` | Alta (finance tests) | `tests/factories.py` |
| `Attendance` | Média (operations tests) | `tests/factories.py` |
| `BehaviorNote` | Baixa | `tests/factories.py` |

### Matrizes a parametrizar

| Arquivo | Candidato | Tamanho estimado |
|---|---|---|
| `boxcore/tests/test_finance.py` | Testes de status de pagamento por ação | ~6 casos |
| `boxcore/tests/test_security_guards.py` | Rate limit por endpoint | ~4 casos |
| `boxcore/tests/test_api.py` | Respostas de API por role | ~8 casos |

### Endpoints sem cobertura de erro

Ver inventário completo: [error-scenarios-inventory.md](./error-scenarios-inventory.md)

Prioridades:
- `finance-center` — sem teste de 401 anônimo
- `api-v1-finance-payments-bulk` — sem teste de 403 por role
- `payment-enrollment-link` — sem teste de 404

### Constraints de banco não cobertas

- `StudentIdentity` — UniqueConstraint condicional (status in PENDING/ACTIVE)
- `FinanceFollowUp.suggestion_key` — unique, sem teste de violação
- `Membership.unique_together (user, box)` — sem teste de violação

### Testes E2E a adicionar

- Cadastro de novo aluno (fluxo owner)
- Confirmação de pagamento no balcão (recepção)
- Check-in de presença (coach)

Ver guia: [e2e-guide.md](./e2e-guide.md)

---

## Referências rápidas

| Documento | O que contém |
|---|---|
| [quality-plan-prompt.md](./quality-plan-prompt.md) | Plano completo fase a fase com critérios de pronto |
| [baseline-2026-05-18.md](./baseline-2026-05-18.md) | Estado da suite antes do plano (Fase 0) |
| [broken-tests-inventory.md](./broken-tests-inventory.md) | Testes pré-existentes quebrados e suas causas |
| [error-scenarios-inventory.md](./error-scenarios-inventory.md) | Mapa de endpoints × status de erro cobertos (Fase 7) |
| [e2e-guide.md](./e2e-guide.md) | Como rodar e adicionar testes E2E Playwright (Fase 8) |
| `tests/factories.py` | Factories factory-boy para os 5 modelos principais |
| `tests/test_db_constraints.py` | 8 testes de constraints de banco (Fase 6) |
| `tests/test_error_scenarios.py` | 16 testes de error path em 5 endpoints (Fase 7) |
| `tests/e2e/` | Suite E2E Playwright (Fase 8) |
| `.coveragerc` | Configuração de cobertura + fail_under |
| `pytest.ini` | Configuração de pytest + markers |
| `.github/workflows/full-test-suite.yml` | CI: suite completa + coverage comment em PRs |
| `.github/workflows/e2e-nightly.yml` | CI: E2E em push para main + nightly |
