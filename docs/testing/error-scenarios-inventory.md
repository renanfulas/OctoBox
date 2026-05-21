# Inventário de Cenários de Erro — OctoBox

> **Gerado em:** Fase 7 do plano de qualidade de testes (2026-05-21).
> **Baseline anterior:** 11 assertions de erro (4xx/5xx) em toda a suite.
> **Após Fase 7:** 27 assertions (+16 novas em `tests/test_error_scenarios.py`).

---

## Como ler esta tabela

| Coluna | Significado |
|---|---|
| Endpoint | Nome da URL (Django `reverse()`) |
| Método | HTTP method aceito |
| Cenário | Condição que provoca o erro |
| Status esperado | HTTP status que o sistema DEVE retornar |
| Testado? | ✅ tem teste em `test_error_scenarios.py`, 🔲 identificado, sem teste ainda |

---

## Endpoints cobertos — `tests/test_error_scenarios.py`

### 1. `stripe-webhook` — `/financeiro/stripe/webhook/`

Caminho público (bypassa TenantBySessionMiddleware). Recebe POST da Stripe.

| Cenário | Status | Testado? |
|---|---|---|
| GET (método errado) | 405 | ✅ |
| POST com assinatura Stripe inválida | 400 | ✅ |
| POST com `event_id` já existente (duplicata) | 200 `Duplicate event` | ✅ |

### 2. `api-v1-payment-link` — `/api/v1/finance/payment-link/<payment_id>/`

Rota privada. Gera link de checkout Stripe para compartilhar manualmente.

| Cenário | Status | Testado? |
|---|---|---|
| Usuário anônimo | 302 → `/login/` | ✅ |
| `payment_id` inexistente | 404 | ✅ |
| Pagamento já quitado (`status=PAID`) | 400 | ✅ |
| Falha no `create_checkout_session` (provider erro) | 500 | 🔲 |

### 3. `api-v1-finance-freeze` — `/api/v1/finance/freeze-student/`

Rota privada (LoginRequired). Congela aluno por N dias, empurrando vencimentos.

| Cenário | Status | Testado? |
|---|---|---|
| Usuário anônimo | 302 → `/login/` | ✅ |
| `days=0` ou `student_id` ausente | 400 | ✅ |
| `student_id` inexistente | 404 | ✅ |

### 4. `attendance-action` — `/operacao/presenca/<id>/<action>/`

Rota privada (LoginRequired + COACH). Aplica check-in / check-out / absent.

| Cenário | Status | Testado? |
|---|---|---|
| Usuário anônimo | 302 → `/login/` | ✅ |
| Papel errado (MANAGER em rota exclusiva de COACH) | 403 | ✅ |
| `attendance_id` inexistente | 404 | ✅ |
| `action` fora do conjunto permitido | 302 + flash error | 🔲 |

### 5. `reception-payment-action` — `/operacao/recepcao/pagamento/<id>/acao/`

Rota privada (LoginRequired + OWNER/RECEPTION). Confirma pagamento no balcão.

| Cenário | Status | Testado? |
|---|---|---|
| Usuário anônimo | 302 → `/login/` | ✅ |
| Papel errado (COACH em rota exclusiva de OWNER/RECEPTION) | 403 | ✅ |
| `payment_id` inexistente | 404 | ✅ |
| Formulário inválido (campos obrigatórios vazios) | 302 + flash error | ✅ |

---

## Endpoints identificados — sem cobertura de erro ainda

Estes endpoints têm apenas happy-path testado. Candidatos para Fase 7+.

| Endpoint | Erros críticos sem teste |
|---|---|
| `finance-center` | 401 anônimo (testa 200, não testa redirect) |
| `api-v1-finance-payments-bulk` | 403 sem role, 400 quando todos os itens falham |
| `payment-enrollment-link` | 403 papel errado, 404 payment ou enrollment não existe |
| `finance-communication-action` | 400 formulário inválido, 403 papel errado |
| `manager-intake-contact` | 404 intake inexistente, 429 rate limit |
| `finance-report-export` | 403 papel errado (só testa 429 rate limit) |

---

## Cobertura por categoria (toda a suite)

| Categoria | Antes Fase 7 | Após Fase 7 |
|---|---|---|
| 400 Bad Request | 4 | 7 |
| 401 / 302 para login | 0 | 4 |
| 403 Forbidden | 5 | 9 |
| 404 Not Found | 2 | 7 |
| 405 Method Not Allowed | 0 | 1 |
| 429 Too Many Requests | 4 | 4 |
| 500 / 502 provider error | 0 | 0 |
| **Total** | **15\*** | **32** |

\* Inclui assertions em `test_dashboard.py`, `test_operations.py`, `test_security_guards.py`, `test_manager_workspace_toggle.py`, `test_wod_template_archive.py`, `student_app/tests.py`, `student_identity/tests.py`.

---

## Como adicionar novos testes de erro

```python
# Padrão para endpoints privados com role check:
def test_<endpoint>_returns_403_for_<wrong_role>(self):
    self.client.force_login(self.<wrong_role_user>)
    response = self.client.post(reverse('<endpoint-name>', args=[...]), data={...})
    self.assertEqual(response.status_code, 403)

# Padrão para 404:
def test_<endpoint>_returns_404_for_nonexistent_<resource>(self):
    self.client.force_login(self.<authorized_user>)
    response = self.client.get(reverse('<endpoint-name>', args=[999_999]))
    self.assertEqual(response.status_code, 404)

# Padrão para 302 anônimo:
def test_<endpoint>_anonymous_redirects_to_login(self):
    response = self.client.get(reverse('<endpoint-name>', args=[...]))
    self.assertEqual(response.status_code, 302)
    self.assertIn('/login/', response['Location'])
```

---

## Referências

- Implementação dos testes: `tests/test_error_scenarios.py`
- Middleware de tenant: `control/middleware.py` — `TenantBySessionMiddleware`
- Mixin de permissão: `access/permissions/mixins.py` — `RoleRequiredMixin`
- Plano de qualidade: `docs/testing/quality-plan-prompt.md` (Fase 7)
