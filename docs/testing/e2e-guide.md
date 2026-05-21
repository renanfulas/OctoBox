# Guia de Testes E2E — OctoBox

> **Fase 8 do plano de qualidade** (2026-05-21).
> Playwright + pytest-playwright. 1 teste POC cobrindo o fluxo de login.

---

## Stack

| Componente | Versão | Papel |
|---|---|---|
| `pytest-playwright` | 0.5.2 | Integração pytest ↔ Playwright |
| `playwright` (dep transitiva) | ≥ 1.38 | Driver de browser |
| `pytest-django` | 4.12.0 | `live_server` fixture |
| Chromium | latest (CI) | Browser padrão |

---

## Como rodar localmente

```bash
# 1. Instalar dependências de teste (incluindo pytest-playwright)
pip install -r requirements_test.txt

# 2. Instalar binário do browser (só precisa fazer uma vez)
playwright install chromium

# 3. Rodar os testes E2E com servidor real
python -m pytest tests/e2e/ --create-db --migrations -v

# 4. Rodar em modo headed (browser visível — ótimo para debug)
python -m pytest tests/e2e/ --create-db --migrations --headed -v

# 5. Rodar em modo slow-motion (ação por ação) para inspecionar
python -m pytest tests/e2e/ --create-db --migrations --slowmo=500 -v
```

> **Por que `--create-db --migrations`?**
> Os testes E2E precisam do schema `box_test` criado via `migrate_schemas`.
> O `addopts` padrão usa `--nomigrations` (suficiente para testes unitários),
> então E2E precisa sobrescrever.

---

## Estrutura de arquivos

```
tests/e2e/
├── __init__.py
├── conftest.py          ← fixtures session-scoped (e2e_owner_credentials, base_url)
└── test_login_e2e.py    ← POC: fluxo de login do funcionário
```

---

## Como adicionar um novo teste E2E

### 1. Criar o arquivo

```python
# tests/e2e/test_meu_fluxo_e2e.py

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_meu_fluxo_critico(page: Page, live_server, e2e_owner_credentials):
    """
    Descreva o fluxo testado e por que ele é crítico.
    """
    creds = e2e_owner_credentials

    # 1. Login (reutilize o helper se for necessário estar autenticado)
    page.goto(f'{live_server.url}/login/funcionario/')
    page.locator('#id_username').fill(creds['username'])
    page.locator('#id_password').fill(creds['password'])
    page.locator('button[type="submit"]').click()
    page.wait_for_url('**/operacao/**', timeout=15_000)

    # 2. Navegar para o fluxo a testar
    page.goto(f'{live_server.url}/meu-fluxo/')

    # 3. Interagir com a UI
    page.locator('#meu-botao').click()

    # 4. Verificar resultado
    expect(page.locator('[data-slot="resultado"]')).to_contain_text('Sucesso')
```

### 2. Checklist antes de abrir PR

- [ ] Teste marcado com `@pytest.mark.e2e`
- [ ] Teste marcado com `@pytest.mark.django_db(transaction=True)`
- [ ] Assertions usam `expect()` quando possível (retry automático do Playwright)
- [ ] `timeout` explícito em `wait_for_url()` e `wait_for_selector()` (default 30s é muito)
- [ ] Teste roda em < 30s em headless
- [ ] Comentário docstring explica o cenário e por que é crítico

---

## Fixtures disponíveis

### `page` (pytest-playwright)
Página Playwright limpa por teste. Fornecida automaticamente pelo plugin.

### `live_server` (pytest-django)
Servidor Django real rodando em thread separada.
URL disponível em `live_server.url` (ex.: `http://localhost:12345`).

### `base_url` (tests/e2e/conftest.py)
Equivale a `live_server.url`. Configurado como URL base do Playwright,
então `page.goto('/login/')` funciona sem precisar de `f'{live_server.url}/login/'`.

### `e2e_owner_credentials` (tests/e2e/conftest.py)
Dicionário `{'username': '...', 'password': '...'}` de um usuário Owner
com Membership no Box de teste. Session-scoped — criado uma vez por sessão.

---

## Como criar fixtures de outros papéis

```python
# tests/e2e/conftest.py — adicione ao lado do e2e_owner_credentials

@pytest.fixture(scope='session')
def e2e_coach_credentials(test_tenant, django_db_blocker):
    username = '__e2e_coach__'
    password = 'E2E-senha-coach-456'

    with django_db_blocker.unblock():
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        from django.core.management import call_command
        from access.roles import ROLE_COACH
        from control.models import Membership

        User = get_user_model()
        call_command('bootstrap_roles', verbosity=0)

        user, _ = User.objects.get_or_create(
            username=username,
            defaults={'email': 'e2e-coach@example.test'},
        )
        user.set_password(password)
        user.save()
        user.groups.add(Group.objects.get(name=ROLE_COACH))

        Membership.objects.get_or_create(
            user=user,
            box=test_tenant,
            defaults={'role': Membership.Role.COACH, 'is_primary_box': True}
        )

    return {'username': username, 'password': password}
```

---

## CI — onde os testes rodam

| Workflow | Trigger | Inclui E2E? |
|---|---|---|
| `full-test-suite.yml` | Todo PR + push para main | ❌ (`tests/e2e/` ignorado) |
| `order-dependence-check.yml` | Todo PR + push para main | ❌ |
| `e2e-nightly.yml` | Push para main + cron 03:00 UTC | ✅ |

**Para rodar E2E manualmente em CI:**
```bash
gh workflow run e2e-nightly.yml
```

---

## Decisões técnicas

### Por que não E2E em todo PR?
Playwright precisa de `playwright install --with-deps chromium` (~150 MB, ~2 min em cold).
Cada teste E2E leva 10-30s. Para uma suite de 20 testes, isso seria ~10 min extras em todo PR.
O nightly garante cobertura sem travar o ciclo de revisão.

### Por que `transaction=True` no teste?
`live_server` usa um servidor em thread separada. Sem `transaction=True`, os dados criados
pelo fixture não são commitados e o servidor não os vê. Com `transaction=True`, os dados
são commitados antes da requisição HTTP chegar.

### Por que `scope='session'` no `e2e_owner_credentials`?
Criar usuário + bootstrap_roles + Membership a cada teste levaria ~1s de setup.
Como o live_server também é session-scoped, os dados persistem para toda a sessão E2E.

### Por que Chromium e não Firefox/WebKit?
Menor download, maior estabilidade em CI headless. Para testar compatibilidade
cross-browser, adicionar `--browser firefox` e `--browser webkit` ao comando pytest.

---

## Referências

- Código: `tests/e2e/`
- CI: `.github/workflows/e2e-nightly.yml`
- Playwright docs: https://playwright.dev/python/
- pytest-playwright: https://pypi.org/project/pytest-playwright/
- Plano de qualidade: `docs/testing/quality-plan-prompt.md` (Fase 8)
